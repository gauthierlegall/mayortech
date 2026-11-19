"""Operator-only additive fictional scenario. Never called by an HTTP route."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from .config import Settings, ensure_public_demo_database
from .documents import DocumentRepository
from .domain import DomainError, canonical_json, utc_now
from .importing import import_mail
from .jobs import JobQueue
from .repository import Repository

STORYLINE_ID = "lovable-travaux-v1"
MANIFEST_SHA256 = "bbeb8eb65fba682e7bc239bbb70c71dd656da99eff7039332ad77751f04351e9"
ACTOR = "demo-initialisation"


def _read_fixture(directory):
    directory = Path(directory).resolve()
    raw = (directory / "storyline.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise DomainError(
            "invalid_fixture", "Le manifeste du scénario ne correspond pas à sa version vérifiée."
        )
    fixture = json.loads(raw)
    assets = {}
    for name, digest in fixture["assets"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory):
            raise DomainError("invalid_fixture", "Chemin de fixture non autorisé.")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise DomainError(
                "invalid_fixture", "Un original du scénario a changé ; aucune donnée n’a été initialisée."
            )
        assets[name] = content
    return fixture, assets


def _public_marker(repo, tenant):
    try:
        marker = repo._db.execute(
            "SELECT mode,tenant_id,schema_version FROM public_demo_metadata WHERE singleton=1"
        ).fetchone()
    except sqlite3.OperationalError:
        marker = None
    if marker is None or tuple(marker) != ("public_demo", tenant, 1):
        raise DomainError(
            "forbidden",
            "Ce scénario est réservé à la base séparée de démonstration publique et à son périmètre.",
        )


def _operator_guard(repo, tenant, settings):
    if settings is None:
        return _public_marker(repo, tenant)
    if settings.tenant_id != tenant or Path(settings.db_path).resolve() != Path(repo.path).resolve():
        raise DomainError(
            "forbidden", "La configuration opérateur ne correspond pas à la base et au périmètre demandés."
        )
    if settings.mode == "public_demo":
        settings.validate_public_demo_connectors()
        return _public_marker(repo, tenant)
    if (
        settings.mode != "demo"
        or settings.llm != "demo"
        or settings.egress_approved
        or any(
            (
                settings.mistral_url,
                settings.mistral_model,
                settings.mistral_key,
                settings.appflowy_url,
            )
        )
    ):
        raise DomainError(
            "forbidden",
            "Seule une démonstration locale explicite, sans connexion externe, peut initialiser ce scénario.",
        )
    if repo._db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='public_demo_metadata'"
    ).fetchone():
        raise DomainError(
            "forbidden", "Une base marquée public_demo ne peut pas être ouverte comme démonstration locale."
        )


def _finish_fixture_jobs(db, tenant, ids, count):
    # Only jobs created inside this still-open transaction belong to this seed.
    # They were deterministically prepared here, with no LLM/network call.
    result = canonical_json(
        {
            "status": "fixture_prepared",
            "candidates": count,
            "warnings": ["Propositions fictives préparées par l’opérateur ; aucun appel LLM."],
        }
    )
    for job_id in ids:
        db.execute(
            "UPDATE jobs SET status='done',result=?,error=NULL WHERE tenant_id=? AND id=? AND status='queued'",
            (result, tenant, job_id),
        )


def _summary(repo, tenant, project_id, content, extra_citations=()):
    memory = repo.get_memory(tenant, project_id)
    citations = [proof for fact in memory["facts"] for proof in fact["evidence"]] + list(extra_citations)
    return repo.create_summary(
        tenant,
        project_id,
        content=content,
        citations=citations,
        actor_id=ACTOR,
        model="fixture-editorial-v1 — texte fictif préparé",
    )


def _catalogue(repo, tenant, project_id, mail_sources, attachments, assets):
    documents = DocumentRepository(repo)
    rows = []
    for version, key, amount, status, label in (
        (1, "m1", "4850.00", "validated", "Validé"),
        (2, "m6", "5120.00", "under_review", "En examen"),
    ):
        filename = f"devis-portail-v{version}.pdf"
        source = attachments[key]
        digest = hashlib.sha256(assets["documents/" + filename]).hexdigest()
        document = next(
            row
            for row in documents.list_project(tenant, project_id)
            if row["source_id"] == source["id"] and row["sha256"] == digest
        )
        status_source = mail_sources["m2"] if version == 1 else source["id"]
        status_quote = (
            "Nous confirmons le devis initial de 4 850,00 € HT."
            if version == 1
            else "Etat : En examen - ne remplace pas le devis valide"
        )
        evidence = {
            "version": {"source_id": source["id"], "quote": f"Devis AF-2026-184 - Version {version}"},
            "status": {"source_id": status_source, "quote": status_quote},
            "amount": {
                "source_id": source["id"],
                "quote": f"Montant total : {'4 850' if version == 1 else '5 120'},00 EUR HT",
            },
        }
        for proof in evidence.values():
            if proof["quote"] not in repo.get_source(tenant, proof["source_id"])["body"]:
                raise DomainError(
                    "invalid_evidence",
                    "Une déclaration documentaire n’est pas étayée par la source du scénario.",
                )
        rows.append(
            {
                "document_id": document["id"],
                "source_id": source["id"],
                "mail_source_id": mail_sources[key],
                "filename": filename,
                "family": "AF-2026-184",
                "version": version,
                "status": status,
                "status_label": label,
                "sha256": digest,
                "amount": {"amount": amount, "currency": "EUR", "basis": "HT"},
                "evidence": evidence,
            }
        )
    body = (
        "Catalogue documentaire fictif préparé par l’opérateur. Chaque déclaration conserve sa preuve exacte.\n"
        + json.dumps(rows, ensure_ascii=False, indent=2)
    )
    source = repo.ingest_source(
        tenant,
        "lovable-document-catalogue-v1@demo.invalid",
        "[TRV-2026-042] Catalogue documentaire du scénario fictif",
        body,
        project_ref="TRV-2026-042",
        sender="opérateur de démonstration",
        received_at="2026-11-15T09:00:00+00:00",
        metadata={
            "fictitious": True,
            "storyline_id": STORYLINE_ID,
            "source_kind": "demo_document_catalog",
            # The existing mailbox/doc inventories exclude note sources.
            # This is explicitly an operator documentary note, not a mail.
            "note_id": "fixture-document-catalogue-v1",
            "origin": "demo_fixture_catalog",
            "document_catalog": rows,
        },
    )
    repo.add_candidates(tenant, project_id, source["id"], [])
    return rows, source["id"]


def seed_storyline(repo, queue, tenant, fixture_dir, *, settings: Settings | None = None):
    """Atomically add four dossiers once; replays preserve every subsequent edit.

    Requires the public_demo marker, or explicit matching local demo settings.
    Never resets a dossier, authenticates fictional people, or changes a mode.
    """
    fixture, assets = _read_fixture(fixture_dir)
    if Path(queue.path).resolve() != Path(repo.path).resolve():
        raise DomainError(
            "invalid_input", "Le scénario exige la même base durable pour ses sources et ses traitements."
        )
    with repo._transaction() as db:
        _operator_guard(repo, tenant, settings)
        db.execute("""CREATE TABLE IF NOT EXISTS demo_storylines(
          tenant_id TEXT NOT NULL,storyline_id TEXT NOT NULL,manifest_sha256 TEXT NOT NULL,
          result_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(tenant_id,storyline_id))""")
        prior = db.execute(
            "SELECT manifest_sha256,result_json FROM demo_storylines WHERE tenant_id=? AND storyline_id=?",
            (tenant, STORYLINE_ID),
        ).fetchone()
        if prior:
            if prior["manifest_sha256"] != MANIFEST_SHA256:
                raise DomainError("conflict", "Une autre version de ce scénario est déjà initialisée.")
            return json.loads(prior["result_json"])
        occupied = {p["reference"].casefold() for p in repo.list_projects(tenant)}
        if any(p["reference"].casefold() in occupied for p in fixture["projects"]):
            raise DomainError(
                "conflict",
                "Une référence du scénario appartient déjà à un dossier existant ; aucune donnée n’est écrasée.",
            )
        projects = {
            item["key"]: repo.create_project(
                tenant,
                item["reference"],
                item["name"],
                description=item["description"],
                status=item["status"],
            )["id"]
            for item in fixture["projects"]
        }
        mail_sources, attachments, confirmed, pending, summaries = {}, {}, [], [], {}
        for phase in ("baseline", "revision"):
            for message in (m for m in fixture["messages"] if m["phase"] == phase):
                imported = import_mail(
                    repo,
                    queue,
                    tenant,
                    assets[message["filename"]],
                    metadata={
                        "fictitious": True,
                        "storyline_id": STORYLINE_ID,
                        "fixture_message": message["key"],
                        "filename": Path(message["filename"]).name,
                        "origin": "reconstructed_fictional_mail_from_user_scenario",
                    },
                )
                source = imported["source"]
                project_id = projects[message["project"]]
                if source["project_id"] != project_id:
                    raise DomainError(
                        "unmatched_source", "Le rattachement exact du courrier du scénario a échoué."
                    )
                mail_sources[message["key"]] = source["id"]
                candidates = repo.add_candidates(
                    tenant,
                    project_id,
                    source["id"],
                    [
                        {key: value for key, value in item.items() if key != "accepted"}
                        | {"origin": "demo_fixture"}
                        for item in message["candidates"]
                    ],
                )
                for definition, candidate in zip(message["candidates"], candidates):
                    if definition["accepted"]:
                        repo.review_candidate(tenant, candidate["id"], "accept", actor_id=ACTOR)
                    else:
                        pending.append(candidate["id"])
                    if candidate["field"].startswith("action."):
                        action = next(
                            a for a in message["native_actions"] if a["title"] == candidate["value"]
                        )
                        confirmed.append(
                            {
                                **action,
                                "candidate_id": candidate["id"],
                                "source_id": source["id"],
                                "project_id": project_id,
                                "field": candidate["field"],
                            }
                        )
                for child in imported["related_sources"]:
                    attachments[message["key"]] = child
                    repo.add_candidates(tenant, project_id, child["id"], [])
                _finish_fixture_jobs(db, tenant, imported["job_ids"], len(candidates))
            if phase == "baseline":
                for item in fixture["projects"]:
                    repo.add_note(
                        tenant,
                        projects[item["key"]],
                        "Note de démonstration préparée : " + item["note"],
                        actor_id=ACTOR,
                        origin="demo_fixture",
                    )
                initial = _summary(
                    repo,
                    tenant,
                    projects["portail"],
                    "Le remplacement du portail de l’école de Ker Avel est en cours. La livraison est confirmée au 18 novembre 2026. "
                    "Le devis initial AF-2026-184 version 1, de 4 850,00 EUR HT, a été validé dans le courriel du 5 novembre. "
                    "L’ouverture de 3,50 mètres et la finition verte sont confirmées. La fabrication est en cours ; le créneau reste à préciser. "
                    "Un cheminement provisoire doit être préparé pour les élèves.",
                )
                repo.approve_summary(
                    tenant,
                    initial["id"],
                    expected_content_hash=initial["content_hash"],
                    expected_snapshot_hash=initial["snapshot_hash"],
                    expected_project_revision=initial["snapshot_revision"],
                    actor_id=ACTOR,
                )
                summaries["portail_initial"] = initial["id"]
                for key in ("voirie", "gymnase", "parc"):
                    summaries[key] = repo.create_summary(
                        tenant, projects[key], actor_id=ACTOR, model="fixture-déterministe"
                    )["id"]
        catalogue, catalogue_id = _catalogue(
            repo, tenant, projects["portail"], mail_sources, attachments, assets
        )
        current = _summary(
            repo,
            tenant,
            projects["portail"],
            "Le remplacement du portail de l’école de Ker Avel est en cours. La date confirmée du dossier reste le 18 novembre 2026. "
            "Dans son courriel du 15 novembre, l’entreprise annonce le 25 novembre à cause d’un retard de thermolaquage : ce report reste à confirmer. "
            "Le devis initial AF-2026-184 version 1 reste validé à 4 850,00 EUR HT. Le devis révisé version 2, de 5 120,00 EUR HT, est en examen ; il ne remplace pas le devis validé. "
            "L’accès pour la visite préparatoire du vendredi 20 novembre doit être confirmé. La sécurisation de l’entrée et le cheminement provisoire sont en préparation.",
            # Cite the pending announcement without accepting it into confirmed memory.
            extra_citations=[
                {"source_id": mail_sources["m6"], "quote": "Livraison : 2026-11-25"},
                {
                    "source_id": attachments["m6"]["id"],
                    "quote": "Etat : En examen - ne remplace pas le devis valide",
                },
            ],
        )
        summaries["portail_current"] = current["id"]
        result = {
            "storyline_id": STORYLINE_ID,
            "manifest_hash": MANIFEST_SHA256,
            "projects": projects,
            "mail_sources": mail_sources,
            "document_catalog": catalogue,
            "catalog_source_id": catalogue_id,
            "confirmed_actions": confirmed,
            "pending_candidates": pending,
            "summary_ids": summaries,
            "native_seed": {
                projects[p["key"]]: {
                    "paragraphs": [p["note"]],
                    "actions": [a for a in confirmed if a["project_id"] == projects[p["key"]]],
                }
                for p in fixture["projects"]
            },
        }
        db.execute(
            "INSERT INTO demo_storylines VALUES(?,?,?,?,?)",
            (tenant, STORYLINE_ID, MANIFEST_SHA256, canonical_json(result), utc_now()),
        )
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Ajouter le scénario fictif Lovable sans réinitialiser les dossiers existants."
    )
    parser.add_argument("--fixture-dir", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.mode not in {"public_demo", "demo"}:
        parser.error(
            "Ce scénario exige public_demo et sa base séparée, ou demo local explicite sans connexion externe."
        )
    ensure_public_demo_database(settings)
    repo = Repository(settings.db_path)
    try:
        result = seed_storyline(
            repo, JobQueue(settings.db_path), settings.tenant_id, args.fixture_dir, settings=settings
        )
        print(json.dumps(result, ensure_ascii=False))
    finally:
        repo.close()


if __name__ == "__main__":
    main()
