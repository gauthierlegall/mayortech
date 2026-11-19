"""Public-demo release acceptance; local isolated HTTPS or explicit post-release URL.

All writes contain fictional QA text. No account, sending, upload, provider or
identity is enabled. Remote mode always keeps certificate validation enabled.
"""

from __future__ import annotations
import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import sqlite3
import ssl
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, ProxyHandler, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
PORT = 19807
LOCAL_BASE = f"https://127.0.0.1:{PORT}"
NATIVE = """async ({projectId,note,title,write})=>{
 const pageResponse=await fetch('/api/v1/projects/'+projectId+'/page',{method:'POST',headers:{'X-Requested-With':'Travaux','Content-Type':'application/json'},body:'{}'});
 if(!pageResponse.ok)throw Error('native_page_'+pageResponse.status);
 const page=await pageResponse.json(),sdk=await import('/native/editor.js'),host=document.createElement('div');
 host.style.cssText='position:fixed;left:-20000px;width:1000px;height:700px';host.inert=true;document.body.append(host);
 const editor=await sdk.mount(host,{pageId:page.id});
 try{
  let target=null,added=null;
  if(write){editor.addParagraph(note);target=editor.ensureDatabase();added=editor.addAction({title,status:'À faire'},target);while(editor.dirty)await editor.save();}
  const metadata=editor.getMetadata();
  return {page_id:page.id,target,added,databases:metadata.databases,notes:await editor.getNotesText(),revision_hash:editor.revisionHash};
 }finally{editor.unmount();host.remove();}
}"""


def listening():
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def serve(output):
    for key in list(os.environ):
        if key.startswith("TRAVAUX_") or key in {"SSLKEYLOGFILE", "QUICLOGDIR"}:
            os.environ.pop(key, None)
    sys.path.insert(0, str(ROOT / "src"))
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    from travaux.api import create_app
    from travaux.config import Settings
    import uvicorn

    data = ROOT / ".local" / "public-release-qa" / str(time.time_ns())
    data.mkdir(parents=True)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    certpath = data / "loopback-cert.pem"
    keypath = data / "loopback-key.pem"
    certpath.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keypath.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )
    settings = Settings(
        mode="public_demo",
        db_path=data / "public.sqlite3",
        tenant_id="public-release-fiction",
        llm="demo",
        public_origin=LOCAL_BASE,
        allowed_hosts=("127.0.0.1",),
    )
    app = create_app(settings)
    with sqlite3.connect(settings.db_path) as db:
        marker = db.execute(
            "SELECT mode,tenant_id,schema_version FROM public_demo_metadata WHERE singleton=1"
        ).fetchone()
    (output / "fixture.json").write_text(
        json.dumps(
            {
                "origin": LOCAL_BASE,
                "database": str(settings.db_path),
                "marker": marker,
                "scope": "Fresh isolated public_demo database; local self-signed HTTPS only.",
            },
            indent=2,
        ),
        encoding="utf8",
    )
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT,
        ssl_certfile=str(certpath),
        ssl_keyfile=str(keypath),
        access_log=False,
        log_level="warning",
    )


