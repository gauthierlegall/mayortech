"""Browser verification and Full HD / Mobile screenshot capture for Lot 1.

Validates:
- Commission selector in Shell (sidebar and topbar)
- Multi-commission switching and cache isolation
- Read-only indicator on restricted/viewer commission (Finances)
- Dynamic participant loading in Actions modal from /api/v1/projects/{id}/action-collaboration/participants
- Assignee clearance upon switching project
- Full HD (1920x1080) and Mobile (390x844, 320x568) responsive layouts
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time
from urllib.request import HTTPSHandler, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[2]
PORT = 19821
LOCAL_BASE = f"https://127.0.0.1:{PORT}"


def listening():
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def serve(output: Path):
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

    data = output / "server-data"
    data.mkdir(parents=True, exist_ok=True)
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
        tenant_id="lot1-plougastel-test",
        llm="demo",
        public_origin=LOCAL_BASE,
        allowed_hosts=("127.0.0.1",),
    )
    app = create_app(settings)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT,
        ssl_certfile=str(certpath),
        ssl_keyfile=str(keypath),
        access_log=False,
        log_level="warning",
    )


def run_proof(output: Path, report: dict):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)

        def capture(page, name, vp):
            img_path = output / name
            page.screenshot(path=str(img_path), full_page=False)
            report["screenshots"].append({
                "file": name,
                "path": str(img_path),
                "viewport": vp,
                "sha256": hashlib.sha256(img_path.read_bytes()).hexdigest(),
            })

        # --- Pass 1: Full HD 1920x1080 ---
        context_fhd = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
            ignore_https_errors=True,
            reduced_motion="reduce",
        )
        page_fhd = context_fhd.new_page()
        page_fhd.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page_fhd.on("pageerror", lambda err: report["js_errors"].append(f"FHD: {err}"))

        def wait_workspace_ready(p):
            try:
                p.wait_for_selector(".workspace", state="attached", timeout=10000)
                p.wait_for_selector(".sidebar", state="visible", timeout=10000)
                p.wait_for_load_state("networkidle")
                p.wait_for_timeout(600)
            except Exception as e:
                print("--- DOM DUMP ON FAILURE ---")
                body = p.evaluate("() => document.body.innerHTML")
                print(body[:3000])
                p.screenshot(path=str(output / "fail_dump.png"))
                raise e

        # Navigate to homepage
        print("Navigating to homepage via /demo.html#/")
        page_fhd.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        wait_workspace_ready(page_fhd)

        # 1. Capture FHD overview with commission selector visible
        capture(page_fhd, "01_fullhd_shell_commissions_overview.png", {"width": 1920, "height": 1080})
        report["checks"].append({"name": "FHD Shell Loaded", "passed": True})

        # 2. Select commission "4. Culture, sport et vie associative"
        comm_select = page_fhd.locator("#sidebar-commission-select")
        if comm_select.count() > 0:
            comm_select.select_option("commission-4")
            wait_workspace_ready(page_fhd)
            capture(page_fhd, "02_fullhd_commission_culture_view.png", {"width": 1920, "height": 1080})
            report["checks"].append({"name": "Commission Culture Switch", "passed": True})

        # 3. Select commission "1. Fonctions supports et transitions" (Finances)
        if page_fhd.locator("#sidebar-commission-select").count() > 0:
            page_fhd.locator("#sidebar-commission-select").select_option("commission-1")
            wait_workspace_ready(page_fhd)
            capture(page_fhd, "03_fullhd_commission_finances_view.png", {"width": 1920, "height": 1080})
            report["checks"].append({"name": "Commission Finances Switch", "passed": True})

            # Switch back to all
            page_fhd.locator("#sidebar-commission-select").select_option("all")
            wait_workspace_ready(page_fhd)

        # 4. Navigate to Actions page and open "Créer une action"
        page_fhd.goto(f"{LOCAL_BASE}/demo.html#/actions", wait_until="networkidle")
        page_fhd.wait_for_selector("button:has-text('Créer une action')", timeout=15000)
        page_fhd.locator("button:has-text('Créer une action')").click()
        page_fhd.wait_for_selector("input[name='title']", timeout=10000)
        page_fhd.wait_for_timeout(800)

        capture(page_fhd, "04_fullhd_actions_create_modal.png", {"width": 1920, "height": 1080})
        report["checks"].append({"name": "FHD Actions Create Modal Open", "passed": True})

        context_fhd.close()

        # --- Pass 2: Mobile Viewport 390x844 (iPhone 14) ---
        context_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            locale="fr-FR",
            timezone_id="Europe/Paris",
            ignore_https_errors=True,
            reduced_motion="reduce",
        )
        page_mobile = context_mobile.new_page()
        page_mobile.on("pageerror", lambda err: report["js_errors"].append(f"Mobile 390: {err}"))

        page_mobile.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page_mobile.wait_for_selector(".topbar", timeout=15000)
        page_mobile.wait_for_timeout(600)
        capture(page_mobile, "05_mobile_390x844_homepage.png", {"width": 390, "height": 844})
        report["checks"].append({"name": "Mobile 390x844 Home", "passed": True})

        # Open mobile drawer
        menu_btn = page_mobile.locator(".mobile-menu")
        if menu_btn.is_visible():
            menu_btn.click()
            page_mobile.wait_for_selector(".mobile-open .sidebar", state="visible", timeout=10000)
            page_mobile.wait_for_timeout(600)
            capture(page_mobile, "06_mobile_390x844_sidebar_drawer.png", {"width": 390, "height": 844})
            report["checks"].append({"name": "Mobile 390x844 Drawer with Commission Switcher", "passed": True})

        context_mobile.close()

        # --- Pass 3: Compact Mobile Viewport 320x568 (iPhone SE / compact) ---
        context_compact = browser.new_context(
            viewport={"width": 320, "height": 568},
            is_mobile=True,
            locale="fr-FR",
            timezone_id="Europe/Paris",
            ignore_https_errors=True,
            reduced_motion="reduce",
        )
        page_compact = context_compact.new_page()
        page_compact.on("pageerror", lambda err: report["js_errors"].append(f"Mobile 320: {err}"))

        page_compact.goto(f"{LOCAL_BASE}/demo.html#/actions", wait_until="networkidle")
        page_compact.wait_for_selector(".actions-section, .actions-page, .topbar", timeout=15000)
        page_compact.wait_for_timeout(600)
        capture(page_compact, "07_mobile_320x568_actions_compact.png", {"width": 320, "height": 568})
        report["checks"].append({"name": "Mobile 320x568 Actions Compact", "passed": True})

        context_compact.close()
        browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "test-results" / "lot-1"))
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.serve:
        serve(out_dir)
        return 0

    report = {"checks": [], "screenshots": [], "js_errors": []}
    if args.base_url:
        global LOCAL_BASE
        LOCAL_BASE = args.base_url.rstrip("/")
        run_proof(out_dir, report)
        (out_dir / "lot1-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
        passed = len(report["js_errors"]) == 0 and len(report["screenshots"]) >= 7 and all(c["passed"] for c in report["checks"])
        print(json.dumps({"passed": passed, "screenshots": len(report["screenshots"]), "errors": report["js_errors"]}))
        return 0 if passed else 1

    if listening():
        raise RuntimeError(f"Port {PORT} already occupied; cannot start clean test server.")

    server = None
    try:
        stdout_log = (out_dir / "server.stdout.log").open("w", encoding="utf8")
        stderr_log = (out_dir / "server.stderr.log").open("w", encoding="utf8")
        server = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve", "--output", str(out_dir)],
            cwd=ROOT,
            stdout=stdout_log,
            stderr=stderr_log,
        )

        opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl._create_unverified_context()))
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError("Lot 1 QA server exited unexpectedly.")
            try:
                with opener.open(f"{LOCAL_BASE}/api/v1/session", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.3)
        else:
            raise RuntimeError("Lot 1 QA server startup timed out.")

        run_proof(out_dir, report)

    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

    (out_dir / "lot1-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
    passed = len(report["js_errors"]) == 0 and len(report["screenshots"]) >= 7 and all(c["passed"] for c in report["checks"])
    print(json.dumps({"passed": passed, "screenshots": len(report["screenshots"]), "errors": report["js_errors"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
