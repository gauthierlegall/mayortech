"""Vérifie la récupération après panne réseau et les ressources absentes."""
import json
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


parser = argparse.ArgumentParser()
parser.add_argument('--channel', default='')
parser.add_argument('--url', default='http://127.0.0.1:8765')
args = parser.parse_args()
screens = Path(__file__).resolve().parents[2] / 'docs' / 'screens'
screens.mkdir(parents=True, exist_ok=True)
base = args.url
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel=args.channel or None, headless=True)
    page = browser.new_page(viewport={'width': 390, 'height': 844}, locale='fr-FR')
    page.goto(base, wait_until='networkidle')
    page.route('**/api/v1/projects', lambda route: route.abort('failed'))
    page.goto(base + '/#/projects', wait_until='networkidle')
    page.get_by_role('heading', name='Impossible de charger cette page').wait_for()
    assert 'Vérifiez qu’il est démarré puis réessayez' in page.locator('#main').inner_text()
    page.screenshot(path=str(screens / 'mobile-network-error.png'))
    page.unroute('**/api/v1/projects')
    page.get_by_role('button', name='Réessayer', exact=True).click()
    page.locator('#project-search').wait_for()
    assert page.locator('.project-row').count() >= 6
    checks.append('Panne réseau injectée dans le navigateur, message utile et reprise réelle')
    page.goto(base + '/#/project/does-not-exist-ux', wait_until='networkidle')
    page.get_by_role('heading', name='Dossier introuvable').wait_for()
    page.get_by_role('link', name='Retour aux chantiers').click()
    page.locator('#project-search').wait_for()
    checks.append('Dossier absent : retour fonctionnel aux chantiers')
    reviews = page.request.get(base + '/api/v1/reviews').json()
    if reviews:
        page.goto(base + '/#/review/' + reviews[0]['id'], wait_until='networkidle')
        page.locator('.review-detail [data-action="source"]').last.click()
        page.locator('#app-dialog .source-content').wait_for()
        page.keyboard.press('Escape')
        assert not page.locator('#app-dialog').evaluate('(dialog) => dialog.open')
        assert page.evaluate("document.activeElement.dataset.action") == 'source'
        checks.append('Preuve : fermeture Échap et retour du focus au bouton d’ouverture')
    page.set_viewport_size({'width': 320, 'height': 844})
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
    browser.close()
report = {'passed': True, 'checks': checks, 'network_failure': 'injected-browser-only', 'data': 'fictitious'}
(screens / 'browser-failure-states.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
