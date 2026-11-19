import base64
import json

import httpx
import pytest

from test_mail_oauth import setup, connect, ADMIN
from travaux.domain import DomainError

MIME = b"From: mairie@commune.example\r\nTo: travaux@commune.example\r\nSubject: Travaux de la cour\r\nMessage-ID: <fixture1@commune.example>\r\n\r\nVerifier le devis et les acces."


def ready(tmp_path, monkeypatch, provider, handler):
    service, hub, repo, _ = setup(tmp_path, monkeypatch)
    connection = connect(service, provider)
    service.http_client = httpx.Client(transport=httpx.MockTransport(handler))
    return service, hub, repo, connection


def select(hub, connection):
    probed = hub.probe(ADMIN, connection["id"], expected_revision=connection["revision"])
    return hub.select(ADMIN, probed["id"], calendar_ids=[], folder_ids=[probed["mail_folders"][0]["id"]], expected_revision=probed["revision"])


def test_graph_nested_folder_probe_and_mime_delta_is_read_only_and_idempotent(tmp_path, monkeypatch):
    seen = []
    def handler(request):
        seen.append((request.method, str(request.url)))
        assert request.method == "GET" and request.headers["authorization"].startswith("Bearer ")
        path = request.url.path
        if path.endswith("/mailFolders"):
            return httpx.Response(200, json={"value": [{"id": "f1", "displayName": "Reception", "childFolderCount": 1}]})
        if path.endswith("/childFolders"):
            return httpx.Response(200, json={"value": [{"id": "f2", "displayName": "Chantiers", "childFolderCount": 0}]})
        if path.endswith("/delta"):
            return httpx.Response(200, json={"value": [{"id": "m1", "changeKey": "v1"}], "@odata.deltaLink": "https://graph.microsoft.com/v1.0/me/mailFolders/f1/messages/delta?$deltatoken=opaque"})
        if path.endswith("/$value"):
            return httpx.Response(200, content=MIME)
        return httpx.Response(500)
    _, hub, repo, connection = ready(tmp_path, monkeypatch, "microsoft365", handler)
    reader = hub.reader(hub._row("commune", connection["id"]))
    assert reader.probe()["mail_folders"] == [{"id": "f1", "name": "Reception"}, {"id": "f2", "name": "Reception / Chantiers"}]
    selected = select(hub, connection)
    result = hub.sync_mail(ADMIN, selected["id"], expected_revision=selected["revision"])
    assert result["accepted"] == 1
    assert result["remote_write_enabled"] is False
    assert repo._db.execute("SELECT count(*) FROM sources").fetchone()[0] == 1
    value = result["connection"]
    again = hub.sync_mail(ADMIN, value["id"], expected_revision=value["revision"])
    assert again["accepted"] == 1
    assert repo._db.execute("SELECT count(*) FROM sources").fetchone()[0] == 1
    assert all(method == "GET" for method, _ in seen)


def test_gmail_bootstrap_then_history_preserves_originals_on_remote_delete(tmp_path, monkeypatch):
    def handler(request):
        assert request.method == "GET"
        path = request.url.path
        if path.endswith("/labels"):
            return httpx.Response(200, json={"labels": [{"id": "INBOX", "name": "Boite de reception"}]})
        if path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "100", "emailAddress": "travaux@commune.example"})
        if path.endswith("/messages"):
            assert request.url.params["labelIds"] == "INBOX"
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        if path.endswith("/messages/m1"):
            assert request.url.params["format"] == "raw"
            return httpx.Response(200, json={"id": "m1", "labelIds": ["INBOX"], "historyId": "100", "raw": base64.urlsafe_b64encode(MIME).decode()})
        if path.endswith("/history"):
            return httpx.Response(200, json={"history": [{"id": "101", "messagesDeleted": [{"message": {"id": "m1"}}]}], "historyId": "102"})
        return httpx.Response(500)
    _, hub, repo, connection = ready(tmp_path, monkeypatch, "google", handler)
    selected = select(hub, connection)
    first = hub.sync_mail(ADMIN, selected["id"], expected_revision=selected["revision"])
    second = hub.sync_mail(ADMIN, selected["id"], expected_revision=first["connection"]["revision"])
    assert first["accepted"] == 1 and second["accepted"] == 1
    assert repo._db.execute("SELECT count(*) FROM original_documents WHERE kind='email'").fetchone()[0] == 1
    assert any("remote_id" in json.loads(row[0]) for row in repo._db.execute("SELECT metadata FROM sources"))
    cursor = repo._db.execute("SELECT cursor_ciphertext FROM cloud_mail_checkpoints").fetchone()[0]
    assert hub.vault.decrypt(cursor)["history_id"] == "102"


