"""Chromium component recipe; every account/message is a synthetic local fixture.

Run explicitly with the project Python. No real mailbox, sending or external URL.
"""

import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = '<!doctype html><meta charset="utf-8"><main id="app"></main><script type="module" src="/fixture.js"></script>'
SCRIPT = """
import {mountMailbox} from '/web/mailbox.js';
const mode=new URL(location.href).searchParams.get('mode')||'private';
window.calls=[];window.saved=[];window.listCalls=[];
const source={id:'mail-fixture',subject:'Visite fictive',body:'Message fictif uniquement.',sender:'Alice <alice@example.invalid>',metadata:{fictitious:true},project_ids:[],read:false,starred:false,mailbox_revision:0};
const writable=['to','cc','bcc','subject','body','in_reply_to','mode','expected_revision','client_id'];
const api={
  mailboxFolders:async()=>({items:[],capabilities:{can_send:false,server_drafts:mode==='private',can_compose:mode==='private',can_manage_flags:mode!=='reader'}}),
  mailboxMessages:async filters=>{window.listCalls.push({...filters});const rows=window.fixtureRows||[{...source}];return {items:rows.slice(Number(filters.offset||0),Number(filters.offset||0)+Number(filters.limit||50)),total:rows.length};},
  mailMessage:async()=>{await new Promise(resolve=>setTimeout(resolve,250));return {source:window.sourceOverride||source};},
  mailboxFlags:async(id,body)=>{window.calls.push({kind:'flags',body});Object.assign(source,body);return {...source,mailbox_revision:++source.mailbox_revision};},
  mailDrafts:async()=>{window.calls.push({kind:'draft-list'});return {items:structuredClone(window.saved)};},
  createMailDraft:async body=>{if(mode!=='private')throw Error('No private draft transport permitted');if(Object.keys(body).some(key=>!writable.includes(key)))throw Error('Unexpected create field');window.calls.push({kind:'create',body:structuredClone(body)});const saved={...structuredClone(body),id:'draft-fixture',revision:1,created_at:'2026-11-15T10:00:00Z',updated_at:'2026-11-15T10:00:00Z'};window.saved.push(saved);return structuredClone(saved);},
  saveMailDraft:async(id,body)=>{if(Object.keys(body).some(key=>!writable.includes(key)||key==='client_id'))throw Error('Unexpected patch field');const saved=window.saved.find(item=>item.id===id);if(body.expected_revision!==saved.revision)throw Error('Stale revision');window.calls.push({kind:'patch',body:structuredClone(body)});Object.assign(saved,body,{revision:saved.revision+1});delete saved.expected_revision;return structuredClone(saved);},
  deleteMailDraft:async id=>{window.saved=window.saved.filter(item=>item.id!==id);},
  sendMail:async()=>{throw Error('No transport configured');}
};
window.remount=async(options={})=>{window.controller?.destroy();window.controller=await mountMailbox(document.querySelector('#app'),{api,publicDemo:mode==='public',...options});};
await window.remount();window.ready=true;
"""


