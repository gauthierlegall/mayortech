"""Tests d'étanchéité stricte inter-commissions et traçabilité RGPD (Lot v3.4).

Vérifie :
1. Qu'un utilisateur de la Commission 1 (Finances) ou Commission 3 (Travaux) ne peut
   en aucun cas accéder aux dossiers ou aides sociales sensibles CCAS (Commission 2).
2. Que la liste des dossiers de ces utilisateurs ne fait fuiter aucun dossier CCAS (0 résultat).
3. Que chaque consultation légitime par un agent CCAS est enregistrée de manière nominative
   dans la chaîne d'audit SHA-256 (conformité RGPD Art. 9 et Art. 30).
4. Que l'Export Souverain Anti-Lock-In est généré avec succès en format ouvert réversible.
"""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.commissions import COMMISSION_1_ID, COMMISSION_2_ID, COMMISSION_3_ID
from travaux.config import Settings


@pytest.fixture
def isolation_env(tmp_path):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        db_path=tmp_path / "isolation_test.sqlite3",
        tenant_id="town-plougastel",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    repo = app.state.repo

    # 1. Dossier CCAS confidentiel en Commission 2
    repo.create_project(
        "town-plougastel",
        "CCAS-2026-001",
        "Aide d'urgence précarité énergétique Famille K.",
        project_id="prj-ccas-urgence",
        commission_id=COMMISSION_2_ID,
    )

    # 2. Dossier Voirie en Commission 3
    repo.create_project(
        "town-plougastel",
        "TRV-2026-015",
        "Réfection enrobé Quai du Tinduff",
        project_id="prj-voirie-tinduff",
        commission_id=COMMISSION_3_ID,
    )

    # 3. Dossier Marchés en Commission 1
    repo.create_project(
        "town-plougastel",
        "FIN-2026-004",
        "Contrôle budgétaire école des Alizés",
        project_id="prj-fin-alizes",
        commission_id=COMMISSION_1_ID,
    )

    # Insérer une aide confidentielle CCAS
    app.state.enfance_sociale.record_social_aid(
        "town-plougastel",
        project_id="prj-ccas-urgence",
        aid_type="aide_energie",
        confidential_ref="SEC-ENER-882",
        amount_cents=45000,
        commission_decision="accorde",
        notes="Aide d'urgence validée en commission CCAS restreinte.",
    )

    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def csrf_headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def provision_user(app, subject, commission_id, role="editor", display_name=""):
    member = app.state.identities.provision("https://identity.example", subject, subject, role)
    if display_name:
        with app.state.repo._transaction() as db:
            db.execute(
                "UPDATE identity_members SET display_name = ? WHERE tenant_id = ? AND actor_id = ?",
                (display_name, "town-plougastel", member["actor_id"]),
            )
    app.state.commissions.set_member_commission_role(
        "town-plougastel", commission_id, member["actor_id"], role, updated_by="admin"
    )
    token = app.state.sessions.issue(member["actor_id"], "town-plougastel")
    return member, token


