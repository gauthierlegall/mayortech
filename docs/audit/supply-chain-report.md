# Supply Chain Risk Report — `travaux-mairie`

**Scanned:** `outputs\travaux-mairie`  
**Manifests read:** `pyproject.toml`, `uv.lock`  
**Scanned at:** 2026-11-14T15:33:36+00:00  
**Direct dependencies:** 12 (PyPI 12)

## Summary

- **No known advisory affects any of the 12 direct dependencies**, checked at the versions this project resolves.
- No known advisory affects any of the 50 registry-verified transitive packages at their locked versions.
- 0 of 12 dependencies carry at least one finding, 0 of which reach production.
- Weakest coverage: **Install-time script execution**, established for 0 of 12; the Coverage section lists every criterion.

## Production dependencies

9 dependencies are declared as runtime dependencies and ship in the built artifact. Advisory status is given for every one, clean or not.

| Dependency | Version | Advisories | Other findings |
|---|---|---|---|
| `exchangelib` | 5.6.0 | none known | — |
| `fastapi` | 0.133.1 | none known | — |
| `httpx` | 0.28.1 | none known | — |
| `jsonschema` | 4.26.0 | none known | — |
| `mcp` | 2.3.0 | none known | — |
| `pydantic` | 2.13.4 | none known | — |
| `pypdf` | 6.21.4 | none known | — |
| `python-docx` | 1.2.0 | none known | — |
| `uvicorn` | 0.41.0 | none known | — |

## Findings

No dependency was flagged on these criteria.

## Upstream repository and CI hygiene — OpenSSF Scorecard

These criteria describe each dependency's own repository, not the audited
project. Remediation, where any exists, is upstream.

No dependency was flagged on these criteria.

## Transitive advisories

No known advisory affects any of the 50 registry-verified packages beyond the direct set (resolved by `uv.lock`), at the locked versions. Only advisories were checked at this depth; every other criterion in this report describes direct dependencies only.

## Informational

Measured, not flagged.

- **CI token permissions**: median 9/10 across 6 scored dependencies; 3 score below 6. Not flagged — this measures whether CI workflows declare least-privilege tokens, which tracks project maturity rather than the likelihood of malicious code being published.
- **Changes reviewed by a second person**: median 7/10 across 7 scored dependencies; 3 score below 6. Not flagged — this measures the share of recent commits reviewed by a second person, which is low for most small single-maintainer projects and largely restates publisher concentration.
- **Publish provenance**: not determinable for any dependency in this project.
- **Security policy published**: 9 of 12 publish a security policy.
  Without: `exchangelib`, `httpx`, `python-docx`
- **Download volume**: not determinable for any dependency in this project.

## Coverage

What was and was not measured, per criterion.

| Criterion | Tier | Assessed | Flagged | Not assessable |
|---|---|---|---|---|
| Known advisories | A | 12/12 | 0 | 0 |
| Deprecated or yanked | A | 12/12 | 0 | 0 |
| Repository archived | A | 12/12 | 0 | 0 |
| Maintenance activity | A | 12/12 | 0 | 0 |
| Publisher concentration | B | 0/12 | 0 | 12 |
| Install-time script execution | B | 0/12 | 0 | 12 |
| Dangerous CI workflow | scorecard | 6/12 | 0 | 6 |
| CI token permissions | scorecard | 6/12 | 0 | 6 |
| Checked-in binaries | scorecard | 7/12 | 0 | 5 |
| Changes reviewed by a second person | scorecard | 7/12 | 0 | 5 |
| Publish provenance | info | 0/12 | 0 | 12 |
| Security policy published | info | 12/12 | 0 | 0 |
| Download volume | info | 0/12 | 0 | 12 |

## Not assessable

**Checked-in binaries**

- 5 dependencies — OpenSSF Scorecard has no report for this repository: `fastapi`, `mcp`, `pydantic`, `ruff`, `uvicorn`

**Changes reviewed by a second person**

- 5 dependencies — OpenSSF Scorecard has no report for this repository: `fastapi`, `mcp`, `pydantic`, `ruff`, `uvicorn`

**Dangerous CI workflow**

- 5 dependencies — OpenSSF Scorecard has no report for this repository: `fastapi`, `mcp`, `pydantic`, `ruff`, `uvicorn`
- 1 dependency — Scorecard could not evaluate Dangerous-Workflow (score -1): `python-docx`

**Download volume**

- 12 dependencies — PyPI's download counters are disabled and return -1: `exchangelib`, `fastapi`, `httpx`, `jsonschema`, `mcp`, `playwright` and 6 more

**Install-time script execution**

- 12 dependencies — install-time execution depends on whether a wheel or an sdist is installed, which this collector does not determine: `exchangelib`, `fastapi`, `httpx`, `jsonschema`, `mcp`, `playwright` and 6 more

**Publish provenance**

- 12 dependencies — PyPI publish attestations are not read by this collector: `exchangelib`, `fastapi`, `httpx`, `jsonschema`, `mcp`, `playwright` and 6 more

**Publisher concentration**

- 12 dependencies — PyPI publishes no upload ACL, so who can publish this package is not observable: `exchangelib`, `fastapi`, `httpx`, `jsonschema`, `mcp`, `playwright` and 6 more

**CI token permissions**

- 5 dependencies — OpenSSF Scorecard has no report for this repository: `fastapi`, `mcp`, `pydantic`, `ruff`, `uvicorn`
- 1 dependency — Scorecard could not evaluate Token-Permissions (score -1): `python-docx`

## Method and caveats

- cache directory ownership was not verified: os.getuid is POSIX-only, so a cache at work\dependency-audit\registry-cache owned by another user would not be detected on this platform. Keep the cache under your own user profile, or pass --cache with a private path.
- Optional tooling detected: npm. Not installed, so not used: bundler-audit, cargo-audit, osv-scanner, pip-audit.
- Every criterion except advisories applies to direct dependencies only. The 50 registry-verified packages resolved by uv.lock were checked for known advisories at their locked versions, and for nothing else.
- HTTP sources: 43 fetched, 12 served from cache (oldest 0.0h old), 0 refetched as stale, 0 unavailable offline, 0 errors.