def test_hostile_pagination_does_not_receive_bearer_and_checkpoint_stays_empty(tmp_path, monkeypatch):
    hosts = []
    def handler(request):
        hosts.append(request.url.host)
        if request.url.path.endswith("/mailFolders"):
            return httpx.Response(200, json={"value": [{"id": "f1", "displayName": "Reception"}]})
        return httpx.Response(200, json={"value": [], "@odata.nextLink": "https://evil.example/steal"})
    service, hub, repo, connection = ready(tmp_path, monkeypatch, "microsoft365", handler)
    selected = select(hub, connection)
    with pytest.raises(DomainError):
        hub.sync_mail(ADMIN, selected["id"], expected_revision=selected["revision"])
    assert set(hosts) == {"graph.microsoft.com"}
    assert repo._db.execute("SELECT count(*) FROM cloud_mail_checkpoints").fetchone()[0] == 0


def test_expired_gmail_history_is_explicit_and_no_checkpoint_advance(tmp_path, monkeypatch):
    expired = [False]
    def handler(request):
        path = request.url.path
        if path.endswith("/labels"):
            return httpx.Response(200, json={"labels": [{"id": "INBOX", "name": "Reception"}]})
        if path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "100"})
        if path.endswith("/messages"):
            return httpx.Response(200, json={})
        if path.endswith("/history"):
            return httpx.Response(404 if expired[0] else 200, json={"historyId": "101"})
        return httpx.Response(500)
    _, hub, repo, connection = ready(tmp_path, monkeypatch, "google", handler)
    selected = select(hub, connection)
    first = hub.sync_mail(ADMIN, selected["id"], expected_revision=selected["revision"])
    old = repo._db.execute("SELECT cursor_ciphertext FROM cloud_mail_checkpoints").fetchone()[0]
    expired[0] = True
    with pytest.raises(DomainError) as failure:
        hub.sync_mail(ADMIN, selected["id"], expected_revision=first["connection"]["revision"])
    assert failure.value.code == "mail_cursor_expired"
    assert repo._db.execute("SELECT cursor_ciphertext FROM cloud_mail_checkpoints").fetchone()[0] == old


def test_failed_import_never_advances_cloud_checkpoint(tmp_path, monkeypatch):
    def handler(request):
        if request.url.path.endswith("/mailFolders"):
            return httpx.Response(200, json={"value": [{"id": "f1", "displayName": "Reception"}]})
        if request.url.path.endswith("/delta"):
            return httpx.Response(200, json={"value": [{"id": "m1"}], "@odata.deltaLink": "https://graph.microsoft.com/v1.0/me/mailFolders/f1/messages/delta?$deltatoken=a"})
        return httpx.Response(200, content=MIME)
    _, hub, repo, connection = ready(tmp_path, monkeypatch, "microsoft365", handler)
    selected = select(hub, connection)
    import travaux.importing
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic database failure")
    monkeypatch.setattr(travaux.importing, "import_mail", fail)
    with pytest.raises(DomainError):
        hub.sync_mail(ADMIN, selected["id"], expected_revision=selected["revision"])
    assert repo._db.execute("SELECT count(*) FROM cloud_mail_checkpoints").fetchone()[0] == 0
    assert repo._db.execute("SELECT count(*) FROM sources").fetchone()[0] == 0


def test_explicit_cursor_reset_preserves_originals_and_checks_revision(tmp_path, monkeypatch):
    def handler(request):
        if request.url.path.endswith("/mailFolders"):
            return httpx.Response(200, json={"value": [{"id": "f1", "displayName": "Reception"}]})
        if request.url.path.endswith("/delta"):
            return httpx.Response(200, json={"value": [{"id": "m1"}], "@odata.deltaLink": "https://graph.microsoft.com/v1.0/me/mailFolders/f1/messages/delta?$deltatoken=a"})
        return httpx.Response(200, content=MIME)
    service, hub, repo, connection = ready(tmp_path, monkeypatch, "microsoft365", handler)
    selected = select(hub, connection)
    synced = hub.sync_mail(ADMIN, selected["id"], expected_revision=selected["revision"])["connection"]
    reset = service.reset_sync(ADMIN, synced["id"], expected_revision=synced["revision"], confirm=True)
    assert reset["revision"] == synced["revision"] + 1
    assert reset["status"] == "verified" and reset["last_mail_sync_at"] is None
    assert repo._db.execute("SELECT count(*) FROM cloud_mail_checkpoints").fetchone()[0] == 0
    assert repo._db.execute("SELECT count(*) FROM original_documents WHERE kind='email'").fetchone()[0] == 1
    for confirm, revision in [(False, reset["revision"]), (True, synced["revision"])]:
        with pytest.raises(DomainError):
            service.reset_sync(ADMIN, synced["id"], expected_revision=revision, confirm=confirm)
