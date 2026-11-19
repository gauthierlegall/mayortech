"""Mailbox boundary tests; the actor dependency below is a server-side fixture.
No SMTP account, external delivery or real municipal message is used.
"""

import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from travaux.domain import DomainError
from travaux.mailbox import MailboxRepository, register_mailbox_routes
from travaux.repository import Repository


def source(repo, external_id="mail-1", *, tenant="town", fictitious=True, metadata=None):
    return repo.ingest_source(
        tenant,
        external_id,
        "École : visite fictive",
        "Un message fictif à examiner.",
        sender="Alice <alice@example.invalid>",
        metadata={"fictitious": fictitious, **(metadata or {})},
    )


@pytest.fixture
def mailbox(tmp_path):
    repo = Repository(tmp_path / "mailbox.sqlite3")
    item = source(repo)
    other = source(repo, "mail-2")
    actor = {"tenant_id": "town", "actor_id": "alice"}
    settings = SimpleNamespace(mode="staging", auth_required=True)
    app = FastAPI()

    @app.exception_handler(DomainError)
    async def domain_error(request, error):
        return JSONResponse(
            {"error": {"code": error.code, "message": error.message}},
            status_code=404 if error.code == "not_found" else 422,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return JSONResponse(
            {"error": {"code": "invalid_request", "message": "Champs invalides."}}, status_code=422
        )

    store = register_mailbox_routes(app, repo, "town", lambda: dict(actor), settings)
    with TestClient(app) as client:
        yield client, repo, store, actor, settings, item, other, app
    repo.close()


def test_global_mailbox_contains_unmatched_messages_but_not_notes_or_attachment_sources(mailbox):
    client, repo, _, _, _, first, _, _ = mailbox
    project = repo.create_project("town", "T-1", "Dossier fictif")
    repo.add_note("town", project["id"], "Note privée de dossier")
    source(repo, "part", metadata={"parent_source_id": first["id"], "filename": "plan.pdf"})
    source(repo, "document", metadata={"filename": "document.pdf", "extraction_status": "extracted"})
    source(repo, "other-town", tenant="other")
    result = client.get("/api/v1/mailbox/messages?folder=all").json()
    assert result["total"] == 2
    assert all(item["project_ids"] == [] for item in result["items"])
    assert all(
        item["folder"] == "inbox" and not item["read"] and not item["starred"] for item in result["items"]
    )
    assert client.get("/api/v1/mailbox/messages?q=éCOLE").json()["total"] == 2
    assert client.get("/api/v1/mailbox/messages?q=%").json()["total"] == 0


def test_flags_and_folders_are_reversible_without_modifying_sources_or_provenance(mailbox):
    client, repo, _, actor, _, first, _, _ = mailbox
    original = json.dumps(repo.get_source("town", first["id"]), sort_keys=True)
    for folder in ["archive", "trash", "inbox"]:
        updated = client.patch(
            f"/api/v1/mailbox/messages/{first['id']}", json={"folder": folder, "read": True, "starred": True}
        )
        assert updated.status_code == 200 and updated.json()["folder"] == folder
    assert client.get("/api/v1/mailbox/messages?folder=starred").json()["total"] == 1
    assert original == json.dumps(repo.get_source("town", first["id"]), sort_keys=True)
    actor["actor_id"] = "bob"
    untouched = client.get(f"/api/v1/mailbox/messages/{first['id']}").json()
    assert untouched["read"] is False and untouched["starred"] is False


def test_project_folder_and_pagination_filter_real_links_before_counting(mailbox):
    client, repo, _, _, _, first, other, _ = mailbox
    project = repo.create_project("town", "CHANTIER-1", "Chantier Alpha")
    second_project = repo.create_project("town", "CHANTIER-2", "Chantier Beta")
    repo.assign_source("town", first["id"], project["id"])
    repo.assign_source("town", other["id"], second_project["id"])
    additional = source(repo, "mail-additional")
    repo.assign_source("town", additional["id"], project["id"])
    # A mail can mention the project's name without belonging to it.
    repo.ingest_source("town", "unrelated", "Chantier Alpha", "Sans rattachement")
    base = f"/api/v1/mailbox/messages?project_id={project['id']}&limit=1"
    one = client.get(base).json()
    two = client.get(base + "&offset=1").json()
    assert one["total"] == two["total"] == 2
    assert {one["items"][0]["id"], two["items"][0]["id"]} == {first["id"], additional["id"]}
    client.patch(f"/api/v1/mailbox/messages/{first['id']}", json={"folder": "archive"}).raise_for_status()
    inbox = client.get(base).json()
    archive = client.get(base + "&folder=archive").json()
    assert inbox["total"] == archive["total"] == 1
    assert inbox["items"][0]["id"] == additional["id"]
    assert archive["items"][0]["id"] == first["id"]
    assert client.get(base + "&q=absent").json()["total"] == 0
    assert client.get("/api/v1/mailbox/messages?project_id=foreign-project").json()["total"] == 0
    assert client.get("/api/v1/mailbox/messages?project_id=" + "x" * 101).status_code == 422


def test_folder_counts_and_capabilities_never_invent_a_connected_account_or_sent_mail(mailbox):
    client, _, _, _, _, first, _, _ = mailbox
    client.patch(
        f"/api/v1/mailbox/messages/{first['id']}", json={"read": True, "starred": True, "folder": "archive"}
    ).raise_for_status()
    result = client.get("/api/v1/mailbox/folders").json()
    counts = {item["id"]: item for item in result["items"]}
    assert counts["all"]["total"] == 2 and counts["all"]["unread"] == 1
    assert counts["inbox"]["total"] == 1 and counts["archive"]["total"] == 1
    assert counts["starred"]["total"] == 1 and counts["sent"]["total"] == 0
    assert result["capabilities"]["can_send"] is False
    assert result["account"]["status"] == "not_connected" and result["account"]["address"] is None


def test_drafts_are_private_per_actor_and_tenant_with_partial_updates_and_revision_checks(mailbox):
    client, _, _, actor, _, first, _, _ = mailbox
    draft = client.post(
        "/api/v1/mailbox/drafts",
        json={
            "to": ["Alice <Alice@EXAMPLE.invalid>"],
            "subject": "Réponse fictive",
            "body": "Corps privé",
            "in_reply_to": first["id"],
        },
    ).json()
    assert draft["to"] == ["Alice <Alice@example.invalid>"] and draft["revision"] == 1
    assert client.get("/api/v1/mailbox/drafts").json()["total"] == 1
    actor["actor_id"] = "bob"
    assert client.get("/api/v1/mailbox/drafts").json()["items"] == []
    assert client.get(f"/api/v1/mailbox/drafts/{draft['id']}").status_code == 404
    assert (
        client.patch(f"/api/v1/mailbox/drafts/{draft['id']}", json={"body": "intrusion"}).status_code == 404
    )
    assert client.delete(f"/api/v1/mailbox/drafts/{draft['id']}").status_code == 404
    actor["actor_id"] = "alice"
    edited = client.patch(
        f"/api/v1/mailbox/drafts/{draft['id']}", json={"body": "Version suivante", "expected_revision": 1}
    ).json()
    assert edited["revision"] == 2 and edited["subject"] == draft["subject"]
    assert (
        client.patch(
            f"/api/v1/mailbox/drafts/{draft['id']}", json={"body": "Ancien onglet", "expected_revision": 1}
        ).status_code
        == 409
    )
    actor["tenant_id"] = "other"
    assert client.get("/api/v1/mailbox/drafts").status_code == 403
    actor["tenant_id"] = "town"
    assert client.delete(f"/api/v1/mailbox/drafts/{draft['id']}?expected_revision=2").status_code == 204


@pytest.mark.parametrize(
    "payload",
    [
        {"to": ["friend@example.invalid\r\nBcc: copied@example.invalid"]},
        {"cc": ["not-an-address"]},
        {"bcc": ["one@example.invalid, two@example.invalid"]},
        {"subject": "Sujet\r\nX-Header: injected"},
        {"to": ["bad@@example.invalid"]},
        {"body": "null\u0000byte"},
        {"actor_id": "another-person"},
        {"to": ["(" * 480 + "a@b" + ")" * 480]},
    ],
)
def test_invalid_recipients_header_injection_and_identity_overrides_are_rejected_without_echo(
    mailbox, payload
):
    client, _, _, _, _, _, _, _ = mailbox
    result = client.post("/api/v1/mailbox/drafts", json={"body": "PRIVATE_DO_NOT_ECHO", **payload})
    assert result.status_code == 422
    assert "PRIVATE_DO_NOT_ECHO" not in result.text
    assert client.get("/api/v1/mailbox/drafts").json()["total"] == 0


def test_public_demo_never_stores_shared_draft_bodies_and_flags_only_fictitious_messages(mailbox):
    client, repo, _, _, settings, first, _, _ = mailbox
    settings.mode, settings.auth_required = "public_demo", False
    foreign = source(repo, "not-fixture", fictitious=False)
    numeric_marker = source(repo, "not-a-boolean", fictitious=1)
    listed = client.get("/api/v1/mailbox/messages?folder=all").json()
    assert listed["total"] == 2
    assert not {foreign["id"], numeric_marker["id"]}.intersection(item["id"] for item in listed["items"])
    assert client.get("/api/v1/mailbox/drafts").json()["items"] == []
    assert client.get("/api/v1/mailbox/folders").json()["capabilities"]["server_drafts"] is False
    assert client.post("/api/v1/mailbox/drafts", json={"body": "PRIVATE_PUBLIC_VISITOR"}).status_code == 403
    assert (
        client.patch(f"/api/v1/mailbox/messages/{first['id']}", json={"folder": "trash"}).status_code == 200
    )
    assert client.patch(f"/api/v1/mailbox/messages/{foreign['id']}", json={"read": True}).status_code == 403
    assert repo._db.execute("SELECT count(*) FROM mailbox_drafts").fetchone()[0] == 0


def test_send_is_fail_closed_without_network_side_effect_or_fake_sent_entry(mailbox):
    client, repo, _, _, _, _, _, _ = mailbox
    draft = client.post(
        "/api/v1/mailbox/drafts", json={"to": ["nobody@example.invalid"], "body": "Message non envoyé"}
    ).json()
    before = len(repo.list_sources("town"))
    result = client.post("/api/v1/mailbox/send", json={"draft_id": draft["id"]})
    assert result.status_code == 503 and result.json()["error"]["code"] == "mail_transport_not_configured"
    assert client.get(f"/api/v1/mailbox/drafts/{draft['id']}").status_code == 200
    assert len(repo.list_sources("town")) == before
    assert client.get("/api/v1/mailbox/messages?folder=sent").json()["total"] == 0


def test_server_permission_service_controls_compose_and_flag_capabilities(mailbox):
    client, _, _, _, _, first, _, app = mailbox
    app.state.governance = SimpleNamespace(authorize=lambda actor, resource, action: action == "read")
    result = client.get("/api/v1/mailbox/folders").json()
    assert result["capabilities"]["server_drafts"] is False
    assert client.post("/api/v1/mailbox/drafts", json={"body": "Not allowed"}).status_code == 403
    assert client.patch(f"/api/v1/mailbox/messages/{first['id']}", json={"read": True}).status_code == 403


def test_draft_create_replay_never_duplicates_or_overwrites_a_later_edit(mailbox):
    client, _, _, _, _, _, _, _ = mailbox
    payload = {"client_id": "f3ec404f-9856-4d25-9854-38d6e109cc1c", "body": "Initial"}
    draft = client.post("/api/v1/mailbox/drafts", json=payload).json()
    client.patch(f"/api/v1/mailbox/drafts/{draft['id']}", json={"body": "Human edit"}).raise_for_status()
    replay = client.post("/api/v1/mailbox/drafts", json=payload)
    assert replay.status_code in {200, 201} and replay.json()["id"] == draft["id"]
    assert replay.json()["body"] == "Human edit"
    assert client.get("/api/v1/mailbox/drafts").json()["total"] == 1


def test_reading_mail_does_not_implicitly_mark_it_as_read(mailbox):
    client, _, _, _, _, first, _, _ = mailbox
    assert client.get(f"/api/v1/mailbox/messages/{first['id']}").json()["read"] is False
    assert client.get("/api/v1/mailbox/folders").json()["items"][0]["unread"] == 2


def test_repository_store_can_be_reopened_without_losing_drafts_or_flags(tmp_path):
    path = tmp_path / "persist.sqlite3"
    repo = Repository(path)
    item = source(repo)
    store = MailboxRepository(repo)
    store.update_message("town", "alice", item["id"], {"folder": "archive", "starred": True})
    draft = store.create_draft("town", "alice", {"body": "Brouillon durable"})
    repo.close()
    repo = Repository(path)
    reopened = MailboxRepository(repo)
    assert reopened.get_message("town", "alice", item["id"])["folder"] == "archive"
    assert reopened.get_draft("town", "alice", draft["id"])["body"] == "Brouillon durable"
    repo.close()
