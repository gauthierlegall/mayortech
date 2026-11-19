"""AppFlowy transport bound to a reviewed, installation-specific OpenAPI contract.

No native page-writing route or rich-text shape is guessed here. The manifest is
operator configuration, not data returned by an LLM or supplied by an API caller.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractError(ValueError):
    """A local vendor contract is missing, unsafe, or inconsistent."""


class IntegrationUnavailable(RuntimeError):
    """Safe, machine-readable failure; never contains remote response bodies."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class RouteBinding(_Model):
    path: str
    method: Literal["GET", "POST"]
    operation_id: str
    proof_ref: str = Field(min_length=1, max_length=500)
    path_bindings: dict[str, str] = Field(default_factory=dict)
    request_constants: dict[str, Any] = Field(default_factory=dict)
    request_bindings: dict[str, str] = Field(default_factory=dict)
    response_id_pointer: str
    response_content_pointer: str


class AppFlowyManifest(_Model):
    tenant_id: str = Field(min_length=1, max_length=200)
    workspace_id: str = Field(min_length=1, max_length=200)
    origin: str
    server_version: str = Field(min_length=1, max_length=200)
    api_version: str
    openapi_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    read_object: RouteBinding | None = None
    create_version: RouteBinding | None = None
    content_roundtrip_verified: bool = False


class PublicationRequest(_Model):
    tenant_id: str = Field(min_length=1, max_length=200)
    publication_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,200}$")
    parent_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,200}$")
    title: str = Field(min_length=1, max_length=300)
    content_markdown: str = Field(min_length=1, max_length=250_000, repr=False)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_hash(self):
        if hashlib.sha256(self.content_markdown.encode("utf-8")).hexdigest() != self.content_sha256:
            raise ValueError("content_hash_mismatch")
        return self


class PublicationResult(_Model):
    publication_id: str
    status: Literal["published", "uncertain", "rejected", "unavailable"]
    remote_object_id: str | None = None
    code: str
    mode: Literal["real", "fake"] = "real"


class WorkspaceObject(_Model):
    tenant_id: str
    object_id: str
    content: Any = Field(repr=False)
    content_sha256: str
    # No server revision / author is invented from a content hash or page text.
    revision: str | None = None
    actor_id: str | None = None
    actor_verified: bool = False


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def openapi_sha256(document: dict[str, Any]) -> str:
    """Hash canonical UTF-8 JSON, not bytes affected by pretty-print formatting."""
    return hashlib.sha256(_canonical(document).encode("utf-8")).hexdigest()


def _pointer(value: Any, pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise ContractError("invalid_json_pointer")
    try:
        for raw in pointer[1:].split("/"):
            part = raw.replace("~1", "/").replace("~0", "~")
            value = value[int(part)] if isinstance(value, list) else value[part]
        return value
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ContractError("missing_json_pointer") from exc


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
        raise IntegrationUnavailable("unsafe_object_id")
    return value


def _origin(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}
            or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})):
        raise ContractError("unsafe_origin")
    return value.rstrip("/")


