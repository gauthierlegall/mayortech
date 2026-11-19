"""Behaviour regressions for synthetic EML import and attachment assignment."""
from email.message import EmailMessage

from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings
from travaux.importing import import_mail
from travaux.jobs import JobQueue
from travaux.repository import Repository


def mail(subject, message_id, *, references=None, attachment=False):
    value = EmailMessage()
    value['Subject'], value['Message-ID'] = subject, message_id
    value['From'], value['To'] = 'source@fictitious.invalid', 'travaux@fictitious.invalid'
    value['Date'] = 'Sat, 14 Nov 2026 10:00:00 +0100'
    if references:
        value['References'] = references
        value['In-Reply-To'] = references
    value.set_content('Entreprise : Société entièrement fictive')
    if attachment:
        value.add_attachment(b'Budget : 12000 EUR HT', maintype='text', subtype='plain', filename='devis-fictif.txt')
    return value.as_bytes()


def test_import_passes_known_thread_to_project_matcher(tmp_path):
    repo = Repository(tmp_path / 'mail.sqlite3')
    queue = JobQueue(tmp_path / 'mail.sqlite3')
    try:
        project = repo.create_project('fictitious-town', 'TR-99', 'Chantier fictif')
        first = import_mail(repo, queue, 'fictitious-town', mail('[TR-99] Début', '<first@fictitious.invalid>'))
        assert first['source']['project_id'] == project['id']
        followup = import_mail(repo, queue, 'fictitious-town', mail('Suite sans référence chantier',
            '<second@fictitious.invalid>', references='<first@fictitious.invalid>'))
        assert followup['source']['project_id'] == project['id']
    finally:
        repo.close()


def test_assigning_imported_mail_keeps_its_attachment_in_project_context(tmp_path):
    with TestClient(create_app(Settings(db_path=tmp_path / 'app.sqlite3'))) as client:
        project = client.get('/api/v1/projects').json()[0]
        headers = {'X-Requested-With': 'Travaux'}
        imported = client.post('/api/v1/imports/eml', headers=headers, json={
            'filename': 'message-fictif.eml',
            'content': mail('Message sans référence connue', '<assignment@fictitious.invalid>', attachment=True).decode(),
        })
        imported.raise_for_status()
        payload = imported.json()
        parent_id = payload['source']['id']
        child_ids = {source['id'] for source in payload['related_sources']}
        assert child_ids
        client.post(f'/api/v1/sources/{parent_id}/assignment', json={'project_id': project['id']}, headers=headers).raise_for_status()
        sources = client.get(f"/api/v1/projects/{project['id']}").json()['sources']
        assert child_ids <= {source['id'] for source in sources}
