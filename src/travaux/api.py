from contextlib import asynccontextmanager
import base64
import binascii
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .auth import SessionStore, verify_password
from .config import Settings, ensure_public_demo_database
from .demo import add_next_mail, seed
from .domain import DomainError
from .jobs import JobQueue
from .llm import make_extractor
from .pipeline import extract_source, process_one
from .summary_format import summary_field_label
from .repository import Repository
from .workspace import WorkspaceRepository
from . import __version__


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    password: str = Field(min_length=1, max_length=1024)


class ImportMail(Input):
    filename: str = Field(min_length=1, max_length=180)
    content: str | None = Field(default=None, min_length=1, max_length=2_000_000)
    content_base64: str | None = Field(default=None, min_length=1, max_length=2_700_000)

    @model_validator(mode="after")
    def exactly_one_payload(self):
        if (self.content is None) == (self.content_base64 is None):
            raise ValueError("Un seul contenu EML est attendu")
        return self


class Decision(Input):
    decision: str = Field(pattern="^(accept|reject|replace)$")
    expected_revision: int | None = None
    reason: str = Field(default="", max_length=2000)
    corrected_value: str | None = Field(default=None, max_length=10000)


class Note(Input):
    body: str = Field(min_length=1, max_length=100000)


class SummaryRequest(Input):
    # Period is a display preference only: the durable context remains project-wide.
    period_start: str | None = None
    period_end: str | None = None


class EditSummary(Input):
    content: str = Field(min_length=1, max_length=500000)
    expected_content_hash: str


class Approval(Input):
    expected_content_hash: str
    expected_snapshot_hash: str
    expected_project_revision: int


class Publish(Input):
    expected_content_hash: str


class Assignment(Input):
    project_id: str


class ProjectInput(Input):
    reference: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    location: str = Field(default="", max_length=200)
    contractor: str = Field(default="", max_length=200)
    delivery_date: str = Field(default="", max_length=10)
    owner: str = Field(default="", max_length=200)
    commission_id: str = Field(default="commission-3", max_length=100)
    specialization: str = Field(default="travaux", max_length=100)
    visibility: str = Field(default="standard", max_length=50)


class PageState(Input):
    state_base64: str = Field(min_length=1, max_length=2_800_000)
    expected_revision_hash: str | None = None
    text: str = Field(max_length=100000)
    editor_version: str = "blocksuite-0.22.4"


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PATCH", "PUT"}:
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        parts = scope.get("path", "").strip("/").split("/")
        upload = len(parts) == 6 and parts[:3] == ["api", "v1", "projects"] and parts[4:] == ["documents", "upload"]
        limit = 7_000_000 if upload else 3_000_000
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                return await JSONResponse({"error": {"code": "body_too_large", "message": "La requête dépasse la taille autorisée."}}, status_code=413)(scope, receive, send)
            chunks.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()
        return await self.app(scope, replay, send)


