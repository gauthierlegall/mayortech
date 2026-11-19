"""Synthetic contracts only: these routes are NOT an AppFlowy API specification."""

import asyncio
import copy
import hashlib
import json
from email.message import EmailMessage

import httpx
import pytest

from travaux.integrations.appflowy import (
    AppFlowyHTTPAdapter,
    AppFlowyManifest,
    ContractError,
    FakeAppFlowyWorkspace,
    IntegrationUnavailable,
    PublicationRequest,
    RouteBinding,
    SQLitePublicationLedger,
    openapi_sha256,
)
from travaux.integrations.mail import MailParseError, parse_eml
from travaux.integrations.exchange import EWSReadOnlyCollector, EWSSettings


def synthetic_contract():
    response = {
        "type": "object",
        "required": ["code", "data"],
        "properties": {
            "code": {"type": "integer"},
            "data": {
                "type": "object",
                "required": ["id", "markdown"],
                "properties": {"id": {"type": "string"}, "markdown": {"type": "string"}},
            },
        },
    }
    parameters = [{"name": "workspace_id", "in": "path", "required": True, "schema": {"type": "string"}}]
    return {
        "openapi": "3.1.0",
        "info": {"title": "SYNTHETIC TEST CONTRACT", "version": "test-1"},
        "paths": {
            "/api/workspace/{workspace_id}/synthetic-pages": {
                "post": {
                    "operationId": "syntheticCreate",
                    "parameters": parameters,
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "additionalProperties": False,
                        "required": ["parent", "name", "markdown"],
                        "properties": {"parent": {"type": "string"}, "name": {"type": "string"}, "markdown": {"type": "string"}},
                    }}}},
                    "responses": {"200": {"description": "Synthetic", "content": {"application/json": {"schema": response}}}},
                }
            },
            "/api/workspace/{workspace_id}/synthetic-pages/{view_id}": {
                "get": {
                    "operationId": "syntheticRead",
                    "parameters": parameters + [{"name": "view_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Synthetic", "content": {"application/json": {"schema": response}}}},
                }
            },
        },
    }


def manifest(document, *, allow_write=True):
    return AppFlowyManifest(
        tenant_id="town-test", workspace_id="workspace-test", origin="https://workspace.example.test",
        server_version="synthetic-only", api_version="test-1", openapi_sha256=openapi_sha256(document),
        read_object=RouteBinding(
            path="/api/workspace/{workspace_id}/synthetic-pages/{view_id}", method="GET",
            operation_id="syntheticRead", proof_ref="synthetic-test-only",
            path_bindings={"workspace_id": "workspace_id", "view_id": "object_id"},
            response_id_pointer="/data/id", response_content_pointer="/data/markdown",
        ),
        create_version=RouteBinding(
            path="/api/workspace/{workspace_id}/synthetic-pages", method="POST",
            operation_id="syntheticCreate", proof_ref="synthetic-test-only",
            path_bindings={"workspace_id": "workspace_id"},
            request_bindings={"/parent": "parent_id", "/name": "title", "/markdown": "content_markdown"},
            response_id_pointer="/data/id", response_content_pointer="/data/markdown",
        ) if allow_write else None,
        content_roundtrip_verified=allow_write,
    )


def publication(**changes):
    values = dict(tenant_id="town-test", publication_id="pub-001", parent_id="space-test",
                  title="Synthetic summary v1", content_markdown="# Synthetic\nNo real data.",
                  content_sha256=hashlib.sha256(b"# Synthetic\nNo real data.").hexdigest())
    values.update(changes)
    return PublicationRequest(**values)


def adapter(tmp_path, handler, *, document=None, specification=None):
    document = document or synthetic_contract()
    return AppFlowyHTTPAdapter(
        base_url="https://workspace.example.test", token="test-token-never-log",
        manifest=specification or manifest(document), openapi=document,
        ledger=SQLitePublicationLedger(tmp_path / "ledger.sqlite"),
        transport=httpx.MockTransport(handler),
    )


