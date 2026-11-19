# Project access implementation plan

> **For agentic workers:** Execute the parent-approved implementation in this existing checkout; no Git repository or deployment is involved.

**Goal:** Restrict OIDC members to explicitly granted dossiers before materialization, counters, retrieval and model calls.

**Architecture:** `ProjectAccess` reloads active member identity and grants from SQLite. Services consume explicit scopes; global Casbin permissions still determine read versus write. Non-OIDC modes and standalone legacy service tests retain their existing behavior.

**Tech stack:** Python 3.11, SQLite, FastAPI, pytest.

**Spec:** Parent task contract: `Settings.auth_mode == 'oidc'`; identity authority is `identity_members`, never client role/email; admins access all projects; others need grants.

## Global constraints

- Do not edit api.py, governance.py, auth.py, config.py or connection_hub.py.
- Add no provider connection or deployment; use only synthetic test records.
- Shared sources require access to every linked project; unassigned sources/events require admin.
- Deny by default; source/object denials use uniform not_found messages.

## Review focus

- Revoked/inactive members cannot reuse cached scopes, notifications or conversation responses.
- Shared-source access cannot reveal inaccessible project IDs or body passages.
- Lists, unread counts, pagination and FTS receive only authorized records.
- Forged role, email, permission dictionaries and cross-tenant IDs grant no dossier access.
- RAG revalidates scope before provider calls and before returning or storing historical context.

## Tasks

- [x] Add failing tests in tests/test_project_access.py for active DB roles, grants, shared sources and SQL clauses; run pytest to observe denial gaps.
- [x] Implement src/travaux/project_access.py: access_scope(repo,actor), scope properties, guards, SQL predicates and safe memory/source helpers; verify scope tests.
- [x] Add failing retrieval/conversation tests, then scope assistant_dossier.py, retrieval.py and conversations.py before retrieval and historical replay.
- [x] Add failing service list/count tests, then scope mailbox.py, documents.py, document_review.py, calendars.py, field_reports.py and notifications.py.
- [x] Scope project_properties.py and the parent-delegated governance audit/capability DTOs; 22 dedicated security tests pass.
- [x] Run dedicated tests, then the complete Python suite; report all failures and communicate the root API integration contract. Final run: 415 passed; dedicated scope tests: 22 passed; Ruff F checks: clean.
