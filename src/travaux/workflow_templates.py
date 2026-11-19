"""Pre-seeded library of 10 certified municipal workflow templates for Plougastel-Daoulas."""

from __future__ import annotations
from typing import Any, Dict, List

from .workflow_engine import BpmnXmlBuilder


MUNICIPAL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "key": "urbanisme_ads",
        "name": "Instruction Permis de Construire (ADS)",
        "category": "urbanisme",
        "commission_id": "comm_urbanisme_cadre_vie",
        "description": "Circuit réglementaire d'instruction des autorisations d'urbanisme avec examen de complétude, consultation ABF, visa technique et signature de l'Adjoint.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Dépôt dossier ADS", "x": 80, "y": 140},
            {"id": "task_completude", "type": "userTask", "name": "Contrôle de complétude (Instructeur)", "role": "instructeur_ads", "commission": "urbanisme", "sla_hours": 48, "x": 200, "y": 120},
            {"id": "gate_completude", "type": "exclusiveGateway", "name": "Dossier complet ?", "x": 390, "y": 135},
            {"id": "task_pieces_manquantes", "type": "userTask", "name": "Demande de pièces complémentaires", "role": "instructeur_ads", "commission": "urbanisme", "sla_hours": 72, "x": 480, "y": 40},
            {"id": "task_abf", "type": "userTask", "name": "Consultation Architecte Bâtiments de France", "role": "abf_consultant", "commission": "urbanisme", "sla_hours": 96, "x": 480, "y": 200},
            {"id": "task_visa_adjoint", "type": "userTask", "name": "Visa Adjoint Urbanisme", "role": "adjoint_urbanisme", "commission": "urbanisme", "sla_hours": 48, "x": 680, "y": 200},
            {"id": "service_arrete_pdf", "type": "serviceTask", "name": "Génération Arrêté Municipal PDF", "action": "generate_decision_pdf", "x": 870, "y": 200},
            {"id": "service_scellement", "type": "serviceTask", "name": "Scellement Cryptographique SHA-256", "action": "seal_decision_hash", "x": 1060, "y": 200},
            {"id": "end_permis", "type": "endEvent", "name": "Arrêté notifié et affiché", "x": 1260, "y": 220},
        ],
        "edges": [
            {"id": "flow_1", "sourceRef": "start", "targetRef": "task_completude"},
            {"id": "flow_2", "sourceRef": "task_completude", "targetRef": "gate_completude"},
            {"id": "flow_incomplet", "sourceRef": "gate_completude", "targetRef": "task_pieces_manquantes", "condition": "pieces_completes == False"},
            {"id": "flow_complet", "sourceRef": "gate_completude", "targetRef": "task_abf", "condition": "pieces_completes == True"},
            {"id": "flow_recomplete", "sourceRef": "task_pieces_manquantes", "targetRef": "task_completude"},
            {"id": "flow_abf_to_visa", "sourceRef": "task_abf", "targetRef": "task_visa_adjoint"},
            {"id": "flow_visa_to_pdf", "sourceRef": "task_visa_adjoint", "targetRef": "service_arrete_pdf"},
            {"id": "flow_pdf_to_seal", "sourceRef": "service_arrete_pdf", "targetRef": "service_scellement"},
            {"id": "flow_seal_to_end", "sourceRef": "service_scellement", "targetRef": "end_permis"},
        ],
    },
    {
        "key": "marches_cao",
        "name": "Commission d'Appel d'Offres (Marchés Publics)",
        "category": "finances",
        "commission_id": "comm_finances_administration",
        "description": "Procédure d'adjudication des marchés publics formalisés avec examen juridique, ouverture des plis et attribution par les élus de la CAO.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Lancement consultation", "x": 80, "y": 140},
            {"id": "task_cahier_charges", "type": "userTask", "name": "Vérification CCTP / RC", "role": "responsable_marches", "commission": "finances", "sla_hours": 72, "x": 200, "y": 120},
            {"id": "gate_seuil", "type": "exclusiveGateway", "name": "Montant > 40 000 € ?", "x": 390, "y": 135},
            {"id": "task_procedure_adaptee", "type": "userTask", "name": "Procédure MAPA simplifiée", "role": "chef_service_finances", "commission": "finances", "sla_hours": 48, "x": 480, "y": 40},
            {"id": "task_seance_cao", "type": "userTask", "name": "Séance formelle des Élus de la CAO", "role": "adjoint_finances", "commission": "finances", "sla_hours": 72, "x": 480, "y": 200},
            {"id": "service_pv_cao", "type": "serviceTask", "name": "Génération PV d'adjudication", "action": "generate_decision_pdf", "x": 700, "y": 200},
            {"id": "service_seal_cao", "type": "serviceTask", "name": "Scellement électronique SHA-256", "action": "seal_decision_hash", "x": 890, "y": 200},
            {"id": "end_marche", "type": "endEvent", "name": "Marché notifié au titulaire", "x": 1090, "y": 220},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_cahier_charges"},
            {"id": "f2", "sourceRef": "task_cahier_charges", "targetRef": "gate_seuil"},
            {"id": "f_mapa", "sourceRef": "gate_seuil", "targetRef": "task_procedure_adaptee", "condition": "montant_ht <= 40000"},
            {"id": "f_cao", "sourceRef": "gate_seuil", "targetRef": "task_seance_cao", "condition": "montant_ht > 40000"},
            {"id": "f_mapa_end", "sourceRef": "task_procedure_adaptee", "targetRef": "service_pv_cao"},
            {"id": "f_cao_pv", "sourceRef": "task_seance_cao", "targetRef": "service_pv_cao"},
            {"id": "f_pv_seal", "sourceRef": "service_pv_cao", "targetRef": "service_seal_cao"},
            {"id": "f_seal_end", "sourceRef": "service_seal_cao", "targetRef": "end_marche"},
        ],
    },
    {
        "key": "ccas_aide_sociale",
        "name": "CCAS — Aide Sociale Facultative d'Urgence",
        "category": "ccas",
        "commission_id": "comm_solidarites_enfance",
        "description": "Instruction confidentielle de secours d'urgence communal, évaluation du reste à vivre et passage en commission permanente.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Demande de secours citoyen", "x": 80, "y": 140},
            {"id": "task_accueil_social", "type": "userTask", "name": "Entretien confidentiel travailleur social", "role": "assistante_sociale", "commission": "social", "sla_hours": 24, "x": 200, "y": 120},
            {"id": "gate_urgence", "type": "exclusiveGateway", "name": "Urgence vitale ?", "x": 390, "y": 135},
            {"id": "task_secours_immediat", "type": "userTask", "name": "Bons d'urgence alimentaire DGS", "role": "dgs", "commission": "social", "sla_hours": 4, "x": 480, "y": 40},
            {"id": "task_commission_ccas", "type": "userTask", "name": "Commission permanente CCAS", "role": "adjoint_social", "commission": "social", "sla_hours": 72, "x": 480, "y": 200},
            {"id": "service_mandatement", "type": "serviceTask", "name": "Génération mandat trésorier", "action": "generate_decision_pdf", "x": 700, "y": 120},
            {"id": "service_seal_ccas", "type": "serviceTask", "name": "Scellement anonymisé SHA-256", "action": "seal_decision_hash", "x": 890, "y": 120},
            {"id": "end_ccas", "type": "endEvent", "name": "Aide décaissée en régie", "x": 1090, "y": 140},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_accueil_social"},
            {"id": "f2", "sourceRef": "task_accueil_social", "targetRef": "gate_urgence"},
            {"id": "f_urg", "sourceRef": "gate_urgence", "targetRef": "task_secours_immediat", "condition": "urgence == True"},
            {"id": "f_ord", "sourceRef": "gate_urgence", "targetRef": "task_commission_ccas", "condition": "urgence == False"},
            {"id": "f_urg_mandat", "sourceRef": "task_secours_immediat", "targetRef": "service_mandatement"},
            {"id": "f_ord_mandat", "sourceRef": "task_commission_ccas", "targetRef": "service_mandatement"},
            {"id": "f_mandat_seal", "sourceRef": "service_mandatement", "targetRef": "service_seal_ccas"},
            {"id": "f_seal_end", "sourceRef": "service_seal_ccas", "targetRef": "end_ccas"},
        ],
    },
    {
        "key": "subventions_associations",
        "name": "Subventions aux Associations Culturelles & Sportives",
        "category": "culture",
        "commission_id": "comm_culture_patrimoine",
        "description": "Instruction de la campagne annuelle de subventions communales avec rapport financier, arbitrage d'adjoint et délibération de conseil.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Dépôt CERFA 12156*06", "x": 80, "y": 140},
            {"id": "task_controle_comptable", "type": "userTask", "name": "Contrôle bilans & RIB (Service Culture)", "role": "coordinateur_culturel", "commission": "culture", "sla_hours": 96, "x": 200, "y": 120},
            {"id": "task_avis_commission", "type": "userTask", "name": "Examen Commission Culture & Sports", "role": "adjoint_culture", "commission": "culture", "sla_hours": 72, "x": 420, "y": 120},
            {"id": "service_deliberation", "type": "serviceTask", "name": "Compilation Projet de Délibération", "action": "generate_decision_pdf", "x": 640, "y": 120},
            {"id": "task_vote_conseil", "type": "userTask", "name": "Vote du Conseil Municipal", "role": "maire", "commission": "general", "sla_hours": 120, "x": 850, "y": 120},
            {"id": "service_seal_subvention", "type": "serviceTask", "name": "Scellement acte budgétaire", "action": "seal_decision_hash", "x": 1060, "y": 120},
            {"id": "end_subvention", "type": "endEvent", "name": "Notification & Convention signée", "x": 1260, "y": 140},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_controle_comptable"},
            {"id": "f2", "sourceRef": "task_controle_comptable", "targetRef": "task_avis_commission"},
            {"id": "f3", "sourceRef": "task_avis_commission", "targetRef": "service_deliberation"},
            {"id": "f4", "sourceRef": "service_deliberation", "targetRef": "task_vote_conseil"},
            {"id": "f5", "sourceRef": "task_vote_conseil", "targetRef": "service_seal_subvention"},
            {"id": "f6", "sourceRef": "service_seal_subvention", "targetRef": "end_subvention"},
        ],
    },
    {
        "key": "voirie_arretes",
        "name": "Arrêté de Circulation & Travaux de Voirie",
        "category": "voirie",
        "commission_id": "comm_urbanisme_cadre_vie",
        "description": "Réglementation temporaire du stationnement et de la circulation pour chantiers de voirie, déménagements ou événements sur le domaine public.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Demande d'occupation du domaine", "x": 80, "y": 140},
            {"id": "task_avis_ctm", "type": "userTask", "name": "Avis technique Centre Technique Municipal", "role": "chef_ctm", "commission": "voirie", "sla_hours": 48, "x": 200, "y": 120},
            {"id": "task_police_municipale", "type": "userTask", "name": "Contrôle Police Municipale (Sécurité)", "role": "chef_police_municipale", "commission": "securite", "sla_hours": 24, "x": 420, "y": 120},
            {"id": "service_arrete", "type": "serviceTask", "name": "Génération Arrêté de Police", "action": "generate_decision_pdf", "x": 640, "y": 120},
            {"id": "task_signature_elu", "type": "userTask", "name": "Signature Adjoint aux Travaux", "role": "adjoint_travaux", "commission": "voirie", "sla_hours": 24, "x": 850, "y": 120},
            {"id": "service_affichage", "type": "serviceTask", "name": "Publication au Registre & Affichage", "action": "publish_to_display", "x": 1060, "y": 120},
            {"id": "end_voirie", "type": "endEvent", "name": "Pose des panneaux d'interdiction", "x": 1260, "y": 140},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_avis_ctm"},
            {"id": "f2", "sourceRef": "task_avis_ctm", "targetRef": "task_police_municipale"},
            {"id": "f3", "sourceRef": "task_police_municipale", "targetRef": "service_arrete"},
            {"id": "f4", "sourceRef": "service_arrete", "targetRef": "task_signature_elu"},
            {"id": "f5", "sourceRef": "task_signature_elu", "targetRef": "service_affichage"},
            {"id": "f6", "sourceRef": "service_affichage", "targetRef": "end_voirie"},
        ],
    },
    {
        "key": "culture_avel_vor",
        "name": "Réservation de l'Espace Culturel Avel Vor",
        "category": "culture",
        "commission_id": "comm_culture_patrimoine",
        "description": "Instruction des demandes d'occupation de l'Espace Avel Vor par les associations ou particuliers avec vérification technique et régie.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Option de réservation en ligne", "x": 80, "y": 140},
            {"id": "task_faisabilite_regie", "type": "userTask", "name": "Contrôle technique régisseur Avel Vor", "role": "regisseur_avel_vor", "commission": "culture", "sla_hours": 48, "x": 200, "y": 120},
            {"id": "gate_conflit", "type": "exclusiveGateway", "name": "Salle disponible ?", "x": 390, "y": 135},
            {"id": "task_rejet_date", "type": "userTask", "name": "Proposition date alternative", "role": "regisseur_avel_vor", "commission": "culture", "sla_hours": 24, "x": 480, "y": 40},
            {"id": "task_validation_tarif", "type": "userTask", "name": "Calcul redevance & caution", "role": "service_finances", "commission": "finances", "sla_hours": 48, "x": 480, "y": 200},
            {"id": "service_convention", "type": "serviceTask", "name": "Édition Convention de mise à disposition", "action": "generate_decision_pdf", "x": 700, "y": 200},
            {"id": "end_avel_vor", "type": "endEvent", "name": "Réservation confirmée au planning", "x": 920, "y": 220},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_faisabilite_regie"},
            {"id": "f2", "sourceRef": "task_faisabilite_regie", "targetRef": "gate_conflit"},
            {"id": "f_non", "sourceRef": "gate_conflit", "targetRef": "task_rejet_date", "condition": "disponible == False"},
            {"id": "f_oui", "sourceRef": "gate_conflit", "targetRef": "task_validation_tarif", "condition": "disponible == True"},
            {"id": "f_tarif_conv", "sourceRef": "task_validation_tarif", "targetRef": "service_convention"},
            {"id": "f_conv_end", "sourceRef": "service_convention", "targetRef": "end_avel_vor"},
        ],
    },
    {
        "key": "ctm_signalement",
        "name": "Signalement d'Anomalie Voirie & Bâtiment (CTM)",
        "category": "voirie",
        "commission_id": "comm_urbanisme_cadre_vie",
        "description": "Prise en compte des signalements sur la voie publique (nid-de-poule, candélabre éteint, dégradation) et suivi d'intervention CTM.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Signalement reçu", "x": 80, "y": 140},
            {"id": "task_qualification", "type": "userTask", "name": "Qualification urgence (Accueil CTM)", "role": "agent_ctm", "commission": "voirie", "sla_hours": 12, "x": 200, "y": 120},
            {"id": "task_intervention", "type": "userTask", "name": "Intervention équipe terrain", "role": "chef_equipe_voirie", "commission": "voirie", "sla_hours": 48, "x": 420, "y": 120},
            {"id": "service_cloture_notif", "type": "serviceTask", "name": "Notification usager & clôture", "action": "seal_decision_hash", "x": 640, "y": 120},
            {"id": "end_ctm", "type": "endEvent", "name": "Anomalie réparée", "x": 840, "y": 140},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_qualification"},
            {"id": "f2", "sourceRef": "task_qualification", "targetRef": "task_intervention"},
            {"id": "f3", "sourceRef": "task_intervention", "targetRef": "service_cloture_notif"},
            {"id": "f4", "sourceRef": "service_cloture_notif", "targetRef": "end_ctm"},
        ],
    },
    {
        "key": "scolaire_inscriptions",
        "name": "Campagne d'Inscription Scolaire & Dérogations",
        "category": "rh",
        "commission_id": "comm_solidarites_enfance",
        "description": "Instruction des dossiers d'admission en écoles maternelles et élémentaires de Plougastel avec gestion des dérogations scolaires.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Dépôt dossier famille", "x": 80, "y": 140},
            {"id": "task_controle_justificatifs", "type": "userTask", "name": "Contrôle résidence & vaccins", "role": "agent_enfance", "commission": "enfance", "sla_hours": 48, "x": 200, "y": 120},
            {"id": "gate_derogation", "type": "exclusiveGateway", "name": "Demande de dérogation ?", "x": 390, "y": 135},
            {"id": "task_commission_derogation", "type": "userTask", "name": "Avis Commission Mixte Dérogations", "role": "adjoint_enfance", "commission": "enfance", "sla_hours": 72, "x": 480, "y": 40},
            {"id": "task_affectation_directe", "type": "userTask", "name": "Affectation école de secteur", "role": "directrice_enfance", "commission": "enfance", "sla_hours": 24, "x": 480, "y": 200},
            {"id": "service_certificat", "type": "serviceTask", "name": "Édition Certificat d'Inscription", "action": "generate_decision_pdf", "x": 700, "y": 120},
            {"id": "end_scolaire", "type": "endEvent", "name": "Inscription définitive enregistrée", "x": 920, "y": 140},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_controle_justificatifs"},
            {"id": "f2", "sourceRef": "task_controle_justificatifs", "targetRef": "gate_derogation"},
            {"id": "f_derog", "sourceRef": "gate_derogation", "targetRef": "task_commission_derogation", "condition": "derogation == True"},
            {"id": "f_direct", "sourceRef": "gate_derogation", "targetRef": "task_affectation_directe", "condition": "derogation == False"},
            {"id": "f_derog_cert", "sourceRef": "task_commission_derogation", "targetRef": "service_certificat"},
            {"id": "f_direct_cert", "sourceRef": "task_affectation_directe", "targetRef": "service_certificat"},
            {"id": "f_cert_end", "sourceRef": "service_certificat", "targetRef": "end_scolaire"},
        ],
    },
    {
        "key": "ports_tinduff",
        "name": "Attribution de Mouillage au Port du Tinduff / Auberlac'h",
        "category": "urbanisme",
        "commission_id": "comm_urbanisme_cadre_vie",
        "description": "Instruction de la liste d'attente d'amarrage, examen des caractéristiques nautiques du navire et délivrance de l'arrêté d'AOT portuaire.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Demande de place de mouillage", "x": 80, "y": 140},
            {"id": "task_controle_navire", "type": "userTask", "name": "Vérification acte francisation & assurance", "role": "maitre_de_port", "commission": "ports", "sla_hours": 48, "x": 200, "y": 120},
            {"id": "task_commission_nautique", "type": "userTask", "name": "Arbitrage Commission Portuaire", "role": "adjoint_littoral", "commission": "ports", "sla_hours": 72, "x": 420, "y": 120},
            {"id": "service_arrete_aot", "type": "serviceTask", "name": "Édition Arrêté AOT Portuaire", "action": "generate_decision_pdf", "x": 640, "y": 120},
            {"id": "end_ports", "type": "endEvent", "name": "Bouée attribuée et contrat signé", "x": 840, "y": 140},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_controle_navire"},
            {"id": "f2", "sourceRef": "task_controle_navire", "targetRef": "task_commission_nautique"},
            {"id": "f3", "sourceRef": "task_commission_nautique", "targetRef": "service_arrete_aot"},
            {"id": "f4", "sourceRef": "service_arrete_aot", "targetRef": "end_ports"},
        ],
    },
    {
        "key": "seances_conseil",
        "name": "Préparation et Clôture de l'Ordre du Jour du Conseil",
        "category": "general",
        "commission_id": "comm_finances_administration",
        "description": "Coordination transversale entre les 4 commissions municipales, arbitrage de la DGS, convocation officielle des 33 élus et publication du PV.",
        "nodes": [
            {"id": "start", "type": "startEvent", "name": "Appel à dossiers délibératifs", "x": 80, "y": 140},
            {"id": "task_centralisation_dgs", "type": "userTask", "name": "Contrôle de légalité DGS", "role": "dgs", "commission": "general", "sla_hours": 48, "x": 200, "y": 120},
            {"id": "task_arbitrage_maire", "type": "userTask", "name": "Arrêt de l'ordre du jour par M. le Maire", "role": "maire", "commission": "general", "sla_hours": 24, "x": 420, "y": 120},
            {"id": "service_convocations", "type": "serviceTask", "name": "Envoi convocations & notes de synthèse", "action": "notify_commission_members", "x": 640, "y": 120},
            {"id": "task_tenue_seance", "type": "userTask", "name": "Déroulement séance & vote des affaires", "role": "secretaire_seance", "commission": "general", "sla_hours": 48, "x": 850, "y": 120},
            {"id": "service_pv_scelle", "type": "serviceTask", "name": "Scellement électronique du Procès-Verbal", "action": "seal_decision_hash", "x": 1060, "y": 120},
            {"id": "end_conseil", "type": "endEvent", "name": "Délibérations transmises en Préfecture", "x": 1260, "y": 140},
        ],
        "edges": [
            {"id": "f1", "sourceRef": "start", "targetRef": "task_centralisation_dgs"},
            {"id": "f2", "sourceRef": "task_centralisation_dgs", "targetRef": "task_arbitrage_maire"},
            {"id": "f3", "sourceRef": "task_arbitrage_maire", "targetRef": "service_convocations"},
            {"id": "f4", "sourceRef": "service_convocations", "targetRef": "task_tenue_seance"},
            {"id": "f5", "sourceRef": "task_tenue_seance", "targetRef": "service_pv_scelle"},
            {"id": "f6", "sourceRef": "service_pv_scelle", "targetRef": "end_conseil"},
        ],
    },
]


