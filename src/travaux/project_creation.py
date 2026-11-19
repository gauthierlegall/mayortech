"""Initial form values become explicit human statements with exact evidence."""

from .domain import DomainError, normalize_value, require_text


def create_with_profile(
    repo,
    tenant,
    actor,
    *,
    reference,
    name,
    description="",
    location="",
    contractor="",
    delivery_date="",
    owner="",
    commission_id="commission-3",
    specialization="travaux",
    visibility="standard",
):
    values = {
        "location": (location, "Localisation", "text"),
        "contractor": (contractor, "Entreprise", "text"),
        "delivery_date": (delivery_date, "Échéance prévue", "date"),
        "owner": (owner, "Responsable", "text"),
    }
    prepared = []
    for field, (value, label, kind) in values.items():
        value = require_text(value or "", field, maximum=200, empty=True).strip()
        if value and not value.isprintable():
            raise DomainError("invalid_input", "Les informations du chantier doivent tenir sur une ligne.")
        if value:
            prepared.append((field, normalize_value(kind, value), label, kind))
    with repo._transaction() as db:
        existing = db.execute(
            "SELECT id FROM projects WHERE tenant_id=? AND reference=? COLLATE NOCASE",
            (tenant, reference.strip()),
        ).fetchone()
        if existing:
            raise DomainError(
                "conflict",
                "Cette référence existe déjà. Ouvrez le chantier correspondant ou choisissez une autre référence.",
            )
        project = repo.create_project(
            tenant,
            reference,
            name,
            description=description,
            status="planned",
            commission_id=commission_id,
            specialization=specialization,
            visibility=visibility,
        )
        if prepared:
            text = "Informations renseignées lors de la création du chantier.\n" + "\n".join(
                f"{label} : {value}" for _, value, label, _ in prepared
            )
            note = repo.add_note(tenant, project["id"], text, actor_id=actor)
            for field, value, label, kind in prepared:
                candidate = repo.add_candidate(
                    tenant,
                    project["id"],
                    note["source_id"],
                    field,
                    value,
                    quote=f"{label} : {value}",
                    kind=kind,
                    origin="human_assertion",
                )
                repo.review_candidate(tenant, candidate["id"], "accept", actor_id=actor)
        return repo.get_project(tenant, project["id"])
