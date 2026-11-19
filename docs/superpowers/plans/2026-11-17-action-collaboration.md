# Action collaboration implementation plan

> **For agentic workers:** Execute the parent-approved isolated module with TDD; no frontend, native SDK or root API changes in this task.

**Goal:** Add subordinate checklists, comments, individual assignment and manually prepared recurrence occurrences to canonical Yjs actions.

**Architecture:** SQLite stores only collaboration metadata and recurrence operation receipts, keyed by tenant/project/page/native action ID. Yjs remains the sole action title/status/operational dates store. Every operation checks the active actor and project contents; mutations repeat authorization inside the transaction.

**Tech Stack:** Existing Python/FastAPI/Pydantic/SQLite, pytest; no additional dependency or scheduler.

**Spec:** Parent contract dated 2026-11-17: checklist <=100 items; comment <=4000 characters; explicit grants; recurrence unit week/month/year; immutable occurrence keyed by rule+ordinal; persisted-page-hash acknowledgement.

## Global constraints

- Only src/travaux/action_collaboration.py and dedicated tests are implemented here.
- SQL never stores canonical action titles, statuses or current dates.
- Author comes exclusively from the server actor; assignee must be an active authorized member.
- Participant DTO selects id/display_name/role only; no email or issuer claims.
- Demo can expose only its actual shared fictional actor, with no fabricated institutional members.
- Recurrence dates are civil ISO dates for Europe/Paris; month-end calculations use the original anchor, preventing clamp drift.
- No automatic Yjs scheduler: client explicitly calls importActions with sourceKey recurrence:<operation_id> then saves and confirms.
- A page hash receipt proves persistence, not independent server parsing of a Yjs row.

## Review focus

- Cross-project and cross-tenant references, deactivated members and revoked grants must fail before reading or writing.
- Concurrent checklist/rule saves use explicit revision CAS.
- Comments and occurrence preparation replay idempotently after a lost response.
- February, leap years and month ends retain the intended calendar anchor.
- Confirmed occurrences and their original action are never reset, merged or silently rewritten.

## Tasks

- [x] Write failing service tests for guards, real participant identities, checklist CAS, author provenance and paginated comments.
- [x] Implement ActionCollaboration methods and bounded FastAPI routes in action_collaboration.py; run service/HTTP tests.
- [x] Write failing recurrence tests for 31 January, leap years, weekly spans, CAS, prepare replay and immutable confirmation.
- [x] Implement recurrence plans and saved-version receipts; test without touching Yjs titles/statuses.
- [x] Run dedicated tests and the full Python suite, then deliver exact route/SDK integration contract to root. Collaboration: 24 passed; Ruff F clean. Full run during root model edits: 441 passed, 2 model-routing failures, subsequently rerun green with collaboration (26 passed).

## Native integration contract

Read the rule through GET collaboration state, then prepare ordinal >=1 with its current revision. Use the returned source_key verbatim in native importActions, taking the template title from Yjs and the returned plan dates. Stop on an existing deleted binding: do not recreate it or reset its original action. Save Yjs, then confirm using page_id, the new row_id and the persisted page revision hash. A confirmed receipt is immutable; re-read it after an ambiguous network response before attempting another confirmation. A changed recurrence rule preserves all prior operation plans and receipts.
