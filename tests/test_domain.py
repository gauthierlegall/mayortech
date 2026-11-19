"""Real SQLite and domain checks; all data is invented for this test suite."""
from __future__ import annotations

from pathlib import Path
from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
try:
    from travaux.domain import DomainError, Money
    from travaux.repository import Repository
except ImportError:
    Repository = None
    DomainError = Exception


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Repository, 'Repository is the missing durable domain implementation')
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / 'demo.sqlite3'
        self.repo = Repository(self.db_path)
        self.project = self.repo.create_project('town-a', 'TR-001', 'École des Pins')

    def tearDown(self):
        if getattr(self, 'repo', None):
            self.repo.close()
        if getattr(self, 'tmp', None):
            self.tmp.cleanup()

    def source(self, external_id='mail-1', body='Livraison prévue le 23 novembre 2026.', **kwargs):
        return self.repo.ingest_source('town-a', external_id, '[TR-001] Livraison', body,
                                      project_ref='TR-001', **kwargs)

    def candidate(self, source=None, value='2026-11-23', field='delivery_date', **kwargs):
        source = source or self.source()
        return self.repo.add_candidate('town-a', self.project['id'], source['id'], field, value,
                                       quote=source['body'], kind='date', **kwargs)

    def test_exact_reference_and_known_thread_match_durable_project(self):
        source = self.source(thread_id='thread-x')
        self.assertEqual(source['match_status'], 'matched')
        self.assertEqual(source['project_id'], self.project['id'])
        followup = self.repo.ingest_source('town-a', 'mail-2', 'Suite du chantier',
            'Nouvelle information.', thread_id='thread-x')
        self.assertEqual(followup['project_id'], self.project['id'])
        self.repo.close()
        self.repo = Repository(self.db_path)
        self.assertEqual(self.repo.get_source('town-a', source['id'])['body'], source['body'])

    def test_homonyms_require_manual_match_and_conflicting_thread_stays_ambiguous(self):
        other = self.repo.create_project('town-a', 'TR-002', 'École des Pins')
        source = self.repo.ingest_source('town-a', 'unknown', 'École des Pins', 'À rattacher.')
        self.assertEqual(source['match_status'], 'ambiguous')
        self.assertEqual(set(source['candidate_project_ids']), {self.project['id'], other['id']})
        linked = self.repo.assign_source('town-a', source['id'], other['id'], actor_id='father')
        self.assertEqual(linked['project_id'], other['id'])
        self.source(thread_id='known')
        conflict = self.repo.ingest_source('town-a', 'mail-3', 'Contradiction de référence', 'Test.',
            project_ref='TR-002', thread_id='known')
        self.assertEqual(conflict['match_status'], 'ambiguous')

    def test_sources_are_immutable_versions_and_replay_is_idempotent(self):
        first = self.source()
        replay = self.source()
        self.assertEqual(first['id'], replay['id'])
        changed = self.source(body='Livraison reportée au 25 novembre 2026.')
        self.assertNotEqual(first['id'], changed['id'])
        self.assertEqual(changed['version'], 2)
        self.assertEqual(self.repo.get_source('town-a', first['id'])['body'], first['body'])
        self.assertEqual(len(self.repo.list_sources('town-a')), 2)

    def test_evidence_is_exact_bounded_and_hashed(self):
        source = self.source()
        candidate = self.candidate(source)
        evidence = candidate['evidence'][0]
        self.assertEqual(evidence['source_hash'], source['body_hash'])
        self.assertEqual(source['body'][evidence['start']:evidence['end']], evidence['quote'])
        with self.assertRaises(DomainError) as error:
            self.repo.add_candidate('town-a', self.project['id'], source['id'], 'delivery_date',
                                    '2030-01-01', kind='date', quote='Passage inventé')
        self.assertEqual(error.exception.code, 'invalid_evidence')

    def test_candidate_dedup_preserves_forwarded_evidence_and_rejection(self):
        first = self.candidate()
        forward = self.source(external_id='forward-1')
        repeated = self.candidate(forward)
        self.assertEqual(first['id'], repeated['id'])
        self.assertEqual(len(repeated['evidence']), 2)
        rejected = self.repo.review_candidate('town-a', first['id'], 'reject', actor_id='father')
        self.assertEqual(rejected['status'], 'rejected')
        self.assertEqual(self.candidate(forward)['status'], 'rejected')

    def test_accept_conflict_requires_explicit_replacement_and_revision(self):
        first = self.candidate()
        self.repo.review_candidate('town-a', first['id'], 'accept', actor_id='father', expected_revision=0)
        second = self.candidate(self.source('mail-2', 'Livraison prévue le 25 novembre 2026.'), '2026-11-25')
        self.assertEqual(second['conflict_with'], [first['id']])
        with self.assertRaises(DomainError) as error:
            self.repo.review_candidate('town-a', second['id'], 'accept', expected_revision=1)
        self.assertEqual(error.exception.code, 'unresolved_conflict')
        with self.assertRaises(DomainError) as error:
            self.repo.review_candidate('town-a', second['id'], 'replace', expected_revision=0)
        self.assertEqual(error.exception.code, 'stale_revision')
        self.repo.review_candidate('town-a', second['id'], 'replace', actor_id='father', expected_revision=1)
        memory = self.repo.get_memory('town-a', self.project['id'])
        self.assertEqual(memory['revision'], 2)
        self.assertEqual([f['value'] for f in memory['facts']], ['2026-11-25'])
        self.assertEqual(self.repo.get_candidate('town-a', first['id'])['status'], 'superseded')

    def test_delivery_and_acceptance_dates_are_distinct_facts(self):
        source = self.source(body='Livraison le 23 et réception le 25 novembre 2026.')
        delivery = self.candidate(source)
        self.repo.review_candidate('town-a', delivery['id'], 'accept')
        acceptance = self.candidate(source, '2026-11-25', field='acceptance_date')
        self.assertEqual(acceptance['conflict_with'], [])

    def test_human_notes_survive_generation_and_are_identified(self):
        note = self.repo.add_note('town-a', self.project['id'], 'Accès impossible le 25 matin.', actor_id='father')
        summary = self.repo.create_summary('town-a', self.project['id'])
        self.assertIn('Accès impossible', summary['content'])
        self.assertIn('Note humaine', summary['content'])
        self.assertEqual(summary['citations'][0]['source_id'], note['source_id'])
        self.repo.create_summary('town-a', self.project['id'])
        self.assertEqual(self.repo.get_memory('town-a', self.project['id'])['notes'][0]['content'], note['content'])

    def test_summary_exact_hash_snapshot_and_stale_after_accepted_event(self):
        candidate = self.candidate()
        self.repo.review_candidate('town-a', candidate['id'], 'accept')
        summary = self.repo.create_summary('town-a', self.project['id'])
        self.assertEqual(summary['project_revision'], summary['snapshot_revision'])
        with self.assertRaises(DomainError) as error:
            self.repo.approve_summary('town-a', summary['id'], expected_content_hash='wrong',
                expected_snapshot_hash=summary['snapshot_hash'], expected_project_revision=summary['snapshot_revision'])
        self.assertEqual(error.exception.code, 'content_mismatch')
        approved = self.repo.approve_summary('town-a', summary['id'],
            expected_content_hash=summary['content_hash'], expected_snapshot_hash=summary['snapshot_hash'],
            expected_project_revision=summary['snapshot_revision'], actor_id='father')
        self.assertEqual(approved['status'], 'approved')
        self.repo.add_note('town-a', self.project['id'], 'Précision humaine.', actor_id='father')
        historical = self.repo.get_summary('town-a', summary['id'])
        self.assertEqual(historical['content_hash'], approved['content_hash'])
        self.assertEqual(historical['status'], 'approved')
        self.assertTrue(historical['stale'])
        stale = self.repo.create_summary('town-a', self.project['id'])
        self.repo.add_note('town-a', self.project['id'], 'Autre précision.', actor_id='father')
        with self.assertRaises(DomainError) as error:
            self.repo.approve_summary('town-a', stale['id'], expected_content_hash=stale['content_hash'],
                expected_snapshot_hash=stale['snapshot_hash'], expected_project_revision=stale['snapshot_revision'])
        self.assertEqual(error.exception.code, 'stale_revision')

    def test_native_draft_edit_creates_version_and_old_hash_cannot_approve_it(self):
        summary = self.repo.create_summary('town-a', self.project['id'])
        edited = self.repo.edit_summary('town-a', summary['id'], 'Texte relu manuellement.',
            expected_content_hash=summary['content_hash'], actor_id='father')
        self.assertEqual(edited['version'], summary['version'] + 1)
        self.assertNotEqual(edited['id'], summary['id'])
        self.assertEqual(self.repo.get_summary('town-a', summary['id'])['content'], summary['content'])
        with self.assertRaises(DomainError):
            self.repo.approve_summary('town-a', edited['id'], expected_content_hash=summary['content_hash'],
                expected_snapshot_hash=edited['snapshot_hash'], expected_project_revision=edited['snapshot_revision'])

    def test_summary_rejects_citation_to_another_project(self):
        self.repo.create_project('town-a', 'TR-002', 'Gymnase fictif')
        source = self.repo.ingest_source('town-a', 'other', 'Gymnase', 'Montant privé.', project_ref='TR-002')
        with self.assertRaises(DomainError) as error:
            self.repo.create_summary('town-a', self.project['id'], content='Donnée hors périmètre.',
                citations=[{'source_id': source['id'], 'quote': source['body']}])
        self.assertEqual(error.exception.code, 'invalid_evidence')

    def test_cancelled_summary_keeps_text_and_cannot_be_approved(self):
        summary = self.repo.create_summary('town-a', self.project['id'])
        cancelled = self.repo.cancel_summary('town-a', summary['id'], reason='Brouillon abandonné.', actor_id='father')
        self.assertEqual(cancelled['status'], 'cancelled')
        self.assertEqual(cancelled['content'], summary['content'])
        with self.assertRaises(DomainError):
            self.repo.approve_summary('town-a', summary['id'], expected_content_hash=summary['content_hash'],
                expected_snapshot_hash=summary['snapshot_hash'], expected_project_revision=summary['snapshot_revision'])

    def test_tenant_and_object_boundaries_hide_sources_and_candidates(self):
        source = self.source()
        candidate = self.candidate(source)
        for read, object_id in [(self.repo.get_source, source['id']), (self.repo.get_project, self.project['id']),
                                (self.repo.get_candidate, candidate['id'])]:
            with self.assertRaises(DomainError) as error:
                read('town-b', object_id)
            self.assertEqual(error.exception.code, 'not_found')
        self.assertEqual(self.repo.list_sources('town-b'), [])
        self.assertEqual(self.repo.list_candidates('town-b'), [])

    def test_money_uses_decimal_and_does_not_equate_ht_ttc(self):
        self.assertEqual(Money('1 234,56', 'EUR', 'HT').as_dict()['amount'], '1234.56')
        self.assertNotEqual(Money('100', 'EUR', 'HT'), Money('100', 'EUR', 'TTC'))
        with self.assertRaises(DomainError):
            Money('NaN', 'EUR', 'HT')

    def test_review_failure_is_atomic_and_outbox_survives_reopen(self):
        candidate = self.candidate()
        with self.assertRaises(DomainError):
            self.repo.review_candidate('town-a', candidate['id'], 'accept', expected_revision=99)
        self.assertEqual(self.repo.get_candidate('town-a', candidate['id'])['status'], 'pending')
        self.assertEqual(self.repo.get_project('town-a', self.project['id'])['revision'], 0)
        self.repo.review_candidate('town-a', candidate['id'], 'accept', expected_revision=0)
        self.repo.close()
        self.repo = Repository(self.db_path)
        events = self.repo.list_events('town-a', self.project['id'])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['event_type'], 'candidate.accepted')
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM outbox').fetchone()[0], 1)

    def test_ht_and_ttc_coexist_and_replacing_ht_preserves_ttc(self):
        source = self.source(body='Devis 100 € HT, soit 120 € TTC. Nouveau montant : 110 € HT.')
        ht = self.repo.add_candidate('town-a', self.project['id'], source['id'], 'amount',
            {'amount': '100', 'currency': 'EUR', 'basis': 'HT'}, kind='money', quote='100 € HT')
        self.repo.review_candidate('town-a', ht['id'], 'accept')
        ttc = self.repo.add_candidate('town-a', self.project['id'], source['id'], 'amount',
            {'amount': '120', 'currency': 'EUR', 'basis': 'TTC'}, kind='money', quote='120 € TTC')
        self.assertEqual(ttc['conflict_with'], [])
        self.repo.review_candidate('town-a', ttc['id'], 'accept')
        revised = self.repo.add_candidate('town-a', self.project['id'], source['id'], 'amount',
            {'amount': '110', 'currency': 'EUR', 'basis': 'HT'}, kind='money', quote='110 € HT')
        self.assertEqual(revised['conflict_with'], [ht['id']])
        self.repo.review_candidate('town-a', revised['id'], 'replace')
        self.assertEqual(self.repo.get_candidate('town-a', ttc['id'])['status'], 'accepted')

    def test_new_announcement_can_restore_a_previously_superseded_value(self):
        first = self.candidate()
        self.repo.review_candidate('town-a', first['id'], 'accept')
        changed = self.candidate(self.source('mail-2', 'Livraison le 25 novembre 2026.'), '2026-11-25')
        self.repo.review_candidate('town-a', changed['id'], 'replace')
        restored = self.candidate(self.source('mail-3', 'Retour à la livraison le 23 novembre 2026.'))
        self.assertNotEqual(restored['id'], first['id'])
        self.assertEqual(restored['status'], 'pending')
        self.assertEqual(restored['conflict_with'], [changed['id']])

    def test_native_revision_and_approval_audit_are_exact(self):
        summary = self.repo.create_summary('town-a', self.project['id'])
        edited = self.repo.edit_summary('town-a', summary['id'], 'Texte humain relu.',
            expected_content_hash=summary['content_hash'], native_revision='remote-fingerprint-2')
        with self.assertRaises(DomainError) as error:
            self.repo.approve_summary('town-a', edited['id'], expected_content_hash=edited['content_hash'],
                expected_snapshot_hash=edited['snapshot_hash'], expected_project_revision=edited['snapshot_revision'],
                expected_remote_revision='remote-fingerprint-1')
        self.assertEqual(error.exception.code, 'remote_revision_mismatch')
        approved = self.repo.approve_summary('town-a', edited['id'], expected_content_hash=edited['content_hash'],
            expected_snapshot_hash=edited['snapshot_hash'], expected_project_revision=edited['snapshot_revision'],
            expected_remote_revision='remote-fingerprint-2', actor_id='father')
        audit = self.repo.list_audit('town-a', self.project['id'])
        approvals = [a for a in audit if a['action'] == 'summary.approved']
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0]['actor_id'], 'father')
        self.assertEqual(approvals[0]['payload']['content_hash'], approved['content_hash'])

    def test_bad_evidence_offset_is_domain_error_and_money_rejects_float(self):
        source = self.source()
        with self.assertRaises(DomainError):
            self.repo.add_candidate('town-a', self.project['id'], source['id'], 'delivery_date', '2026-11-23',
                kind='date', quote=source['body'], evidence_start='bad')
        with self.assertRaises(DomainError):
            Money(0.1, 'EUR', 'HT')

    def test_human_correction_has_its_own_source_and_atomic_decision(self):
        original = self.candidate()
        corrected = self.repo.correct_candidate('town-a', original['id'], '2026-11-26',
            reason='Date confirmée personnellement dans le scénario fictif.', actor_id='father', expected_revision=0)
        self.assertEqual(corrected['value'], '2026-11-26')
        self.assertEqual(corrected['origin'], 'human_assertion')
        self.assertEqual(corrected['status'], 'accepted')
        self.assertNotEqual(corrected['source_id'], original['source_id'])
        evidence = corrected['evidence'][0]
        source = self.repo.get_source('town-a', evidence['source_id'])
        self.assertIn('2026-11-26', source['body'])
        self.assertEqual(source['metadata']['origin'], 'human_assertion')
        self.assertEqual(evidence['quote'], source['body'][evidence['start']:evidence['end']])
        self.assertEqual(self.repo.get_candidate('town-a', original['id'])['status'], 'rejected')
        memory = self.repo.get_memory('town-a', self.project['id'])
        self.assertEqual(memory['revision'], 1)
        self.assertEqual([f['id'] for f in memory['facts']], [corrected['id']])
        self.assertEqual(len(memory['notes']), 1)
        self.assertEqual(self.repo.list_events('town-a', self.project['id'])[0]['event_type'], 'candidate.corrected')

    def test_invalid_or_stale_human_correction_leaves_no_partial_note(self):
        original = self.candidate()
        for value, revision in [('vendredi prochain', 0), ('2026-11-26', 99)]:
            with self.assertRaises(DomainError):
                self.repo.correct_candidate('town-a', original['id'], value, reason='À vérifier.',
                    actor_id='father', expected_revision=revision)
        self.assertEqual(self.repo.get_memory('town-a', self.project['id'])['notes'], [])
        self.assertEqual(self.repo.get_candidate('town-a', original['id'])['status'], 'pending')
        self.assertEqual(len(self.repo.list_sources('town-a')), 1)

    def test_workspace_note_change_updates_current_pointer_and_keeps_old_source(self):
        first = self.repo.ingest_workspace_note('town-a', self.project['id'], 'native-note-1',
            'Note native initiale.', remote_revision='fingerprint-1')
        first_source = self.repo.get_source('town-a', first['source_id'])
        first_revision = self.repo.get_project('town-a', self.project['id'])['revision']
        same = self.repo.ingest_workspace_note('town-a', self.project['id'], 'native-note-1',
            'Note native initiale.', remote_revision='fingerprint-2')
        self.assertEqual(same['id'], first['id'])
        self.assertEqual(same['source_id'], first['source_id'])
        self.assertEqual(self.repo.get_project('town-a', self.project['id'])['revision'], first_revision)
        summary = self.repo.create_summary('town-a', self.project['id'])
        changed = self.repo.ingest_workspace_note('town-a', self.project['id'], 'native-note-1',
            'Note native corrigée.', remote_revision='fingerprint-3')
        self.assertEqual(changed['id'], first['id'])
        self.assertNotEqual(changed['source_id'], first['source_id'])
        self.assertEqual(changed['actor_id'], 'appflowy:actor_unverified')
        self.assertEqual(self.repo.get_source('town-a', first['source_id'])['body'], first_source['body'])
        self.assertEqual(self.repo.get_source('town-a', changed['source_id'])['version'], 2)
        memory = self.repo.get_memory('town-a', self.project['id'])
        self.assertEqual(len(memory['notes']), 1)
        self.assertEqual(memory['notes'][0]['content'], 'Note native corrigée.')
        self.assertTrue(self.repo.get_summary('town-a', summary['id'])['stale'])
        next_summary = self.repo.create_summary('town-a', self.project['id'])
        self.assertIn('Note native corrigée.', next_summary['content'])
        self.assertNotIn('Note native initiale.', next_summary['content'])

    def test_workspace_note_is_bound_to_current_tenant_project(self):
        with self.assertRaises(DomainError) as error:
            self.repo.ingest_workspace_note('town-b', self.project['id'], 'native-note-1', 'Texte hors tenant.')
        self.assertEqual(error.exception.code, 'not_found')
        self.assertEqual(self.repo.list_sources('town-b'), [])

    def test_candidate_batch_is_atomic_when_a_later_value_is_invalid(self):
        source = self.source(body='Entreprise fictive. Livraison prévue le 23 novembre 2026.')
        with self.assertRaises(DomainError):
            self.repo.add_candidates('town-a', self.project['id'], source['id'], [
                {'field': 'contractor', 'value': 'Entreprise fictive', 'kind': 'text', 'quote': 'Entreprise fictive'},
                {'field': 'delivery_date', 'value': '2026-99-99', 'kind': 'date', 'quote': '23 novembre 2026'},
            ])
        self.assertEqual(self.repo.list_candidates('town-a', self.project['id']), [])
        self.assertEqual(self.repo.get_source('town-a', source['id'])['status'], 'ready')


if __name__ == '__main__':
    unittest.main()
