"""Client applicatif étroit : publication de versions et lecture de notes natives.

Contrats observés dans le catalogue officiel AppFlowy au commit
318a8c81cab86418fa3e71cc8e03b7cb874378a6 (pas de code éditeur recopié).
Le LLM n'a jamais accès à ce client ni aux jetons.
"""
from contextlib import asynccontextmanager
import hashlib
import json
from uuid import UUID
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, ValidationError as SchemaValidationError, SchemaError

from .appflowy import IntegrationUnavailable, PublicationResult, WorkspaceObject


PINNED_SCHEMAS = {
    "fetch": "faf793980a913e32c36b62b39cfc0f91a670f8dcbb97862ea31d8a911bd3b000",
    "create-pages": "77fb812ee2307116c83f80a7b60448564e503dcb7383da62bc97c96e5db12df1",
}


def schema_hash(input_schema, output_schema):
    value = json.dumps({"input": input_schema, "output": output_schema}, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(value.encode()).hexdigest()


def _uuid(value):
    return str(UUID(value))


@asynccontextmanager
async def connect_mcp(endpoint: str, token: str):
    url = urlsplit(endpoint)
    if url.scheme != "https" or not url.hostname or url.username or url.query or url.fragment or url.path.rstrip("/") != "/mcp":
        raise IntegrationUnavailable("https_mcp_endpoint_required")
    if not token or any(char in token for char in "\r\n"):
        raise IntegrationUnavailable("appflowy_access_token_required")
    # SDK officiel : Streamable HTTP, authentification provisionnée par l'opérateur.
    # Aucun OAuth interactif ni rafraîchissement avec mot de passe de messagerie.
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=60, follow_redirects=False, trust_env=False) as http:
        async with Client(streamable_http_client(endpoint, http_client=http), read_timeout_seconds=60) as session:
            yield session


class AppFlowyMCPAdapter:
    def __init__(self, *, tenant_id, workspace_id, session, ledger, expected_schemas=None):
        self.tenant_id, self.workspace_id = tenant_id, workspace_id
        self.session, self.ledger = session, ledger
        self.expected_schemas = dict(PINNED_SCHEMAS if expected_schemas is None else expected_schemas)
        self.tools = {}

    async def verify(self):
        if self.tools:
            return
        cursor, seen, tools = None, set(), {}
        for _ in range(10):
            batch = await self.session.list_tools(**({"cursor": cursor} if cursor else {}))
            tools.update({tool.name: tool for tool in batch.tools})
            cursor = batch.next_cursor
            if not cursor:
                break
            if cursor in seen:
                raise IntegrationUnavailable("tool_catalogue_cursor_loop")
            seen.add(cursor)
        else:
            raise IntegrationUnavailable("tool_catalogue_limit")
        for name, expected in self.expected_schemas.items():
            tool = tools.get(name)
            if tool is None or schema_hash(tool.input_schema, tool.output_schema) != expected:
                raise IntegrationUnavailable("appflowy_tool_schema_changed")
        self.tools = {name: tools[name] for name in self.expected_schemas}

    async def _call(self, name, arguments):
        if name not in {"fetch", "create-pages"} or name not in self.tools:
            raise IntegrationUnavailable("tool_not_allowed")
        tool = self.tools[name]
        try:
            Draft202012Validator(tool.input_schema).validate(arguments)
        except (SchemaValidationError, SchemaError):
            raise IntegrationUnavailable("appflowy_input_contract_invalid") from None
        result = await self.session.call_tool(name, arguments)
        if result.is_error or not isinstance(result.structured_content, dict):
            raise IntegrationUnavailable("appflowy_tool_failed")
        value = result.structured_content
        if len(json.dumps(value, ensure_ascii=False)) > 1_000_000:
            raise IntegrationUnavailable("appflowy_response_too_large")
        try:
            Draft202012Validator(tool.output_schema).validate(value)
        except (SchemaValidationError, SchemaError):
            raise IntegrationUnavailable("appflowy_output_contract_invalid") from None
        return value

    async def read_object(self, tenant_id, object_id):
        if tenant_id != self.tenant_id:
            raise IntegrationUnavailable("tenant_mismatch")
        await self.verify()
        object_id = _uuid(object_id)
        value = await self._call("fetch", {"view_id": object_id, "body_format": "markdown"})
        if value.get("view_id") != object_id or value.get("format") != "markdown" or value.get("has_more") is True or not isinstance(value.get("content"), str):
            raise IntegrationUnavailable("appflowy_document_incomplete")
        return WorkspaceObject(tenant_id=tenant_id, object_id=object_id, content=value["content"], content_sha256=hashlib.sha256(value["content"].encode()).hexdigest(), revision=value.get("version"), actor_id=None, actor_verified=False)

    async def publish_version(self, request):
        def result(status, code, object_id=None):
            return PublicationResult(publication_id=request.publication_id, status=status, code=code, remote_object_id=object_id)
        if request.tenant_id != self.tenant_id:
            return result("rejected", "tenant_mismatch")
        try:
            _uuid(request.parent_id)
            await self.verify()
        except Exception:
            return result("unavailable", "appflowy_contract_unverified")
        previous = self.ledger.reserve(self.tenant_id, self.workspace_id, request)
        if previous is not None:
            return previous
        object_id = None
        try:
            # The publication identifier remains visible for manual reconciliation.
            title = f"{request.title[:160]} · {request.publication_id}"
            value = await self._call("create-pages", {"confirm": True, "pages": [{"name": title, "parent_view_id": request.parent_id, "layout": "document", "content": request.content_markdown}]})
            rows = value.get("results", [])
            if len(rows) != 1 or rows[0].get("index") != 0 or rows[0].get("ok") is not True:
                outcome = result("uncertain", "appflowy_create_requires_reconciliation")
            else:
                object_id = _uuid(rows[0]["view_id"])
                fetched = await self.read_object(self.tenant_id, object_id)
                if fetched.content_sha256 != request.content_sha256:
                    outcome = result("uncertain", "appflowy_roundtrip_mismatch", object_id)
                else:
                    outcome = result("published", "native_markdown_roundtrip_verified", object_id)
        except Exception:
            # An interrupted POST may have succeeded. Never retry this ID blindly.
            outcome = result("uncertain", "requires_reconciliation", object_id)
        self.ledger.complete(self.tenant_id, self.workspace_id, request, outcome)
        return outcome
