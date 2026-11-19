"""Real Chromium proof against the native SDK; HTTP fixture is synthetic, not a mairie mailbox."""
import base64
import hashlib
import json
import os
import sys
import mimetypes
from urllib.parse import urlparse, unquote
from pathlib import Path

from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

OUT = Path(__file__).resolve().parents[1] / "test-results"
OUT.mkdir(exist_ok=True)
state = {"state_base64": None, "revision_hash": None, "revision": 0,
         "title": "École des Ajoncs", "id": "native-editor-fixture", "project_id": "fixture",
         "text": "Note fictive de départ"}
requests = []
errors = []
console_errors = []
reject_writes = False

with sync_playwright() as p:
    executable = os.environ.get("TRAVAUX_CHROMIUM_EXECUTABLE")
    browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.on("pageerror", lambda error: errors.append(error.stack))
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("request", lambda request: requests.append(request.url))
    page.on("requestfailed", lambda request: console_errors.append(f"{request.url}: {request.failure}"))

    def fixture(route):
        request = route.request
        if request.method == "PUT":
            if reject_writes:
                route.fulfill(status=409, content_type="application/json", body='{"detail":"revision_conflict"}')
                return
            payload = request.post_data_json
            assert request.headers.get("x-requested-with") == "Travaux"
            assert payload["expected_revision_hash"] == state["revision_hash"]
            assert payload["editor_version"] == "blocksuite-0.22.4"
            raw = base64.b64decode(payload["state_base64"], validate=True)
            state.update(state_base64=payload["state_base64"], revision_hash=hashlib.sha256(raw).hexdigest(),
                         revision=state["revision"] + 1, text=payload["text"])
        route.fulfill(status=200, content_type="application/json", body=json.dumps(state))

    page.route("**/api/v1/pages/native-editor-fixture/state", fixture)
    html = (OUT.parent / "index.html").read_text(encoding="utf-8").replace('src="/src/poc.ts"', 'src="/fixture.js"').replace('</head>', '<link rel="stylesheet" href="/dist/style.css"></head>').replace('max-width:1100px', 'max-width:1560px')
    script = (OUT.parent / "src/poc.ts").read_text(encoding="utf-8")
    script = script.replace("from './editor'", "from '/dist/editor.js'").replace("document.querySelector('#status')!", "document.querySelector('#status')").replace("document.querySelector('#editor') as HTMLElement", "document.querySelector('#editor')").replace("(window as any)", "window").replace("document.querySelector('#database')!", "document.querySelector('#database')").replace("document.querySelector('#save')!", "document.querySelector('#save')")
    page.route("**/native/", lambda route: route.fulfill(body=html, content_type="text/html", headers={"Content-Security-Policy": "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; worker-src 'self' blob:; connect-src 'self'; object-src 'none'"}))
    page.route("**/fixture.js", lambda route: route.fulfill(body=script, content_type="text/javascript"))
    def asset(route):
        relative = unquote(urlparse(route.request.url).path).removeprefix("/dist/")
        path = (OUT.parent / "dist" / relative).resolve()
        assert path.is_relative_to((OUT.parent / "dist").resolve())
        route.fulfill(body=path.read_bytes(), content_type=mimetypes.guess_type(path)[0] or "application/octet-stream")
    page.route("**/dist/**", asset)
    page.goto("http://127.0.0.1:18765/native/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    assert page.locator("editor-host").count() == 1, errors + console_errors
    assert not errors and not console_errors, errors + console_errors
    assert page.evaluate("typeof window.nativeEditor.addBlock") == 'function', 'Visible native block API is missing'
    assert page.evaluate("typeof window.nativeEditor.setDatabaseView") == 'function', 'Native view switching API is missing'
    assert page.evaluate("typeof window.nativeEditor.setPresentation") == 'function', 'Presentation-only integration API is missing'
    paragraph = page.locator('affine-paragraph [contenteditable="true"]').first
    paragraph.click()
    page.keyboard.press("End")
    page.keyboard.type(" — visite de chantier confirmée")
    page.get_by_role("button", name="Ajouter une base native fictive").click()
    page.wait_for_timeout(600)
    print("DATABASE_INSPECTION", json.dumps({"body": page.locator("#editor").inner_text()[:5000], "errors": errors, "console_errors": console_errors, "editable": page.locator('[contenteditable="true"]').count()}, ensure_ascii=False))
    assert page.locator("affine-database").count() == 1
    assert page.locator("#editor").get_by_text("Visite fictive", exact=True).count() >= 1
    database_id = page.evaluate('() => window.nativeEditor.ensureDatabase()')
    assert page.evaluate('() => window.nativeEditor.ensureDatabase()') == database_id
    assert page.locator('affine-database').count() == 1
    for label in ['Ajouter un titre', 'Ajouter une liste', 'Ajouter une case à cocher', 'Ajouter une citation', 'Ajouter une séparation']:
        page.get_by_role('button', name=label, exact=True).click()
    page.wait_for_function("() => window.nativeEditor.getMetadata().blocks.some(block => block.flavour === 'affine:divider')")
    native_blocks = page.evaluate('() => window.nativeEditor.getMetadata().blocks')
    assert any(block.get('type') == 'h1' for block in native_blocks)
    assert any(block.get('type') == 'todo' and block['flavour'] == 'affine:list' for block in native_blocks)
    assert page.locator('affine-divider').count() == 1
    assert page.locator('affine-paragraph').filter(has_text='Bloc fictif h1').is_visible()
    assert not page.locator('data-view-header-views').is_visible()
    page.get_by_role('button', name='Voir le Kanban natif', exact=True).click()
    page.wait_for_function("() => window.nativeEditor.getMetadata().activeView === 'kanban'")
    page.locator('affine-data-view-kanban-card').first.wait_for()
    page.wait_for_timeout(100)
    state_before_presentation = page.evaluate('() => Array.from(window.nativeEditor.getState())')
    view_names_before = page.evaluate('() => window.nativeEditor.getDatabases()[0].views.map(view => view.name)')
    page.evaluate("() => window.nativeEditor.setPresentation('kanban')")
    page.wait_for_timeout(100)
    assert not page.get_by_role('region', name='Structure et réglages de la base', include_hidden=True).is_visible()
    assert page.evaluate('() => window.nativeEditor.setStructureOpen(true)') is True
    region = page.get_by_role('region', name='Structure et réglages de la base')
    region.wait_for(state='visible')
    assert page.locator('data-view-header-views').is_visible()
    region.focus()
    page.screenshot(path=str(OUT / 'native-structure-1920.png'), full_page=True)
    page.keyboard.press('Escape')
    assert page.evaluate('window.nativeEditor.structureOpen') is False
    page.wait_for_timeout(100)
    assert page.evaluate('() => Array.from(window.nativeEditor.getState())') == state_before_presentation
    assert page.evaluate('() => window.nativeEditor.getDatabases()[0].views.map(view => view.name)') == view_names_before
    assert page.evaluate('globalThis.nativeStructureChanges')[-2:] == [True, False]
    page.screenshot(path=str(OUT / 'native-presentation-1920.png'), full_page=True)
    assert page.locator('affine-data-view-kanban-card').count() == 2
    assert page.locator('affine-data-view-kanban-group').count() == 4, 'Empty unassigned group must not consume a column'
    unassigned_id = page.evaluate('''() => {
        const source = document.querySelector('affine-database-title').dataViewLogic.view.manager.dataSource;
        const id = source.rowAdd('end'); source.cellValueChange(id, 'title', 'Action fictive sans statut'); return id;
    }''')
    page.wait_for_function("() => document.querySelectorAll('affine-data-view-kanban-group').length === 5")
    assert page.locator('affine-data-view-kanban-group').filter(has_text='Sans statut').count() == 1
    assert page.locator(f'affine-data-view-kanban-card[data-card-id="{unassigned_id}"]').count() == 1
    page.evaluate('''id => {
        const source = document.querySelector('affine-database-title').dataViewLogic.view.manager.dataSource;
        const status = source.properties$.value.find(id => source.propertyNameGet(id) === 'Statut');
        const todo = source.propertyDataGet(status).options.find(option => option.value === 'À faire');
        source.cellValueChange(id, status, todo.id); source.rowDelete([id]);
    }''', unassigned_id)
    page.wait_for_function("() => document.querySelectorAll('affine-data-view-kanban-group').length === 4")
    group_labels = page.evaluate('() => window.nativeEditor.getDatabases()[0].groups.map(group => group.name)')
    assert all(label in group_labels for label in ['À faire', 'En cours', 'En attente', 'Terminé'])
    page.locator('affine-database').screenshot(path=str(OUT / 'native-kanban.png'))
    assert page.evaluate('() => Object.isFrozen(window.nativeMetadata.databases[0].rows)') is True
    page.get_by_role('button', name='Voir le tableau natif', exact=True).click()
    page.wait_for_function("() => window.nativeEditor.getMetadata().activeView === 'table'")
    assert page.locator('affine-data-view-kanban-card').count() == 0
    # Import two confirmed fixture proposals once; editing/deleting their native
    # rows must survive a repeated import and a full save/remount.
    action_inputs = [{'sourceKey': 'candidate-proof-1', 'title': 'Visite issue du mail fictif', 'description': 'Prévoir la rencontre sur place', 'sourceUrl': '#/mail/source-proof-1', 'owner': 'Responsable fictif', 'dueDate': '2026-11-18'}, {'sourceKey': 'candidate-proof-2', 'title': 'Action supprimée volontairement'}]
    imported = page.evaluate('(actions) => window.nativeEditor.importActions(actions)', action_inputs)
    assert len(imported['created']) == 2, {'result': imported, 'errors': errors, 'console': console_errors}
    kept_id, deleted_id = [item['rowId'] for item in imported['created']]
    page.evaluate('''([kept, deleted]) => {
        const source = document.querySelector('affine-database-title').dataViewLogic.view.manager.dataSource;
        source.cellValueChange(kept, 'title', 'Action renommée par la personne');
        const status = source.properties$.value.find(id => source.propertyNameGet(id) === 'Statut');
        const done = source.propertyDataGet(status).options.find(option => option.value === 'Terminé');
        source.cellValueChange(kept, status, done.id);
        source.rowDelete([deleted]);
    }''', [kept_id, deleted_id])
    replayed = page.evaluate('(actions) => window.nativeEditor.importActions(actions)', action_inputs)
    assert replayed['created'] == [] and replayed['existing'][0]['rowId'] == kept_id and replayed['deleted'][0]['rowId'] == deleted_id
    manual = page.evaluate("() => window.nativeEditor.addAction({title:'Action saisie explicitement',status:'En attente'})")
    assert manual['databaseId'] == database_id and manual['rowId'] != kept_id
    metadata = page.evaluate('() => window.nativeEditor.getDatabases()[0]')
    assert len(metadata['rows']) == 4
    assert metadata['managedActions'] is False, 'Existing/explicit bases must not be relabelled from bindings'
    kept = next(row for row in metadata['rows'] if row['id'] == kept_id)
    assert any(field['text'] == 'Action renommée par la personne' for field in kept['fields'])
    assert any(field['text'] == 'Terminé' for field in kept['fields'])
    assert any(field['text'] == '2026-11-18' for field in kept['fields'])
    page.get_by_role('button', name='Voir le Kanban natif', exact=True).click()
    page.wait_for_function("() => window.nativeEditor.getMetadata().activeView === 'kanban'")
    assert page.locator('affine-data-view-kanban-card').count() == 4
    native_card_ids = page.locator('affine-data-view-kanban-card').evaluate_all('(nodes) => nodes.map(node => node.dataset.cardId).sort()')
    assert native_card_ids == sorted(row['id'] for row in metadata['rows'])
    for cell in page.locator('affine-data-view-kanban-cell').all():
        if cell.is_visible(): assert cell.inner_text().strip(), 'Empty card properties must stay in detail, not consume card space'
    assert all('http://127.0.0.1' not in text for text in page.locator('affine-data-view-kanban-card').all_inner_texts())
    group_rects = page.locator('affine-data-view-kanban-group').evaluate_all('(nodes) => nodes.map(node => {const box=node.getBoundingClientRect();return {left:box.left,right:box.right};})')
    assert max(box['right'] for box in group_rects) - min(box['left'] for box in group_rects) <= 1100
    page.locator('affine-database').screenshot(path=str(OUT / 'native-kanban.png'))
    native_text = page.evaluate("() => window.nativeEditor.getText()")
    print("NATIVE_TEXT", json.dumps(native_text, ensure_ascii=False))
    assert "visite de chantier confirmée" in native_text
    assert "Visite fictive" in native_text and "Contrôler les accès" in native_text and "12000" in native_text
    page.get_by_role("button", name="Enregistrer", exact=True).click()
    page.wait_for_function("() => window.nativeEditor && !window.nativeEditor.dirty")
    assert state["revision"] == 1 and state["text"] == native_text
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => window.nativeEditor !== undefined")
    assert "visite de chantier confirmée" in page.locator("#editor").inner_text()
    assert page.locator("affine-database").count() == 1
    assert page.evaluate("() => window.nativeEditor.getText()") == native_text
    page.wait_for_function("() => window.nativeEditor.getMetadata().activeView === 'kanban'")
    after_reload = page.evaluate('(actions) => window.nativeEditor.importActions(actions)', action_inputs)
    assert after_reload['created'] == [] and after_reload['existing'][0]['rowId'] == kept_id and after_reload['deleted'][0]['rowId'] == deleted_id
    reject_writes = True
    page.evaluate("() => window.nativeEditor.addParagraph('Modification locale conservée')")
    page.get_by_role("button", name="Enregistrer", exact=True).click()
    page.wait_for_function("() => document.querySelector('#status').textContent === 'page_revision_conflict'")
    assert page.evaluate("window.nativeEditor.dirty") is True
    assert "Modification locale conservée" in page.evaluate("() => window.nativeEditor.getText()")
    assert "Modification locale conservée" not in state["text"]
    expected_conflict_errors = [error for error in console_errors if '409 (Conflict)' in error]
    assert not errors and len(console_errors) == len(expected_conflict_errors), errors + console_errors
    external = [url for url in requests if not url.startswith("http://127.0.0.1:18765/") and not url.startswith("blob:")]
    assert not external, external
    page.screenshot(path=str(OUT / "native-desktop.png"), full_page=True)
    metadata = page.evaluate("() => window.nativeEditor.getDatabases()")
    assert len(metadata) == 1 and len(metadata[0]["rows"]) == 4
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("() => window.nativeEditor.setPresentation('kanban')")
    mobile = page.locator('.travaux-native-mobile-databases')
    assert mobile.is_visible() and mobile.locator('article').count() == 4
    assert not page.locator('affine-database').is_visible()
    for detail in mobile.locator('details').all():
        detail.locator('summary').click()
    assert 'Contrôler les accès à la cour' in mobile.inner_text() and '12000' in mobile.inner_text()
    actual_ids = mobile.locator('article').evaluate_all('(nodes) => nodes.map(node => node.dataset.rowId)')
    assert sorted(actual_ids) == sorted(row['id'] for row in metadata[0]['rows'])
    assert all(label in mobile.inner_text() for label in ['À faire', 'En cours', 'En attente', 'Terminé'])
    assert mobile.get_by_role('link', name='Voir l’échange').get_attribute('href') == '#/mail/source-proof-1'
    assert 'http://127.0.0.1' not in mobile.inner_text()
    assert mobile.evaluate('(node) => node.scrollWidth <= node.clientWidth')
    page.screenshot(path=str(OUT / "native-mobile.png"), full_page=True)
    page.screenshot(path=str(OUT / "native-presentation-390.png"), full_page=True)
    print(json.dumps({"status": page.locator("#status").inner_text(), "errors": errors,
                      "console_errors": console_errors,
                      "editor_hosts": page.locator("editor-host").count(),
                      "contenteditable": page.locator("[contenteditable=true]").count(),
                      "body": page.locator("body").inner_text()[:4000]}, ensure_ascii=False))
    page.screenshot(path=str(OUT / "native-inspection.png"), full_page=True)
    (OUT / "native-inspection.html").write_text(page.content(), encoding="utf-8")
    (OUT / "native-network.json").write_text(json.dumps(requests, indent=2), encoding="utf-8")
    page.evaluate('() => window.nativeEditor.unmount()')
    assert page.locator('editor-host').count() == 0 and page.locator('.travaux-native-mobile-databases').count() == 0
    saved_bytes = len(base64.b64decode(state['state_base64']))
    state.update(state_base64=None, revision_hash=None, revision=0, text='Dossier fictif vide')
    page.reload()
    page.wait_for_function('() => window.nativeEditor !== undefined')
    assert page.evaluate('() => window.nativeEditor.getDatabases().length') == 0
    invalid = page.evaluate("() => {try {window.nativeEditor.addAction({title:''});return false;}catch{return window.nativeEditor.getDatabases().length===0;}}")
    assert invalid is True
    assert page.evaluate('() => window.nativeEditor.importActions([]).created.length') == 0
    empty_id = page.evaluate('() => window.nativeEditor.ensureDatabase()')
    assert page.evaluate('() => window.nativeEditor.ensureDatabase()') == empty_id
    assert page.evaluate('() => window.nativeEditor.getDatabases()[0].rows.length') == 0
    page.evaluate("() => window.nativeEditor.setDatabaseView('kanban')")
    assert page.evaluate('() => window.nativeEditor.getDatabases()[0].rows.length') == 0
    assert page.evaluate('window.nativeEditor.getMetadata().managedActionDatabaseId') == empty_id
    assert page.evaluate('window.nativeEditor.getDatabases()[0].managedActions') is True
    page.evaluate("() => window.nativeEditor.setPresentation('page')")
    page.wait_for_timeout(50)
    assert not page.locator(f'.travaux-native-mobile-databases [data-database-id="{empty_id}"]').is_visible()
    personal_id = page.evaluate("() => window.nativeEditor.addDatabase({title:'Tableau personnel explicite'})")
    page.wait_for_timeout(50)
    assert page.locator(f'.travaux-native-mobile-databases [data-database-id="{personal_id}"]').is_visible()
    assert page.evaluate('() => window.nativeEditor.ensureDatabase()') == empty_id
    native_target = page.evaluate("() => window.nativeEditor.importActions([{sourceKey:'candidate-managed-proof',title:'Action fictive créée explicitement pour la recette'}])")
    assert native_target['created'][0]['databaseId'] == empty_id
    page.evaluate('() => window.nativeEditor.unmount()')
    (OUT / 'presentation-proof.json').write_text(json.dumps({
        'fixture': True, 'viewport_desktop': [1920, 1080], 'viewport_mobile': [390, 844],
        'duplicate_native_viewbar_hidden': True, 'data_header_hidden_by_default': True,
        'structure_opens_real_native_tools': True, 'escape_closes_structure': True,
        'structure_callback': True, 'presentation_binary_state_unchanged': True,
        'human_h1_visible': True, 'human_view_names_unchanged': True,
        'existing_explicit_database_not_marked_from_bindings': True,
        'new_automatic_database_marked': True, 'notes_hide_only_marked_automatic_database': True,
        'explicit_personal_database_kept_visible': True, 'action_import_targets_managed_database': True,
    }, indent=2), encoding='utf-8')
    (OUT / "native-proof.json").write_text(json.dumps({"engine": "AFFiNE BlockSuite 0.22.4", "fixture": True, "keyboard_edit": True, "visible_native_block_commands": True, "native_database": True, "actual_kanban_four_status_groups": True, "empty_unassigned_group_not_seeded": True, "real_unassigned_row_group_visible_in_french": True, "kanban_four_groups_fit_1100px": True, "kanban_empty_cells_hidden": True, "no_technical_url_on_cards_or_mobile": True, "same_row_ids_across_views": True, "action_import_deduplication": True, "human_edits_preserved_on_reimport": True, "deleted_action_not_resurrected": True, "bindings_and_view_survive_reload": True, "explicit_manual_action": True, "empty_database_without_placeholder_rows": True, "readonly_metadata_callback": True, "database_values_in_text": True, "save_reload": True, "conflict_preserves_edits": True, "mobile_grouped_cards_same_native_ids": True, "mobile_complete_values": True, "mobile_no_horizontal_overflow": True, "unmount": True, "external_requests": external, "errors": errors, "expected_conflict_console": expected_conflict_errors, "saved_state_bytes": saved_bytes}, indent=2), encoding="utf-8")
    browser.close()
