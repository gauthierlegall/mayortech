"""Real React/Chrome lifecycle regression fixture, with an explicit native mock.

No provider/backend integration is claimed. No new Python/Node dependency is
installed. Each case uses a fresh browser context and fictional text only.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading

from playwright.sync_api import expect, sync_playwright


PROJECT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT / "frontend-lovable"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="Optional frozen old components for the negative control")
    parser.add_argument("--unsafe-lifecycle-control", action="store_true", help="Mutate only the test bundle to restore the two unsafe lifecycle behaviors; expected failure")
    parser.add_argument("--unsafe-workspace-observation-control", action="store_true", help="Mutate only the test bundle to suppress observation of account B; expected failure")
    parser.add_argument("--output", type=Path, default=PROJECT / "test-results/native-session-react")
    parser.add_argument("--case", help="Run only a named regression while diagnosing the fixture")
    args = parser.parse_args()
    output = args.output.resolve()
    site = output / "site"
    output.mkdir(parents=True, exist_ok=True)
    command = ["node", "tests/browser/native-session/build.mjs", str(site)]
    if args.baseline:
        command.append(str(args.baseline.resolve()))
    if args.unsafe_lifecycle_control:
        command.append("--unsafe-lifecycle-control")
    if args.unsafe_workspace_observation_control:
        command.append("--unsafe-workspace-observation-control")
    subprocess.run(command, cwd=FRONTEND, check=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    results = []
    draft = "Note fictive saisie PENDANT le rechargement — à conserver."

    def note(page):
        return page.get_by_role("textbox", name="Note fictive du contrôleur natif simulé")

    def dirty_reload(page):
        note(page).fill("Note fictive enregistrée avant le rechargement.")
        page.evaluate("()=>window.lab.preserveBeforeReload()")
        note(page).fill(draft)
        page.evaluate("()=>window.lab.receiveChangedActions()")
        expect(page.get_by_role("status")).to_have_text("Nouvelles actions reçues")
        expect(note(page)).to_have_value(draft)
        diagnostics = page.evaluate("()=>window.lab.diagnostics()")
        assert len(diagnostics) == 1, "Action/name refresh remounted the controller"
        assert diagnostics[0]["dirty"] and not diagnostics[0]["destroyed"]
        assert diagnostics[0]["updates"] >= 1, "New actions were never delivered to the retained controller"
        return diagnostics

    def account_switch(page):
        note(page).fill("Brouillon fictif privé du compte A.")
        page.evaluate("()=>window.lab.beginDeferredSave()")
        page.evaluate("()=>window.lab.switchAccount()")
        expect(page.get_by_text("Compte B actif", exact=True)).to_be_visible()
        expect(note(page)).to_have_value("")
        result = page.evaluate("()=>window.lab.releaseDeferredSave()")
        assert result["ok"] is False, "Old account's deferred native write was accepted"
        diagnostics = page.evaluate("()=>window.lab.diagnostics()")
        assert len(diagnostics) == 2 and diagnostics[0]["destroyed"]
        assert diagnostics[0]["writes"] == 0 and diagnostics[0]["blocked"] == 1
        return diagnostics

    def current_grant_removed(page):
        note(page).fill("Note fictive du dossier dont l’accès sera retiré.")
        page.evaluate("()=>window.lab.beginDeferredSave()")
        page.evaluate("()=>window.lab.revokeCurrent()")
        result = page.evaluate("()=>window.lab.releaseDeferredSave()")
        assert result["ok"] is False, "Revoked project's deferred native write was accepted"
        diagnostics = page.evaluate("()=>window.lab.diagnostics()")
        assert diagnostics[0]["writes"] == 0 and diagnostics[0]["blocked"] == 1
        return diagnostics

    def neighbor_grant_removed(page):
        note(page).fill("Note fictive du dossier conservé, malgré le retrait du voisin.")
        page.evaluate("()=>window.lab.beginDeferredSave()")
        page.evaluate("()=>window.lab.revokeNeighbor()")
        expect(note(page)).to_have_value("Note fictive du dossier conservé, malgré le retrait du voisin.")
        result = page.evaluate("()=>window.lab.releaseDeferredSave()")
        assert result["ok"] is True, "Unrelated grant removal permanently invalidated the retained editor"
        diagnostics = page.evaluate("()=>window.lab.diagnostics()")
        assert len(diagnostics) == 1 and not diagnostics[0]["destroyed"]
        assert diagnostics[0]["writes"] == 1 and diagnostics[0]["blocked"] == 0
        return diagnostics

    def revoked_action_hidden_on_failed_reload(page):
        page.evaluate("()=>window.lab.showActions()")
        expect(page.get_by_role("button", name="Action fictive du dossier révoqué")).to_be_visible()
        page.evaluate("()=>window.lab.revokeNeighborWithFailedActionLoad()")
        expect(page.get_by_role("alert")).to_contain_text("Échec réseau fictif")
        expect(page.get_by_role("button", name="Action fictive du dossier révoqué")).to_have_count(0)
        expect(page.get_by_role("button", name="Action fictive du dossier conservé")).to_be_visible()
        return page.evaluate("()=>window.lab.diagnostics()")

    def failed_business_load_masks_previous_identity(page):
        expect(page.get_by_role("heading", name="Contenu métier fictif du compte A")).to_be_visible()
        result = page.evaluate("()=>window.lab.refreshAfterCookieSwitch()")
        assert result["failed"] is True and result["cachedActor"] is None and result["cachedProjects"] == [], "The observed account switch must purge the real QueryClient's old identity and project cache even when B's business load fails"
        assert "session:account-b" in result["requests"] and "bootstrap:account-b" in result["requests"]
        expect(page.get_by_role("heading", name="Contenu métier fictif du compte A")).to_have_count(0)
        expect(page.get_by_text("Le compte actif a changé. Son espace doit être chargé avant de poursuivre.", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Recharger l’espace")).to_be_visible()
        return result

    def failed_detail_masks_revoked_access_and_keeps_draft(page):
        expect(page.get_by_role("heading", name="Dossier fictif neighbor")).to_be_visible()
        box = page.get_by_role("textbox", name="Note fictive du dossier conservé", include_hidden=True)
        box.fill("Brouillon fictif à conserver après retrait du dossier voisin.")
        result = page.evaluate("()=>window.lab.refreshAfterGrantRemoval()")
        assert result["failed"] is True and sorted(result["cachedProjects"]) == ["neighbor", "retained"]
        expect(page.get_by_role("heading", name="Dossier fictif neighbor", include_hidden=True)).to_be_hidden()
        expect(page.get_by_role("heading", name="Dossier fictif retained", include_hidden=True)).to_be_hidden()
        expect(page.get_by_text("La liste de vos dossiers a changé. Rechargez votre espace pour poursuivre.", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Recharger l’espace")).to_be_visible()
        expect(box).to_have_value("Brouillon fictif à conserver après retrait du dossier voisin.")
        resumed = page.evaluate("()=>window.lab.retryGrantedLoad()")
        expect(page.get_by_role("heading", name="Dossier fictif retained")).to_be_visible()
        expect(page.get_by_role("heading", name="Dossier fictif neighbor", include_hidden=True)).to_have_count(0)
        expect(box).to_be_visible()
        expect(box).to_have_value("Brouillon fictif à conserver après retrait du dossier voisin.")
        assert resumed["mounts"] == result["mounts"] == 1
        return {**result, "retainedDraftPreserved": True, "mountsAfterRetry": resumed["mounts"]}

    cases = [("dirty-note-during-action-reload", dirty_reload), ("account-switch-clears-ui-and-stops-old-write", account_switch),
             ("current-grant-stops-deferred-write", current_grant_removed), ("neighbor-grant-keeps-dirty-retained-editor", neighbor_grant_removed),
             ("revoked-action-hidden-even-when-reload-fails", revoked_action_hidden_on_failed_reload),
             ("session-b-read-business-failure-masks-cached-a", failed_business_load_masks_previous_identity),
             ("grant-list-read-detail-failure-masks-cache-keeps-draft", failed_detail_masks_revoked_access_and_keeps_draft)]
    if args.case:
        cases = [item for item in cases if item[0] == args.case]
        if not cases:
            raise ValueError("Unknown regression name")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel="chrome")
            try:
                for index, (name, run) in enumerate(cases, 1):
                    if index > 1:
                        browser.close()
                        browser = playwright.chromium.launch(headless=True, channel="chrome")
                    context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
                    page = context.new_page()
                    page.set_default_timeout(5000)
                    blocked = []
                    errors = []
                    request_failures = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("requestfailed", lambda request: request_failures.append({"url": request.url, "failure": request.failure}))
                    def route_request(route):
                        if route.request.url.startswith(origin + "/"):
                            route.continue_()
                        else:
                            blocked.append(route.request.url)
                            route.abort()
                    page.route("**/*", route_request)
                    workspace_case = run in (failed_business_load_masks_previous_identity, failed_detail_masks_revoked_access_and_keeps_draft)
                    item = {"name": name, "passed": False, "explicit_mocks": ["API transport"] if workspace_case else ["workspace context", "native page controller", "Actions projection/transport"]}
                    try:
                        path = "/workspace-provider.html?scenario=grants" if run is failed_detail_masks_revoked_access_and_keeps_draft else "/workspace-provider.html" if workspace_case else "/"
                        page.goto(origin + path, wait_until="networkidle", timeout=20000)
                        if not workspace_case:
                            expect(note(page)).to_be_visible()
                        item["workspace" if workspace_case else "controllers"] = run(page)
                        assert blocked == [], "Unexpected external request from fixture"
                        item["passed"] = True
                    except Exception as error:
                        item["error"] = str(error).split("Call log:")[0].strip()
                        item["page_errors"] = errors
                        item["request_failures"] = request_failures
                        item["blocked_requests"] = blocked
                        item["controllers"] = page.evaluate("()=>window.lab?.diagnostics?.()||[]")
                    finally:
                        page.screenshot(path=str(output / f"{index:02d}-{name}.png"), full_page=True)
                        context.close()
                    results.append(item)
                    print(json.dumps({"case": name, "passed": item["passed"], "error": item.get("error")}, ensure_ascii=False), flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    report = {"fixture": True, "baseline": bool(args.baseline), "negative_control": args.unsafe_lifecycle_control, "negative_workspace_observation": args.unsafe_workspace_observation_control, "viewport": {"width": 1920, "height": 1080},
              "real": ["Chrome", "React", "production AuthGate, BlockEditor and Actions", "native scope guard", "panel lifecycle", "WorkspaceProvider, QueryClient and loadWorkspace (cases 6 and 7)"],
              "not_qualified": ["OIDC", "BlockSuite renderer", "backend persistence", "real identity provider"], "results": results}
    (output / "proof.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(item["passed"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
