# Document uploads implementation plan

> **For agentic workers:** Implement the parent-approved isolated module with TDD. Root owns API middleware, permissions and model configuration; do not edit their files.

**Goal:** Import original dossier documents into immutable document storage and dynamic retrieval, with proposals requiring human review.

**Architecture:** Validate a bounded JSON upload, extract document text outside a transaction, then atomically commit its source, original, client receipt and targeted queue job in the existing shared SQLite database. Run the configured document extractor outside transactions; validate and commit its cached result through pipeline.extract_source after another scope check inside the mutation transaction.

**Tech Stack:** Existing Python/FastAPI/Pydantic/SQLite, isolated document parser, JobQueue and pytest; no additional dependency.

**Spec:** POST /api/v1/projects/{project_id}/documents/upload with strict filename/content_base64/client_id; <=5,000,000 original bytes; PDF/DOCX/TXT/MD/CSV; immutable originals, actor/project-bound idempotency and no automatic fact acceptance.

## Global constraints

- Only document_uploads.py, tests/test_document_uploads.py and this plan are changed.
- Shared public_demo rejects arbitrary uploads; local demo and protected test organization remain supported.
- Actor must have workspace write and current project contents access, rechecked inside transactions and after model work.
- Source project_ref comes from the selected authorized project, never text or model output.
- No model call or document parser runs while a database transaction is open.
- Existing PDF/DOCX subprocess isolation is reused; no antivirus or complete sandbox guarantee is claimed.
- The queue must share the repository database for an atomic source/original/job commit.

## Review focus

- Replayed client ID must return the same document; changed filename/content/project must conflict.
- A newer upload must preserve every earlier original byte and source version.
- Encrypted, scanned or failed extraction must preserve the original and expose manual-review warnings without invented text.
- Revoked, read-only and foreign actors must not persist data or cause a model call.
- Retrieval must see new valid text dynamically and must hide a source linked to an inaccessible project.

## Tasks

- [x] Write failing tests for real PDF text, durability/idempotency/versioning, input limits and access boundaries.
- [x] Implement DocumentUploadService and register_document_upload_routes with the shared transactional job helper.
- [x] Add failure/OCR/queue rollback and model-transport tests; run dedicated tests. Fifteen upload tests pass, including a lost-response/crash queued-job replay and Large 4 MockTransport outside transactions.
- [ ] Run the full Python suite and deliver exact response/registration contract with proof results.

## Integrated HTTP proof

`tests/test_document_chat_workflow.py` exercises real create_app routes, individual server-issued test sessions, dossier grants, a real text PDF, original-byte download, dynamic FTS retrieval, a pending modification and explicit confirmation/replay. All provider requests use httpx.MockTransport. The observed model sequence is exactly document `mistral-large-4-0`, RAG `zai-glm-5-3-flash`, change proposal `zai-glm-5-3-flash`; none occurs inside a database transaction. Revoking the grant then denies document, retrieval, history and confirmation without another provider request. This test does not claim a live SSO or provider connection.
