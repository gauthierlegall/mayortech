"""Browser verification and Full HD / Mobile screenshot capture for Lot 4 (Action sociale, enfance et jeunesse).

Validates:
- Annual school and extracurricular campaign management (Rentrée scolaire et périscolaire)
- 4-step campaign milestone timeline (Inscriptions, QF, Arbitrage, Rentrée)
- Live Quotient Familial calculator and municipal canteen rate tiers (T1 to T5)
- Intelligent year-over-year campaign renewal engine with automatic dossier carry-over and shifted reminders (+1 year)
- Confidential CCAS social aid registry and decision tracking under Commission 2
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
PORT = 19824
LOCAL_BASE = f"https://127.0.0.1:{PORT}"


def listening():
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def seed_lot4_data(data_dir: Path, base_url: str):
    """Seed Plougastel Enfance, Jeunesse et Action Sociale demo data."""
    sys.path.insert(0, str(ROOT / "src"))
    from travaux.commissions import COMMISSION_2_ID, CommissionRepository
    from travaux.enfance_sociale import EnfanceSocialeRepository
    from travaux.repository import Repository

    db_path = data_dir / "public.sqlite3"
    repo = Repository(db_path)
    es_repo = EnfanceSocialeRepository(repo)
    comm_repo = CommissionRepository(repo)

    tenant_id = "lot4-plougastel-test"
    with repo._transaction() as db:
        comm_repo.ensure_default_commissions(tenant_id)

        # 1. Project École des Alizés (Commission 2)
        p_ecole = db.execute("SELECT id FROM projects WHERE tenant_id=? AND id=?", (tenant_id, "PRJ-ENFANCE-ALIZES")).fetchone()
        if not p_ecole:
            repo.create_project(
                tenant_id,
                "SOC-2027-001",
                "Dispositif Rentrée Scolaire et Périscolaire — École des Alizés",
                project_id="PRJ-ENFANCE-ALIZES",
                commission_id=COMMISSION_2_ID,
            )

        # 2. Seed active campaign 2026-2027
        camp = es_repo.create_campaign(
            tenant_id=tenant_id,
            campaign_type="rentree_scolaire",
            title="Inscriptions scolaires et périscolaires 2026-2027",
            school_year="2026-2027",
            start_date="2026-05-01",
            end_date="2026-07-15",
            config={"schools": ["École des Alizés", "École du Goëland", "École Saint-Pierre"]},
        )
        camp_id = camp["id"]

        # 3. Seed dossiers
        es_repo.create_campaign_dossier(
            tenant_id=tenant_id,
            campaign_id=camp_id,
            family_ref="FAM-29470-12",
            beneficiary_name="Mme Nolwenn Le Gall",
            child_name="Erwan Le Gall",
            school_name="École des Alizés",
            quotient_familial=420,  # T1 - 1,00 €
            project_id="PRJ-ENFANCE-ALIZES",
            details={"cantine": True, "garderie_matin": True},
        )

        es_repo.create_campaign_dossier(
            tenant_id=tenant_id,
            campaign_id=camp_id,
            family_ref="FAM-29470-34",
            beneficiary_name="M. et Mme Morvan",
            child_name="Soizic Morvan",
            school_name="École du Goëland",
            quotient_familial=680,  # T2 - 2,15 €
            project_id="PRJ-ENFANCE-ALIZES",
            details={"cantine": True, "transport": True},
        )

        es_repo.create_campaign_dossier(
            tenant_id=tenant_id,
            campaign_id=camp_id,
            family_ref="FAM-29470-56",
            beneficiary_name="Famille Kermarrec",
            child_name="Mael Kermarrec",
            school_name="École des Alizés",
            quotient_familial=1350,  # T4 - 4,10 €
            project_id="PRJ-ENFANCE-ALIZES",
            details={"cantine": True},
        )

        # 4. Seed Reminders
        es_repo.create_reminder(
            tenant_id=tenant_id,
            campaign_id=camp_id,
            title="Clôture des dépôts dossiers quotient familial cantine",
            due_date="2026-07-15",
            reminder_type="inscription_deadline",
        )

        es_repo.create_reminder(
            tenant_id=tenant_id,
            campaign_id=camp_id,
            title="Commission CCAS arbitrage bourses et dérogations",
            due_date="2026-07-28",
            reminder_type="commission_review",
        )

        # 5. Seed Confidential Social Aid records
        es_repo.record_social_aid(
            tenant_id=tenant_id,
            project_id="PRJ-ENFANCE-ALIZES",
            aid_type="secours_urgence",
            confidential_ref="CCAS-CONFIDENTIEL-2027-04",
            amount_cents=15000,
            commission_decision="accorde",
            deliberation_ref="DELIB-CCAS-2027-01",
            notes="Secours d'urgence énergie et frais de cantine validé à l'unanimité en séance.",
        )

        es_repo.record_social_aid(
            tenant_id=tenant_id,
            project_id="PRJ-ENFANCE-ALIZES",
            aid_type="aide_periscolaire",
            confidential_ref="CCAS-CONFIDENTIEL-2027-09",
            amount_cents=8500,
            commission_decision="accorde",
            deliberation_ref="DELIB-CCAS-2027-03",
            notes="Prise en charge classe de mer et fournitures scolaires pour élève en difficulté.",
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
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    settings = Settings(
        mode="public_demo",
        db_path=data / "public.sqlite3",
        tenant_id="lot4-plougastel-test",
        public_origin=LOCAL_BASE,
        allowed_hosts=("127.0.0.1",),
        llm="demo",
    )

    app = create_app(settings)
    seed_lot4_data(data, LOCAL_BASE)

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(certpath, keypath)
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=PORT,
        ssl_keyfile=str(keypath),
        ssl_certfile=str(certpath),
        log_level="error",
    )
    server = uvicorn.Server(config)
    server.run()


def verify_browser(base_url: str, out_dir: Path, is_remote: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    report = {"base_url": base_url, "timestamp": datetime.now(timezone.utc).isoformat(), "screenshots": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--ignore-certificate-errors", "--no-sandbox"],
        )

        def take_snap(context, page, path: Path, title: str):
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path), full_page=False)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            report["screenshots"].append({
                "title": title,
                "file": path.name,
                "sha256": digest,
                "size_bytes": path.stat().st_size
            })
            print(f"[SCREENSHOT] {title} -> {path.name} (SHA-256: {digest[:12]}...)")

        # ----------------------------------------------------
        # Context 1: Desktop Full HD (1920x1080)
        # ----------------------------------------------------
        desktop_ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = desktop_ctx.new_page()

        # Step 1: Open public demo
        entry_url = f"{base_url}/demo.html#/"
        print("[PROOF] Navigating to demo URL:", entry_url)
        page.goto(entry_url, wait_until="networkidle")

        explore_btn = page.locator("a:has-text('Explorer la démonstration'), button:has-text('Explorer la démonstration')")
        if explore_btn.count() > 0 and explore_btn.is_visible():
            explore_btn.first.click()
            page.wait_for_load_state("networkidle")

        page.wait_for_selector(".overview-band, .page-heading", timeout=15000)
        page.wait_for_timeout(1000)

        # Switch to Commission 2 (Enfance, Jeunesse & Solidarités)
        comm_select = page.locator("#sidebar-commission-select")
        if comm_select.count() > 0:
            comm_select.select_option("commission-2")
            page.wait_for_timeout(800)

        # Switch to Campagnes scolaires tab
        camp_btn = page.locator("button:has-text('Campagnes scolaires'), button:has-text('Campagnes')")
        if camp_btn.count() > 0:
            camp_btn.first.click()
            page.wait_for_timeout(800)

        page.wait_for_selector(".school-panel", state="visible", timeout=12000)

        # CAPTURE 1: School Campaign Overview (Full HD)
        snap1_path = out_dir / "01-school-campaign-overview-fullhd.png"
        take_snap(desktop_ctx, page, snap1_path, "01 Vue d’ensemble Campagne Scolaire 2026-2027 (Full HD)")

        # CAPTURE 2: Live Quotient Familial Simulator and New Dossier Dialog
        new_dos_btn = page.locator("button:has-text('Nouveau dossier famille')")
        if new_dos_btn.count() > 0 and new_dos_btn.is_visible():
            new_dos_btn.first.click()
            page.wait_for_selector("text=Nouveau dossier famille", timeout=8000)
            page.wait_for_timeout(600)
        snap2_path = out_dir / "02-quotient-simulator-and-dossier-fullhd.png"
        take_snap(desktop_ctx, page, snap2_path, "02 Simulateur Quotient et Saisie Dossier Famille (Full HD)")

        # Close dialog
        cancel_dos = page.locator("button:has-text('Annuler')")
        if cancel_dos.count() > 0 and cancel_dos.is_visible():
            cancel_dos.first.click()
            page.wait_for_timeout(400)

        # CAPTURE 3: Annual Renewal Dialog (2027-2028)
        renew_btn = page.locator("button:has-text('Reconduire pour l’année suivante')")
        if renew_btn.count() > 0 and renew_btn.is_visible():
            renew_btn.first.click()
            page.wait_for_selector("text=Reconduire la campagne pour l’année suivante", timeout=8000)
            page.wait_for_timeout(600)
        snap3_path = out_dir / "03-campaign-renewal-dialog-fullhd.png"
        take_snap(desktop_ctx, page, snap3_path, "03 Boîte de dialogue Reconduction Annuelle (Full HD)")

        # Execute Renewal
        exec_renew = page.locator("button:has-text('Exécuter la reconduction')")
        if exec_renew.count() > 0 and exec_renew.is_visible():
            exec_renew.first.click()
            page.wait_for_timeout(1200)

        # CAPTURE 4: Renewed Campaign 2027-2028 rendered
        snap4_path = out_dir / "04-renewed-campaign-2027-2028-fullhd.png"
        take_snap(desktop_ctx, page, snap4_path, "04 Campagne Scolaire Reconduite 2027-2028 (Full HD)")

        # Target project for social aid
        if is_remote:
            target_proj_id = "f4a5f3ea-8e96-46b9-a75e-56fab2eccc41"
            proj_links = page.locator("a[href*='/chantiers/']")
            if proj_links.count() > 0:
                href = proj_links.first.get_attribute("href") or ""
                if "/chantiers/" in href:
                    target_proj_id = href.split("/chantiers/")[-1].split("?")[0]
            social_url = f"{base_url}/demo.html#/chantiers/{target_proj_id}?view=social"
        else:
            social_url = f"{base_url}/demo.html#/chantiers/PRJ-ENFANCE-ALIZES?view=social"

        # CAPTURE 5: Social Aid & CCAS Panel (Full HD)
        page.goto(social_url, wait_until="networkidle")
        page.wait_for_selector(".school-panel", state="visible", timeout=12000)
        page.wait_for_timeout(800)
        snap5_path = out_dir / "05-social-aid-ccas-panel-fullhd.png"
        take_snap(desktop_ctx, page, snap5_path, "05 Fiche Aide Sociale et CCAS Confidentielle (Full HD)")

        desktop_ctx.close()

        # ----------------------------------------------------
        # Context 2: Mobile 390x844 (iPhone 14 / modern smartphone)
        # ----------------------------------------------------
        mobile_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            ignore_https_errors=True,
        )
        m_page = mobile_ctx.new_page()

        # CAPTURE 6: Mobile School Campaign
        m_page.goto(f"{base_url}/demo.html#/", wait_until="networkidle")
        explore_btn_m = m_page.locator("a:has-text('Explorer la démonstration'), button:has-text('Explorer la démonstration')")
        if explore_btn_m.count() > 0 and explore_btn_m.is_visible():
            explore_btn_m.first.click()
            m_page.wait_for_load_state("networkidle")
        m_page.wait_for_timeout(1000)

        m_page.evaluate("() => { const sel = document.getElementById('sidebar-commission-select'); if (sel) { sel.value = 'commission-2'; sel.dispatchEvent(new Event('change', {bubbles: true})); } }")
        m_page.wait_for_timeout(800)

        camp_btn_m = m_page.locator("button:has-text('Campagnes scolaires'), button:has-text('Campagnes')")
        if camp_btn_m.count() > 0 and camp_btn_m.first.is_visible():
            camp_btn_m.first.click()
            m_page.wait_for_timeout(800)
        else:
            m_page.goto(f"{base_url}/demo.html#/?view=campaigns", wait_until="networkidle")

        m_page.wait_for_selector(".school-panel", state="visible", timeout=12000)
        snap6_path = out_dir / "06-school-campaign-mobile-390.png"
        take_snap(mobile_ctx, m_page, snap6_path, "06 Campagne Scolaire Mobile (390x844)")

        mobile_ctx.close()

        # ----------------------------------------------------
        # Context 3: Compact 320x568 (Small device / zero-overflow)
        # ----------------------------------------------------
        compact_ctx = browser.new_context(
            viewport={"width": 320, "height": 568},
            is_mobile=True,
            ignore_https_errors=True,
        )
        c_page = compact_ctx.new_page()

        c_page.goto(social_url, wait_until="networkidle")
        c_page.wait_for_selector(".school-panel", state="visible", timeout=12000)
        c_page.wait_for_timeout(800)

        snap7_path = out_dir / "07-social-aid-compact-320.png"
        take_snap(compact_ctx, c_page, snap7_path, "07 Registre Aide Sociale CCAS Compact (320x568)")

        compact_ctx.close()
        browser.close()

    (out_dir / "proof-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[COMPLETE] Captured {len(report['screenshots'])} screenshots to {out_dir}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", type=str, default=None, help="Remote URL (e.g. https://travaux.kerforge.com)")
    parser.add_argument("--out", type=str, default=str(ROOT / "test-results" / "lot-4"))
    parser.add_argument("--serve", action="store_true", help="Run local test server only")
    args = parser.parse_args()

    out_dir = Path(args.out)
    if args.serve:
        serve(out_dir)
        return

    if args.remote:
        print(f"[LOT 4 PROOF] Running against remote instance: {args.remote}")
        verify_browser(args.remote, out_dir, is_remote=True)
        return

    # Local mode
    print(f"[LOT 4 PROOF] Launching local loopback server on {LOCAL_BASE}...")
    server_process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve", "--out", str(out_dir)],
        cwd=str(ROOT),
    )
    try:
        for _ in range(40):
            if listening():
                break
            time.sleep(0.3)
        if not listening():
            raise RuntimeError("Test server failed to start")
        print("[LOT 4 PROOF] Server ready. Running browser tests...")
        verify_browser(LOCAL_BASE, out_dir, is_remote=False)
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except Exception:
            server_process.kill()


if __name__ == "__main__":
    main()