def run():
    result = {"fixture": True, "external_requests": [], "cases": []}
    with sync_playwright() as p:
        executable = os.environ.get("TRAVAUX_CHROMIUM_EXECUTABLE")
        browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def fixture(route):
            address = urlparse(route.request.url)
            if address.hostname != "127.0.0.1":
                result["external_requests"].append(route.request.url)
                route.abort()
                return
            if address.path == "/fixture.html":
                route.fulfill(body=HTML, content_type="text/html")
            elif address.path == "/fixture.js":
                route.fulfill(body=SCRIPT, content_type="text/javascript")
            elif address.path.startswith("/web/"):
                path = (ROOT / unquote(address.path[1:])).resolve()
                assert path.is_relative_to(ROOT / "web")
                route.fulfill(
                    body=path.read_bytes(),
                    content_type="text/javascript" if path.suffix == ".js" else mimetypes.guess_type(path)[0],
                )
            else:
                route.fulfill(status=204)

        page.route("**/*", fixture)
        page.goto("http://127.0.0.1:18766/fixture.html?mode=private")
        page.wait_for_function("window.ready===true")
        page.locator('[data-inbox="compose"]').click()
        page.locator("#compose-to").fill("alice@example.invalid")
        page.locator("#compose-subject").fill("Brouillon fictif")
        page.locator("#compose-body").fill("Première version fictive")
        page.evaluate("window.controller.flush()")
        assert page.evaluate("window.calls.filter(x=>x.kind==='create').length") == 1
        page.evaluate("window.remount({folder:'drafts'})")
        page.locator('[data-inbox="open"]').click()
        page.locator("#compose-body").fill("Seconde version fictive")
        page.evaluate("window.controller.flush()")
        assert page.evaluate("window.saved[0].body") == "Seconde version fictive"
        assert page.evaluate("window.calls.filter(x=>x.kind==='patch').length") == 1
        assert page.evaluate("window.calls.find(x=>x.kind==='patch').body.expected_revision") == 1
        result["cases"].append("private_create_reopen_patch_no_readonly_fields")

        page.evaluate("window.remount()")
        page.locator('[data-inbox="open"]').click()
        page.locator('[data-inbox="compose"]').click()
        page.wait_for_timeout(350)
        assert page.locator("#compose-body").count() == 1
        result["cases"].append("late_mail_response_does_not_replace_composer")

        page.goto("http://127.0.0.1:18766/fixture.html?mode=public")
        page.wait_for_function("window.ready===true")
        page.locator('[data-inbox="compose"]').click()
        page.locator("#compose-body").fill("Brouillon public local fictif")
        page.evaluate("window.controller.flush()")
        assert page.evaluate("window.calls.length") == 0
        assert "Brouillon public local fictif" in page.evaluate(
            "localStorage.getItem('travaux:mail-drafts:v1')"
        )
        page.evaluate("window.remount({folder:'drafts'})")
        assert page.locator('[data-inbox="open"]').count() == 1
        result["cases"].append("public_draft_only_in_own_browser")

        page.goto("http://127.0.0.1:18766/fixture.html?mode=reader")
        page.wait_for_function("window.ready===true")
        assert not page.locator('[data-inbox="compose"]').is_visible()
        assert page.locator('[data-inbox="star"]').is_disabled()
        page.locator('[data-inbox="open"]').click()
        page.wait_for_timeout(350)
        assert not page.locator('[data-inbox="reply"]').is_visible()
        assert not page.evaluate("window.calls.some(x=>x.kind==='flags')")
        page.evaluate("window.remount({folder:'drafts'})")
        assert page.locator('[data-inbox="open"]').count() == 0
        assert not page.evaluate("window.calls.some(x=>x.kind==='draft-list')")
        result["cases"].append("reader_has_no_compose_flags_or_public_local_draft_leak")

        page.evaluate("""async()=>{
          window.listCalls=[];
          window.fixtureRows=Array.from({length:51},(_,i)=>({id:'mail-'+i,subject:'Message fictif '+i,body:'Source liée',project_ids:['project-1']}));
          await window.remount({layout:'lovable',projectId:'project-1',onLayout:({folderTarget})=>{folderTarget.textContent='Dossiers de courrier';}});
        }""")
        assert page.locator('.lovable-mail .inbox-folders').count() == 1
        page.locator('[data-inbox="next"]').click()
        page.wait_for_function("window.listCalls.at(-1)?.offset==='50'")
        assert page.evaluate("window.listCalls.every(call=>call.project_id==='project-1')")
        assert page.locator('[data-inbox="open"]').count() == 1
        result["cases"].append("lovable_folder_slot_and_project_filter_survive_pagination")

        page.evaluate("window.sourceOverride={id:'mail-50',subject:'Autre chantier',body:'Ne pas afficher dans ce filtre',project_ids:['project-other']}")
        page.locator('[data-inbox="open"]').click()
        page.wait_for_timeout(350)
        assert page.locator('.mail-message').count() == 0
        assert 'chantier sélectionné' in page.locator('.inbox-status').inner_text()
        result["cases"].append("deep_link_cannot_show_a_source_from_another_project_filter")
        assert not errors, errors
        assert not result["external_requests"]
        browser.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    run()
