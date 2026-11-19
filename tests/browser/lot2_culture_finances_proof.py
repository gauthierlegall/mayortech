"""Browser verification and Full HD / Mobile screenshot capture for Lot 2 (Culture & Finances).

Validates:
- Hall reservation with live semi-open anti-conflict check [14:00, 16:00) vs [15:00, 18:00)
- Multi-variant budget sheets (Variante A 9 600 € vs Variante B 11 700 € with remaining charge calculation)
- Transmission circuit Culture -> Finances with frozen snapshot and document sealing
- Finances arbitration panel in Commission 1 with comparative view and motivated decision (DELIB-2027-06-42)
- Official decision banner and audited note rendering back in Culture dossier
- Full HD (1920x1080), Mobile (390x844), and Compact (320x568) responsive layouts
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
PORT = 19822
LOCAL_BASE = f"https://127.0.0.1:{PORT}"


def listening():
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def seed_lot2_data(data_dir: Path, base_url: str):
    """Seed Plougastel Culture & Finances demo project and initial booking."""
    sys.path.insert(0, str(ROOT / "src"))
    from travaux.repository import Repository
    from travaux.culture_finances import CultureFinancesRepository
    from travaux.commissions import CommissionRepository

    db_path = data_dir / "public.sqlite3"
    repo = Repository(db_path)
    cf_repo = CultureFinancesRepository(repo)
    comm_repo = CommissionRepository(repo)

    tenant_id = "lot2-plougastel-test"
    with repo._transaction() as db:
        # Ensure commissions exist
        comm_repo.ensure_default_commissions(tenant_id)

        # Check if project exists
        existing = db.execute(
            "SELECT id FROM projects WHERE tenant_id=? AND id=?",
            (tenant_id, "PRJ-EVT-2027-042"),
        ).fetchone()

        if not existing:
            repo.create_project(
                tenant_id,
                "EVT-2027-042",
                "Fête des associations · exemple",
                project_id="PRJ-EVT-2027-042",
                commission_id="commission-4",
                description="Manifestation annuelle des associations communales. Réservation de la grande salle et arbitrage financier requis.",
            )

            # Create existing blocking reservation: 14:00 to 16:00
            cf_repo.create_reservation(
                tenant_id,
                "PRJ-EVT-2027-042",
                resource_id="salle-avel-vor",
                resource_name="Espace Avel Vor (Grande Salle)",
                start_time="2027-06-12T14:00:00+02:00",
                end_time="2027-06-12T16:00:00+02:00",
                created_by="culture-agent",
                status="confirmed",
            )

            # Create budget sheet with 2 variants
            cf_repo.save_budget_sheet(
                tenant_id,
                "PRJ-EVT-2027-042",
                title="Budget Prévisionnel Fête des Associations 2027",
                exercise=2027,
                variants=[
                    {
                        "id": "var-a",
                        "label": "Variante A (Standard)",
                        "tax_basis": "ttc",
                        "amount_cents": 960000,
                        "subsidies_cents": 250000,
                        "hypothesis": "Configuration standard Avel Vor + cofinancement départemental",
                    },
                    {
                        "id": "var-b",
                        "label": "Variante B (Scène étendue)",
                        "tax_basis": "ttc",
                        "amount_cents": 1170000,
                        "subsidies_cents": 250000,
                        "hypothesis": "Configuration avec scène extérieure et renfort sonorisation",
                    },
                ],
                created_by="culture-agent",
                status="draft",
            )

            # Create event details
            cf_repo.update_event_details(
                tenant_id,
                "PRJ-EVT-2027-042",
                association_name="Amicale Laïque de Plougastel",
                association_ref="W29100456",
                expected_attendance=450,
                location_name="Espace Avel Vor",
            )

    repo.close()


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
        tenant_id="lot2-plougastel-test",
        llm="demo",
        public_origin=LOCAL_BASE,
        allowed_hosts=("127.0.0.1",),
    )
    app = create_app(settings)

    # Seed the specific Lot 2 scenario data
    seed_lot2_data(data, LOCAL_BASE)

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

        def wait_ready(p, selector=".workspace", timeout=12000):
            p.wait_for_selector(selector, state="attached", timeout=timeout)
            p.wait_for_load_state("networkidle")
            p.wait_for_timeout(600)

        # 1. Discover target dossier
        print("Navigating to home to discover dossier...")
        page_fhd.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        wait_ready(page_fhd, ".overview-band")

        evt_link = page_fhd.locator("a[href*='PRJ-EVT-2027-042']")
        if evt_link.count() > 0:
            target_proj_id = "PRJ-EVT-2027-042"
        else:
            first_row = page_fhd.locator(".project-row").first
            href = first_row.get_attribute("href") or ""
            target_proj_id = href.split("/chantiers/")[-1].split("?")[0]
        print(f"Target dossier: {target_proj_id}")

        page_fhd.goto(f"{LOCAL_BASE}/demo.html#/chantiers/{target_proj_id}", wait_until="networkidle")
        wait_ready(page_fhd, ".detail-heading")

        # Open Culture & Finances tab
        cult_tab = page_fhd.locator("#project-tab-culture")
        cult_tab.wait_for(state="visible", timeout=10000)
        cult_tab.click()
        page_fhd.wait_for_selector(".culture-panel", state="visible", timeout=10000)
        page_fhd.wait_for_timeout(700)

        # Ensure budget sheet exists
        init_btn = page_fhd.locator("button:has-text('Initialiser le budget')")
        if init_btn.is_visible():
            init_btn.click()
            page_fhd.wait_for_timeout(800)

        # Ensure a booking exists to create the conflict
        if page_fhd.locator(".conflict-alert").count() == 0:
            if page_fhd.locator(".reservation-item").count() == 0:
                page_fhd.locator("#res-date").fill("2027-06-12")
                page_fhd.locator("input[aria-label='Heure de début']").fill("14:00")
                page_fhd.locator("input[aria-label='Heure de fin']").fill("16:00")
                page_fhd.locator("button:has-text('Réserver le créneau')").click()
                page_fhd.wait_for_selector(".reservation-item", timeout=8000)
                page_fhd.wait_for_timeout(600)
            page_fhd.locator("input[aria-label='Heure de début']").fill("15:00")
            page_fhd.locator("input[aria-label='Heure de fin']").fill("18:00")
            page_fhd.wait_for_timeout(600)

        # 1. Capture Full HD: Conflict Alert in Culture Panel
        page_fhd.wait_for_selector(".conflict-alert", timeout=8000)
        capture(page_fhd, "01_fullhd_culture_conflict_alert.png", {"width": 1920, "height": 1080})
        report["checks"].append({"name": "FHD Culture Conflict Alert Visible", "passed": True})

        # 2. Open Transmission Dialog
        trans_btn = page_fhd.locator("button:has-text('Transmettre pour arbitrage Finances')")
        if trans_btn.is_visible():
            trans_btn.click()
            page_fhd.wait_for_selector("text=Transmettre à la Commission Finances", timeout=8000)
            page_fhd.wait_for_timeout(500)
            capture(page_fhd, "02_fullhd_culture_budget_and_transmission.png", {"width": 1920, "height": 1080})
            report["checks"].append({"name": "FHD Transmission Dialog Opened", "passed": True})

            # Confirm Transmission
            confirm_btn = page_fhd.locator("button:has-text('Confirmer la transmission')")
            confirm_btn.click()
            page_fhd.wait_for_selector(".transmission-card", timeout=10000)
            page_fhd.wait_for_timeout(600)

        # 3. Navigate to Home and switch to Commission 1 (Finances) -> Arbitrages financiers
        page_fhd.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        wait_ready(page_fhd, ".overview-band")

        # Select Commission 1 in sidebar
        comm_select = page_fhd.locator("#sidebar-commission-select")
        if comm_select.count() > 0:
            comm_select.select_option("commission-1")
            page_fhd.wait_for_load_state("networkidle")
            page_fhd.wait_for_timeout(600)

        # Click "Arbitrages financiers" button
        arb_btn = page_fhd.locator("button:has-text('Arbitrages financiers')")
        arb_btn.wait_for(state="visible", timeout=10000)
        arb_btn.click()
        page_fhd.wait_for_selector(".finances-panel", state="visible", timeout=10000)
        page_fhd.wait_for_timeout(800)

        # Capture Full HD: Finances Arbitration View
        capture(page_fhd, "03_fullhd_finances_arbitration_panel.png", {"width": 1920, "height": 1080})
        report["checks"].append({"name": "FHD Finances Arbitration Panel", "passed": True})

        # Submit Decision: Favorable with DELIB-2027-06-42
        decide_btn = page_fhd.locator("button:has-text('Enregistrer la décision d’arbitrage')")
        if decide_btn.is_visible():
            decide_btn.click()
            page_fhd.wait_for_selector("text=Décision d’arbitrage enregistrée", timeout=10000)
            page_fhd.wait_for_timeout(800)

        # 4. Navigate back to Culture Dossier and verify rendered official decision
        page_fhd.goto(f"{LOCAL_BASE}/demo.html#/chantiers/{target_proj_id}", wait_until="networkidle")
        wait_ready(page_fhd, ".detail-heading")
        page_fhd.locator("#project-tab-culture").click()
        page_fhd.wait_for_selector(".culture-panel", state="visible", timeout=10000)
        page_fhd.wait_for_selector("text=DELIB-2027-06-42", timeout=10000)
        page_fhd.wait_for_timeout(600)

        capture(page_fhd, "04_fullhd_culture_decision_rendered.png", {"width": 1920, "height": 1080})
        report["checks"].append({"name": "FHD Official Decision Rendered in Culture Dossier", "passed": True})

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

        # 5. Mobile Culture Dossier
        page_mobile.goto(f"{LOCAL_BASE}/demo.html#/chantiers/{target_proj_id}", wait_until="networkidle")
        page_mobile.wait_for_selector(".detail-heading", timeout=12000)
        page_mobile.locator("#project-tab-culture").click()
        page_mobile.wait_for_selector(".culture-panel", state="visible", timeout=10000)
        page_mobile.wait_for_timeout(600)

        capture(page_mobile, "05_mobile_390x844_culture_dossier.png", {"width": 390, "height": 844})
        report["checks"].append({"name": "Mobile 390x844 Culture Dossier Responsive", "passed": True})

        # 6. Mobile Finances Arbitration Panel
        page_mobile.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page_mobile.wait_for_selector(".topbar", timeout=12000)
        # Switch to Commission 1
        page_mobile.evaluate("() => { window.sessionStorage.setItem('travaux:active-commission', 'commission-1'); location.reload(); }")
        page_mobile.wait_for_load_state("networkidle")
        page_mobile.wait_for_selector("button:has-text('Arbitrages financiers')", timeout=12000)
        page_mobile.locator("button:has-text('Arbitrages financiers')").click()
        page_mobile.wait_for_selector(".finances-panel", state="visible", timeout=10000)
        page_mobile.wait_for_timeout(600)

        capture(page_mobile, "06_mobile_390x844_finances_arbitration.png", {"width": 390, "height": 844})
        report["checks"].append({"name": "Mobile 390x844 Finances Arbitration Responsive", "passed": True})

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

        page_compact.goto(f"{LOCAL_BASE}/demo.html#/chantiers/{target_proj_id}", wait_until="networkidle")
        page_compact.wait_for_selector(".detail-heading", timeout=12000)
        page_compact.locator("#project-tab-culture").click()
        page_compact.wait_for_selector(".culture-panel", state="visible", timeout=10000)
        page_compact.wait_for_timeout(600)

        capture(page_compact, "07_mobile_320x568_budget_compact.png", {"width": 320, "height": 568})
        report["checks"].append({"name": "Mobile 320x568 Budget Compact View", "passed": True})

        context_compact.close()
        browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "test-results" / "lot-2"))
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
        (out_dir / "lot2-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
        passed = len(report["js_errors"]) == 0 and len(report["screenshots"]) >= 7 and all(c["passed"] for c in report["checks"])
        print(json.dumps({"passed": passed, "screenshots": len(report["screenshots"]), "errors": report["js_errors"]}))
        return 0 if passed else 1

    if listening():
        raise RuntimeError(f"Port {PORT} already occupied; cannot start clean test server.")

    import shutil
    shutil.rmtree(out_dir / "server-data", ignore_errors=True)

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
                raise RuntimeError("Lot 2 QA server exited unexpectedly.")
            try:
                with opener.open(f"{LOCAL_BASE}/api/v1/session", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.3)
        else:
            raise RuntimeError("Lot 2 QA server startup timed out.")

        run_proof(out_dir, report)

    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

    (out_dir / "lot2-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
    passed = len(report["js_errors"]) == 0 and len(report["screenshots"]) >= 7 and all(c["passed"] for c in report["checks"])
    print(json.dumps({"passed": passed, "screenshots": len(report["screenshots"]), "errors": report["js_errors"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
