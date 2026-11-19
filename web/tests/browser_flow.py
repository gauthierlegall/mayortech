"""Parcours utilisateur mobile réel sur un chantier dédié entièrement fictif."""
import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--screens', default=str(Path(__file__).resolve().parents[2] / 'docs' / 'screens'))
    parser.add_argument('--channel', default='')
    args = parser.parse_args()
    screens = Path(args.screens)
    screens.mkdir(parents=True, exist_ok=True)
    report = {'checks': [], 'errors': []}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel or None, headless=True)
        context = browser.new_context(viewport={'width': 390, 'height': 844}, locale='fr-FR', timezone_id='Europe/Paris', accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.goto(args.url, wait_until='networkidle')
        headers = {'X-Requested-With': 'Travaux'}
        projects = page.request.get(args.url + '/api/v1/projects').json()
        project = next((item for item in projects if item['reference'] == 'TEST-UX-001'), None)
        if project is None:
            response = page.request.post(args.url + '/api/v1/projects', headers=headers, data={'reference': 'TEST-UX-001', 'name': 'Chantier de recette mobile', 'description': 'Dossier entièrement fictif pour les tests du parcours.'})
            assert response.ok, response.text()
            project = response.json()
        project_id = project['id']
        unique = str(time.time_ns())
        memory = page.request.get(args.url + '/api/v1/projects/' + project_id).json()
        count = len(memory['sources'])
        delivery_value = f'2027-{count // 28 % 12 + 1:02}-{count % 28 + 1:02}'
        mail = f'''From: chantier@entreprise-fictive.invalid
To: demonstration@collectivite-fictive.invalid
Subject: Point de chantier mobile sans référence {unique}
Message-ID: <mobile-{unique}@test.invalid>
Date: Sat, 14 Nov 2026 09:00:00 +0100
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Point entièrement fictif.
Avancement : Cheminement piéton sécurisé, contrôle de recette {count + 1}
Livraison : {delivery_value}
Action : Confirmer la visite de réception, recette {unique}
'''
        page.goto(args.url + '/#/imports', wait_until='networkidle')
        page.locator('#eml-file').set_input_files({'name': 'recette-mobile.eml', 'mimeType': 'message/rfc822', 'buffer': mail.encode('utf-8')})
        page.get_by_role('button', name='Importer et analyser').click()
        page.locator('#import-result .result-box').wait_for()
        page.locator('#import-result').get_by_role('button', name='Choisir le chantier').click()
        page.locator('#source-project').select_option(project_id)
        page.get_by_role('button', name='Confirmer le chantier et analyser').click()
        page.wait_for_function("() => !document.getElementById('app-dialog').open")
        report['checks'].append('Rattachement manuel du mail sans référence au bon chantier')
        reviews = page.request.get(args.url + '/api/v1/reviews?project_id=' + project_id).json()
        assert reviews, 'Le mail importé doit produire des propositions du chantier dédié.'
        report['checks'].append('Import EML réel et extraction de propositions')
        progress = next((r for r in reviews if r['field'] == 'progress'), reviews[0])
        page.goto(args.url + '/#/review/' + progress['id'], wait_until='networkidle')
        page.locator('.review-detail .evidence-quote').wait_for()
        assert 'Cheminement' in page.locator('.review-detail').inner_text()
        source = page.locator('.review-detail [data-action="source"]').last
        source.click()
        page.locator('#app-dialog .source-content').wait_for()
        assert 'Point entièrement fictif' in page.locator('#app-dialog').inner_text()
        page.screenshot(path=str(screens / 'flow-mobile-source.png'), full_page=True)
        page.get_by_role('button', name='Fermer la fenêtre').click()
        report['checks'].append('Consultation du mail source sur mobile')
        accept = page.locator('.review-detail [data-action="accept-review"]')
        if accept.count():
            with page.expect_response(lambda response: response.url.endswith('/decision') and response.request.method == 'POST') as decision_response:
                accept.click()
        else:
            page.locator('[data-action="replace-review"]').click()
            page.locator('#decision-reason').fill('Nouvelle annonce explicite du mail fictif.')
            with page.expect_response(lambda response: response.url.endswith('/decision') and response.request.method == 'POST') as decision_response:
                page.get_by_role('button', name='Confirmer le remplacement').click()
        assert decision_response.value.ok, decision_response.value.text()
        decided = page.request.get(args.url + '/api/v1/projects/' + project_id).json()
        assert any(fact['id'] == progress['id'] for fact in decided['facts'])
        report['checks'].append('Confirmation explicite d’une proposition sourcée')

        remaining = page.request.get(args.url + '/api/v1/reviews?project_id=' + project_id).json()
        delivery = next((r for r in remaining if r['field'] == 'delivery_date'), None)
        if delivery:
            page.goto(args.url + '/#/review/' + delivery['id'], wait_until='networkidle')
            page.locator('[data-action="correct-review"]').click()
            page.locator('#corrected-value').fill('2026-12-21')
            page.locator('#decision-reason').fill('Correction humaine fictive après appel de démonstration.')
            page.get_by_role('button', name='Confirmer la correction').click()
            page.wait_for_function("() => !document.getElementById('app-dialog').open")
            report['checks'].append('Correction avec provenance humaine distincte')
        remaining = page.request.get(args.url + '/api/v1/reviews?project_id=' + project_id).json()
        if remaining:
            page.goto(args.url + '/#/review/' + remaining[0]['id'], wait_until='networkidle')
            page.locator('[data-action="reject-review"]').click()
            page.locator('#decision-reason').fill('Action à reformuler pendant cette recette fictive.')
            page.get_by_role('dialog').get_by_role('button', name='Écarter la proposition').click()
            page.wait_for_function("() => !document.getElementById('app-dialog').open")
            report['checks'].append('Rejet d’une proposition avec motif')

        page.goto(args.url + '/#/project/' + project_id, wait_until='networkidle')
        page.get_by_role('tab', name='Notes humaines', exact=False).click()
        note = f'Constat humain de recette mobile, contrôle {count + 1} : accès piéton maintenu. <script>non exécuté</script>'
        page.locator('#note-body').fill(note)
        page.get_by_role('button', name='Ajouter la note').click()
        page.locator('.note p').filter(has_text=note).wait_for()
        assert not page.locator('.note script').count()
        report['checks'].append('Note conservée, provenance affichée, HTML rendu comme texte')
        page.screenshot(path=str(screens / 'flow-mobile-human-note.png'), full_page=True)
        page.locator('[data-action="generate-dialog"]').first.click()
        page.get_by_role('button', name='Préparer le brouillon').click()
        page.locator('#summary-content').wait_for()
        content = page.locator('#summary-content').input_value()
        assert 'accès piéton maintenu' in content
        assert '2026-12-21' in content
        report['checks'].append('Génération depuis la mémoire et les notes humaines')
        old_url = page.url
        page.locator('#summary-content').fill(content + '\n\nPrécision de relecture : démonstration fictive validée par le test mobile.')
        page.get_by_role('button', name='Enregistrer', exact=True).click()
        page.wait_for_function('(previous) => location.href !== previous', arg=old_url)
        page.locator('#summary-content').wait_for()
        assert 'Précision de relecture' in page.locator('#summary-content').input_value()
        report['checks'].append('Édition enregistrée comme nouvelle version et redirection')
        page.get_by_role('button', name='Voir les preuves', exact=False).click()
        page.screenshot(path=str(screens / 'flow-mobile-summary-proofs.png'), full_page=True)
        page.get_by_role('button', name='Valider cette version', exact=True).click()
        page.get_by_role('dialog').get_by_role('button', name='Valider cette version', exact=True).click()
        page.get_by_role('link', name='Exporter en Markdown').wait_for()
        assert page.locator('#summary-content').get_attribute('readonly') is not None
        report['checks'].append('Validation contrôlée de la version courante')
        with page.expect_download() as download_event:
            page.get_by_role('link', name='Exporter en Markdown').click()
        download = download_event.value
        destination = screens / 'flow-export-fictif.md'
        download.save_as(str(destination))
        exported = destination.read_text(encoding='utf-8')
        assert 'Précision de relecture' in exported and 'Sources :' in exported
        report['checks'].append('Export réel de la version approuvée avec ses preuves')
        page.screenshot(path=str(screens / 'flow-mobile-summary-approved.png'), full_page=True)
        for width in [390, 320]:
            page.set_viewport_size({'width': width, 'height': 844})
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
        browser.close()
    report['passed'] = not report['errors']
    (screens / 'browser-flow.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert report['passed']


if __name__ == '__main__':
    main()
