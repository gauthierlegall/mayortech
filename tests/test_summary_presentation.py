"""Readable new summaries must retain their exact, versioned evidence contract."""

import hashlib
import json

from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings
from travaux.repository import Repository


HEADERS = {"X-Requested-With": "Travaux"}


def build_dossier(repo, tenant):
    project = repo.create_project(tenant, "RECETTE-FR", "Chantier de recette fictif")
    body = "Avancement : Accès sécurisé\nEntreprise : Atelier fictif\nBudget : 12345,67 EUR HT"
    source = repo.ingest_source(tenant, "recette-fr@example.invalid", "[RECETTE-FR] Situation", body)
    for field, value, quote, kind in [
        ("progress", "Accès sécurisé", "Avancement : Accès sécurisé", "text"),
        ("contractor", "Atelier fictif", "Entreprise : Atelier fictif", "text"),
        (
            "budget_raw",
            {"amount": "12345.67", "currency": "EUR", "basis": "HT"},
            "Budget : 12345,67 EUR HT",
            "money",
        ),
    ]:
        candidate = repo.add_candidate(
            tenant, project["id"], source["id"], field, value, quote=quote, kind=kind
        )
        repo.review_candidate(tenant, candidate["id"], "accept", actor_id="reviewer")
    return project, source


def test_new_summary_uses_readable_french_labels_and_exact_values(tmp_path):
    repo = Repository(tmp_path / "labels.sqlite3")
    project, source = build_dossier(repo, "town")
    summary = repo.create_summary("town", project["id"])
    assert "Avancement : Accès sécurisé" in summary["content"]
    assert "Entreprise : Atelier fictif" in summary["content"]
    assert "Budget : 12345.67 EUR HT" in summary["content"]
    assert not any(f"- {field} :" in summary["content"] for field in ["progress", "contractor", "budget_raw"])
    assert {citation["source_id"] for citation in summary["citations"]} == {source["id"]}
    assert all(source["body"][item["start"] : item["end"]] == item["quote"] for item in summary["citations"])
    assert summary["content_hash"] == hashlib.sha256(summary["content"].encode()).hexdigest()
    repo.close()


def test_old_hashed_versions_and_proofs_survive_new_generation_edit_approval_and_export(tmp_path):
    path = tmp_path / "versioned.sqlite3"
    settings = Settings(db_path=path)
    with TestClient(create_app(settings)) as client:
        repo, tenant = client.app.state.repo, settings.tenant_id
        project, source = build_dossier(repo, tenant)
        citations = [
            item for fact in repo.get_memory(tenant, project["id"])["facts"] for item in fact["evidence"]
        ]
        old_text = "# Version antérieure\n- progress : Accès sécurisé\n- contractor : Atelier fictif"
        old = repo.create_summary(tenant, project["id"], content=old_text, citations=citations)
        old_proof = json.dumps(
            {key: old[key] for key in ["content", "content_hash", "snapshot_hash", "citations"]},
            sort_keys=True,
        )

        generated = client.post(f"/api/v1/projects/{project['id']}/summaries", json={}, headers=HEADERS)
        generated.raise_for_status()
        summary = generated.json()
        assert "- Avancement : Accès sécurisé" in summary["content"]
        edited = client.patch(
            f"/api/v1/summaries/{summary['id']}",
            json={
                "content": summary["content"] + "\n\nRelecture humaine fictive.",
                "expected_content_hash": summary["content_hash"],
            },
            headers=HEADERS,
        )
        edited.raise_for_status()
        reviewed = edited.json()
        assert reviewed["version"] > summary["version"]
        assert reviewed["citations"] == summary["citations"]
        assert reviewed["snapshot_hash"] == summary["snapshot_hash"]
        approved = client.post(
            f"/api/v1/summaries/{reviewed['id']}/approve",
            json={
                "expected_content_hash": reviewed["content_hash"],
                "expected_snapshot_hash": reviewed["snapshot_hash"],
                "expected_project_revision": reviewed["project_revision"],
            },
            headers=HEADERS,
        )
        approved.raise_for_status()
        assert approved.json()["content_hash"] == reviewed["content_hash"]
        for format in ["md", "html"]:
            exported = client.get(f"/api/v1/summaries/{reviewed['id']}/export?format={format}")
            exported.raise_for_status()
            assert "Avancement : Accès sécurisé" in exported.text
            assert "Relecture humaine fictive." in exported.text
            assert "Budget : 12345,67 EUR HT" in exported.text  # Original citation, not reformatted evidence.
            assert source["id"] in exported.text
        preserved = client.get(f"/api/v1/summaries/{old['id']}").json()
        assert (
            json.dumps(
                {key: preserved[key] for key in ["content", "content_hash", "snapshot_hash", "citations"]},
                sort_keys=True,
            )
            == old_proof
        )

    reopened = Repository(path)
    preserved = reopened.get_summary(tenant, old["id"])
    assert preserved["content"] == old_text
    assert preserved["content_hash"] == old["content_hash"]
    assert preserved["citations"] == old["citations"]
    reopened.close()
