import threading
import time
import json
from pathlib import Path
import sys

ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / 'src'))
from travaux.api import create_app
from travaux.config import Settings
import uvicorn

settings = Settings(
    mode='demo',
    db_path=ROOT / 'temp_run' / 'gallery.sqlite3',
    tenant_id='plougastel-audit',
    llm='demo',
    allowed_hosts=('127.0.0.1', 'localhost'),
    password_hash='test-hash',
    auth_mode='password',
)
app = create_app(settings)
t = threading.Thread(target=uvicorn.run, args=(app,), kwargs={'host': '127.0.0.1', 'port': 19866, 'log_level': 'error'}, daemon=True)
t.start()
time.sleep(1)

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()
    page.goto('http://127.0.0.1:19866/demo.html#/')
    page.wait_for_timeout(1000)
    
    # Check current modules from API
    api_res = page.evaluate('''async () => {
        const r = await fetch('/api/v1/organizations/current/modules', { headers: { 'X-Requested-With': 'Travaux' } });
        return { status: r.status, data: await r.json() };
    }''')
    print('Initial API modules:', api_res['data']['enabled_modules'])
    
    # Now PATCH to minimal
    patch_res = page.evaluate('''async () => {
        const r = await fetch('/api/v1/organizations/current/modules', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'Travaux' },
            body: JSON.stringify({ enabled_modules: ['core_directory', 'core_workflows', 'core_documents'] })
        });
        return { status: r.status, data: await r.json() };
    }''')
    print('PATCH response status:', patch_res['status'])
    print('PATCH response data:', patch_res['data'])
    
    # Check localStorage in page
    ls = page.evaluate('''() => localStorage.getItem('mayortech_active_modules')''')
    print('LocalStorage before reload:', ls)

    # Reload page
    page.reload(wait_until='networkidle')
    page.wait_for_timeout(1000)

    # Check localStorage after reload
    ls_after = page.evaluate('''() => localStorage.getItem('mayortech_active_modules')''')
    print('LocalStorage after reload:', ls_after)
    
    # Check DOM for Messagerie link
    msg_count = page.locator('a:has-text("Messagerie")').count()
    planning_count = page.locator('a:has-text("Planning")').count()
    terrain_count = page.locator('a:has-text("Suivi terrain")').count()
    chantiers_label = page.locator('text=CHANTIERS FAVORIS').count()
    fab_count = page.locator('button:has-text("Assistant")').count()
    print('Messagerie text link count:', msg_count)
    print('Planning text link count:', planning_count)
    print('Suivi terrain count:', terrain_count)
    print('Chantiers favoris count:', chantiers_label)
    print('Assistant button count:', fab_count)
    
    browser.close()
