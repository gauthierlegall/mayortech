"""Independent browser acceptance of both mail splitters against a local demo API.

No external mail account, provider or secret is used. The owned loopback server
is started only when this script is explicitly executed, and stopped in finally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
PORT = 19806
BASE = f"http://127.0.0.1:{PORT}"
NAME = "Redimensionner la liste des messages"
REFERENCE = "QA-SPLITTER-1711"
SUBJECTS = ["Recette fictive — accès du chantier", "Recette fictive — livraison du matériel"]
MARKER = "BROUILLON_FICTIF_SEPARATEUR_1711"


def listening():
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def serve(output):
    for name in list(os.environ):
        if name.startswith("TRAVAUX_") or name in {"SSLKEYLOGFILE", "QUICLOGDIR"}:
            os.environ.pop(name, None)
    sys.path.insert(0, str(ROOT / "src"))
    from fastapi.staticfiles import StaticFiles
    from travaux.api import create_app
    from travaux.config import Settings
    import uvicorn

    data = ROOT / ".local" / "mail-splitter-browser-qa" / str(time.time_ns())
    data.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        mode="demo",
        db_path=data / "workspace.sqlite3",
        tenant_id="splitter-qa",
        llm="demo",
        allowed_hosts=("127.0.0.1",),
    )
    app = create_app(settings)
    repo = app.state.repo
    projects = [row for row in repo.list_projects(settings.tenant_id) if row["reference"] == REFERENCE]
    project = (
        projects[0]
        if projects
        else repo.create_project(settings.tenant_id, REFERENCE, "Chantier fictif du séparateur")
    )
    mails = []
    for index, subject in enumerate(SUBJECTS):
        body = (
            f"Bonjour,\n\nMessage entièrement fictif numéro {index + 1}.\nAccès du chantier à vérifier avec le service travaux.\n"
            + (("Texte_long_fictif_" * 28) if index else "Accès piéton de recette fictive.")
            + "\n\nCordialement,\nAtelier fictif"
        )
        source = repo.ingest_source(
            settings.tenant_id,
            f"mail-splitter-{index}@demo.invalid",
            subject,
            body,
            project_ref=REFERENCE,
            sender="atelier@entreprise-fictive.invalid",
            received_at=f"2026-11-17T{10 + index}:00:00+00:00",
            metadata={"fictitious": True, "source_kind": "mail"},
        )
        mails.append({"id": source["id"], "subject": subject})
    output.mkdir(parents=True, exist_ok=True)
    (output / "fixture.json").write_text(
        json.dumps(
            {
                "origin": BASE,
                "project_id": project["id"],
                "mails": mails,
                "scope": "Local fictional demo; authentication and real mail providers are not exercised.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    app.mount(
        "/web/product",
        StaticFiles(directory=ROOT / "frontend-lovable/dist", html=True),
        name="splitter-current-build",
    )
    mount = app.router.routes.pop()
    before = next(
        index for index, route in enumerate(app.router.routes) if getattr(route, "path", None) == "/web"
    )
    app.router.routes.insert(before, mount)
    uvicorn.run(app, host="127.0.0.1", port=PORT, access_log=False, log_level="warning")


def numeric_preference(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return 240 <= value <= 720
    return (
        isinstance(value, dict)
        and bool(value)
        and all(
            isinstance(key, str) and len(key) < 80 and numeric_preference(item) for key, item in value.items()
        )
    )


def recipe(output, report):
    from playwright.sync_api import expect, sync_playwright

    fixture = json.loads((output / "fixture.json").read_text(encoding="utf-8"))
    assert fixture["origin"] == BASE
    project_id, mail_id = fixture["project_id"], fixture["mails"][0]["id"]
    subject = fixture["mails"][0]["subject"]
    app = BASE + "/web/product/index.html"

    def check(name, passed, observed=None):
        report["checks"].append(
            {"name": name, "passed": bool(passed), **({"observed": observed} if observed is not None else {})}
        )
        assert passed, name

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        page.on("pageerror", lambda error: report["js_errors"].append(str(error)))
        page.on(
            "console",
            lambda entry: report["console_errors"].append(entry.text) if entry.type == "error" else None,
        )

        def route(request):
            url = request.request.url
            if url.startswith(BASE + "/") or url.startswith(("data:", "blob:")):
                request.continue_()
            else:
                report["external_requests"].append(url)
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

        def storage():
            return page.evaluate(
                "()=>Object.fromEntries(Object.keys(localStorage).map(key=>[key,localStorage.getItem(key)]))"
            )

        def width(selector):
            return page.locator(selector).bounding_box()["width"]

        def separator():
            return page.get_by_role("separator", name=NAME, exact=True)

        def value():
            return float(separator().get_attribute("aria-valuenow"))

        def begin_drag(delta=None, target=None):
            bounds = separator().bounding_box()
            x, y = bounds["x"] + bounds["width"] / 2, bounds["y"] + min(160, bounds["height"] / 2)
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(target if target is not None else x + delta, y, steps=8)
            return x, y

        def settle():
            page.evaluate(
                "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
            )

        def drag(delta=None, target=None):
            begin_drag(delta, target)
            page.mouse.up()
            page.evaluate(
                "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
            )

        def no_overflow(label):
            check(label, page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"))

        def selected_global():
            return page.locator('.inbox-row.selected [data-inbox="open"]').get_attribute("data-id")

        try:
            page.goto(app + "#/mail/" + mail_id + "?folder=inbox", wait_until="networkidle")
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            expect(separator()).to_be_visible()
            check(
                "FHD global splitter has vertical orientation and keyboard focus",
                separator().get_attribute("aria-orientation") == "vertical"
                and separator().get_attribute("tabindex") == "0",
            )
            initial = width(".inbox-list")
            before_storage = storage()
            before_text = page.locator(".inbox-reader .mail-body").inner_text()
            before_hash = page.evaluate("location.hash")
            capture("1920-01-global-default.png")
            drag(delta=100)
            check(
                "Pointer drag changes actual global list width",
                width(".inbox-list") > initial + 50,
                {"before": initial, "after": width(".inbox-list")},
            )
            check(
                "Pointer drag preserves selected message, reader text and navigation",
                selected_global() == mail_id
                and page.locator(".inbox-reader .mail-body").inner_text() == before_text
                and page.evaluate("location.hash") == before_hash,
            )
            after_storage = storage()
            changed = {key: value for key, value in after_storage.items() if before_storage.get(key) != value}
            check(
                "Splitter stores only a numeric layout preference",
                bool(changed)
                and all(numeric_preference(json.loads(value)) for value in changed.values())
                and not any(subject in value or before_text in value for value in changed.values()),
                {"preference_keys": list(changed)},
            )
            check(
                "Global preference uses its explicit layout-only key",
                list(changed) == ["travaux:mail-list-width:global:v1"],
            )
            report["preference_keys"] = list(changed)
            stored_width = width(".inbox-list")
            page.reload(wait_until="networkidle")
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            check(
                "Global list width survives a complete reload", abs(width(".inbox-list") - stored_width) < 2
            )
            drag(target=1)
            minimum = float(separator().get_attribute("aria-valuemin"))
            check(
                "Dragging left clamps at declared minimum",
                abs(value() - minimum) < 1 and abs(width(".inbox-list") - minimum) < 2,
            )
            drag(target=1919)
            maximum = float(separator().get_attribute("aria-valuemax"))
            check(
                "Dragging right clamps at declared maximum",
                abs(value() - maximum) < 1
                and abs(width(".inbox-list") - maximum) < 2
                and width(".inbox-reader") >= 319,
            )
            no_overflow("No FHD horizontal overflow at maximum width")
            separator().focus()
            separator().press("Home")
            check(
                "Home selects the minimum list width",
                abs(value() - float(separator().get_attribute("aria-valuemin"))) < 1,
            )
            separator().press("ArrowRight")
            right = value()
            check("Right arrow widens the list by ten pixels", abs(right - minimum - 10) < 1)
            separator().press("ArrowLeft")
            check("Left arrow narrows the list", value() < right)
            value_before_shift = value()
            separator().press("Shift+ArrowRight")
            shifted = value()
            check("Shift-right uses a fifty-pixel step", abs(shifted - value_before_shift - 50) < 1)
            separator().press("Shift+ArrowLeft")
            check("Shift-left reverses the fifty-pixel step", abs(value() - value_before_shift) < 1)
            separator().press("End")
            check(
                "End selects the maximum list width",
                abs(value() - float(separator().get_attribute("aria-valuemax"))) < 1,
            )
            capture("1920-02-global-resized.png")
            separator().dblclick()
            check("Double click restores the default list width", abs(width(".inbox-list") - initial) < 2)
            check(
                "Double click removes the global saved width",
                page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')") is None,
            )
            page.locator('[data-inbox="reply"]').click()
            composer = page.locator('[data-compose-form] textarea[name="body"]')
            expect(composer).to_be_visible()
            composer.fill(MARKER)
            drag(delta=55)
            check(
                "Resizing does not remount or lose the open reply",
                composer.input_value() == MARKER
                and page.locator('[data-compose-form] input[name="to"]')
                .input_value()
                .endswith("entreprise-fictive.invalid"),
            )
            check(
                "Reply text never enters the splitter preference",
                all(
                    MARKER not in page.evaluate("key=>localStorage.getItem(key)", key)
                    for key in report["preference_keys"]
                ),
            )
            page.locator('[data-inbox="close-compose"]').click()
            page.locator(f'[data-inbox="open"][data-id="{mail_id}"]').click()
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            preserved_width = width(".inbox-list")
            preserved_preference = page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')")
            begin_drag(delta=30)
            capture_id = separator().evaluate(
                "element=>Array.from({length:16},(_,id)=>id).find(id=>element.hasPointerCapture(id))"
            )
            check("Mouse drag owns a real browser pointer capture", capture_id is not None)
            separator().evaluate("(element,id)=>element.releasePointerCapture(id)", capture_id)
            page.mouse.move(20, 20)
            page.mouse.up()
            settle()
            check(
                "Lost pointer capture cleans drag mode without saving the partial width",
                not page.evaluate("document.documentElement.classList.contains('mail-layout-resizing')")
                and abs(width(".inbox-list") - preserved_width) < 2
                and page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')")
                == preserved_preference,
            )
            begin_drag(delta=35)
            page.set_viewport_size({"width": 390, "height": 844})
            settle()
            page.mouse.up()
            check(
                "Switching to mobile cancels an in-flight drag and clears pointer styling",
                separator().count() == 0
                and not page.evaluate("document.documentElement.classList.contains('mail-layout-resizing')")
                and page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')")
                == preserved_preference,
            )
            page.set_viewport_size({"width": 1920, "height": 1080})
            settle()
            expect(separator()).to_be_visible()
            begin_drag(delta=30)
            page.evaluate("location.hash='#/assistant'")
            expect(page.locator(".mail-page")).to_have_count(0)
            page.mouse.up()
            settle()
            check(
                "Navigation destroys pointer capture and drag styling",
                not page.evaluate("document.documentElement.classList.contains('mail-layout-resizing')")
                and page.locator("[data-mail-resizing]").count() == 0,
            )
            page.goto(app + "#/mail/" + mail_id + "?folder=inbox", wait_until="networkidle")
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            expect(separator()).to_be_visible()
            resize_preference = page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')")
            page.set_viewport_size({"width": 1280, "height": 900})
            page.evaluate(
                "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
            )
            check(
                "Responsive resize does not rewrite the saved width",
                page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')")
                == resize_preference,
            )
            expect(separator()).to_be_visible()
            drag(delta=35)
            check(
                "1280px global layout remains resizable within its bounds",
                float(separator().get_attribute("aria-valuemin"))
                <= value()
                <= float(separator().get_attribute("aria-valuemax")),
            )
            no_overflow("No 1280px global horizontal overflow")
            capture("1280-03-global.png")

            page.set_viewport_size({"width": 1920, "height": 1080})
            page.goto(
                app + "#/chantiers/" + project_id + "?view=exchanges",
                wait_until="networkidle",
            )
            expect(page.locator(f'[data-mail-id="{mail_id}"]')).to_be_visible()
            expect(separator()).to_be_visible()
            separator().focus()
            separator().press("End")
            page.locator(f'[data-mail-id="{mail_id}"]').click()
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            settle()
            check(
                "Selecting a short project mail after End recomputes the reader-safe bounds",
                width(".mail-message-pane") >= 319
                and value() <= float(separator().get_attribute("aria-valuemax"))
                and abs(width(".mail-list-pane") - value()) < 2,
            )
            separator().dblclick()
            settle()
            global_preference = page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')")
            contextual_before = width(".mail-list-pane")
            contextual_text = page.locator(".mail-message-pane .mail-body").inner_text()
            drag(delta=90)
            check(
                "Project mail list is independently resizable",
                width(".mail-list-pane") > contextual_before + 40,
            )
            check(
                "Project mail selection and body survive resizing",
                page.locator('.mail-list-item[aria-current="true"]').get_attribute("data-mail-id") == mail_id
                and page.locator(".mail-message-pane .mail-body").inner_text() == contextual_text,
            )
            contextual_saved = width(".mail-list-pane")
            check(
                "Project width is a separate numeric preference",
                numeric_preference(
                    json.loads(page.evaluate("localStorage.getItem('travaux:mail-list-width:project:v1')"))
                )
                and page.evaluate("localStorage.getItem('travaux:mail-list-width:global:v1')")
                == global_preference,
            )
            page.reload(wait_until="networkidle")
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            check(
                "Project width and selected message survive a full reload",
                abs(width(".mail-list-pane") - contextual_saved) < 2
                and page.locator('.mail-list-item[aria-current="true"]').get_attribute("data-mail-id")
                == mail_id,
            )
            capture("1920-04-project.png")
            page.get_by_role("button", name="Répondre", exact=True).click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_be_visible()
            reply = dialog.locator("form textarea")
            reply.fill(MARKER + "_PROJET")
            page.set_viewport_size({"width": 1280, "height": 900})
            check(
                "Project reply remains intact during responsive resize",
                reply.input_value() == MARKER + "_PROJET",
            )
            dialog.get_by_role("button", name="Fermer", exact=True).click()
            expect(dialog).not_to_be_visible()
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            expect(separator()).to_be_visible()
            separator().focus()
            separator().press("Home")
            separator().press("ArrowRight")
            check(
                "Project splitter also supports keyboard control at 1280px",
                value() > float(separator().get_attribute("aria-valuemin")),
            )
            no_overflow("No 1280px project horizontal overflow")

            page.set_viewport_size({"width": 390, "height": 844})
            check("Mobile project layout exposes no active separator", separator().count() == 0)
            no_overflow("No mobile project horizontal overflow")
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            capture("390-05-project.png")
            page.locator('[data-mail-action="back"]').click()
            expect(page.locator(f'[data-mail-id="{mail_id}"]')).to_be_visible()
            check(
                "Mobile project reader can return to message selection",
                page.locator(f'[data-mail-id="{mail_id}"]').is_visible(),
            )
            page.goto(app + "#/mail/" + mail_id + "?folder=inbox", wait_until="networkidle")
            expect(page.locator(".mail-message-title")).to_have_text(subject)
            check("Mobile global layout exposes no active separator", separator().count() == 0)
            no_overflow("No mobile global horizontal overflow")
            capture("390-06-global.png")
            page.locator('[data-inbox="back"]').click()
            expect(page.locator(f'[data-inbox="open"][data-id="{mail_id}"]')).to_be_visible()
            check(
                "Mobile global reader can return to message selection",
                page.locator(f'[data-inbox="open"][data-id="{mail_id}"]').is_visible(),
            )
            check(
                "No JavaScript error or external request",
                not report["js_errors"] and not report["console_errors"] and not report["external_requests"],
            )
        except Exception:
            capture("failure.png")
            (output / "failure-dom.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
            raise
        finally:
            context.close()
            browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "test-results/mail-splitter")
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    if arguments.serve:
        serve(output)
        return 0
    if listening():
        raise RuntimeError("Port 19806 is already in use. No existing process will be stopped.")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "Built application and real local demo API/SQLite. Fictional mail only; no account, provider, sending, identity or MFA qualification.",
        "checks": [],
        "screenshots": [],
        "js_errors": [],
        "console_errors": [],
        "external_requests": [],
    }
    with (
        (output / "server.stdout.log").open("w", encoding="utf-8") as stdout,
        (output / "server.stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        server = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve", "--output", str(output)],
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
        )
        report["owned_server_pid"] = server.pid
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("Owned QA server exited during startup; inspect server.stderr.log.")
                try:
                    with urlopen(BASE + "/api/v1/session", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Owned QA server did not become ready.")
            recipe(output, report)
        except Exception as failure:
            report["failure"] = type(failure).__name__ + ": " + str(failure)
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            stop_deadline = time.monotonic() + 5
            while listening() and time.monotonic() < stop_deadline:
                time.sleep(0.05)
            report["owned_server_stopped"] = server.poll() is not None and not listening()
    report["passed"] = (
        not report.get("failure")
        and bool(report["checks"])
        and all(row["passed"] for row in report["checks"])
        and report["owned_server_stopped"]
    )
    (output / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "checks": len(report["checks"]),
                "failure": report.get("failure"),
                "server_stopped": report["owned_server_stopped"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
