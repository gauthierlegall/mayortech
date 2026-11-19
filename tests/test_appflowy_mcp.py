import asyncio
from types import SimpleNamespace
from uuid import uuid4

from travaux.integrations.appflowy import PublicationRequest, SQLitePublicationLedger
from travaux.integrations.appflowy_mcp import AppFlowyMCPAdapter


SCHEMA = {"type": "object"}
# This fixture is a deliberately different installation contract; production defaults
# are pinned to the official catalogue, not to this test transport.
APPROVED = {name: "42b3e7d5744568b9aff0692a180aae07a03a7754f4bebde5679d90d681a9522a" for name in ["fetch", "create-pages"]}


class Remote:
    def __init__(self, *, timeout=False, mismatch=False):
        self.id = str(uuid4())
        self.body = ""
        self.creates = 0
        self.timeout, self.mismatch = timeout, mismatch

    async def list_tools(self, **kwargs):
        return SimpleNamespace(tools=[SimpleNamespace(name=n, input_schema=SCHEMA, output_schema=SCHEMA) for n in APPROVED], next_cursor=None)

    async def call_tool(self, name, arguments):
        if name == "create-pages":
            self.creates += 1
            self.body = arguments["pages"][0]["content"]
            if self.timeout:
                raise TimeoutError()
            value = {"results": [{"index": 0, "ok": True, "view_id": self.id}]}
        else:
            value = {"view_id": self.id, "format": "markdown", "version": "1", "content": "modified" if self.mismatch else self.body}
        return SimpleNamespace(is_error=False, structured_content=value, content=[])


def adapter(tmp_path, remote):
    return AppFlowyMCPAdapter(tenant_id="a", workspace_id="workspace-a", session=remote, ledger=SQLitePublicationLedger(tmp_path / "ledger.sqlite3"), expected_schemas=APPROVED)


def request():
    return PublicationRequest(tenant_id="a", publication_id="publication-1", parent_id=str(uuid4()), title="Version approuvée", content_markdown="# Travaux\nTest", content_sha256="6a6055687b107a38b92a31672397818c302dbbf6c3df263ee94e5681dbd0534f")


def test_timeout_after_creation_is_not_repeated_after_restart(tmp_path):
    async def run():
        remote = Remote(timeout=True)
        req = request()
        first = await adapter(tmp_path, remote).publish_version(req)
        second = await adapter(tmp_path, remote).publish_version(req)
        assert first.status == second.status == "uncertain"
        assert remote.creates == 1
    asyncio.run(run())


def test_publication_requires_retrieved_exact_content(tmp_path):
    async def run():
        remote = Remote(mismatch=True)
        result = await adapter(tmp_path, remote).publish_version(request())
        assert result.status == "uncertain"
        assert result.remote_object_id == remote.id
    asyncio.run(run())


def test_live_schema_drift_prevents_creation(tmp_path):
    async def run():
        remote = Remote()
        item = adapter(tmp_path, remote)
        item.expected_schemas = {"fetch": "0" * 64, "create-pages": "0" * 64}
        result = await item.publish_version(request())
        assert result.status == "unavailable"
        assert remote.creates == 0
    asyncio.run(run())