def test_commission_isolation_and_ccas_dossier_protection(isolation_env):
    app, client = isolation_env

    # Provisionner un agent Finances (Com 1) et un agent Travaux (Com 3)
    user_fin, token_fin = provision_user(app, "valerie-finances", COMMISSION_1_ID, "editor", "Valérie Gestin")
    user_trv, token_trv = provision_user(app, "loic-travaux", COMMISSION_3_ID, "editor", "Loïc Kerbrat")

    # 1. Agent Finances tente d'accéder au dossier CCAS -> Rejeté (404 / périmètre étanche)
    client.cookies.set("travaux_session", token_fin)
    res_fin = client.get("/api/v1/projects/prj-ccas-urgence/social-aid", headers=csrf_headers())
    assert res_fin.status_code in {403, 404}, f"Agent finances ne doit pas accéder au CCAS: {res_fin.status_code}"

    # Vérifier que le dossier CCAS n'apparaît pas dans la liste des projets de l'agent Finances
    res_list_fin = client.get("/api/v1/projects", headers=csrf_headers())
    assert res_list_fin.status_code == 200
    items_fin = res_list_fin.json() if isinstance(res_list_fin.json(), list) else res_list_fin.json().get("items", [])
    pids_fin = [p["id"] for p in items_fin]
    assert "prj-ccas-urgence" not in pids_fin

    # 2. Agent Travaux tente d'accéder au dossier CCAS -> Rejeté (404 / périmètre étanche)
    client.cookies.set("travaux_session", token_trv)
    res_trv = client.get("/api/v1/projects/prj-ccas-urgence/social-aid", headers=csrf_headers())
    assert res_trv.status_code in {403, 404}, f"Agent travaux ne doit pas accéder au CCAS: {res_trv.status_code}"

    # Vérifier que le dossier CCAS n'apparaît pas dans la liste des projets de l'agent Travaux
    res_list_trv = client.get("/api/v1/projects", headers=csrf_headers())
    assert res_list_trv.status_code == 200
    items_trv = res_list_trv.json() if isinstance(res_list_trv.json(), list) else res_list_trv.json().get("items", [])
    pids_trv = [p["id"] for p in items_trv]
    assert "prj-ccas-urgence" not in pids_trv


def test_ccas_agent_access_and_nominative_rgpd_logging(isolation_env):
    app, client = isolation_env

    # Provisionner un agent CCAS (Com 2)
    user_ccas, token_ccas = provision_user(app, "nolwenn-ccas", COMMISSION_2_ID, "editor", "Nolwenn Péron")
    client.cookies.set("travaux_session", token_ccas)

    # 1. Agent CCAS consulte le dossier et les aides sociales associées
    res_ccas = client.get("/api/v1/projects/prj-ccas-urgence/social-aid", headers=csrf_headers())
    assert res_ccas.status_code == 200
    data = res_ccas.json()
    assert data["total"] == 1
    assert data["items"][0]["confidential_ref"] == "SEC-ENER-882"
    assert data["items"][0]["amount_cents"] == 45000

    # 2. Vérifier que la consultation a généré une entrée nominative dans la chaîne d'audit SHA-256
    audit_chain = app.state.audit_chain
    entries = audit_chain.list_entries("town-plougastel")
    rgpd_entries = [e for e in entries if e["action"] == "rgpd_consultation_dossier_ccas"]

    assert len(rgpd_entries) >= 1
    last_rgpd = rgpd_entries[-1]
    assert last_rgpd["actor_id"] == user_ccas["actor_id"]
    assert last_rgpd["document_ref"] == "CCAS-prj-ccas-urgence"

    # 3. Vérifier que l'intégrité mathématique de la chaîne reste 100 % valide
    verification = audit_chain.verify_chain("town-plougastel")
    assert verification["valid"] is True
    assert verification["total_entries"] == len(entries)


def test_sovereign_export_anti_lock_in_zip(isolation_env):
    app, client = isolation_env
    user_ccas, token_ccas = provision_user(app, "admin-maire", COMMISSION_2_ID, "admin", "Maire Dominique Cap")
    client.cookies.set("travaux_session", token_ccas)

    res = client.post("/api/v1/organizations/current/sovereign-export", headers=csrf_headers())
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "attachment" in res.headers["content-disposition"]

    # Valider le contenu de l'archive ouverte
    archive = zipfile.ZipFile(io.BytesIO(res.content))
    namelist = archive.namelist()

    # Formats ouverts requis par Lot v3.4
    assert "README_REVERSIBILITE.md" in namelist
    assert "audit/journal_audit_chaine_sha256.json" in namelist
    assert "audit/certificat_integrite.json" in namelist
    assert "actes/PC-2026-042_permis_construire.html" in namelist
    assert "workflows/circuits_validation_bpmn20.xml" in namelist
    assert "registres/dossiers_registre.csv" in namelist
    assert "registres/deliberations_conseil.csv" in namelist

    # Vérifier la présence du manifeste de réversibilité
    manifeste = archive.read("README_REVERSIBILITE.md").decode("utf-8")
    assert "EXPORT SOUVERAIN MAYORTECH" in manifeste
    assert "ISO/IEC 19510" in manifeste