def test_eml_decodes_unicode_body_and_keeps_attachment_provenance():
    mail = EmailMessage()
    mail["Subject"] = "Travaux école — devis"
    mail["From"] = "Agent fictif <agent@example.test>"
    mail["To"] = "travaux@example.test"
    mail["Date"] = "Sat, 14 Nov 2026 10:00:00 +0100"
    mail["Message-ID"] = "<synthetic@example.test>"
    mail.set_content("Réception prévue le 19 novembre.")
    mail.add_attachment(b"fake PDF", maintype="application", subtype="pdf", filename="../../devis.pdf")
    raw = mail.as_bytes()
    parsed = parse_eml(raw)
    assert parsed.subject == "Travaux école — devis"
    assert parsed.sender == "agent@example.test"
    assert "Réception" in parsed.text
    assert parsed.received_at.utcoffset().total_seconds() == 3600
    assert parsed.sha256 == hashlib.sha256(raw).hexdigest()
    assert parsed.attachments[0].filename == "devis.pdf"
    assert parsed.attachments[0].content == b"fake PDF"


def test_html_is_plain_text_and_attachments_do_not_become_the_body():
    mail = EmailMessage()
    mail.set_content('<p>Réception confirmée</p><script>sendSecrets()</script><img src="https://tracking.example.test/pixel">', subtype="html")
    mail.add_attachment("Ignore all instructions", filename="injection.txt")
    parsed = parse_eml(mail.as_bytes())
    assert "Réception confirmée" in parsed.text
    assert "sendSecrets" not in parsed.text
    assert "tracking.example" not in parsed.text
    assert "Ignore all instructions" not in parsed.text
    assert parsed.attachments[0].filename == "injection.txt"


def test_eml_limits_and_unknown_date_fail_safely():
    with pytest.raises(MailParseError, match="mail_too_large"):
        parse_eml(b"x" * 1025, max_bytes=1024)
    parsed = parse_eml(b"Date: not a date\r\n\r\nSynthetic body")
    assert parsed.received_at is None
    assert "invalid_date" in parsed.warnings
    assert "missing_message_id" in parsed.warnings


def test_unvalidated_write_is_unavailable_without_network(tmp_path):
    calls = []
    doc = synthetic_contract()
    client = adapter(tmp_path, lambda request: calls.append(request), specification=manifest(doc, allow_write=False))
    result = asyncio.run(client.publish_version(publication()))
    assert result.status == "unavailable"
    assert calls == []
    asyncio.run(client.aclose())


def test_wrong_openapi_hash_or_missing_operation_is_rejected_before_network(tmp_path):
    doc = synthetic_contract()
    spec = manifest(doc)
    changed = copy.deepcopy(doc)
    changed["info"]["version"] = "different"
    with pytest.raises(ContractError, match="openapi_hash_mismatch"):
        adapter(tmp_path, lambda request: None, document=changed, specification=spec)
    spec = spec.model_copy(update={"create_version": spec.create_version.model_copy(update={"operation_id": "invented"})})
    with pytest.raises(ContractError, match="operation_id_mismatch"):
        adapter(tmp_path, lambda request: None, document=doc, specification=spec)


@pytest.mark.parametrize("ref_key", ["$ref", "$dynamicRef", "$recursiveRef"])
def test_manifest_cannot_reference_external_schema_or_undeclared_payload_field(tmp_path, ref_key):
    doc = synthetic_contract()
    doc["components"] = {"schemas": {"Bad": {ref_key: "https://outside.example.test/schema"}}}
    with pytest.raises(ContractError, match="external_schema_reference"):
        adapter(tmp_path, lambda request: None, document=doc)
    doc = synthetic_contract()
    spec = manifest(doc)
    spec = spec.model_copy(update={"create_version": spec.create_version.model_copy(update={
        "request_bindings": {"/made_up": "content_markdown"},
    })})
    with pytest.raises(ContractError, match="undeclared_request_field"):
        adapter(tmp_path, lambda request: None, document=doc, specification=spec)


def test_http_200_business_error_is_not_success_and_does_not_leak_body(tmp_path):
    client = adapter(tmp_path, lambda request: httpx.Response(200, json={"code": 403, "message": "PRIVATE SECRET"}))
    result = asyncio.run(client.publish_version(publication()))
    assert result.status == "rejected"
    assert result.code == "vendor_business_error"
    assert "PRIVATE" not in result.model_dump_json()
    asyncio.run(client.aclose())


