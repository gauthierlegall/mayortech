"""Jeu de démonstration entièrement inventé : aucun courrier municipal réel."""

PROJECTS = [
    ("TRV-2026-014", "Parvis de l'école des Alizés", "Sécurisation des cheminements et reprise du parvis.", "active"),
    ("TRV-2026-021", "Rue des Ajoncs", "Renouvellement du réseau pluvial et réfection de chaussée.", "active"),
    ("TRV-2026-008", "Salle du Rivage", "Rénovation énergétique de la salle associative.", "active"),
    ("TRV-2026-032", "Chemin de Kerbrume", "Mise en accessibilité de l'arrêt de transport.", "planned"),
    ("TRV-2026-017", "Vestiaires des Goélands", "Réhabilitation des vestiaires et ventilation.", "active"),
    ("TRV-2026-003", "Éclairage du port des Dunes", "Remplacement des luminaires et contrôle de réception.", "completed"),
]


def seed(repo, tenant):
    if repo.list_projects(tenant):
        return
    for index, (reference, name, description, status) in enumerate(PROJECTS):
        project = repo.create_project(tenant, reference, name, description=description, status=status)
        body = f"Bonjour,\n\nPoint de suivi du chantier {reference}.\nAvancement : {['Préparation du terrassement', 'Réseau pluvial posé à 60 %', 'Isolation des combles terminée', 'Études en cours', 'Ventilation en cours de pose', 'Travaux terminés, réserves levées'][index]}\nEntreprise : Entreprise Fictive {index + 1}\nBudget : {42000 + index * 18500} EUR HT\nLivraison : 2026-12-{index + 10:02d}\n\nCordialement,\nÉquipe de démonstration"
        source = repo.ingest_source(tenant, f"seed-{index}@demo.invalid", f"[{reference}] Point chantier", body, thread_id=f"thread-{index}", project_ref=reference, sender="suivi@entreprise-fictive.invalid", received_at="2026-11-12T08:30:00+00:00", metadata={"fictitious": True})
        facts = [("progress", body.split("Avancement : ")[1].split("\n")[0], "Avancement"), ("contractor", f"Entreprise Fictive {index + 1}", "Entreprise"), ("budget_raw", f"{42000 + index * 18500} EUR HT", "Budget")]
        for field, value, label in facts:
            candidate = repo.add_candidate(tenant, project["id"], source["id"], field, value, quote=f"{label} : {value}")
            repo.review_candidate(tenant, candidate["id"], "accept", actor_id="demo-initialisation")
        repo.add_note(tenant, project["id"], "Préserver l'accès des riverains pendant les interventions. Point à confirmer à la prochaine réunion.", actor_id="responsable-demo")
        if index == 0:
            summary = repo.create_summary(tenant, project["id"])
            repo.approve_summary(tenant, summary["id"], expected_content_hash=summary["content_hash"], expected_snapshot_hash=summary["snapshot_hash"], expected_project_revision=summary["snapshot_revision"], actor_id="responsable-demo")
            add_next_mail(repo, tenant, project)


def add_next_mail(repo, tenant, project=None):
    project = project or repo.list_projects(tenant)[0]
    reference = project["reference"]
    body = f"Bonjour,\n\nNouveau point pour {reference}.\nAvancement : Terrassement terminé, attente de validation du plan de circulation\nLivraison : 2026-12-18\nAction : Confirmer le cheminement piéton avec le service scolaire\n\nMerci,\nEntreprise Fictive 1"
    return repo.ingest_source(tenant, "next-mail-v1@demo.invalid", f"[{reference}] Nouveau point et livraison", body, thread_id="thread-0", project_ref=reference, sender="conducteur@entreprise-fictive.invalid", received_at="2026-11-14T09:15:00+00:00", metadata={"fictitious": True})