def seed_municipal_templates(repo: Any, tenant_id: str) -> List[Dict[str, Any]]:
    """Seeds the 10 municipal templates into the database if not already present."""
    seeded = []
    for tmpl in MUNICIPAL_TEMPLATES:
        key = tmpl["key"]
        existing = repo.list_definitions(tenant_id)
        if any(d["key"] == key for d in existing):
            continue

        bpmn_json = {
            "nodes": tmpl["nodes"],
            "edges": tmpl["edges"],
        }
        bpmn_xml = BpmnXmlBuilder.to_xml(
            process_id=tmpl["key"],
            process_name=tmpl["name"],
            nodes=tmpl["nodes"],
            edges=tmpl["edges"],
        )

        res = repo.create_definition(
            tenant_id=tenant_id,
            key=tmpl["key"],
            name=tmpl["name"],
            category=tmpl["category"],
            commission_id=tmpl.get("commission_id"),
            description=tmpl.get("description"),
            bpmn_xml=bpmn_xml,
            bpmn_json=bpmn_json,
        )
        seeded.append(res)
    return seeded


def seed_demo_workflow_instances(token_engine: Any, repo: Any, tenant_id: str) -> None:
    """Pre-seeds active demonstration instances for Play Inbox and Watch Dashboard."""
    if repo.list_instances(tenant_id):
        return

    defs = repo.list_definitions(tenant_id)
    by_key = {d["key"]: d for d in defs}

    # 1. Urbanisme ADS
    if "urbanisme_ads" in by_key:
        token_engine.start_instance(
            tenant_id=tenant_id,
            definition_id=by_key["urbanisme_ads"]["id"],
            business_key="PC-2026-042",
            title="Permis de Construire — Rénovation Maison Ty-Ar-Braz",
            initiator_id="agt_dupont",
            initiator_name="Marie DUPONT (Instructeur ADS)",
            initial_variables={
                "demandeur": "Jean-Pierre Le Gall",
                "surface_m2": 145,
                "pieces_completes": True,
                "zone_plu": "UC",
            },
        )

    # 2. Marchés Publics CAO
    if "marches_cao" in by_key:
        token_engine.start_instance(
            tenant_id=tenant_id,
            definition_id=by_key["marches_cao"]["id"],
            business_key="MAPA-2026-018",
            title="Marché Public — Réfection des Pontons du Port du Tinduff",
            initiator_id="agt_roux",
            initiator_name="Sébastien ROUX (Responsable Marchés)",
            initial_variables={
                "montant_ht": 85000,
                "lot": "Génie civil maritime",
                "candidats_admis": 3,
            },
        )

    # 3. CCAS Aide d'Urgence
    if "ccas_aide_sociale" in by_key:
        token_engine.start_instance(
            tenant_id=tenant_id,
            definition_id=by_key["ccas_aide_sociale"]["id"],
            business_key="CCAS-2026-089",
            title="Secours d'Urgence Alimentaire — Famille Kerdraon",
            initiator_id="agt_jezequel",
            initiator_name="Solange JEZEQUEL (CCAS)",
            initial_variables={
                "urgence": True,
                "montant_demande": 350,
                "reste_a_vivre": 4.5,
            },
        )

