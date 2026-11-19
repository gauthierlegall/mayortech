"""Operator-only invented corpus. Never reads a real mailbox or accepts uploads."""

import json
from email.message import EmailMessage
from travaux.config import Settings, ensure_public_demo_database
from travaux.demo import seed
from travaux.repository import Repository
from travaux.jobs import JobQueue
from travaux.importing import import_mail
from travaux.pipeline import process_one
from travaux.llm import DemoExtractor


def pdf():
    stream = b"BT /F1 12 Tf 50 750 Td (Parvis des Alizes - cheminement pieton maintenu.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(
        f"{pos:010d} 00000 n \n".encode() for pos in offsets[1:]
    )
    return data + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


def main():
    settings = Settings.from_env()
    if not settings.fixture_mode:
        raise ValueError("Fixtures reserved for demo modes")
    ensure_public_demo_database(settings)
    repo = Repository(settings.db_path)
    queue = JobQueue(settings.db_path)
    tenant = settings.tenant_id
    seed(repo, tenant)
    project = next(p for p in repo.list_projects(tenant) if p["reference"] == "TRV-2026-014")
    subjects = [
        (
            "Plan de circulation et accès à l’école",
            "Préparation du terrassement",
            "Confirmer le cheminement piéton avec le service scolaire",
        ),
        (
            "Réunion de chantier du lundi",
            "Terrassement terminé, cheminement protégé",
            "Prévoir une visite du parvis avec l’entreprise",
        ),
        (
            "Commande des barrières",
            "Signalisation temporaire en préparation",
            "Vérifier la livraison des barrières avant vendredi",
        ),
    ]
    sources = []
    for index, (subject, progress, action) in enumerate(subjects):
        mail = EmailMessage()
        mail["From"] = "Camille Le Gall <suivi@entreprise-fictive.invalid>"
        mail["To"] = "travaux@collectivite-fictive.invalid"
        mail["Subject"] = f"[TRV-2026-014] {subject}"
        mail["Message-ID"] = f"<parvis-exemple-04-{index}@demo.invalid>"
        mail["Date"] = f"{13 + index} Nov 2026 09:15:00 +0100"
        mail.set_content(
            f"Bonjour,\n\nVoici le point de suivi du parvis de l’école des Alizés.\n\nAvancement : {progress}\nAction : {action}\n\nNous maintenons les accès aux heures d’entrée et de sortie.\n\nBonne journée,\nCamille Le Gall\nConductrice de travaux\n"
        )
        if index == 0:
            mail.add_attachment(
                pdf(), maintype="application", subtype="pdf", filename="Plan de circulation.pdf"
            )
            mail.add_attachment(
                "Accès piéton maintenu côté médiathèque.\nBarrières posées avant 8 h 15.\n".encode(),
                maintype="text",
                subtype="plain",
                filename="Consignes accès.txt",
            )
            mail.set_boundary("travaux-parvis-exemple-04")
        imported = import_mail(
            repo,
            queue,
            tenant,
            mail.as_bytes(),
            metadata={"fictitious": True, "filename": f"parvis-{index + 1}.eml"},
        )
        sources.append(imported["source"]["id"])
    while process_one(queue, repo, DemoExtractor()):
        pass
    # Operator seeds only explicit actions with exact source evidence; the
    # evolving progress proposals remain available for human review.
    for candidate in repo.list_candidates(tenant, project_id=project["id"]):
        if candidate["field"].startswith("action.") and candidate["status"] == "pending":
            repo.review_candidate(tenant, candidate["id"], "accept", actor_id="demo-initialisation")
    print(
        json.dumps(
            {"project_id": project["id"], "source_ids": sources, "projects": len(repo.list_projects(tenant))}
        )
    )
    repo.close()


if __name__ == "__main__":
    main()
