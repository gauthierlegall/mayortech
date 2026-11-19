"""Explicit human dossier properties, separate from extracted/accepted facts.

This additive view covers the photographed Notion columns. Empty properties stay
empty; a generic budget or a delivery date never becomes an estimate/deadline.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re

from .documents import DocumentRepository
from .domain import DomainError, canonical_json, require_text, utc_now


FIELDS = [
    {"key": "name", "label": "Dossier", "type": "text"},
    {"key": "category", "label": "Catégorie", "type": "text"},
    {"key": "estimated_cost", "label": "Coût estimé", "type": "money"},
    {"key": "actual_cost", "label": "Coût réel", "type": "money"},
    {"key": "request_date", "label": "Date demande", "type": "date"},
    {"key": "requester", "label": "Demandeur", "type": "text"},
    {"key": "contractor", "label": "Entreprise", "type": "text"},
    {"key": "location", "label": "Lieu", "type": "text"},
    {"key": "notes", "label": "Notes", "type": "long_text"},
    {"key": "observation", "label": "Observation", "type": "long_text"},
    {"key": "attachments", "label": "Pièces jointes", "type": "files"},
    {"key": "priority", "label": "Priorité", "type": "choice"},
    {"key": "service_owner", "label": "Service / Responsable", "type": "text"},
    {"key": "status", "label": "Statut", "type": "choice"},
    {"key": "deadline", "label": "Échéance", "type": "date"},
]
EDITABLE = {row["key"]: row for row in FIELDS if row["type"] != "files"}
STATUS_LABELS = {
    "active": "En cours",
    "in_progress": "En cours",
    "planned": "À traiter",
    "on_hold": "En attente",
    "completed": "Terminé",
    "closed": "Terminé",
    "blocked": "Bloqué",
    "cancelled": "Annulé",
    "pending": "À traiter",
}
STATUS_CODES = {
    "À traiter": "planned",
    "En cours": "active",
    "En attente": "on_hold",
    "Terminé": "completed",
    "Bloqué": "blocked",
    "Annulé": "cancelled",
}
PRIORITIES = ("", "Urgente", "Haute", "Normale", "Basse")


def _validated(key, value):
    if key not in EDITABLE or not isinstance(value, str):
        raise DomainError("invalid_input", "Une propriété connue et une valeur textuelle sont attendues.")
    field = EDITABLE[key]
    value = require_text(
        value,
        key,
        maximum=40000 if field["type"] == "long_text" else 300 if key == "name" else 500,
        empty=True,
    )
    if field["type"] != "long_text":
        value = value.strip()
        if value and not value.isprintable():
            raise DomainError("invalid_input", f"{field['label']} doit tenir sur une ligne.")
    if key == "name" and not value:
        raise DomainError("invalid_input", "Le dossier doit conserver un titre.")
    if field["type"] == "date" and value:
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            raise DomainError(
                "invalid_input", f"{field['label']} doit être une date valide au format AAAA-MM-JJ."
            ) from None
    if field["type"] == "money" and value:
        value = re.sub(r"[ \u00a0\u202f]", "", value).replace(",", ".")
        if not re.fullmatch(r"\d{1,12}(?:\.\d{1,2})?", value):
            raise DomainError(
                "invalid_input",
                "Le coût doit être un montant positif en euros, avec deux décimales au maximum.",
            )
        try:
            value = format(Decimal(value).quantize(Decimal("0.01")), "f")
        except InvalidOperation:
            raise DomainError("invalid_input", "Le montant est invalide.") from None
    if key == "priority" and value not in PRIORITIES:
        raise DomainError("invalid_input", "Choisissez une priorité proposée.")
    if key == "status" and value not in STATUS_CODES:
        raise DomainError("invalid_input", "Choisissez un statut proposé.")
    return value


class ProjectProfileService:
    def __init__(self, repo):
        self.repo = repo
        self.documents = DocumentRepository(repo)
        with repo._lock:
            repo._db.execute("""CREATE TABLE IF NOT EXISTS project_properties (
                tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0,values_json TEXT NOT NULL DEFAULT '{}',
                origins_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT,
                PRIMARY KEY(tenant_id,project_id),
                FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id))""")

    @staticmethod
    def _actor(tenant, actor, action):
        if (
            not isinstance(actor, dict)
            or actor.get("tenant_id") != tenant
            or actor.get("permissions", {}).get("workspace", {}).get(action) is not True
        ):
            raise DomainError("forbidden", "Votre accès ne permet pas cette opération sur ce dossier.")
        return require_text(actor.get("actor_id"), "actor_id", maximum=1000)

    def _get(self, tenant, project_id, actor):
        from .project_access import access_scope
        scope = access_scope(self.repo, actor)
        scope.require_project_contents(project_id)
        memory = scope.sanitize_memory(self.repo.get_memory(tenant, project_id))
        project = memory["project"]
        row = self.repo._db.execute(
            "SELECT * FROM project_properties WHERE tenant_id=? AND project_id=?", (tenant, project_id)
        ).fetchone()
        stored, origins = (
            (json.loads(row["values_json"]), json.loads(row["origins_json"])) if row else ({}, {})
        )
        values = {key: "" for key in EDITABLE}
        provenance = {key: {"kind": "unset"} for key in EDITABLE}
        # Aliases are explicit semantic matches only. Never map budget_raw to an
        # estimate or delivery_date to the distinct photographed deadline field.
        aliases = {"service_owner": ("service_owner", "owner")}
        for key in EDITABLE:
            if key in {"name", "status", "notes", "observation"}:
                continue
            facts = [fact for fact in memory["facts"] if fact["field"] in aliases.get(key, (key,))]
            if facts and isinstance(facts[-1].get("value"), str):
                fact = facts[-1]
                values[key] = fact["value"]
                provenance[key] = {
                    "kind": "confirmed_fact",
                    "source_id": fact["source_id"],
                    "candidate_id": fact["id"],
                }
        values.update(stored)
        provenance.update(origins)
        # Title and status always read the canonical project, even if another
        # authorized surface changed them since this panel last saved.
        values["name"] = project["name"]
        values["status"] = STATUS_LABELS.get(project["status"], project["status"])
        for key in ("name", "status"):
            provenance.setdefault(key, {"kind": "project"})
            if provenance[key]["kind"] == "unset":
                provenance[key] = {"kind": "project"}
        documents = [
            item for item in self.documents.list_project(tenant, project_id, actor=actor) if item["kind"] == "attachment"
        ]
        return {
            "project_id": project_id,
            "revision": row["revision"] if row else 0,
            "project_revision": project["revision"],
            "values": values,
            "origins": provenance,
            "fields": FIELDS,
            "documents": documents,
            "can_edit": actor.get("permissions", {}).get("workspace", {}).get("write") is True,
            "updated_at": row["updated_at"] if row else None,
            "policy": "human_properties_separate_from_confirmed_facts",
        }

    def get(self, tenant, project_id, actor):
        self._actor(tenant, actor, "read")
        with self.repo._lock:
            return self._get(tenant, project_id, actor)

    def update(self, tenant, project_id, actor, *, expected_revision, expected_project_revision, changes):
        from .project_access import access_scope
        access_scope(self.repo, actor).require_project(project_id, write=True)
        actor_id = self._actor(tenant, actor, "write")
        if (
            type(expected_revision) is not int
            or expected_revision < 0
            or type(expected_project_revision) is not int
            or expected_project_revision < 0
        ):
            raise DomainError("invalid_input", "Les versions du dossier et des propriétés sont requises.")
        if not isinstance(changes, dict) or len(changes) > len(EDITABLE):
            raise DomainError("invalid_input", "Un ensemble borné de propriétés est attendu.")
        prepared = {key: _validated(key, value) for key, value in changes.items()}
        with self.repo._transaction() as db:
            access_scope(self.repo, actor).require_project_contents(project_id, write=True)
            before = self._get(tenant, project_id, actor)
            if (
                before["revision"] != expected_revision
                or before["project_revision"] != expected_project_revision
            ):
                raise DomainError(
                    "stale_revision",
                    "Le dossier a changé. Rechargez ses propriétés avant de réappliquer votre saisie.",
                )
            prepared = {key: value for key, value in prepared.items() if value != before["values"][key]}
            if not prepared:
                return before
            row = db.execute(
                "SELECT values_json,origins_json FROM project_properties WHERE tenant_id=? AND project_id=?",
                (tenant, project_id),
            ).fetchone()
            values, origins = (json.loads(row[0]), json.loads(row[1])) if row else ({}, {})
            text = (
                "Propriétés du dossier renseignées explicitement par une personne.\nCes propriétés ne valident aucune annonce reçue par mail.\n"
                + "\n".join(
                    f"{EDITABLE[key]['label']} : {value if value else '(effacé)'}"
                    for key, value in prepared.items()
                )
            )
            note = self.repo._insert_note(db, tenant, project_id, text, actor_id, "human_property")
            for key, value in prepared.items():
                values[key] = value
                origins[key] = {
                    "kind": "human_property",
                    "actor_id": actor_id,
                    "source_id": note["source_id"],
                    "updated_at": note["created_at"],
                }
            if "name" in prepared:
                db.execute(
                    "UPDATE projects SET name=? WHERE tenant_id=? AND id=?",
                    (prepared["name"], tenant, project_id),
                )
            if "status" in prepared:
                db.execute(
                    "UPDATE projects SET status=? WHERE tenant_id=? AND id=?",
                    (STATUS_CODES[prepared["status"]], tenant, project_id),
                )
            db.execute(
                """INSERT INTO project_properties(tenant_id,project_id,revision,values_json,origins_json,updated_at)
                       VALUES(?,?,?,?,?,?) ON CONFLICT(tenant_id,project_id) DO UPDATE SET
                       revision=excluded.revision,values_json=excluded.values_json,origins_json=excluded.origins_json,updated_at=excluded.updated_at""",
                (
                    tenant,
                    project_id,
                    expected_revision + 1,
                    canonical_json(values),
                    canonical_json(origins),
                    utc_now(),
                ),
            )
            self.repo._event(
                db,
                tenant,
                project_id,
                actor_id,
                "project.properties.updated",
                {
                    "fields": sorted(prepared),
                    "source_id": note["source_id"],
                    "properties_revision": expected_revision + 1,
                },
            )
            self.repo._audit(
                db,
                tenant,
                project_id,
                "project.properties.updated",
                actor_id,
                project_id,
                {
                    "fields": sorted(prepared),
                    "source_id": note["source_id"],
                    "properties_revision": expected_revision + 1,
                },
            )
            return self._get(tenant, project_id, actor)


def register_project_profile_routes(app, repo, tenant, actor, settings):
    from fastapi import Depends
    from pydantic import BaseModel, ConfigDict, Field

    class Update(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int = Field(ge=0, strict=True)
        expected_project_revision: int = Field(ge=0, strict=True)
        changes: dict[str, str] = Field(max_length=14)

    service = ProjectProfileService(repo)

    @app.get("/api/v1/projects/{project_id}/properties")
    def properties(project_id: str, current=Depends(actor)):
        return service.get(tenant, project_id, current)

    @app.patch("/api/v1/projects/{project_id}/properties")
    def update_properties(project_id: str, body: Update, current=Depends(actor)):
        return service.update(tenant, project_id, current, **body.model_dump())

    return service