class SQLitePublicationLedger:
    """Crash-safe reservation BEFORE any create request. Contains no mail/content.

    A reserved/uncertain publication stays blocked until explicit reconciliation
    outside this adapter. It is never automatically released because of a timeout.
    """

    def __init__(self, path: str | Path):
        if str(path) == ":memory:":
            raise ValueError("durable_ledger_required")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS appflowy_publication_attempts (
                tenant TEXT NOT NULL, workspace TEXT NOT NULL, publication TEXT NOT NULL,
                fingerprint TEXT NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY (tenant, workspace, publication))""")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def reserve(self, tenant: str, workspace: str, request: PublicationRequest) -> PublicationResult | None:
        fingerprint = openapi_sha256(request.model_dump())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT fingerprint, result FROM appflowy_publication_attempts WHERE tenant=? AND workspace=? AND publication=?",
                (tenant, workspace, request.publication_id),
            ).fetchone()
            if row:
                if row[0] != fingerprint:
                    return PublicationResult(publication_id=request.publication_id, status="rejected", code="publication_id_reused")
                return PublicationResult.model_validate_json(row[1])
            pending = PublicationResult(publication_id=request.publication_id, status="uncertain", code="requires_reconciliation")
            connection.execute(
                "INSERT INTO appflowy_publication_attempts VALUES (?, ?, ?, ?, ?)",
                (tenant, workspace, request.publication_id, fingerprint, pending.model_dump_json()),
            )
        return None

    def complete(self, tenant: str, workspace: str, request: PublicationRequest, result: PublicationResult) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE appflowy_publication_attempts SET result=? WHERE tenant=? AND workspace=? AND publication=? AND fingerprint=?",
                (result.model_dump_json(), tenant, workspace, request.publication_id, openapi_sha256(request.model_dump())),
            )


class _Contract:
    def __init__(self, document: dict[str, Any], manifest: AppFlowyManifest):
        self.document = copy.deepcopy(document)
        if openapi_sha256(document) != manifest.openapi_sha256:
            raise ContractError("openapi_hash_mismatch")
        if not str(document.get("openapi", "")).startswith("3."):
            raise ContractError("openapi_3_required")
        if document.get("info", {}).get("version") != manifest.api_version:
            raise ContractError("openapi_version_mismatch")
        self._check_refs(document)
        self.schemas: dict[str, tuple[dict[str, Any] | None, dict[str, Any]]] = {}
        self.response_statuses: dict[str, int] = {}
        for binding, method in ((manifest.read_object, "GET"), (manifest.create_version, "POST")):
            if binding is not None:
                self._bind(binding, method)

    def _check_refs(self, value: Any):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"$ref", "$dynamicRef", "$recursiveRef"} and (not isinstance(child, str) or not child.startswith("#/")):
                    raise ContractError("external_schema_reference")
                self._check_refs(child)
        elif isinstance(value, list):
            for child in value:
                self._check_refs(child)

    def _resolve(self, value: dict[str, Any]) -> dict[str, Any]:
        seen = set()
        while "$ref" in value:
            reference = value["$ref"]
            if reference in seen:
                raise ContractError("recursive_schema_path")
            seen.add(reference)
            value = _pointer(self.document, reference[1:])
        return value

    def _schema_field(self, schema: dict[str, Any], pointer: str):
        if not pointer.startswith("/"):
            raise ContractError("invalid_json_pointer")
        current = schema
        for raw in pointer[1:].split("/"):
            current = self._resolve(current)
            key = raw.replace("~1", "/").replace("~0", "~")
            if key not in current.get("properties", {}):
                raise ContractError("undeclared_request_field")
            current = current["properties"][key]
        return self._resolve(current)

    def _bind(self, binding: RouteBinding, method: str):
        if (binding.method != method or not binding.path.startswith("/api/")
                or any(mark in binding.path for mark in ("..", "?", "#", "%", "//"))):
            raise ContractError("unsafe_operation_path")
        path_item = self.document.get("paths", {}).get(binding.path, {})
        operation = path_item.get(method.lower())
        if not isinstance(operation, dict):
            raise ContractError("operation_not_in_openapi")
        if operation.get("operationId") != binding.operation_id:
            raise ContractError("operation_id_mismatch")
        placeholders = set(re.findall(r"\{([^{}]+)\}", binding.path))
        if placeholders != set(binding.path_bindings):
            raise ContractError("path_bindings_mismatch")
        if any(value not in {"workspace_id", "object_id"} for value in binding.path_bindings.values()):
            raise ContractError("unsupported_path_binding")
        declared_paths = set()
        for raw in path_item.get("parameters", []) + operation.get("parameters", []):
            parameter = self._resolve(raw)
            if parameter.get("in") == "path":
                declared_paths.add(parameter.get("name"))
            elif parameter.get("required"):
                raise ContractError("unsupported_required_parameter")
        if declared_paths != placeholders:
            raise ContractError("undeclared_path_parameter")
        responses = operation.get("responses", {})
        response = responses.get("200") or responses.get("201")
        if not response:
            raise ContractError("json_success_response_required")
        response = self._resolve(response)
        response_schema = response.get("content", {}).get("application/json", {}).get("schema")
        if not isinstance(response_schema, dict):
            raise ContractError("json_success_response_required")
        self._schema_field(response_schema, binding.response_id_pointer)
        self._schema_field(response_schema, binding.response_content_pointer)
        request_schema = None
        if method == "POST":
            request = self._resolve(operation.get("requestBody", {}))
            request_schema = request.get("content", {}).get("application/json", {}).get("schema")
            if not isinstance(request_schema, dict):
                raise ContractError("json_request_schema_required")
            for pointer, source in binding.request_bindings.items():
                self._schema_field(request_schema, pointer)
                if source not in {"parent_id", "title", "content_markdown", "publication_id"}:
                    raise ContractError("unsupported_request_binding")
            if "content_markdown" not in binding.request_bindings.values():
                raise ContractError("content_write_not_mapped")
        for schema in (request_schema, response_schema):
            if schema is not None:
                try:
                    Draft202012Validator.check_schema(self._wrapped(schema))
                except Exception as exc:
                    raise ContractError("unsupported_json_schema") from exc
        self.schemas[binding.operation_id] = request_schema, response_schema
        self.response_statuses[binding.operation_id] = 200 if "200" in responses else 201

    def _wrapped(self, schema):
        # Internal '#/components/...' refs remain local. No network resolver exists.
        return {**schema, "components": self.document.get("components", {})}

    def validate(self, binding: RouteBinding, value: Any, *, request=False):
        schema = self.schemas[binding.operation_id][0 if request else 1]
        if schema is None:
            raise ContractError("request_schema_missing")
        validator = Draft202012Validator(self._wrapped(schema), format_checker=FormatChecker())
        if next(validator.iter_errors(value), None) is not None:
            raise ContractError("request_schema_mismatch" if request else "response_schema_mismatch")


class AppFlowyHTTPAdapter:
    mode = "real"

    def __init__(self, *, base_url: str, token: str, manifest: AppFlowyManifest,
                 openapi: dict[str, Any], ledger: SQLitePublicationLedger,
                 transport: httpx.AsyncBaseTransport | None = None, timeout_seconds: float = 15):
        origin = _origin(base_url)
        if origin != _origin(manifest.origin):
            raise ContractError("manifest_origin_mismatch")
        self.manifest = manifest.model_copy(deep=True)
        self.contract = _Contract(openapi, self.manifest)
        self.ledger = ledger
        self._client = httpx.AsyncClient(
            base_url=origin, headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds, follow_redirects=False, trust_env=False,
            transport=transport, limits=httpx.Limits(max_connections=4),
        )

    async def aclose(self):
        await self._client.aclose()

    async def inspect_capabilities(self) -> dict[str, Any]:
        return {"mode": self.mode, "server_version": self.manifest.server_version,
                "read_object": self.manifest.read_object is not None,
                "create_version": self._can_publish(), "conditional_write": False,
                "read_changes": False, "author_verified": False,
                "proof": "installation_manifest_required; live qualification remains operator responsibility"}

    def _can_publish(self):
        return bool(self.manifest.read_object and self.manifest.create_version
                    and self.manifest.content_roundtrip_verified)

    def _check_tenant(self, tenant_id):
        if tenant_id != self.manifest.tenant_id:
            raise IntegrationUnavailable("tenant_mismatch")

    def _path(self, binding, *, object_id=None):
        values = {"workspace_id": _safe_id(self.manifest.workspace_id)}
        if object_id is not None:
            values["object_id"] = _safe_id(object_id)
        try:
            return binding.path.format(**{key: values[value] for key, value in binding.path_bindings.items()})
        except KeyError as exc:
            raise ContractError("missing_path_value") from exc

    async def _response(self, binding, *, object_id=None, payload=None):
        response = await self._client.request(binding.method, self._path(binding, object_id=object_id), json=payload)
        if response.status_code >= 500 or response.status_code == 429:
            raise IntegrationUnavailable("remote_outcome_uncertain")
        if not 200 <= response.status_code < 300:
            raise IntegrationUnavailable("remote_http_rejected")
        if response.status_code != self.contract.response_statuses[binding.operation_id]:
            raise IntegrationUnavailable("undocumented_success_status")
        try:
            body = response.json()
        except (ValueError, UnicodeError) as exc:
            raise IntegrationUnavailable("invalid_remote_response") from exc
        if not isinstance(body, dict) or type(body.get("code")) is not int:
            raise IntegrationUnavailable("invalid_remote_envelope")
        if body["code"] != 0:
            raise IntegrationUnavailable("vendor_business_error")
        try:
            self.contract.validate(binding, body)
        except ContractError as exc:
            raise IntegrationUnavailable("invalid_remote_response") from exc
        return body

    async def read_object(self, *, tenant_id: str, object_id: str) -> WorkspaceObject:
        self._check_tenant(tenant_id)
        _safe_id(object_id)
        binding = self.manifest.read_object
        if binding is None:
            raise IntegrationUnavailable("read_unavailable")
        try:
            body = await self._response(binding, object_id=object_id)
            remote_id = _pointer(body, binding.response_id_pointer)
            if remote_id != object_id:
                raise IntegrationUnavailable("remote_object_mismatch")
            content = _pointer(body, binding.response_content_pointer)
        except ContractError as exc:
            raise IntegrationUnavailable("invalid_remote_response") from exc
        except httpx.HTTPError as exc:
            raise IntegrationUnavailable("remote_read_failed") from exc
        canonical = content if isinstance(content, str) else _canonical(content)
        return WorkspaceObject(tenant_id=tenant_id, object_id=object_id, content=content,
                               content_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest())

    async def publish_version(self, request: PublicationRequest) -> PublicationResult:
        def result(status, code, object_id=None):
            return PublicationResult(publication_id=request.publication_id, status=status, code=code, remote_object_id=object_id)

        if request.tenant_id != self.manifest.tenant_id:
            return result("rejected", "tenant_mismatch")
        if not self._can_publish():
            return result("unavailable", "create_version_not_qualified")
        binding = self.manifest.create_version
        assert binding is not None
        payload = copy.deepcopy(binding.request_constants)
        for pointer, source in binding.request_bindings.items():
            target = payload
            keys = [key.replace("~1", "/").replace("~0", "~") for key in pointer[1:].split("/")]
            for key in keys[:-1]:
                target = target.setdefault(key, {})
            target[keys[-1]] = getattr(request, source)
        try:
            self.contract.validate(binding, payload, request=True)
        except ContractError:
            return result("rejected", "request_schema_mismatch")
        previous = self.ledger.reserve(request.tenant_id, self.manifest.workspace_id, request)
        if previous is not None:
            return previous
        remote_id = None
        try:
            body = await self._response(binding, payload=payload)
            candidate_id = _pointer(body, binding.response_id_pointer)
            if not isinstance(candidate_id, str):
                raise IntegrationUnavailable("invalid_remote_response")
            remote_id = _safe_id(candidate_id)
            observed = await self.read_object(tenant_id=request.tenant_id, object_id=remote_id)
            if observed.content != request.content_markdown:
                raise IntegrationUnavailable("content_readback_mismatch")
            outcome = result("published", "created_and_read_back", remote_id)
        except httpx.HTTPError:
            outcome = result("uncertain", "requires_reconciliation", remote_id)
        except (IntegrationUnavailable, ContractError) as exc:
            # A successful create followed by a rejected read is still ambiguous.
            rejected = remote_id is None and str(exc) in {"vendor_business_error", "remote_http_rejected"}
            outcome = result("rejected" if rejected else "uncertain", str(exc), remote_id)
        self.ledger.complete(request.tenant_id, self.manifest.workspace_id, request, outcome)
        return outcome


class FakeAppFlowyWorkspace:
    """In-memory fake only. It does not emulate native permissions or a server."""
    mode = "fake"

    def __init__(self, *, tenant_id: str):
        self.tenant_id = tenant_id
        self._objects: dict[str, WorkspaceObject] = {}
        self._publications: dict[str, tuple[str, PublicationResult]] = {}

    async def inspect_capabilities(self):
        return {"mode": "fake", "create_version": True, "read_object": True, "conditional_write": False,
                "read_changes": False, "author_verified": False, "production_qualified": False}

    async def publish_version(self, request: PublicationRequest) -> PublicationResult:
        if request.tenant_id != self.tenant_id:
            return PublicationResult(publication_id=request.publication_id, status="rejected", code="tenant_mismatch", mode="fake")
        fingerprint = openapi_sha256(request.model_dump())
        previous = self._publications.get(request.publication_id)
        if previous:
            if previous[0] == fingerprint:
                return previous[1]
            return PublicationResult(publication_id=request.publication_id, status="rejected", code="publication_id_reused", mode="fake")
        object_id = f"fake-{request.publication_id}"
        self._objects[object_id] = WorkspaceObject(tenant_id=self.tenant_id, object_id=object_id,
                                                  content=request.content_markdown, content_sha256=request.content_sha256)
        result = PublicationResult(publication_id=request.publication_id, status="published", code="fake_created", remote_object_id=object_id, mode="fake")
        self._publications[request.publication_id] = fingerprint, result
        return result

    async def read_object(self, *, tenant_id: str, object_id: str) -> WorkspaceObject:
        if tenant_id != self.tenant_id:
            raise IntegrationUnavailable("tenant_mismatch")
        try:
            return self._objects[object_id].model_copy(deep=True)
        except KeyError as exc:
            raise IntegrationUnavailable("object_not_found") from exc

    async def aclose(self):
        pass
