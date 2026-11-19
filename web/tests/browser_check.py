"""Recette réelle du complément ; données fictives uniquement."""
import argparse
import json
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
    report = {'pages': [], 'console_errors': [], 'page_errors': [], 'overflow': []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel=args.channel or None)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='fr-FR', timezone_id='Europe/Paris')
        page = context.new_page()
        page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
        page.on('console', lambda message: report['console_errors'].append(message.text) if message.type == 'error' else None)
        page.goto(args.url, wait_until='networkidle')
        page.get_by_role('heading', name='Le point sur les travaux.').wait_for()
        page.screenshot(path=str(screens / 'desktop-overview.png'), full_page=True)
        projects = page.request.get(args.url + '/api/v1/projects').json()
        summaries = page.request.get(args.url + '/api/v1/summaries').json()
        display_project = next((item for item in projects if item.get('reference') == 'TRV-2026-014'), projects[0] if projects else None)
        display_summary = next((item for item in summaries if display_project and item['project_id'] == display_project['id']), summaries[0] if summaries else None)
        routes = [('overview', 'Vue d’ensemble'), ('projects', 'Chantiers'), ('review', 'À vérifier'), ('imports', 'Imports'), ('summaries', 'Récapitulatifs'), ('settings', 'Connexions et accès')]
        if display_project:
            routes.append((f"project/{display_project['id']}", display_project['name']))
        if display_summary:
            routes.append((f"summary/{display_summary['id']}", 'Récapitulatif'))
        for width in [1440, 390, 320]:
            page.set_viewport_size({'width': width, 'height': 900})
            for route, label in routes:
                page.goto(args.url + '/#/' + route, wait_until='networkidle')
                page.locator('#main h1').wait_for()
                body_text = page.locator('#main').inner_text()
                assert 'Impossible de charger cette page' not in body_text, (width, route, body_text)
                assert 'Informations indisponibles' not in body_text, (width, route, body_text)
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                report['pages'].append({'width': width, 'route': route, 'heading': page.locator('#main h1').inner_text()})
                if overflow:
                    report['overflow'].append({'width': width, 'route': route, 'elements': page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1&&getComputedStyle(e).position!=='fixed').map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})).slice(0,12)")})
                if width in [390, 320] and route == 'projects':
                    page.locator('#project-search').fill('TRV')
                if width in [390, 320] and route.split('/')[0] in ['overview', 'projects', 'review', 'summaries', 'summary', 'project']:
                    page.screenshot(path=str(screens / f"mobile-{width}-{route.split('/')[0]}.png"), full_page=False)
        page.set_viewport_size({'width': 390, 'height': 844})
        page.goto(args.url + '/#/review', wait_until='networkidle')
        source = page.locator('.review-detail [data-action="source"]').first
        if source.count():
            source.click()
            page.locator('#app-dialog .source-content').wait_for()
            page.screenshot(path=str(screens / 'mobile-source-proof.png'), full_page=True)
            assert page.locator('#app-dialog').evaluate('(element)=>element.open')
            page.get_by_role('button', name='Fermer la fenêtre').click()
        report['passed'] = not report['overflow'] and not report['page_errors'] and not report['console_errors']
        browser.close()
    (screens / 'browser-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert report['passed'], 'La recette navigateur a détecté des erreurs ; consulter browser-check.json.'


if __name__ == '__main__':
    main()