def recipe(base, output, remote, report):
    from playwright.sync_api import sync_playwright, expect

    headers = {"Origin": base, "X-Requested-With": "Travaux"}

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
            ignore_https_errors=not remote,
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.set_default_timeout(20000)
        page.on("pageerror", lambda error: report["js_errors"].append(str(error)))
        context.add_init_script(
            "window.__releaseIntervals=[];const actualSetInterval=window.setInterval;window.setInterval=function(fn,ms,...args){window.__releaseIntervals.push(Number(ms));return actualSetInterval(fn,ms,...args);};"
        )

        def route(request):
            if request.request.url.startswith(base + "/") or request.request.url.startswith(
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

        def get(path):
            response = context.request.get(base + "/api/v1" + path)
            assert response.ok, (path, response.status)
            return response.json()

        def post(path, payload):
            return context.request.post(
                base + "/api/v1" + path, headers=headers, data=payload, max_redirects=0
            )

        try:
            session = get("/session")
            check(
                "Public demonstration is authenticated anonymously before any QA mutation",
                session.get("authenticated") is True
                and session.get("public_demo") is True
                and not session.get("auth_required"),
            )
            settings = get("/settings")
            check("Actual server mode is public_demo", settings.get("mode") == "public_demo")
            if not remote:
                fixture = json.loads((output / "fixture.json").read_text())
                check(
                    "Local SQLite is explicitly marked public_demo",
                    fixture["marker"] == ["public_demo", "public-release-fiction", 1],
                )
            check("Packaged application is served", context.request.get(base + "/").ok)
            folders = get("/mailbox/folders")
            hub = get("/integrations")
            check(
                "Real mail sending and external connections remain disabled",
                folders["capabilities"].get("can_send") is False
                and hub.get("public_demo") is True
                and hub.get("external_connections_enabled") is False
                and not hub.get("connections"),
            )
            mails = get("/mailbox/messages?folder=inbox&limit=100")["items"]
            mail = next(
                row
                for row in mails
                if row.get("metadata", {}).get("fictitious") is True
                and row.get("project_ids")
                and ".invalid" in row.get("sender", "")
            )
            pid = mail["project_ids"][0]
            page.goto(base + "/#/mail/" + mail["id"] + "?folder=inbox", wait_until="networkidle")
            expect(page.locator(".mail-message-title")).to_have_text(mail["subject"])
            check(
                "Public mail reader uses an explicitly fictional message",
                page.locator(".inbox-reader .mail-body").inner_text() == mail["body"],
            )
            separator = page.get_by_role("separator", name="Redimensionner la liste des messages", exact=True)
            expect(separator).to_be_visible()
            before = page.locator(".inbox-list").bounding_box()["width"]
            bounds = separator.bounding_box()
            x = bounds["x"] + bounds["width"] / 2
            y = bounds["y"] + 100
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 80, y, steps=8)
            page.mouse.up()
            page.evaluate(
                "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
            )
            check(
                "Published public-mode mail splitter changes actual width",
                page.locator(".inbox-list").bounding_box()["width"] > before + 40
                and page.locator(".mail-message-title").inner_text() == mail["subject"],
            )
            check(
                "No decorative saved label or 400ms status poll",
                page.get_by_text("Tout est enregistré", exact=True).count() == 0
                and page.get_by_text("Enregistré.", exact=True).count() == 0
                and 400 not in page.evaluate("window.__releaseIntervals"),
            )
            capture("1920-01-public-mail.png")
            page.goto(
                base + "/#/chantiers/" + pid + "?view=exchanges&mail=" + mail["id"], wait_until="networkidle"
            )
            page.get_by_role("button", name="Ouvrir le chat Assistant", exact=True).click()
            chat = page.locator(".assistant-popup")
            expect(chat.get_by_label("Votre question", exact=True)).to_be_visible()
            chat.get_by_label("Votre question", exact=True).fill(
                "Résume l’avancement du chantier fictif et cite les sources."
            )
            with page.expect_response(
                lambda response: (
                    "/conversations/" in response.url
                    and response.url.endswith("/messages")
                    and response.request.method == "POST"
                )
            ) as answer_response:
                chat.get_by_role("button", name="Envoyer la question", exact=True).click()
            answer = answer_response.value
            check(
                "Current frontend question intent is accepted by public backend",
                answer.status == 200 and answer.request.post_data_json.get("intent") == "question",
            )
            assistant = chat.locator(".conversation-message.assistant").last
            expect(assistant).to_be_visible()
            check(
                "Public assistant answers with actual retained source citations",
                bool(assistant.locator(".conversation-text").inner_text().strip())
                and assistant.locator(".conversation-sources").count() > 0,
            )
            capture("1920-02-public-assistant.png")
            page.set_viewport_size({"width": 390, "height": 844})
            check(
                "Public assistant fits mobile viewport",
                chat.evaluate(
                    "(element)=>{const r=element.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1}"
                )
                and page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),
            )
            capture("390-03-public-assistant.png")
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.locator(".assistant-launcher").click()
            stamp = str(time.time_ns())
            reference = "QA-PUBLIC-" + stamp[-16:]
            note = "NOTE FICTIVE DE RECETTE PUBLIQUE " + stamp
            title = "ACTION FICTIVE DE RECETTE " + stamp
            created = post(
                "/projects",
                {
                    "reference": reference,
                    "name": "Dossier entièrement fictif de recette publique " + stamp[-6:],
                    "description": "Aucune donnée municipale réelle. Recette publique du frontend.",
                },
            )
            check("QA edits target a newly created fictional public project", created.status == 201)
            project = created.json()
            project_id = project["id"]
            report["fictional_project_id"] = project_id
            page.goto(base + "/#/chantiers/" + project_id + "?view=documents", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            expect(page.get_by_role("heading", name="Documents", exact=False)).to_be_visible()
            check(
                "Public UI exposes no document upload field",
                page.locator("input[type=file]").count() == 0
                and "Le dépôt de fichiers est réservé" in page.locator("body").inner_text(),
            )
            blocked = post(
                "/projects/" + project_id + "/documents/upload",
                {
                    "filename": "recette-fictive.txt",
                    "content_base64": base64.b64encode(b"CONTENU FICTIF DE RECETTE").decode(),
                    "client_id": str(uuid4()),
                },
            )
            check("Small fictional document upload is refused", blocked.status == 403)
            imported = post(
                "/imports/eml",
                {
                    "filename": "recette-fictive.eml",
                    "content": "From: fictif@example.invalid\nSubject: RECETTE FICTIVE\n\nCorps entièrement fictif.",
                },
            )
            check("Fictional MIME import is refused", imported.status == 403)
            connected = post(
                "/integrations/connections",
                {
                    "provider": "exchange",
                    "label": "Connexion FICTIVE INTERDITE",
                    "endpoint": "https://exchange.example.invalid/EWS/Exchange.asmx",
                    "username": "fictif@example.invalid",
                    "mailbox": "fictif@example.invalid",
                    "password": "FAUX_NON_SECRET_DE_RECETTE",
                },
            )
            check("Fictional external connection setup is refused", connected.status == 403)
            sent = post(
                "/mailbox/send", {"draft_id": "00000000-0000-0000-0000-000000000000", "expected_revision": 1}
            )
            check(
                "Sending remains blocked by public ACL or unavailable transport",
                (sent.status == 403 and sent.json().get("error", {}).get("code") == "forbidden")
                or (
                    sent.status == 503
                    and sent.json().get("error", {}).get("code") == "mail_transport_not_configured"
                ),
                {"status": sent.status, "code": sent.json().get("error", {}).get("code")},
            )
            native = page.evaluate(
                NATIVE, {"projectId": project_id, "note": note, "title": title, "write": True}
            )
            check(
                "Real Yjs write targets its native database and receives a revision hash",
                native["added"]["databaseId"] == native["target"] and len(native["revision_hash"]) == 64,
            )
            reloaded = page.evaluate(
                NATIVE, {"projectId": project_id, "note": note, "title": title, "write": False}
            )
            rows = [
                row
                for db in reloaded["databases"]
                for row in db["rows"]
                if any(field.get("text") == title for field in row["fields"])
            ]
            check(
                "Native note and action survive an actual SDK remount once",
                note in reloaded["notes"] and len(rows) == 1,
            )
            summary = post("/projects/" + project_id + "/summaries", {})
            check(
                "Public recap uses the actual saved fictional native note",
                summary.status == 201 and note in summary.json().get("content", ""),
            )
            page.goto(base + "/#/chantiers/" + project_id + "?view=table", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            expect(page.locator(".action-row").filter(has_text=title)).to_have_count(1, timeout=45000)
            capture("1920-04-public-native-action.png")
            check(
                "Public action UI reads the real native row",
                page.locator(".action-row").filter(has_text=title).count() == 1,
            )
            page.goto(base + "/#/chantiers/" + project_id + "?view=page", wait_until="networkidle")
            page.reload(wait_until="networkidle")
            page.get_by_role("button", name="Préparer un récapitulatif", exact=True).click()
            dialog = page.get_by_role("dialog")
            expect(dialog.locator("textarea")).to_have_value(summary.json()["content"])
            check(
                "Public recap UI displays the actual generated version",
                note in dialog.locator("textarea").input_value(),
            )
            capture("1920-05-public-recap.png")
            page.keyboard.press("Escape")
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(base + "/#/mail/" + mail["id"] + "?folder=inbox", wait_until="networkidle")
            expect(page.locator(".mail-message-title")).to_have_text(mail["subject"])
            check(
                "Mobile public reader has no active splitter or horizontal overflow",
                page.get_by_role("separator", name="Redimensionner la liste des messages", exact=True).count()
                == 0
                and page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),
            )
            capture("390-06-public-mail.png")
            check(
                "No browser exception or external-origin request",
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
    parser.add_argument("--base-url")
    parser.add_argument("--output", type=Path, default=ROOT / "test-results/public-release-20261117")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.serve:
        serve(output)
        return 0
    remote = bool(args.base_url)
    base = (args.base_url or LOCAL_BASE).rstrip("/")
    address = urlsplit(base)
    if (
        address.scheme != "https"
        or not address.hostname
        or address.username
        or address.password
        or address.path
        or address.query
        or address.fragment
    ):
        raise ValueError("Use a plain HTTPS origin without credentials, path, query or fragment.")
    report = {
        "scope": "Actual packaged frontend and real public_demo API/SQLite/Yjs; fictional QA writes only. No real mail/identity/MFA/provider qualification.",
        "base_url": base,
        "remote": remote,
        "tls_verification": remote,
        "local_tls_exception": "Chromium and health probe ignore only the ephemeral loopback certificate; no CA installed and no public TLS qualification."
        if not remote
        else None,
        "checks": [],
        "screenshots": [],
        "js_errors": [],
        "external_requests": [],
    }
    server = None
    stdout = stderr = None
    try:
        if not remote:
            if listening():
                raise RuntimeError("Port19807 already occupied; no existing process is stopped.")
            stdout = (output / "server.stdout.log").open("w", encoding="utf8")
            stderr = (output / "server.stderr.log").open("w", encoding="utf8")
            server = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--serve", "--output", str(output)],
                cwd=ROOT,
                stdout=stdout,
                stderr=stderr,
            )
            report["owned_server_pid"] = server.pid
            opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl._create_unverified_context()))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("Public QA server exited; inspect stderr log.")
                try:
                    with opener.open(base + "/api/v1/session", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Public QA server startup timed out.")
        recipe(base, output, remote, report)
    except Exception as failure:
        report["failure"] = type(failure).__name__ + ": " + str(failure)
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
            deadline = time.monotonic() + 5
            while listening() and time.monotonic() < deadline:
                time.sleep(0.05)
            report["owned_server_stopped"] = server.poll() is not None and not listening()
        if stdout:
            stdout.close()
        if stderr:
            stderr.close()
    report["passed"] = (
        not report.get("failure")
        and bool(report["checks"])
        and all(row["passed"] for row in report["checks"])
        and (remote or report.get("owned_server_stopped"))
    )
    (output / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "checks": len(report["checks"]),
                "failure": report.get("failure"),
                "server_stopped": report.get("owned_server_stopped"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
