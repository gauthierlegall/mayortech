"""SDK compatibility and synthetic native contracts, NOT a live AppFlowy test."""
import asyncio
import hashlib
from uuid import uuid4

import pytest
from mcp import Client, types
from mcp.server import Server

from travaux.integrations.appflowy import IntegrationUnavailable, PublicationRequest, SQLitePublicationLedger
from travaux.integrations.appflowy_mcp import AppFlowyMCPAdapter, schema_hash


SCHEMA = {'type': 'object'}
APPROVED = {name: schema_hash(SCHEMA, SCHEMA) for name in ('fetch', 'create-pages')}


def test_official_mcp_sdk_client_server_in_process_uses_actual_snake_case_models(tmp_path):
    """Proves adapter access to SDK fields/Client API, without any AppFlowy server."""
    async def run():
        view_id = str(uuid4())
        state = {'content': '', 'created': 0}
        async def list_tools(ctx, params):
            return types.ListToolsResult(tools=[types.Tool(name=name, inputSchema=SCHEMA, outputSchema=SCHEMA) for name in APPROVED])
        async def call_tool(ctx, params):
            if params.name == 'create-pages':
                state['created'] += 1
                state['content'] = params.arguments['pages'][0]['content']
                value = {'results': [{'index': 0, 'ok': True, 'view_id': view_id}]}
            else:
                value = {'view_id': view_id, 'format': 'markdown', 'content': state['content'], 'version': 'sdk-test-1'}
            return types.CallToolResult(content=[], structuredContent=value)
        server = Server('synthetic-travaux-sdk-test', on_list_tools=list_tools, on_call_tool=call_tool)
        async with Client(server, cache=None) as session:
            adapter = AppFlowyMCPAdapter(tenant_id='synthetic-tenant', workspace_id=str(uuid4()), session=session,
                ledger=SQLitePublicationLedger(tmp_path / 'sdk.sqlite3'), expected_schemas=APPROVED)
            text = '# Texte entièrement fictif\nNote relue.'
            request = PublicationRequest(tenant_id='synthetic-tenant', publication_id='sdk-publication-1',
                parent_id=str(uuid4()), title='SDK fictif', content_markdown=text,
                content_sha256=hashlib.sha256(text.encode()).hexdigest())
            result = await adapter.publish_version(request)
            assert result.status == 'published'
            assert result.remote_object_id == view_id
            assert state['created'] == 1
            fetched = await adapter.read_object('synthetic-tenant', view_id)
            assert fetched.content == text
            assert fetched.actor_verified is False
    asyncio.run(run())


class SyntheticRemote:
    def __init__(self, *, partial=False, trim=False):
        self.id = str(uuid4())
        self.text = 'Texte partiel.'
        self.partial, self.trim = partial, trim
    async def list_tools(self, **kwargs):
        return types.ListToolsResult(tools=[types.Tool(name=n, inputSchema=SCHEMA, outputSchema=SCHEMA) for n in APPROVED])
    async def call_tool(self, name, arguments):
        if name == 'create-pages':
            self.text = arguments['pages'][0]['content']
            value = {'results': [{'index': 0, 'ok': True, 'view_id': self.id}]}
        else:
            value = {'view_id': self.id, 'format': 'markdown', 'content': self.text.strip() if self.trim else self.text,
                     'version': 'test-1', 'has_more': self.partial}
        return types.CallToolResult(content=[], structuredContent=value)


def test_partial_native_note_is_not_silently_imported_as_complete(tmp_path):
    async def run():
        remote = SyntheticRemote(partial=True)
        adapter = AppFlowyMCPAdapter(tenant_id='test', workspace_id=str(uuid4()), session=remote,
            ledger=SQLitePublicationLedger(tmp_path / 'partial.sqlite3'), expected_schemas=APPROVED)
        with pytest.raises(IntegrationUnavailable):
            await adapter.read_object('test', remote.id)
    asyncio.run(run())


def test_native_roundtrip_does_not_claim_exact_hash_after_trimming_approved_content(tmp_path):
    async def run():
        remote = SyntheticRemote(trim=True)
        adapter = AppFlowyMCPAdapter(tenant_id='test', workspace_id=str(uuid4()), session=remote,
            ledger=SQLitePublicationLedger(tmp_path / 'hash.sqlite3'), expected_schemas=APPROVED)
        text = '    Note approuvée avec indentation.\n'
        request = PublicationRequest(tenant_id='test', publication_id='hash-1', parent_id=str(uuid4()),
            title='Version fictive', content_markdown=text, content_sha256=hashlib.sha256(text.encode()).hexdigest())
        result = await adapter.publish_version(request)
        assert result.status == 'uncertain'
        assert result.remote_object_id == remote.id
    asyncio.run(run())


def test_native_schema_error_does_not_expose_note_content_in_exception(tmp_path):
    async def run():
        marker = 'CONFIDENTIAL_SYNTHETIC_NOTE_MARKER'
        output = {'type': 'object', 'additionalProperties': False, 'properties': {
            'view_id': {'type': 'string'}, 'format': {'type': 'string'}, 'content': {'type': 'string'},
            'version': {'type': 'string'}, 'has_more': {'type': 'boolean'},
        }}
        class UnexpectedResponse(SyntheticRemote):
            async def list_tools(self, **kwargs):
                return types.ListToolsResult(tools=[types.Tool(name=n, inputSchema=SCHEMA, outputSchema=output) for n in APPROVED])
            async def call_tool(self, name, arguments):
                value = {'view_id': self.id, 'format': 'markdown', 'content': marker, 'version': '1',
                         'has_more': False, 'unexpected': True}
                return types.CallToolResult(content=[], structuredContent=value)
        remote = UnexpectedResponse()
        adapter = AppFlowyMCPAdapter(tenant_id='test', workspace_id=str(uuid4()), session=remote,
            ledger=SQLitePublicationLedger(tmp_path / 'safe-error.sqlite3'),
            expected_schemas={n: schema_hash(SCHEMA, output) for n in APPROVED})
        with pytest.raises(IntegrationUnavailable) as error:
            await adapter.read_object('test', remote.id)
        assert marker not in str(error.value)
    asyncio.run(run())
