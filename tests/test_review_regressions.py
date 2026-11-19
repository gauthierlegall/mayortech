"""Independent review regressions. Entirely synthetic; no socket or real account."""
import httpx
import pytest

from travaux.domain import DomainError
from travaux.jobs import JobQueue
from travaux.llm import Extraction, ExtractionError, MistralExtractor
from travaux.pipeline import extract_source
from travaux.repository import Repository


def test_unread_attachment_coverage_is_visible_on_generated_summary(tmp_path):
    repo = Repository(tmp_path / 'coverage.sqlite3')
    try:
        project = repo.create_project('test-town', 'TR-99', 'Chantier entièrement fictif')
        repo.ingest_source('test-town', 'mail-attachment', '[TR-99] Devis joint', 'Voir le devis joint.',
            project_ref='TR-99', metadata={'attachments': [{'filename': 'devis-fictif.pdf', 'status': 'not_extracted'}]})
        summary = repo.create_summary('test-town', project['id'])
        assert summary.get('coverage') == 'partial', 'A summary must expose the unread attachment, not imply complete source coverage'
        assert summary.get('warnings'), 'The reader needs an actionable explanation of missing coverage'
    finally:
        repo.close()


def test_new_unreviewed_mail_marks_old_draft_coverage_outdated(tmp_path):
    repo = Repository(tmp_path / 'freshness.sqlite3')
    try:
        project = repo.create_project('test-town', 'TR-99', 'Chantier entièrement fictif')
        draft = repo.create_summary('test-town', project['id'])
        source = repo.ingest_source('test-town', 'mail-new', '[TR-99] Report',
            'Livraison : 2026-12-21', project_ref='TR-99')
        repo.add_candidate('test-town', project['id'], source['id'], 'delivery_date', '2026-12-21',
            kind='date', quote=source['body'])
        refreshed = repo.get_summary('test-town', draft['id'])
        assert refreshed['stale'] or refreshed.get('coverage_stale'), 'Pending news must be visible before any human acceptance'
        with pytest.raises(DomainError) as error:
            repo.approve_summary('test-town', draft['id'], expected_content_hash=draft['content_hash'],
                expected_snapshot_hash=draft['snapshot_hash'], expected_project_revision=draft['snapshot_revision'])
        assert error.value.code == 'stale_source_context'
    finally:
        repo.close()


def test_extraction_failure_does_not_leave_a_partially_applied_batch(tmp_path):
    repo = Repository(tmp_path / 'batch.sqlite3')
    try:
        project = repo.create_project('test-town', 'TR-99', 'Chantier entièrement fictif')
        source = repo.ingest_source('test-town', 'mail-batch', '[TR-99] Dates',
            'Entreprise : Société fictive\nLivraison : 2026-99-99', project_ref='TR-99')
        class MalformedBatchExtractor:
            def extract(self, text):
                return Extraction.model_validate({'candidates': [
                    {'field': 'Entreprise', 'value': 'Société fictive', 'kind': 'text', 'quote': 'Entreprise : Société fictive'},
                    {'field': 'Livraison', 'value': '2026-99-99', 'kind': 'date', 'quote': 'Livraison : 2026-99-99'},
                ], 'warnings': []})
        with pytest.raises(ExtractionError):
            extract_source(repo, 'test-town', source['id'], MalformedBatchExtractor())
        assert repo.list_candidates('test-town', project['id']) == [], 'A failed batch should be recoverable without partially visible facts'
    finally:
        repo.close()


def test_malformed_provider_envelope_is_a_recoverable_extraction_error():
    extractor = MistralExtractor('https://approved-fictitious.example/v1/chat/completions', 'fake-model', 'fake-key',
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'choices': None})))
    with pytest.raises(ExtractionError):
        extractor.extract('Livraison : 2026-12-21')


def test_reused_queue_key_with_different_payload_is_rejected(tmp_path):
    queue = JobQueue(tmp_path / 'idempotence.sqlite3')
    queue.enqueue('test-town', 'extract', {'source_id': 'source-a'}, 'same-key')
    with pytest.raises((ValueError, DomainError)):
        queue.enqueue('test-town', 'extract', {'source_id': 'source-b'}, 'same-key')