def request_permission(method: str, path: str):
    """Known API routes only. Unknown resources fail closed in actor()."""
    parts = path.rstrip("/").split("/")
    if len(parts) < 4 or parts[:3] != ["", "api", "v1"]:
        return None
    tail = parts[3:]
    area, count = tail[0], len(tail)
    read = method in {"GET", "HEAD"}
    if area == "bootstrap" and count == 1 and read:
        return "workspace", "read"
    if area == "onboarding" and count == 1 and (read or method == "PATCH"):
        return "workspace", "read"
    if area == "integrations":
        if count == 4 and tail[1] == "oauth" and tail[2] in {"google", "microsoft365"} and tail[3] == "start" and method == "POST":
            return "organization", "write"
        if count == 1 and read:
            return "organization", "read"
        if count == 2 and tail[1] == "connections" and method == "POST":
            return "organization", "write"
        if count == 4 and tail[1] == "connections" and tail[3] in {"probe", "selection", "disconnect", "sync", "sync-mail", "reset-mail-sync"} and method in {"POST", "PUT"}:
            return "organization", "write"
        if count == 3 and tail[1] == "telegram":
            if tail[2] == "configure" and method == "POST":
                return "organization", "write"
            if (tail[2] == "status" and read) or (tail[2] == "pairing" and method in {"POST", "DELETE"}):
                return "workspace", "read"
    if area == "calendars":
        if read and (count == 1 or (count == 2 and tail[1] in {"events", "export.ics"}) or (count == 3 and tail[1] == "events")):
            return "workspace", "read"
        if count == 2 and tail[1] == "import-ics" and method == "POST":
            return "organization", "write"
        if count == 4 and tail[1] == "events" and tail[3] == "assignment" and method in {"POST", "PATCH"}:
            return "workspace", "write"
    if area == "conversations" and ((count == 1 and (read or method == "POST")) or (count == 2 and (read or method == "DELETE")) or (count == 3 and tail[2] == "messages" and method == "POST")):
        return "workspace", "read"
    if area == "assistant-changes" and ((count == 2 and read) or (count == 3 and tail[2] in {"confirm", "reject"} and method == "POST")):
        return "workspace", "read" if read else "write"
    if area == "projects" and count >= 3 and tail[2] == "action-collaboration":
        if read and (count == 3 or (count == 4 and tail[3] in {"participants", "comments", "occurrences"})):
            return "workspace", "read"
        if (count == 3 and method == "PATCH") or (count == 4 and tail[3] in {"comments", "recurrence", "occurrences"} and method in {"POST", "PUT"}) or (count == 6 and tail[3] == "occurrences" and tail[5] == "confirm" and method == "POST"):
            return "workspace", "write"
    if area == "notifications" and ((count == 1 and read) or (count == 2 and tail[1] == "settings" and (read or method == "PATCH")) or (count == 3 and tail[2] == "read" and method == "PATCH")):
        return "workspace", "read"
    if area == "mail-backfills":
        if read and count in {1, 2}:
            return "organization", "read"
        if method == "POST" and (count == 1 or (count == 2 and tail[1] == "preview") or (count == 3 and tail[2] in {"run", "pause", "resume", "cancel"})):
            return "organization", "write"
    if area == "projects" and count == 3 and tail[2] == "properties" and (read or method == "PATCH"):
        return "workspace", "read" if read else "write"
    if area == "projects" and count == 4 and tail[2:] == ["documents", "upload"] and method == "POST":
        return "workspace", "write"
    if area == "projects" and count == 5 and tail[2] == "documents" and tail[4] == "signature-circuit" and (read or method in {"POST", "PATCH"}):
        return "workspace", "read" if read else "write"
    if area == "field-reports":
        if read and count in {1, 2}:
            return "workspace", "read"
        if (count == 1 and method == "POST") or (count == 2 and method == "PATCH") or (count == 3 and tail[2] == "action-link" and method == "POST"):
            return "workspace", "write"
    if area in {"organization", "organizations"}:
        if count == 3 and tail[1] == "current" and tail[2] == "modules":
            return "organization", "read" if read else "write"
        if count == 3 and tail[1] == "current" and tail[2] == "sovereign-export" and method == "POST":
            return "organization", "read"
        if count == 1 and method == "POST":
            return "organization", "write"
        if count == 3 and tail[1] == "members" and method == "PATCH":
            return "organization", "write"
        if count == 1 and (read or method == "PATCH"):
            return "organization", "read" if read else "write"
        if count == 2 and tail[1] in {"members", "roles", "audit"} and read:
            return tail[1], "read"
        if count >= 2 and tail[1] == "join-requests":
            return "organization", "read" if read else "write"
    if area == "audit" and count in {1, 2} and read:
        return "audit", "read"
    if area == "settings" and count == 1:
        return "organization", "read" if read else "write"
    if area == "mailbox" and count >= 2:
        section = tail[1]
        if section in {"capabilities", "folders"} and count == 2 and read:
            return "mail", "read"
        if section == "messages" and count in {2, 3}:
            return "mail", "read" if read else "flags" if method == "PATCH" and count == 3 else "write"
        if section == "drafts" and count in {2, 3}:
            return "mail", "write"
        if section == "send" and count == 2 and method == "POST":
            return "mail", "write"
    if area == "mail" and count in {1, 2} and read:
        return "mail", "read"
    if area == "sources" and ((count == 2 and read) or (count == 3 and tail[2] == "assignment" and method == "POST")):
        return "mail", "read" if read else "write"
    if area == "imports" and ((count == 1 and read) or (count == 2 and tail[1] == "eml" and method == "POST")):
        return "mail", "read" if read else "write"
    if area == "documents" and count == 3 and tail[2] in {"download", "preview"} and read:
        return "mail", "read"
    if area == "documents" and count == 3 and tail[2] == "decision" and method == "POST":
        return "workspace", "write"
    if area == "demo" and count == 2 and tail[1] == "next-mail" and method == "POST":
        # Fixed, server-owned fictional source, not arbitrary mail content.
        return "workspace", "write"
    if area == "projects":
        if count in {3, 4} and tail[2] == "access" and (read or method == "PUT"):
            return "organization", "write"
        if count == 3 and tail[2] == "retrieval" and read:
            return "workspace", "read"
        if count == 3 and tail[2] == "assistant" and method == "POST":
            return "workspace", "read"
        if count in {1, 2}:
            return "workspace", "read" if read else "write"
        if count == 3 and tail[2] in {"page", "documents", "notes", "summaries", "document-reviews", "event-details", "budget", "geo", "urbanisme", "port-inspections", "social-aid"}:
            # Idempotent page factory is required to open a read-only document.
            return "workspace", "read" if read or (tail[2] == "page" and method == "POST") else "write"
        if count == 4 and tail[2] == "budget" and tail[3] == "export.csv" and read:
            return "workspace", "read"
        if count >= 3 and tail[2] == "reservations":
            if count == 3 and read:
                return "workspace", "read"
            if count == 3 and method == "POST":
                return "workspace", "write"
            if count == 4 and method == "DELETE":
                return "workspace", "write"
        if count == 4 and tail[2] == "transmissions" and tail[3] == "finance":
            return "workspace", "read" if read else "write"

    if area == "pages" and (count == 1 or (count == 3 and tail[2] in {"state", "history"})):
        return "workspace", "read" if read else "write"
    if area == "reviews" and (count == 1 or (count == 3 and tail[2] == "decision")):
        return "workspace", "read" if read else "write"
    if area == "summaries" and (count in {1, 2} or (count == 3 and tail[2] in {"approve", "publish", "export"})):
        return "workspace", "read" if read else "write"
    if area == "commissions":
        if count == 1 and read:
            return "workspace", "read"
        if count == 2 and read:
            return "workspace", "read"
        if count == 3 and tail[2] == "members" and read:
            return "organization", "read"
        if count == 4 and tail[2] == "members" and method in {"PUT", "DELETE"}:
            return "organization", "write"
    if area == "culture" and count == 2 and tail[1] == "rooms" and read:
        return "workspace", "read"
    if area == "geo" and count == 2 and tail[1] == "features" and read:
        return "workspace", "read"
    if area == "social":
        if count == 2 and tail[1] == "quotient-calculator" and read:
            return "workspace", "read"
        if count in {2, 3, 4} and tail[1] in {"campaigns", "reminders"}:
            return "workspace", "read" if read else "write"
    if area == "finance" and count >= 2 and tail[1] == "transmissions":
        if count in {2, 3} and read:
            return "workspace", "read"
        if count == 4 and tail[3] == "decision" and method == "POST":
            return "workspace", "write"
    if area in {"sessions", "instances", "council-sessions"}:
        return "workspace", "read" if read else "write"
    if area == "jobs" and (count == 2 or (count == 3 and tail[2] == "retry")):
        return "workspace", "read" if read else "write"
    if area == "municipal":
        return ("workspace", "read") if read else ("organization", "write")
    if area == "workflows":
        return "workspace", "read" if read else "write"
    if area == "connectors":
        return "organization", "read" if read else "write"
    if area in {"validation", "anonymizer"}:
        return "workspace", "read" if read else "write"
    return None


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()
    ensure_public_demo_database(settings)
    repo = Repository(settings.db_path)
    pages = WorkspaceRepository(repo)
    queue = JobQueue(settings.db_path)
    sessions = SessionStore(settings.db_path)
    from .identity import IdentityStore
    from .project_access import ProjectAccess, access_scope
    from .commissions import CommissionRepository, register_commission_routes
    from .culture_finances import CultureFinancesRepository, setup_culture_finances_routes
    from .urbanisme_ports import UrbanismePortsRepository, setup_urbanisme_ports_routes
    from .enfance_sociale import EnfanceSocialeRepository, setup_enfance_sociale_routes
    from .seances_instances import SeancesInstancesRepository, setup_seances_instances_routes
    from .municipal_directory import MunicipalDirectoryRepository, register_municipal_directory_routes
    identities = repo.identity_store = IdentityStore(repo, settings.tenant_id, sessions)
    commissions = repo.commissions = CommissionRepository(repo)
    commissions.ensure_default_commissions(settings.tenant_id)
    culture_finances = repo.culture_finances = CultureFinancesRepository(repo)
    urbanisme_ports = repo.urbanisme_ports = UrbanismePortsRepository(repo)
    enfance_sociale = repo.enfance_sociale = EnfanceSocialeRepository(repo)
    seances_instances = repo.seances_instances = SeancesInstancesRepository(repo)
    from .council_sessions import CouncilSessionsRepository, register_council_sessions_routes
    council_sessions = repo.council_sessions = CouncilSessionsRepository(repo)
    council_sessions.seed_default_council_session(settings.tenant_id)
    municipal_directory = repo.municipal_directory = MunicipalDirectoryRepository(repo)
    municipal_directory.seed_default_directory(settings.tenant_id)
    from .organigram_engine import MunicipalOrganigramEngine, register_organigram_routes
    organigram = repo.organigram = MunicipalOrganigramEngine(municipal_directory)
    from .workflow_engine import WorkflowEngineRepository
    from .workflow_routes import register_workflow_routes
    workflow_engine = repo.workflow_engine = WorkflowEngineRepository(repo)
    project_access = repo.project_access = ProjectAccess(repo, settings)
    extractor = make_extractor(settings)
    tenant = settings.tenant_id
    if settings.fixture_mode:
        seed(repo, tenant)
        commissions.backfill_tenant(tenant)
        for source in repo.list_sources(tenant):
            if source["external_id"] == "next-mail-v1@demo.invalid":
                extract_source(repo, tenant, source["id"], extractor)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if hasattr(app.state, "identity_login"):
            app.state.identity_login.close()
        repo.close()

    app = FastAPI(title="Travaux — pilote municipal", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.repo, app.state.queue, app.state.settings = repo, queue, settings
    app.state.sessions, app.state.identities, app.state.project_access, app.state.pages = sessions, identities, project_access, pages
    app.state.commissions = commissions
    app.state.culture_finances = culture_finances
    app.state.urbanisme_ports = urbanisme_ports
    app.state.enfance_sociale = enfance_sociale
    app.state.seances_instances = seances_instances
    app.state.council_sessions = council_sessions
    app.state.municipal_directory = municipal_directory
    app.state.organigram = organigram
    app.state.workflow_engine = workflow_engine
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        telegram_webhook = request.method == "POST" and request.url.path == "/api/v1/integrations/telegram/webhook"
        if telegram_webhook and not settings.auth_required:
            return JSONResponse({"error": {"code": "forbidden", "message": "La démonstration refuse les connexions externes."}}, status_code=403)
        if request.method in {"POST", "PATCH", "PUT", "DELETE"} and not telegram_webhook:
            origin = request.headers.get("origin")
            expected = settings.public_origin.rstrip("/") if settings.mode != "demo" else f"{request.url.scheme}://{request.url.netloc}"
            if request.headers.get("X-Requested-With") != "Travaux" or (origin and origin != expected) or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"error": {"code": "csrf_rejected", "message": "Cette requête doit venir de l'application."}}, status_code=403)
            path = request.url.path.rstrip("/")
            if settings.test_organization_self_join and (path == "/api/v1/imports/eml" or path.startswith("/api/v1/integrations/")):
                return JSONResponse({"error": {"code": "forbidden", "message": "L’organisation test utilise uniquement des documents fictifs, sans messagerie externe."}}, status_code=403)
            if settings.mode == "public_demo" and (path == "/api/v1/imports/eml" or (path.startswith("/api/v1/summaries/") and path.endswith("/publish"))):
                return JSONResponse({"error": {"code": "public_demo_restricted", "message": "Démonstration publique : utilisez uniquement les courriels fictifs proposés. L'import de fichiers et les connexions externes sont désactivés."}}, status_code=403)
        response = await call_next(request)
        response.headers.update({
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Cache-Control": "public, max-age=31536000, immutable" if request.url.path.startswith("/native/assets/") else "no-cache" if request.url.path.startswith(("/native/", "/web/")) else "no-store",
        })
        if response.headers.get("content-disposition", "").lower().startswith("attachment"):
            response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        elif request.url.path.startswith("/api/v1/documents/") and request.url.path.endswith("/preview") and response.status_code == 200 and response.headers.get("content-type", "").startswith("application/pdf"):
            response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'; frame-ancestors 'self'"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    def actor(request: Request):
        if not settings.auth_required:
            current = {"actor_id": "responsable-demo", "tenant_id": tenant}
        else:
            current = sessions.resolve(request.cookies.get("travaux_session"))
        if current is None or current["tenant_id"] != tenant:
            raise DomainError("unauthenticated", "Connectez-vous pour accéder à cet espace.")
        if settings.auth_mode == "oidc" and identities.get_active(current["actor_id"]) is None:
            raise DomainError("unauthenticated", "Cet accès a été retiré. Reconnectez-vous avec votre compte professionnel.")
        governance = app.state.governance
        permission = request_permission(request.method, request.url.path)
        if permission is None:
            raise DomainError("forbidden", "Cette ressource n'est pas autorisée dans cet espace.")
        governance.require_authorized(current, *permission)
        scope = access_scope(repo, current)
        write = permission[1] in {"write", "flags"}
        guards = {"project_id": "project", "page_id": "page", "candidate_id": "candidate", "summary_id": "summary", "source_id": "source"}
        for key, kind in guards.items():
            if key in request.path_params:
                scope.require_object(kind, request.path_params[key], write=write)
        if request.query_params.get("project_id"):
            scope.require_project(request.query_params["project_id"], write=write)
        if scope.restricted and not scope.all_projects and request.url.path.split("/")[3] in {"imports", "jobs", "demo"}:
            raise DomainError("forbidden", "Cette opération exige un administrateur de l’espace.")
        # Module guard: verify module is enabled for specialized routes
        perms = governance.permissions(current)
        if hasattr(app.state, "organization_modules_repo"):
            repo_mod = app.state.organization_modules_repo
            req_path = request.url.path
            if not repo_mod.is_module_enabled(tenant, "messagerie_eml"):
                if "mail" in perms:
                    perms["mail"] = {**perms["mail"], "read": False, "write": False}
            if req_path.startswith("/api/v1/projects") and ("urbanisme" in req_path) and not repo_mod.is_module_enabled(tenant, "urbanisme_ads"):
                raise DomainError("forbidden", "Le module Urbanisme & PLU est désactivé pour cette collectivité.")
            if req_path.startswith("/api/v1/projects") and ("port-inspections" in req_path) and not repo_mod.is_module_enabled(tenant, "ports_littoral"):
                raise DomainError("forbidden", "Le module Ports & Littoral est désactivé pour cette collectivité.")
            if req_path.startswith("/api/v1/social") and not repo_mod.is_module_enabled(tenant, "enfance_ccas"):
                raise DomainError("forbidden", "Le module Enfance & CCAS est désactivé pour cette collectivité.")
            if req_path.startswith("/api/v1/finance") and not repo_mod.is_module_enabled(tenant, "finances_m57"):
                raise DomainError("forbidden", "Le module Finances M57 est désactivé pour cette collectivité.")
            if (req_path.startswith("/api/v1/sessions") or req_path.startswith("/api/v1/instances") or req_path.startswith("/api/v1/council-sessions")) and not repo_mod.is_module_enabled(tenant, "conseil_seances"):
                raise DomainError("forbidden", "Le module Séances du Conseil est désactivé pour cette collectivité.")
            if req_path.startswith("/api/v1/mailbox") and not repo_mod.is_module_enabled(tenant, "messagerie_eml"):
                raise DomainError("forbidden", "Le module Messagerie municipale est désactivé pour cette collectivité.")
        return {**current, "role": governance.current_role(current), "permissions": perms}

    @app.exception_handler(DomainError)
    async def domain_error(request, error):
        status = 404 if error.code == "not_found" else 401 if error.code == "unauthenticated" else 403 if error.code == "forbidden" else 429 if error.code == "conversation_limit" else 422 if error.code in {"invalid_input", "invalid_amount", "invalid_date", "invalid_evidence"} else 409
        return JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=status)

    from .documents import register_document_routes
    app.state.documents = register_document_routes(app, repo, tenant, actor)
    if settings.signature_workflow_enabled:
        from .signature_workflow import register_signature_workflow
        register_signature_workflow(app, repo, tenant, actor, app.state.documents)
    from .governance import register_governance_routes
    app.state.governance = register_governance_routes(app, repo, tenant, actor, settings)
    if settings.test_organization_self_join:
        with repo._transaction() as db:
            db.execute("UPDATE organization_profiles SET name='Mairie test',service='Présentation · données fictives' WHERE tenant_id=?", (tenant,))
    from .oidc import register_identity_routes
    app.state.identity_login = register_identity_routes(app, repo, settings, sessions, identities)
    from .account_onboarding import register_account_onboarding_routes
    app.state.account_onboarding = register_account_onboarding_routes(app, repo, settings, sessions, identities)
    from .identity_routes import register_member_routes
    register_member_routes(app, repo, tenant, actor, settings, members=identities, governance=app.state.governance)
    register_commission_routes(app, repo, tenant, actor, settings, commissions=commissions, governance=app.state.governance)
    register_municipal_directory_routes(app, repo, tenant, actor, municipal_directory)
    register_organigram_routes(app, repo, tenant, actor, organigram)
    register_workflow_routes(app, repo, tenant, actor, workflow_engine)
    from .intelligence_routes import register_intelligence_routes
    register_intelligence_routes(app, repo, tenant, actor, workflow_engine)
    from .organization_modules import register_organization_modules_routes
    app.state.organization_modules_repo = register_organization_modules_routes(app, settings.db_path, tenant, actor)
    from .connector_routes import register_connector_and_ux_routes
    app.state.connectors = register_connector_and_ux_routes(app, settings.db_path, tenant, actor)

    def _require_proj_read(pid, cur):
        access_scope(repo, cur).require_project(pid, write=False)

    def _require_proj_write(pid, cur):
        access_scope(repo, cur).require_project(pid, write=True)

    setup_culture_finances_routes(
        app,
        repo,
        settings,
        culture_finances,
        commissions,
        actor,
        _require_proj_write,
        _require_proj_read,
    )
    setup_urbanisme_ports_routes(
        app,
        repo,
        settings,
        urbanisme_ports,
        actor,
        _require_proj_write,
        _require_proj_read,
    )
    setup_enfance_sociale_routes(
        app,
        repo,
        settings,
        enfance_sociale,
        actor,
        _require_proj_write,
        _require_proj_read,
    )
    setup_seances_instances_routes(
        app,
        repo,
        settings,
        seances_instances,
        actor,
        _require_proj_write,
        _require_proj_read,
    )
    register_council_sessions_routes(
        app,
        repo,
        settings,
        council_sessions,
        actor,
    )
    from .mailbox import register_mailbox_routes
    app.state.mailbox = register_mailbox_routes(app, repo, tenant, actor, settings)
    from .assistant_dossier import register_assistant_routes
    app.state.assistant = register_assistant_routes(app, repo, tenant, actor, settings)
    from .document_review import register_document_review_routes
    app.state.document_reviews = register_document_review_routes(app, repo, tenant, actor)
    from .project_properties import register_project_profile_routes
    app.state.project_properties = register_project_profile_routes(app, repo, tenant, actor, settings)
    from .field_reports import register_field_report_routes
    app.state.field_reports = register_field_report_routes(app, repo, tenant, actor, settings)
    from .connection_hub import register_connection_routes
    app.state.connections = register_connection_routes(app, repo, tenant, actor, settings)
    from .anonymizer import register_anonymizer_routes
    app.state.anonymizer = register_anonymizer_routes(app, repo, tenant, actor, settings)
    from .audit_chain import register_audit_chain_routes
    app.state.audit_chain = register_audit_chain_routes(app, repo, tenant, actor, settings)
    from .mail_oauth import register_mail_oauth_routes
    app.state.mail_oauth = register_mail_oauth_routes(app, repo, tenant, actor, settings, hub=app.state.connections, governance=app.state.governance)
    from .mail_backfill import register_mail_backfill_routes
    app.state.mail_backfills = register_mail_backfill_routes(app, repo, tenant, actor, settings, hub=app.state.connections)
    from .calendars import register_calendar_routes
    app.state.calendars = register_calendar_routes(app, repo, tenant, actor, settings, hub=app.state.connections)
    from .conversations import register_conversation_routes
    app.state.conversations = register_conversation_routes(app, repo, tenant, actor, settings, calendars=app.state.calendars)
    from .telegram_routes import register_telegram_routes
    app.state.telegram = register_telegram_routes(app, repo, tenant, actor, settings, conversations=app.state.conversations, hub=app.state.connections, calendars=app.state.calendars)
    from .notifications import register_notification_routes
    app.state.notifications = register_notification_routes(app, repo, tenant, actor, settings, telegram=app.state.telegram, calendars=app.state.calendars)
    from .action_collaboration import register_action_collaboration_routes
    app.state.action_collaboration = register_action_collaboration_routes(app, repo, tenant, actor, settings)
    from .document_uploads import register_document_upload_routes
    app.state.document_uploads = register_document_upload_routes(app, repo, tenant, actor, settings, queue=queue, extractor=extractor)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Framework defaults can echo an entire invalid mail/password in detail.
        return JSONResponse({"error": {"code": "invalid_request", "message": "Champs absents, invalides ou trop volumineux. Vérifiez le formulaire."}}, status_code=422)

    def visible_ids(current, table, kind, project_id=None):
        scope = access_scope(repo, current)
        clause, args = scope.project_clause("project_id")
        where = "tenant_id=? AND "+clause
        params = [tenant, *args]
        if project_id:
            scope.require_project(project_id)
            where += " AND project_id=?"
            params.append(project_id)
        # Table and object kind are internal constants at every call site.
        if table not in {"candidates", "summaries", "native_pages"}:
            raise ValueError("Unknown scoped table")
        with repo._lock:
            ids = [row[0] for row in repo._db.execute("SELECT id FROM "+table+" WHERE "+where+" ORDER BY created_at,id", params)]
        result = []
        for ident in ids:
            try:
                scope.require_object(kind, ident)
                result.append(ident)
            except DomainError as failure:
                if failure.code != "not_found":
                    raise
        return result

    def visible_sources(current, project_id=None):
        scope = access_scope(repo, current)
        clause, args = scope.source_clause("s.id")
        sql = "SELECT s.id FROM sources s WHERE s.tenant_id=? AND "+clause
        params = [tenant, *args]
        if project_id:
            scope.require_project(project_id)
            sql += " AND EXISTS(SELECT 1 FROM source_links l WHERE l.tenant_id=s.tenant_id AND l.source_id=s.id AND l.project_id=?)"
            params.append(project_id)
        with repo._lock:
            ids = [row[0] for row in repo._db.execute(sql+" ORDER BY s.created_at,s.id", params)]
        return [scope.sanitize_source(repo.get_source(tenant, ident)) for ident in ids]

    def decorate_candidate(candidate, current):
        scope = access_scope(repo, current)
        scope.require_object("candidate", candidate["id"])
        result = dict(candidate)
        result["label"] = summary_field_label(result["field"])
        result["project_name"] = repo.get_project(tenant, result["project_id"])["name"]
        result["source"] = scope.sanitize_source(repo.get_source(tenant, result["source_id"]))
        previous = []
        for cid in result.get("conflict_with", []):
            try:
                scope.require_object("candidate", cid)
                previous.append(repo.get_candidate(tenant, cid))
            except DomainError as failure:
                if failure.code != "not_found":
                    raise
        result["previous_values"] = previous
        result["conflict_with"] = [row["id"] for row in previous]
        return result

    def decorate_summary(summary, current):
        access_scope(repo, current).require_object("summary", summary["id"])
        return {**summary, "project_revision": summary["snapshot_revision"], "project_name": repo.get_project(tenant, summary["project_id"])["name"]}

    def capabilities(current=None):
        installed_native = Path(__file__).resolve().parent / "native-editor" / "editor.js"
        checkout_native = Path(__file__).resolve().parents[2] / "native-editor" / "dist" / "editor.js"
        native_ready = installed_native.is_file() or checkout_native.is_file()
        native = {"status": "not_configured", "name": "AppFlowy", "url": settings.appflowy_url, "detail": "Installation native et contrat MCP à vérifier sur votre serveur. Aucune synchronisation distante active.", "can_publish": False}
        if settings.mode != "public_demo" and os.getenv("TRAVAUX_APPFLOWY_CONFIG"):
            try:
                from .native import NativeConfig
                NativeConfig.from_env(tenant)
                if os.getenv("TRAVAUX_APPFLOWY_TOKEN"):
                    native.update(status="configured", can_publish=True, detail="Configuration native présente. Le contrat et le contenu seront vérifiés lors de chaque publication.")
            except (OSError, ValueError, DomainError):
                native.update(status="unverified", detail="Configuration native incomplète ou non approuvée par l'exploitant.")
        exchange = {"status": "not_configured", "name": "Exchange local", "detail": "Collecteur en lecture seule fourni ; compte technique et serveur non configurés.", "can_send": False}
        if current is not None:
            provider = app.state.connections.mail_status(current)
            if provider["status"] != "not_connected":
                exchange.update(status=provider["status"], detail="Serveur vérifié et dossiers sélectionnés ; lancez l’import des courriels." if provider["status"] == "ready" else "Courriels importés en lecture seule. Aucun envoi de message n’est activé.", last_mail_sync_at=provider.get("last_successful_mail_sync_at"))
        return {
            "native_editor": {"status": "ready" if native_ready else "unavailable", "name": "AFFiNE BlockSuite intégré", "detail": "Pages, blocs, bases avec vues tableau et cartes, enregistrés dans cet espace. Les relations avancées, images et collaboration simultanée ne sont pas activées." if native_ready else "Le module de pages doit être construit avant l'ouverture des dossiers."},
            "appflowy": native,
            "exchange": exchange,
            "llm": {"status": "demo" if settings.llm == "demo" else "configured", "name": extractor.name, "detail": "Aucune donnée envoyée à un tiers." if settings.llm == "demo" else "Endpoint autorisé par configuration serveur. Contrats et localisation à valider avant données réelles."},
            "storage": {"status": "local", "name": "Mémoire locale persistante", "detail": "SQLite transactionnel, pilote sur un seul hôte."},
        }

    @app.get("/health/live")
    def health():
        return {"status": "ok"}

    @app.get("/api/v1/auth/options")
    def auth_options():
        """Safe entry-page capabilities; never disclose IdP configuration or account data."""
        identity = app.state.identity_login
        available = settings.auth_mode == "oidc" and identity.available
        return {"method": "demo" if not settings.auth_required else settings.auth_mode,
                "login_available": bool(available),
                "signup_available": bool(available and identity.signup_available),
                "recovery_available": bool(available and identity.recovery_available),
                "demo_available": not settings.auth_required,
                "private_access_url": settings.private_access_origin.rstrip("/") + "/connexion.html" if settings.private_access_origin else "",
                "label": "Connexion de la collectivité"}

    @app.get("/api/v1/session")
    def session(request: Request):
        current = {"actor_id": "responsable-demo", "tenant_id": tenant} if not settings.auth_required else sessions.resolve(request.cookies.get("travaux_session"))
        onboarding = app.state.account_onboarding.session_state(current) if settings.auth_mode == "oidc" else None
        if not onboarding and current and current["tenant_id"] != tenant:
            current = None
        auth = {"method": "demo" if not settings.auth_required else settings.auth_mode, "sso_available": app.state.identity_login.available, "signup_available": app.state.identity_login.signup_available, "label": "Connexion de la collectivité"}
        response = JSONResponse({"authenticated": bool(current), "demo": settings.fixture_mode, "public_demo": settings.mode == "public_demo", "auth_required": settings.auth_required, "actor": current, **({"auth": auth} if settings.auth_required else {}), **(onboarding or {})})
        if current and not settings.auth_required:
            from .conversations import conversation_owner
            conversation_owner(request, response, current, settings)
        return response

    @app.post("/api/v1/session")
    def login(request: Request, body: Login | None = None):
        if settings.mode == "public_demo":
            return session(request)
        if settings.auth_mode == "oidc":
            raise DomainError("forbidden", "Utilisez votre compte professionnel pour accéder à cet espace.")
        if body is None:
            raise DomainError("invalid_input", "Une phrase de passe est attendue pour cet espace protégé.")
        if not sessions.allow_attempt(request.client.host if request.client else "unknown"):
            return JSONResponse({"error": {"code": "rate_limit", "message": "Trop de tentatives. Réessayez dans cinq minutes."}}, status_code=429)
        if settings.mode != "demo" and not verify_password(body.password, settings.password_hash):
            return JSONResponse({"error": {"code": "unauthenticated", "message": "Connexion refusée."}}, status_code=401)
        token = sessions.issue("responsable", tenant)
        response = JSONResponse({"authenticated": True, "demo": settings.mode == "demo"})
        response.set_cookie("travaux_session", token, httponly=True, secure=settings.mode != "demo", samesite="strict", max_age=8 * 3600)
        return response

    @app.delete("/api/v1/session")
    def logout(request: Request):
        if settings.mode == "public_demo":
            return session(request)
        sessions.revoke(request.cookies.get("travaux_session", ""))
        response = JSONResponse({"authenticated": False})
        response.delete_cookie("travaux_session")
        return response

    @app.get("/api/v1/bootstrap")
    def bootstrap(current=Depends(actor)):
        scope = access_scope(repo, current)
        clause, args = scope.project_clause("id")
        with repo._lock:
            projects = [dict(row) for row in repo._db.execute("SELECT id,status FROM projects WHERE tenant_id=? AND "+clause, [tenant, *args])]
        reviews = [repo.get_candidate(tenant, ident) for ident in visible_ids(current, "candidates", "candidate")]
        reviews = [decorate_candidate(row, current) for row in reviews if row["status"] == "pending"]
        summaries = [repo.get_summary(tenant, ident) for ident in visible_ids(current, "summaries", "summary")]
        commissions_list = []
        for comm in app.state.commissions.list_commissions(tenant):
            caps = scope.commission_capabilities(comm["id"])
            commissions_list.append(
                {
                    **comm,
                    "capabilities": caps,
                    "can_read": caps["can_read"],
                    "can_edit": caps["can_edit"],
                    "can_submit_for_review": caps["can_submit_for_review"],
                    "role": caps["role"],
                }
            )
        return {
            "demo": settings.fixture_mode,
            "role": current["role"],
            "permissions": current["permissions"],
            "access": {
                "auth_required": settings.auth_required,
                "shared_demo": settings.mode == "public_demo",
                "mail_import": settings.mode != "public_demo" and scope.all_projects,
                "signature_workflow": settings.signature_workflow_enabled,
                **({"project_create": scope.all_projects} if scope.restricted else {}),
            },
            "workspace": {
                "name": "Travaux · Démonstration" if settings.mode != "pilot" else "Travaux",
                "subtitle": "Données entièrement fictives" if settings.mode != "pilot" else "Espace institutionnel",
            },
            "commissions": commissions_list,
            "capabilities": capabilities(current),
            "stats": {
                "projects": len(projects),
                "active_projects": sum(p["status"] == "active" for p in projects),
                "pending_reviews": len(reviews),
                "conflicts": sum(bool(c["conflict_with"]) for c in reviews),
                "sources": len(visible_sources(current)),
                "approved_summaries": sum(s["status"] == "approved" for s in summaries),
            },
        }

    @app.get("/api/v1/settings")
    def get_settings(current=Depends(actor)):
        return {"mode": settings.mode, "demo": settings.fixture_mode, "capabilities": capabilities(current), "retention": "Durées à définir avec les archives et le DPO avant données réelles.", "privacy": "Aucun transfert automatique vers Gmail, Google ou ChatGPT.", "version": __version__}

    @app.get("/api/v1/projects")
    def projects(commission_id: str | None = None, current=Depends(actor)):
        results = []
        scope = access_scope(repo, current, commission_id=commission_id)
        clause, args = scope.project_clause("id")
        with repo._lock:
            permitted_projects = [
                dict(row)
                for row in repo._db.execute(
                    "SELECT * FROM projects WHERE tenant_id=? AND " + clause + " ORDER BY created_at,id",
                    [tenant, *args],
                )
            ]
        for project in permitted_projects:
            memory = scope.sanitize_memory(repo.get_memory(tenant, project["id"]))
            events = repo.list_events(tenant, project["id"])
            properties = app.state.project_properties.get(tenant, project["id"], current)
            caps = scope.project_capabilities(project["id"])
            results.append(
                {
                    **project,
                    "capabilities": caps,
                    "can_edit": caps["can_edit"],
                    "can_submit_for_review": caps["can_submit_for_review"],
                    "properties": {
                        "values": properties["values"],
                        "origins": properties["origins"],
                        "revision": properties["revision"],
                    },
                    "pending_count": len(memory["pending"]),
                    "conflict_count": len(memory["conflicts"]),
                    "source_count": len(memory["sources"]),
                    "progress": next((f["value"] for f in memory["facts"] if f["field"] == "progress"), "À renseigner"),
                    "updated_at": events[-1]["created_at"] if events else project.get("created_at"),
                }
            )
        return results

    @app.post("/api/v1/projects", status_code=201)
    def create_project(body: ProjectInput, current=Depends(actor)):
        scope = access_scope(repo, current)
        comm_id = body.commission_id or "commission-3"
        caps = scope.commission_capabilities(comm_id)
        if not scope.all_projects and not caps["can_edit"]:
            raise DomainError(
                "forbidden",
                "La création d’un dossier exige un administrateur ou les droits d'édition dans cette commission.",
            )
        from .project_creation import create_with_profile
        return create_with_profile(repo, tenant, current["actor_id"], **body.model_dump())

    @app.get("/api/v1/projects/{project_id}")
    def project(project_id: str, current=Depends(actor)):
        scope = access_scope(repo, current)
        memory = scope.sanitize_memory(repo.get_memory(tenant, project_id))
        facts = [decorate_candidate(c, current) for c in memory["facts"]]
        properties = app.state.project_properties.get(tenant, project_id, current)
        caps = scope.project_capabilities(project_id)
        return {
            **memory["project"],
            **memory,
            "capabilities": caps,
            "can_edit": caps["can_edit"],
            "can_submit_for_review": caps["can_submit_for_review"],
            "properties": {"values": properties["values"], "origins": properties["origins"], "revision": properties["revision"]},
            "facts": facts,
            "actions": [f for f in facts if f["field"].startswith("action.")],
            "summaries": [decorate_summary(repo.get_summary(tenant, ident), current) for ident in visible_ids(current, "summaries", "summary", project_id)],
            "events": repo.list_events(tenant, project_id) if scope.all_projects else [],
            "history_candidates": [decorate_candidate(repo.get_candidate(tenant, ident), current) for ident in visible_ids(current, "candidates", "candidate", project_id)],
        }

    @app.post("/api/v1/projects/{project_id}/page")
    def ensure_native_page(project_id: str, current=Depends(actor)):
        access_scope(repo, current).require_project_contents(project_id)
        return pages.ensure_main(tenant, project_id)

    @app.get("/api/v1/pages")
    def list_pages(project_id: str | None = None, current=Depends(actor)):
        return [pages.get(tenant, ident) for ident in visible_ids(current, "native_pages", "page", project_id)]

    @app.get("/api/v1/pages/{page_id}/state")
    def get_page_state(page_id: str, current=Depends(actor)):
        return pages.get(tenant, page_id)

    @app.put("/api/v1/pages/{page_id}/state")
    def save_page_state(page_id: str, body: PageState, current=Depends(actor)):
        return pages.save(tenant, page_id, **body.model_dump(), actor_id=current["actor_id"])

    @app.get("/api/v1/pages/{page_id}/history")
    def page_history(page_id: str, current=Depends(actor)):
        return pages.history(tenant, page_id)

    @app.get("/api/v1/mail")
    def mail(q: str = "", project_id: str | None = None, match_status: str | None = None, current=Depends(actor)):
        if len(q) > 200 or match_status not in {None, "", "matched", "unmatched", "ambiguous"}:
            raise DomainError("invalid_input", "Filtre de courrier invalide.")
        items = [s for s in visible_sources(current, project_id) if not s["metadata"].get("note_id") and not s["metadata"].get("parent_source_id") and s["metadata"].get("source_kind") != "uploaded_document"]
        if match_status:
            items = [s for s in items if s["match_status"] == match_status]
        if q.strip():
            needle = q.casefold().strip()
            items = [s for s in items if needle in (s["subject"] + " " + s["sender"] + " " + s["body"]).casefold()]
        items.sort(key=lambda s: s["received_at"], reverse=True)
        return {"items": items[:200], "total": len(items)}

    @app.get("/api/v1/mail/{source_id}")
    def mail_message(source_id: str, current=Depends(actor)):
        source = access_scope(repo, current).sanitize_source(repo.get_source(tenant, source_id))
        if source["metadata"].get("note_id") or source["metadata"].get("source_kind") == "uploaded_document":
            raise DomainError("not_found", "Ce document n'est pas un courrier.")
        children = [s for s in visible_sources(current) if s["metadata"].get("parent_source_id") == source_id]
        return {**source, "related_sources": children}

    @app.post("/api/v1/projects/{project_id}/notes", status_code=201)
    def add_note(project_id: str, body: Note, current=Depends(actor)):
        return repo.add_note(tenant, project_id, body.body, actor_id=current["actor_id"])

    @app.get("/api/v1/reviews")
    def reviews(project_id: str | None = None, current=Depends(actor)):
        rows = [repo.get_candidate(tenant, ident) for ident in visible_ids(current, "candidates", "candidate", project_id)]
        return [decorate_candidate(row, current) for row in rows if row["status"] == "pending"]

    @app.post("/api/v1/reviews/{candidate_id}/decision")
    def review(candidate_id: str, body: Decision, current=Depends(actor)):
        if body.corrected_value is not None:
            if body.decision != "accept" or not body.reason.strip():
                raise DomainError("invalid_input", "Une correction exige une confirmation et un motif.")
            return decorate_candidate(repo.correct_candidate(tenant, candidate_id, body.corrected_value, body.reason, actor_id=current["actor_id"], expected_revision=body.expected_revision), current)
        return decorate_candidate(repo.review_candidate(tenant, candidate_id, body.decision, actor_id=current["actor_id"], expected_revision=body.expected_revision), current)

    @app.get("/api/v1/sources/{source_id}")
    def source(source_id: str, current=Depends(actor)):
        return access_scope(repo, current).sanitize_source(repo.get_source(tenant, source_id))

    @app.post("/api/v1/sources/{source_id}/assignment")
    def assignment(source_id: str, body: Assignment, current=Depends(actor)):
        scope = access_scope(repo, current)
        scope.require_source(source_id)
        scope.require_project(body.project_id, write=True)
        children = [s for s in repo.list_sources(tenant) if s["metadata"].get("parent_source_id") == source_id]
        for child in children:
            scope.require_source(child["id"])
        if any(s.get("project_ids") and body.project_id not in s["project_ids"] for s in children):
            raise DomainError("assignment_conflict", "Une pièce jointe est déjà liée à un autre chantier : vérifiez-la séparément.")
        result = repo.assign_source(tenant, source_id, body.project_id, actor_id=current["actor_id"])
        job_id = queue.enqueue(tenant, "extract", {"source_id": source_id}, f"{source_id}:assignment:{body.project_id}")
        related_jobs = []
        for child in children:
            repo.assign_source(tenant, child["id"], body.project_id, actor_id=current["actor_id"])
            related_jobs.append(queue.enqueue(tenant, "extract", {"source_id": child["id"]}, f"{child['id']}:assignment:{body.project_id}"))
        if settings.llm == "demo":
            for _ in range(1 + len(related_jobs)):
                process_one(queue, repo, extractor)
        return {**result, "job_id": job_id, "related_job_ids": related_jobs}

    @app.get("/api/v1/imports")
    def imports(current=Depends(actor)):
        return {"sources": [s for s in repo.list_sources(tenant) if not s["metadata"].get("note_id")], "jobs": queue.list(tenant)}

    @app.post("/api/v1/imports/eml", status_code=202)
    def import_eml(body: ImportMail, current=Depends(actor)):
        if not body.filename.lower().endswith(".eml"):
            raise DomainError("invalid_input", "Un fichier .eml est attendu.")
        from .importing import import_mail
        from .integrations.mail import MailParseError
        try:
            raw = base64.b64decode(body.content_base64, validate=True) if body.content_base64 is not None else body.content.encode("utf-8")
        except (ValueError, binascii.Error):
            raise DomainError("invalid_input", "Encodage du fichier EML invalide.") from None
        if len(raw) > 2_000_000:
            raise DomainError("invalid_input", "Fichier EML limité à 2 Mo.")
        try:
            result = import_mail(repo, queue, tenant, raw, metadata={"filename": body.filename})
        except MailParseError:
            raise DomainError("invalid_input", "Message MIME invalide ou trop volumineux.") from None
        if settings.llm == "demo":
            for _ in result["job_ids"]:
                process_one(queue, repo, extractor)
        return {**result, "status": queue.get(tenant, result["job_id"])["status"]}

    @app.post("/api/v1/demo/next-mail")
    def next_mail(current=Depends(actor)):
        if not settings.fixture_mode:
            raise DomainError("not_found", "Fonction réservée à la démonstration.")
        source = add_next_mail(repo, tenant)
        job_id = queue.enqueue(tenant, "extract", {"source_id": source["id"]}, source["id"])
        process_one(queue, repo, extractor)
        return {"source": source, "job_id": job_id, "status": "imported"}

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str, current=Depends(actor)):
        result = queue.get(tenant, job_id)
        if result is None:
            raise DomainError("not_found", "Traitement introuvable.")
        return result

    @app.post("/api/v1/jobs/{job_id}/retry")
    def retry_job(job_id: str, current=Depends(actor)):
        if not queue.retry(tenant, job_id):
            raise DomainError("invalid_state", "Seul un traitement en échec peut être relancé.")
        return queue.get(tenant, job_id)

    @app.get("/api/v1/summaries")
    def summaries(current=Depends(actor)):
        return [decorate_summary(repo.get_summary(tenant, ident), current) for ident in visible_ids(current, "summaries", "summary")]

    @app.get("/api/v1/summaries/{summary_id}")
    def summary(summary_id: str, current=Depends(actor)):
        return decorate_summary(repo.get_summary(tenant, summary_id), current)

    @app.post("/api/v1/projects/{project_id}/summaries", status_code=201)
    def generate_summary(project_id: str, body: SummaryRequest, current=Depends(actor)):
        access_scope(repo, current).require_project_contents(project_id)
        return decorate_summary(repo.create_summary(tenant, project_id, actor_id=current["actor_id"]), current)

    @app.patch("/api/v1/summaries/{summary_id}")
    def edit_summary(summary_id: str, body: EditSummary, current=Depends(actor)):
        return decorate_summary(repo.edit_summary(tenant, summary_id, body.content, expected_content_hash=body.expected_content_hash, actor_id=current["actor_id"]), current)

    @app.post("/api/v1/summaries/{summary_id}/approve")
    def approve_summary(summary_id: str, body: Approval, current=Depends(actor)):
        return decorate_summary(repo.approve_summary(tenant, summary_id, **body.model_dump(), actor_id=current["actor_id"]), current)

    @app.post("/api/v1/summaries/{summary_id}/publish")
    async def native_publication(summary_id: str, body: Publish, current=Depends(actor)):
        from .native import publish_summary
        # Content is never taken from this HTTP body: only the approved DB snapshot.
        try:
            return await publish_summary(settings, repo, summary_id, body.expected_content_hash)
        except DomainError:
            raise
        except Exception:
            raise DomainError("integration_unavailable", "Connexion native indisponible. Vérifiez la configuration et l'autorisation du compte.") from None

    @app.get("/api/v1/summaries/{summary_id}/export")
    def export_summary(summary_id: str, format: str = "md", current=Depends(actor)):
        result = repo.get_summary(tenant, summary_id)
        if result["status"] != "approved":
            raise DomainError("invalid_state", "Valider cette version avant de l'exporter.")
        citations = "\n\nSources :\n" + "\n".join(f"- {c['source_id']} : {c['quote']}" for c in result["citations"])
        notice = f"Version {result['version']} — validée le {result['approved_at']} — mémoire révision {result['snapshot_revision']}\n"
        notice += f"Couverture : {result.get('coverage', 'partial')}\n"
        notice += "\n".join(f"Attention : {warning}" for warning in result.get("warnings", [])) + "\n"
        if result["stale"]:
            notice += "ARCHIVE : le chantier a évolué depuis cette validation.\n"
        content = notice + "\n" + result["content"] + citations
        if format == "html":
            from .exporting import render_summary_html
            content = render_summary_html(result)
        elif format != "md":
            raise DomainError("invalid_input", "Formats disponibles : md, html.")
        return Response(content, media_type="text/html" if format == "html" else "text/markdown", headers={"Content-Disposition": f'attachment; filename="recapitulatif-v{result["version"]}.{format}"'})

    packaged_web = Path(__file__).resolve().parent / "web"
    web = packaged_web if packaged_web.is_dir() else Path(__file__).resolve().parents[2] / "web"
    if web.exists():
        app.mount("/web", StaticFiles(directory=web), name="web")
        @app.get("/")
        def index():
            return FileResponse(web / "connexion.html")
        @app.get("/connexion.html")
        def connection_entry():
            return FileResponse(web / "connexion.html")
        @app.get("/inscription.html")
        def signup_entry():
            return FileResponse(web / "inscription.html")
        @app.get("/mot-de-passe-oublie.html")
        def recovery_entry():
            return FileResponse(web / "mot-de-passe-oublie.html")
        @app.get("/mentions-legales.html")
        def legal_entry():
            return FileResponse(web / "mentions-legales.html")
        @app.get("/confidentialite.html")
        def privacy_entry():
            return FileResponse(web / "confidentialite.html")
        @app.get("/demo.html")
        @app.get("/espace.html")
        def application_entry():
            return FileResponse(web / "index.html")
    packaged_native = Path(__file__).resolve().parent / "native-editor"
    native_dist = packaged_native if packaged_native.is_dir() else Path(__file__).resolve().parents[2] / "native-editor" / "dist"
    if native_dist.is_dir():
        app.mount("/native", StaticFiles(directory=native_dist), name="native-editor")
    return app
