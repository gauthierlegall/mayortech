"""Read-only inspection of an installation's real OpenAPI, never a write probe."""
from __future__ import annotations

import argparse
import json
import os
import ssl
from pathlib import Path
from typing import Any

import httpx

from .appflowy import AppFlowyManifest, ContractError, _Contract, _origin, openapi_sha256

MAX_OPENAPI_BYTES = 8_000_000


def _references(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"$ref", "$dynamicRef", "$recursiveRef"} and isinstance(child, str):
                result.add(child)
            result.update(_references(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_references(child))
    return result


def analyse_contract(document: dict[str, Any], *, origin: str, tenant_id: str,
                     workspace_id: str, server_version: str = "UNVERIFIED"):
    if not isinstance(document, dict):
        raise ContractError("openapi_object_required")
    origin = _origin(origin)
    version = document.get("info", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ContractError("openapi_version_missing")
    skeleton = AppFlowyManifest(tenant_id=tenant_id, workspace_id=workspace_id, origin=origin,
                                server_version=server_version, api_version=version,
                                openapi_sha256=openapi_sha256(document))
    _Contract(document, skeleton)  # Validates root/version and rejects external refs.
    operations = []
    for path, path_item in document.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            searchable = " ".join((path, str(operation.get("operationId", "")), str(operation.get("tags", "")))).lower()
            if not any(term in searchable for term in ("workspace", "page", "document", "view", "row", "markdown", "import", "database")):
                continue
            operations.append({
                "method": method.upper(), "path": path,
                "operation_id": operation.get("operationId"), "tags": operation.get("tags", []),
                "summary": operation.get("summary", ""),
                "schema_references": sorted(_references(operation)),
                "request_body": operation.get("requestBody"),
                "responses": operation.get("responses", {}),
                "parameters": path_item.get("parameters", []) + operation.get("parameters", []),
            })
    return {"status": "UNAPPROVED_NO_WRITE_ENABLED", "origin": origin,
            "api_version": version, "server_version": server_version,
            "openapi_sha256": skeleton.openapi_sha256, "operations": operations,
            "schema_references": sorted(_references(document)),
            "qualification_required": ["user permissions", "native content encoding", "create and read-back on synthetic workspace", "failure envelope", "license", "remote identity/revisions"]}, skeleton


def write_preflight(directory: Path, document, report, skeleton):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    targets = {"appflowy-openapi.json": document, "appflowy-preflight-report.json": report,
               "appflowy-manifest.unapproved.json": skeleton.model_dump()}
    if any((directory / name).exists() for name in targets):
        raise FileExistsError("preflight_output_exists_choose_new_directory")
    for name, value in targets.items():
        with (directory / name).open("x", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write("\n")


def download_contract(origin: str, *, token: str | None = None, ca_file: str | None = None):
    origin = _origin(origin)
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    context = ssl.create_default_context(cafile=ca_file)
    with httpx.Client(verify=context, timeout=20, trust_env=False, follow_redirects=False) as client:
        with client.stream("GET", origin + "/api/docs/openapi.json", headers=headers) as response:
            if response.status_code != 200:
                raise ContractError("openapi_download_rejected")
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > MAX_OPENAPI_BYTES:
                    raise ContractError("openapi_download_limit")
    document = json.loads(content)
    if not isinstance(document, dict):
        raise ContractError("openapi_object_required")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only AppFlowy OpenAPI preflight. Creates an UNAPPROVED manifest with every capability disabled.")
    parser.add_argument("--base-url", default=os.environ.get("APPFLOWY_BASE_URL"))
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--server-version", default="UNVERIFIED")
    parser.add_argument("--token-env", default="APPFLOWY_ACCESS_TOKEN", help="Environment variable NAME; never put a token on the command line.")
    parser.add_argument("--ca-file", help="Optional trusted root CA PEM; TLS verification remains enabled.")
    parser.add_argument("--openapi-file", type=Path, help="Analyse a saved OpenAPI document without network.")
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if not arguments.base_url:
        parser.error("--base-url or APPFLOWY_BASE_URL is required")
    try:
        if arguments.openapi_file:
            if arguments.openapi_file.stat().st_size > MAX_OPENAPI_BYTES:
                raise ContractError("openapi_file_limit")
            document = json.loads(arguments.openapi_file.read_text(encoding="utf-8-sig"))
        else:
            document = download_contract(arguments.base_url, token=os.environ.get(arguments.token_env), ca_file=arguments.ca_file)
        report, skeleton = analyse_contract(document, origin=arguments.base_url,
                                            tenant_id=arguments.tenant_id, workspace_id=arguments.workspace_id,
                                            server_version=arguments.server_version)
        write_preflight(arguments.output_dir, document, report, skeleton)
    except (ValueError, TypeError, KeyError, OSError, httpx.HTTPError) as exc:
        # Do not print exception bodies: URLs, tokens and vendor responses stay private.
        print(f"Preflight failed ({type(exc).__name__}); no capability enabled.")
        return 2
    print(f"API version: {report['api_version']}")
    print(f"Canonical OpenAPI SHA-256: {report['openapi_sha256']}")
    print(f"Relevant documented operations: {len(report['operations'])}")
    print("UNAPPROVED: read/create remain disabled. Review the saved schemas and qualify a synthetic workspace.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