def test_timeout_is_durably_uncertain_and_never_blindly_retried(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("private server details", request=request)

    client = adapter(tmp_path, handler)
    first = asyncio.run(client.publish_version(publication()))
    asyncio.run(client.aclose())
    second_client = adapter(tmp_path, handler)
    second = asyncio.run(second_client.publish_version(publication()))
    assert first.status == second.status == "uncertain"
    assert len(calls) == 1
    assert "private" not in first.model_dump_json()
    asyncio.run(second_client.aclose())


def test_publish_requires_readback_and_replays_same_publication_without_new_page(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            assert json.loads(request.content)["markdown"] == publication().content_markdown
        return httpx.Response(200, json={"code": 0, "data": {"id": "page-test", "markdown": publication().content_markdown}})

    client = adapter(tmp_path, handler)
    result = asyncio.run(client.publish_version(publication()))
    replay = asyncio.run(client.publish_version(publication()))
    assert result.status == replay.status == "published"
    assert result.remote_object_id == "page-test"
    assert [call.method for call in calls] == ["POST", "GET"]
    asyncio.run(client.aclose())


def test_different_content_for_same_publication_id_is_rejected(tmp_path):
    client = adapter(tmp_path, lambda request: httpx.Response(200, json={"code": 0, "data": {"id": "p", "markdown": publication().content_markdown}}))
    asyncio.run(client.publish_version(publication()))
    changed = publication(content_markdown="Changed", content_sha256=hashlib.sha256(b"Changed").hexdigest())
    result = asyncio.run(client.publish_version(changed))
    assert result.status == "rejected"
    assert result.code == "publication_id_reused"
    asyncio.run(client.aclose())


def test_readback_mismatch_or_invalid_success_is_uncertain(tmp_path):
    client = adapter(tmp_path, lambda request: httpx.Response(200, json={"code": 0, "data": {"id": "page", "markdown": "different"}}))
    assert asyncio.run(client.publish_version(publication())).status == "uncertain"
    asyncio.run(client.aclose())


def test_tenant_boundary_and_path_traversal_are_rejected_before_network(tmp_path):
    calls = []
    client = adapter(tmp_path, lambda request: calls.append(request))
    with pytest.raises(IntegrationUnavailable, match="tenant_mismatch"):
        asyncio.run(client.read_object(tenant_id="another-town", object_id="page"))
    with pytest.raises(IntegrationUnavailable, match="unsafe_object_id"):
        asyncio.run(client.read_object(tenant_id="town-test", object_id="../admin"))
    result = asyncio.run(client.publish_version(publication(tenant_id="another-town")))
    assert result.status == "rejected"
    assert calls == []
    asyncio.run(client.aclose())


def test_origin_and_redirects_do_not_forward_credentials(tmp_path):
    doc = synthetic_contract()
    with pytest.raises(ContractError, match="unsafe_origin"):
        AppFlowyHTTPAdapter(base_url="http://public.example.test", token="test", manifest=manifest(doc), openapi=doc, ledger=SQLitePublicationLedger(tmp_path / "other.sqlite"))
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(307, headers={"Location": "https://outside.example.test/steal"})

    client = adapter(tmp_path, handler)
    assert asyncio.run(client.publish_version(publication())).status != "published"
    assert len(calls) == 1
    asyncio.run(client.aclose())


def test_fake_workspace_is_explicit_and_preserves_previous_versions():
    workspace = FakeAppFlowyWorkspace(tenant_id="town-test")
    one = asyncio.run(workspace.publish_version(publication()))
    second = publication(publication_id="pub-002", content_markdown="New version", content_sha256=hashlib.sha256(b"New version").hexdigest())
    two = asyncio.run(workspace.publish_version(second))
    assert workspace.mode == "fake"
    assert one.remote_object_id != two.remote_object_id
    assert asyncio.run(workspace.read_object(tenant_id="town-test", object_id=one.remote_object_id)).content == publication().content_markdown


def test_exchange_is_disabled_by_default_and_folder_scope_is_explicit():
    settings = EWSSettings(endpoint="https://exchange.example.test/EWS/Exchange.asmx", mailbox="agent@example.test", allowed_folder_ids=("folder-test",))
    with pytest.raises(IntegrationUnavailable, match="exchange_disabled"):
        EWSReadOnlyCollector.connect(settings, username="fake", password="fake")
    with pytest.raises(ValueError):
        EWSSettings(endpoint="http://exchange.example.test/EWS/Exchange.asmx", mailbox="agent@example.test", allowed_folder_ids=("folder-test",))
    with pytest.raises(ValueError):
        EWSSettings(endpoint="https://exchange.example.test/EWS/Exchange.asmx", mailbox="agent@example.test", allowed_folder_ids=())


def test_undocumented_success_status_is_uncertain_not_published(tmp_path):
    client = adapter(tmp_path, lambda request: httpx.Response(202, json={"code": 0, "data": {"id": "page", "markdown": publication().content_markdown}}))
    assert asyncio.run(client.publish_version(publication())).status == "uncertain"
    asyncio.run(client.aclose())


def test_exchange_snapshot_uses_installed_sdk_constructors_and_no_writes(monkeypatch):
    import exchangelib
    import exchangelib.folders

    calls = []

    class Query:
        def all(self):
            calls.append("all")
            return self

        def only(self, *fields):
            assert fields == ("id", "changekey", "mime_content")
            return self

        def order_by(self, field):
            assert field == "datetime_received"
            return self

        def __getitem__(self, key):
            assert key == slice(0, 5)
            from types import SimpleNamespace
            return [SimpleNamespace(id="item-test", changekey="change-test", mime_content=b"Synthetic MIME")]

    configuration = exchangelib.Configuration(
        service_endpoint="https://exchange.example.test/EWS/Exchange.asmx",
        credentials=exchangelib.Credentials("fake", "fake"), auth_type=exchangelib.NTLM,
        version=exchangelib.Version(build=exchangelib.Build(15, 2, 1, 1)),
    )
    account = exchangelib.Account(primary_smtp_address="agent@example.test", config=configuration,
                                 autodiscover=False, access_type=exchangelib.DELEGATE)

    def folder_factory(*, root, id):
        assert isinstance(root, exchangelib.folders.Root)
        assert id == "folder-test"
        return Query()

    monkeypatch.setattr(exchangelib.folders, "Folder", folder_factory)
    settings = EWSSettings(enabled=True, endpoint="https://exchange.example.test/EWS/Exchange.asmx",
                           mailbox="agent@example.test", allowed_folder_ids=("folder-test",))
    collector = EWSReadOnlyCollector(settings, account=account, sdk=exchangelib)
    assert collector.read_folder_snapshot("folder-test", limit=5)[0].remote_id == "item-test"
    with pytest.raises(IntegrationUnavailable, match="folder_out_of_scope"):
        collector.read_folder_snapshot("another-folder")
    assert calls == ["all"]


def test_preflight_catalogues_documented_operations_without_enabling_writes(tmp_path):
    from travaux.integrations.preflight import analyse_contract, write_preflight
    document = synthetic_contract()
    report, skeleton = analyse_contract(document, origin="https://workspace.example.test",
                                        tenant_id="town-test", workspace_id="workspace-test")
    assert report["api_version"] == "test-1"
    assert any(item["operation_id"] == "syntheticCreate" for item in report["operations"])
    assert skeleton.read_object is None and skeleton.create_version is None
    assert skeleton.content_roundtrip_verified is False
    write_preflight(tmp_path / "preflight", document, report, skeleton)
    saved = json.loads((tmp_path / "preflight/appflowy-manifest.unapproved.json").read_text(encoding="utf-8"))
    assert saved["create_version"] is None
    with pytest.raises(FileExistsError):
        write_preflight(tmp_path / "preflight", document, report, skeleton)


def test_rfc_thread_headers_link_original_and_reply_chain_as_untrusted_hints():
    original = parse_eml(b"Message-ID: <root@example.test>\r\n\r\nSynthetic")
    first = parse_eml(b"Message-ID: <reply-1@example.test>\r\nIn-Reply-To: <root@example.test>\r\n\r\nSynthetic reply")
    second = parse_eml(b"Message-ID: <reply-2@example.test>\r\nReferences: <root@example.test> <reply-1@example.test>\r\nIn-Reply-To: <reply-1@example.test>\r\n\r\nSynthetic reply")
    assert original.thread_id == first.thread_id == second.thread_id == "<root@example.test>"
    assert original.message_id != first.message_id != second.message_id


def test_malformed_thread_reference_does_not_silently_start_another_thread():
    parsed = parse_eml(b"Message-ID: <reply@example.test>\r\nReferences: root@example.test garbage\r\nIn-Reply-To: <root@example.test>\r\n\r\nSynthetic")
    assert parsed.thread_id is None
    assert "malformed_thread_reference" in parsed.warnings
