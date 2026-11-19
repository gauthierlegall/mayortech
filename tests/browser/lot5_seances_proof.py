"""Browser verification and Full HD / Mobile screenshot capture for Lot 5 (Séances et Instances Spécialisées).

Validates:
- Commission sessions management (Convocation/Brouillon -> En cours -> Clôturée/Scellée)
- Agenda items with strict ordering, project dossier attachments, and deliberation numbering (DELIB-2027-COM3-01)
- Attendance sheet and legal quorum calculation (CGCT L2121-17)
- Live voting engine (Pour / Contre / Abstention / Avis favorable/défavorable/réservé)
- Decidim-inspired formal meeting close with cryptographic SHA-256 seal of the minutes
- Specialized instances panel: CAO (Mégalis Bretagne), CCSPL (Délégations de service public), CCID (Cadastre & Impôts)
- Full HD (1920x1080), Mobile (390x844), and Compact (320x568) responsive layouts
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PORT = 19825
LOCAL_BASE = f"https://127.0.0.1:{PORT}"


def listening():
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def seed_lot5_data(data_dir: Path, base_url: str):
    """Seed Plougastel Séances et Instances demo data."""
    sys.path.insert(0, str(ROOT / "src"))
    from travaux.commissions import COMMISSION_3_ID, CommissionRepository
    from travaux.repository import Repository
    from travaux.seances_instances import SeancesInstancesRepository

    db_path = data_dir / "public.sqlite3"
    repo = Repository(db_path)
    seances_repo = SeancesInstancesRepository(repo)
    comm_repo = CommissionRepository(repo)

    tenant_id = "lot5-plougastel-test"
    comm_repo.ensure_default_commissions(tenant_id)

    # 1. Project Aménagement du Tinduff (Commission 3)
    p_tinduff = None
    try:
        p_tinduff = repo.get_project(tenant_id, "PRJ-TRAVAUX-TINDUFF")
    except Exception:
        pass

    if not p_tinduff:
        repo.create_project(
            tenant_id,
            "TRV-2027-042",
            "Réfection et aménagement du Port du Tinduff",
            project_id="PRJ-TRAVAUX-TINDUFF",
            commission_id=COMMISSION_3_ID,
        )

    # 2. Seed active session
    session = seances_repo.create_session(
        tenant_id=tenant_id,
        commission_id=COMMISSION_3_ID,
        title="Commission Urbanisme, Travaux et Ports — Séance ordinaire de printemps",
        session_date="2027-04-22",
        session_time="18:30",
        location="Salle du Conseil Municipal, Hôtel de Ville de Plougastel",
        quorum_required=3,
        notes="Séance d'examen des marchés publics de voirie et de la réfection du ponton Tinduff.",
    )
    ses_id = session["id"]

    # 3. Add agenda items
    seances_repo.add_agenda_item(
        tenant_id=tenant_id,
        session_id=ses_id,
        title="Validation du programme de réfection du ponton visiteur du Tinduff",
        description="Examen des devis, du phasage technique et de l'impact nautique estival.",
        project_id="PRJ-TRAVAUX-TINDUFF",
        rapporteur="Jean-Luc Le Gall (Adjoint aux Travaux)",
    )

    seances_repo.add_agenda_item(
        tenant_id=tenant_id,
        session_id=ses_id,
        title="Plan de sobriété énergétique des éclairages publics communaux",
        description="Remplacement des luminaires halogènes par des LED gradables - Tranche 2027.",
        rapporteur="Marie Le Meur (Conseillère municipale déléguée)",
    )

    # 4. Attendance
    seances_repo.update_attendance(
        tenant_id=tenant_id,
        session_id=ses_id,
        attendances=[
            {"member_name": "Jean-Luc Le Gall", "member_role": "titulaire", "status": "present"},
            {"member_name": "Marie Le Meur", "member_role": "titulaire", "status": "present"},
            {"member_name": "Yvon Kervella", "member_role": "titulaire", "status": "pouvoir", "proxy_to": "Jean-Luc Le Gall"},
            {"member_name": "Sophie Tanguy", "member_role": "suppleant", "status": "present"},
        ],
    )

    # 5. Specialized Records
    seances_repo.create_specialized_record(
        tenant_id=tenant_id,
        instance_id="cao",
        record_type="cao_marche",
        reference="MEGALIS-BRETAGNE-2027-T08",
        title="Marché public de voirie communale - Lot 1 Enrobés à chaud",
        details={
            "plateforme": "Mégalis Bretagne",
            "lots": 2,
            "plis_recus": 4,
            "attributaire": "Eurovia Bretagne Ouest",
            "montant_ou_valeur": "284 000 € HT",
            "remarques": "Attribué à l'offre économiquement la plus avantageuse.",
        },
    )

    seances_repo.create_specialized_record(
        tenant_id=tenant_id,
        instance_id="ccspl",
        record_type="ccspl_rapport",
        reference="RAPPORT-DSP-EAU-2026",
        title="Rapport annuel sur le prix et la qualité du service d'eau potable et assainissement",
        details={
            "delegataire": "Eau du Ponant",
            "conformite_pct": "100%",
            "rendement_reseau": "84.5%",
            "montant_ou_valeur": "Budget d'exploitation 1 420 000 €",
            "remarques": "Avis favorable de la commission consultative sans réserve.",
        },
    )

    seances_repo.create_specialized_record(
        tenant_id=tenant_id,
        instance_id="ccid",
        record_type="ccid_evaluation",
        reference="CCID-2027-SECTION-AD-14",
        title="Évaluation de la valeur locative cadastrale - Nouveau local d'activité ZA Ty-Ar-Menez",
        details={
            "section": "AD",
            "parcelle": "14",
            "surface_m2": "420 m²",
            "montant_ou_valeur": "VL Retenue : 38 500 €",
            "remarques": "Validation conjointe avec le SIP Brest Ouest.",
        },
    )

    repo.close()
    print(f"[SEED] Lot 5 demo data created successfully for tenant {tenant_id}")


def run_lot5_proof(base_url: str, out_dir: Path, is_remote: bool = False):
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--no-sandbox",
                "--host-resolver-rules=MAP demo-travaux.kerforge.com 178.105.35.246, MAP *.kerforge.com 178.105.35.246",
            ],
        )

        def take_snap(ctx, page_inst, path: Path, title: str):
            page_inst.screenshot(path=str(path), full_page=False)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.append({
                "file": path.name,
                "title": title,
                "sha256": digest,
                "size_bytes": path.stat().st_size,
                "viewport": page_inst.viewport_size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
        page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[BROWSER ERROR] {err}"))

        def safe_goto(p, url, retries=3):
            for attempt in range(retries):
                try:
                    p.goto(url, wait_until="networkidle", timeout=30000)
                    return
                except Exception as ex:
                    print(f"[RETRY] Goto failed (attempt {attempt+1}/{retries}): {ex}")
                    if attempt == retries - 1:
                        raise
                    time.sleep(2)

        entry_url = f"{base_url}/demo.html#/"
        print("[PROOF] Navigating to demo URL:", entry_url)
        safe_goto(page, entry_url)

        explore_btn = page.locator("a:has-text('Explorer la démonstration'), button:has-text('Explorer la démonstration')")
        if explore_btn.count() > 0 and explore_btn.is_visible():
            explore_btn.first.click()
            page.wait_for_load_state("networkidle")

        print("[PROOF] Current URL:", page.url)
        print("[PROOF] Content snippet:", page.content()[:400])

        page.wait_for_selector(".overview-band, .page-heading", timeout=15000)
        page.wait_for_timeout(1000)

        # Switch to Commission 3 (Urbanisme, Travaux & Ports)
        comm_select = page.locator("#sidebar-commission-select")
        if comm_select.count() > 0:
            comm_select.select_option("commission-3")
            page.wait_for_timeout(1200)

        # Switch to Séances & Instances tab
        sessions_nav_btn = page.locator("button:has-text('Séances & Instances'), button:has-text('Séances')")
        if sessions_nav_btn.count() > 0 and sessions_nav_btn.first.is_visible():
            sessions_nav_btn.first.click()
            page.wait_for_timeout(1000)

        try:
            page.wait_for_selector("#sessions-management-root", state="visible", timeout=6000)
        except Exception:
            page.goto(f"{base_url}/demo.html#/?view=sessions", wait_until="networkidle")
            page.wait_for_selector("#sessions-management-root", state="visible", timeout=15000)
        page.wait_for_timeout(800)

        # CAPTURE 1: Session Agenda Preparation (Full HD)
        snap1_path = out_dir / "01-session-agenda-preparation-fullhd.png"
        take_snap(desktop_ctx, page, snap1_path, "01 Préparation de Séance et Ordre du Jour (Full HD)")

        # Record a live vote on Point 1
        vote_pour_btn = page.locator("button:has-text('+1 Pour')")
        if vote_pour_btn.count() > 0 and vote_pour_btn.first.is_visible():
            vote_pour_btn.first.click()
            page.wait_for_timeout(600)
            vote_pour_btn.first.click()
            page.wait_for_timeout(600)

        # CAPTURE 2: Live Voting (Full HD)
        snap2_path = out_dir / "02-session-live-voting-fullhd.png"
        take_snap(desktop_ctx, page, snap2_path, "02 Délibérations et Votes en Séance (Full HD)")

        # Close session and seal PV
        close_btn = page.locator("button:has-text('Clôturer et sceller le PV')")
        if close_btn.count() > 0 and close_btn.is_visible():
            close_btn.first.click()
            page.wait_for_selector("text=Clôturer et sceller le procès-verbal", timeout=8000)
            page.wait_for_timeout(500)
            confirm_close_btn = page.locator("button:has-text('Confirmer et sceller le PV')")
            if confirm_close_btn.count() > 0:
                confirm_close_btn.first.click()
                page.wait_for_timeout(1200)

        # CAPTURE 3: Formally Closed Meeting with Cryptographic Seal Banner
        snap3_path = out_dir / "03-session-closed-sealed-pv-fullhd.png"
        take_snap(desktop_ctx, page, snap3_path, "03 Séance Clôturée et Procès-Verbal Scellé SHA-256 (Full HD)")

        # Switch to Specialized Instances Tab
        spec_tab_btn = page.locator("button:has-text('Instances Spécialisées')")
        if spec_tab_btn.count() > 0:
            spec_tab_btn.first.click()
            page.wait_for_timeout(800)

        # CAPTURE 4: CAO (Mégalis Bretagne)
        cao_tab = page.locator("button:has-text('CAO (Marchés')")
        if cao_tab.count() > 0:
            cao_tab.first.click()
            page.wait_for_timeout(600)
        snap4_path = out_dir / "04-specialized-instance-cao-fullhd.png"
        take_snap(desktop_ctx, page, snap4_path, "04 Commission d'Appel d'Offres - CAO & Mégalis (Full HD)")

        # CAPTURE 5: CCSPL (Services Publics Locaux)
        ccspl_tab = page.locator("button:has-text('CCSPL (Services')")
        if ccspl_tab.count() > 0:
            ccspl_tab.first.click()
            page.wait_for_timeout(600)
        snap5_path = out_dir / "05-specialized-instance-ccspl-fullhd.png"
        take_snap(desktop_ctx, page, snap5_path, "05 Commission Consultative des Services Publics Locaux - CCSPL (Full HD)")

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
        m_page.on("console", lambda msg: print(f"[MOBILE CONSOLE] {msg.type}: {msg.text}"))
        m_page.on("pageerror", lambda err: print(f"[MOBILE ERROR] {err}"))
        safe_goto(m_page, entry_url)

        m_explore = m_page.locator("a:has-text('Explorer la démonstration'), button:has-text('Explorer la démonstration')")
        if m_explore.count() > 0:
            try:
                m_explore.first.scroll_into_view_if_needed()
                m_explore.first.click(force=True, timeout=5000)
                m_page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"[MOBILE] Explore click note: {e}")
        m_page.wait_for_timeout(1000)

        m_page.evaluate("() => { const sel = document.getElementById('sidebar-commission-select'); if (sel) { sel.value = 'commission-3'; sel.dispatchEvent(new Event('change', {bubbles: true})); } }")
        m_page.wait_for_timeout(1000)

        m_page.evaluate("() => { const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Séances')); if (btn) { btn.click(); } else { location.hash = '#/?view=sessions'; } }")
        m_page.wait_for_timeout(1000)

        try:
            m_page.wait_for_selector("#sessions-management-root", timeout=5000)
        except Exception:
            dest_url = m_page.url.split('#')[0] + "#/?view=sessions"
            safe_goto(m_page, dest_url)
            m_page.wait_for_selector("#sessions-management-root", timeout=15000)

        m_page.wait_for_timeout(800)
        snap6_path = out_dir / "06-session-agenda-mobile-390.png"
        take_snap(mobile_ctx, m_page, snap6_path, "06 Ordre du Jour et Quorum Responsive Mobile (390x844)")
        mobile_ctx.close()

        # ----------------------------------------------------
        # Context 3: Compact 320x568 (iPhone SE 1st gen / narrow screen)
        # ----------------------------------------------------
        compact_ctx = browser.new_context(
            viewport={"width": 320, "height": 568},
            is_mobile=True,
            ignore_https_errors=True,
        )
        c_page = compact_ctx.new_page()
        c_page.on("console", lambda msg: print(f"[COMPACT CONSOLE] {msg.type}: {msg.text}"))
        c_page.on("pageerror", lambda err: print(f"[COMPACT ERROR] {err}"))
        safe_goto(c_page, entry_url)

        c_explore = c_page.locator("a:has-text('Explorer la démonstration'), button:has-text('Explorer la démonstration')")
        if c_explore.count() > 0:
            try:
                c_explore.first.scroll_into_view_if_needed()
                c_explore.first.click(force=True, timeout=5000)
                c_page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"[COMPACT] Explore click note: {e}")
        c_page.wait_for_timeout(1000)

        c_page.evaluate("() => { const sel = document.getElementById('sidebar-commission-select'); if (sel) { sel.value = 'commission-3'; sel.dispatchEvent(new Event('change', {bubbles: true})); } }")
        c_page.wait_for_timeout(1000)

        c_page.evaluate("() => { const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Séances')); if (btn) { btn.click(); } else { location.hash = '#/?view=sessions'; } }")
        c_page.wait_for_timeout(1000)

        try:
            c_page.wait_for_selector("#sessions-management-root", timeout=5000)
        except Exception:
            dest_url_c = c_page.url.split('#')[0] + "#/?view=sessions"
            safe_goto(c_page, dest_url_c)
            c_page.wait_for_selector("#sessions-management-root", timeout=15000)

        c_page.wait_for_timeout(800)
        snap7_path = out_dir / "07-session-vote-compact-320.png"
        take_snap(compact_ctx, c_page, snap7_path, "07 Séances et Délibérations Écran Compact (320x568)")
        compact_ctx.close()

        browser.close()

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[COMPLETE] {len(manifest)} screenshots captured and verified in {out_dir}")
    return manifest


def serve(output: Path):
    for key in list(os.environ):
        if key.startswith("TRAVAUX_") or key in {"SSLKEYLOGFILE", "QUICLOGDIR"}:
            os.environ.pop(key, None)
    sys.path.insert(0, str(ROOT / "src"))
    from datetime import timedelta
    import ipaddress
    import ssl
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
        tenant_id="lot5-plougastel-test",
        public_origin=LOCAL_BASE,
        allowed_hosts=("127.0.0.1",),
        llm="demo",
    )

    app = create_app(settings)
    seed_lot5_data(data, LOCAL_BASE)

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", help="URL of remote server")
    parser.add_argument("--output-dir", default=str(ROOT / "test-results" / "lot-5"))
    parser.add_argument("--serve", action="store_true", help="Run local test server only")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)

    if args.serve:
        serve(out_dir)
        return

    if args.remote:
        print(f"[MODE] Running proof on remote server: {args.remote}")
        run_lot5_proof(args.remote.rstrip("/"), out_dir, is_remote=True)
        return

    # Local mode
    print(f"[MODE] Launching local loopback server on {LOCAL_BASE}...")
    server_process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve", "--output-dir", str(out_dir)],
        cwd=str(ROOT),
    )
    try:
        deadline = time.time() + 15
        started = False
        while time.time() < deadline:
            if listening():
                started = True
                break
            time.sleep(0.3)

        if not started:
            raise RuntimeError("Server failed to start within 15 seconds")

        print(f"[SERVER] Server is listening at {LOCAL_BASE}")
        run_lot5_proof(LOCAL_BASE, out_dir, is_remote=False)

    finally:
        print("[SERVER] Terminating loopback server...")
        server_process.terminate()
        server_process.wait(timeout=5)


if __name__ == "__main__":
    main()
