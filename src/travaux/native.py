"""Raccordement natif configuré par l'exploitant, jamais par un mail ou un LLM."""
import os
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError
from .integrations.appflowy import PublicationRequest, SQLitePublicationLedger
from .integrations.appflowy_mcp import AppFlowyMCPAdapter, connect_mcp


class NoteMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    view_id: str


class NativeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str
    workspace_id: str
    endpoint: str
    parent_id: str
    egress_approved: bool = False
    license_verified: bool = False
    notes: list[NoteMapping] = Field(default_factory=list, max_length=100)

    @classmethod
    def from_env(cls, tenant):
        filename = os.getenv("TRAVAUX_APPFLOWY_CONFIG")
        if not filename:
            raise DomainError("integration_unavailable", "Le serveur AppFlowy natif n'est pas configuré.")
        config = cls.model_validate_json(Path(filename).read_text(encoding="utf-8"))
        if config.tenant_id != tenant or not config.egress_approved or not config.license_verified:
            raise DomainError("integration_unavailable", "Vérifier le périmètre, l'autorisation de sortie et la licence AppFlowy.")
        UUID(config.workspace_id)
        UUID(config.parent_id)
        for note in config.notes:
            UUID(note.view_id)
        return config


async def check_native(settings):
    config = NativeConfig.from_env(settings.tenant_id)
    async with connect_mcp(config.endpoint, os.getenv("TRAVAUX_APPFLOWY_TOKEN", "")) as session:
        adapter = AppFlowyMCPAdapter(tenant_id=config.tenant_id, workspace_id=config.workspace_id, session=session, ledger=SQLitePublicationLedger(settings.db_path))
        await adapter.verify()
    return {"status": "contract_verified", "workspace_id": config.workspace_id, "operations": ["fetch", "create-pages"], "roundtrip_verified": False}


async def sync_notes(settings, repo):
    config = NativeConfig.from_env(settings.tenant_id)
    results = []
    async with connect_mcp(config.endpoint, os.getenv("TRAVAUX_APPFLOWY_TOKEN", "")) as session:
        adapter = AppFlowyMCPAdapter(tenant_id=config.tenant_id, workspace_id=config.workspace_id, session=session, ledger=SQLitePublicationLedger(settings.db_path))
        for mapping in config.notes:
            repo.get_project(config.tenant_id, mapping.project_id)
            page = await adapter.read_object(config.tenant_id, mapping.view_id)
            if not page.content.strip():
                raise DomainError("invalid_input", "Une note distante vide exige une revue manuelle de sa suppression.")
            note = repo.ingest_workspace_note(config.tenant_id, mapping.project_id, mapping.view_id, page.content, remote_revision=page.revision)
            results.append({"project_id": mapping.project_id, "note_id": note["id"], "actor_verified": False})
    return {"status": "notes_imported", "notes": results}


async def publish_summary(settings, repo, summary_id, expected_content_hash):
    config = NativeConfig.from_env(settings.tenant_id)
    summary = repo.get_summary(config.tenant_id, summary_id)
    if summary["status"] != "approved" or summary["stale"] or summary["content_hash"] != expected_content_hash:
        raise DomainError("invalid_state", "Seule la version validée, courante et relue peut être publiée.")
    project = repo.get_project(config.tenant_id, summary["project_id"])
    publication = PublicationRequest(tenant_id=config.tenant_id, publication_id=f"summary-{summary['id']}", parent_id=config.parent_id, title=f"{project['reference']} · récapitulatif v{summary['version']}", content_markdown=summary["content"], content_sha256=summary["content_hash"])
    async with connect_mcp(config.endpoint, os.getenv("TRAVAUX_APPFLOWY_TOKEN", "")) as session:
        adapter = AppFlowyMCPAdapter(tenant_id=config.tenant_id, workspace_id=config.workspace_id, session=session, ledger=SQLitePublicationLedger(settings.db_path))
        result = await adapter.publish_version(publication)
    return result.model_dump()
