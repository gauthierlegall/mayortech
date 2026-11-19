"""Current frontend against an offline demo API; fictional summary bookmarks."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import urlopen

import mail_splitter as fixture

ROOT = Path(__file__).resolve().parents[2]
fixture.PORT = 19808
fixture.BASE = BASE = "http://127.0.0.1:19808"


def recipe(output, report):
    from playwright.sync_api import expect, sync_playwright

    def check(name, passed):
        report["checks"].append({"name": name, "passed": bool(passed)})
        assert passed, name

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}, locale="fr-FR", reduced_motion="reduce"
        )
        page = context.new_page()
        page.set_default_timeout(20000)
        page.on("pageerror", lambda error: report["js_errors"].append(str(error)))

        def route(request):
            if request.request.url.startswith(BASE + "/") or request.request.url.startswith(
                ("data:", "blob:")
            ):
                request.continue_()
            else:
                report["external_requests"].append(request.request.url)
                request.abort()

        context.route("**/*", route)

        def capture(name):
            page.screenshot(path=str(output / name), full_page=False)
            report["screenshots"].append(
                {
                    "file": name,
                    "viewport": page.viewport_size,
                    "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
                }
            )

        def open_bookmark(hash):
            page.goto(BASE + "/web/product/index.html" + hash, wait_until="networkidle")

        def home():
            expect(page.get_by_role("heading", name="Chantiers", exact=True)).to_be_visible()
            expect(page).to_have_url(re.compile(r"/#/$|/index.html#/$"))

        try:
            before = context.request.get(BASE + "/api/v1/summaries").json()
            summary = before[0]
            project_id = summary["project_id"]
            project = context.request.get(BASE + "/api/v1/projects/" + project_id).json()
            open_bookmark("#/")
            home()
            check(
                "Desktop navigation has no global recap link",
                page.locator('.sidebar a[href*="summar"],.sidebar a[href*="recapitulatifs"]').count() == 0,
            )
            capture("1920-01-project-navigation.png")
            for path in ["#/summaries", "#/recapitulatifs"]:
                open_bookmark(path)
                home()
                check(
                    "Former index " + path + " redirects to projects",
                    page.get_by_role("heading", name="Récapitulatifs", exact=True).count() == 0,
                )
            for path in ["#/summary/", "#/summaries/", "#/recapitulatifs/"]:
                open_bookmark(path + summary["id"])
                expect(page).to_have_url(
                    re.compile(r"#/chantiers/" + re.escape(project_id) + r"\?view=page$")
                )
                expect(page.get_by_role("heading", name=project["name"], exact=True)).to_be_visible()
                check(
                    "Legacy version " + path + " opens its actual project",
                    page.get_by_role("button", name=re.compile("Historique des récapitulatifs")).count() == 1,
                )
            page.get_by_role("button", name=re.compile("Historique des récapitulatifs")).click()
            dialog = page.get_by_role("dialog")
            expect(
                dialog.get_by_role("heading", name="Récapitulatifs du chantier", exact=True)
            ).to_be_visible()
            expect(dialog.locator("textarea")).to_have_value(summary["content"])
            check(
                "Project recap history retains its real saved content",
                dialog.locator("textarea").input_value() == summary["content"],
            )
            capture("1920-02-project-recap.png")
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
            open_bookmark("#/summary/missing-summary")
            home()
            check(
                "Missing version returns to projects",
                page.get_by_role("heading", name="Récapitulatifs", exact=True).count() == 0,
            )
            held = {}

            def hold(request):
                held["response"] = request.fetch()
                held["route"] = request

            page.route("**/api/v1/summaries/" + summary["id"], hold)
            page.goto(
                BASE + "/web/product/index.html#/summary/" + summary["id"], wait_until="domcontentloaded"
            )
            expect(page.get_by_text("Ouverture du chantier…", exact=True)).to_be_visible()
            deadline = time.monotonic() + 5
            while "route" not in held and time.monotonic() < deadline:
                page.wait_for_timeout(25)
            assert "route" in held
            page.locator(".sidebar .main-nav a").filter(has_text="Messagerie").click()
            expect(page.get_by_role("heading", name="Messagerie", exact=True)).to_be_visible()
            held["route"].fulfill(response=held["response"])
            page.evaluate(
                "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
            )
            check("Late lookup cannot override a newer navigation choice", "#/messagerie" in page.url)
            page.unroute("**/api/v1/summaries/" + summary["id"], hold)
            page.set_viewport_size({"width": 390, "height": 844})
            open_bookmark("#/summaries")
            home()
            page.get_by_role("button", name="Ouvrir la navigation", exact=True).click()
            expect(page.locator(".workspace.mobile-open")).to_be_visible()
            check(
                "Mobile menu has no global recap entry",
                page.locator(".sidebar").get_by_role("link", name="Récapitulatifs", exact=True).count() == 0,
            )
            check(
                "Mobile settings remain accessible",
                page.locator(".sidebar").get_by_role("link", name="Paramètres", exact=True).count() == 1,
            )
            capture("390-03-navigation.png")
            page.keyboard.press("Escape")
            open_bookmark("#/summary/" + summary["id"])
            expect(page).to_have_url(re.compile(r"#/chantiers/" + re.escape(project_id) + r"\?view=page$"))
            button = page.get_by_role("button", name=re.compile("Historique des récapitulatifs"))
            button.scroll_into_view_if_needed()
            button.click()
            expect(
                dialog.get_by_role("heading", name="Récapitulatifs du chantier", exact=True)
            ).to_be_visible()
            check(
                "Project recap remains available on mobile",
                dialog.locator("textarea").input_value() == summary["content"]
                and page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),
            )
            capture("390-04-project-recap.png")
            page.keyboard.press("Escape")
            after = context.request.get(BASE + "/api/v1/summaries").json()
            check(
                "No summary version or content changed or disappeared",
                sorted((row["id"], row["content_hash"]) for row in before)
                == sorted((row["id"], row["content_hash"]) for row in after),
            )
            check(
                "No browser exception or external request",
                not report["js_errors"] and not report["external_requests"],
            )
        except Exception:
            capture("failure.png")
            (output / "failure-dom.txt").write_text(page.locator("body").inner_text(), encoding="utf8")
            raise
        finally:
            context.close()
            browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "test-results/summary-navigation-20261117")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.serve:
        fixture.serve(output)
        return 0
    if fixture.listening():
        raise RuntimeError("Port 19808 occupied; no existing process is stopped.")
    report = {
        "scope": "Current frontend and real offline demo API/SQLite. Fictional data only; no remote deployment.",
        "checks": [],
        "screenshots": [],
        "js_errors": [],
        "external_requests": [],
    }
    with (
        (output / "server.stdout.log").open("w", encoding="utf8") as stdout,
        (output / "server.stderr.log").open("w", encoding="utf8") as stderr,
    ):
        server = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve", "--output", str(output)],
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("Offline QA server exited; see stderr.")
                try:
                    with urlopen(BASE + "/api/v1/session", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Offline QA startup timed out.")
            recipe(output, report)
        except Exception as error:
            report["failure"] = type(error).__name__ + ": " + str(error)
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            deadline = time.monotonic() + 5
            while fixture.listening() and time.monotonic() < deadline:
                time.sleep(0.05)
            report["server_stopped"] = server.poll() is not None and not fixture.listening()
    report["passed"] = (
        not report.get("failure")
        and bool(report["checks"])
        and all(row["passed"] for row in report["checks"])
        and report["server_stopped"]
    )
    (output / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(
        json.dumps(
            {"passed": report["passed"], "checks": len(report["checks"]), "failure": report.get("failure")},
            ensure_ascii=True,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
