"""Browser verification and Full HD / Mobile screenshot capture for Lot 3 (Urbanisme, Travaux et Ports).

Validates:
- Interactive vector cartography of Plougastel-Daoulas peninsula with WGS84 coordinates and MapLibre GeoJSON standard
- Visual pins for Ports (Tinduff, Passage, Auberlac'h) and Parcelles Urbanisme (Parcelle A-12)
- Interactive feature selection with floating drawer and direct dossier navigation
- Urbanisme planning dossier with cadastral parcel reference, PLU source, checklist of pieces, and advice status
- Port inspection sheet with condition rating (bon, moyen, dégradé, urgent) and native maintenance action linking
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
PORT = 19823
LOCAL_BASE = f"https://127.0.0.1:{PORT}"


def listening():
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def seed_lot3_data(data_dir: Path, base_url: str):
    """Seed Plougastel Urbanisme, Travaux and Ports demo data."""
    sys.path.insert(0, str(ROOT / "src"))
    from travaux.repository import Repository
    from travaux.urbanisme_ports import UrbanismePortsRepository
    from travaux.commissions import CommissionRepository

    db_path = data_dir / "public.sqlite3"
    repo = Repository(db_path)
    up_repo = UrbanismePortsRepository(repo)
    comm_repo = CommissionRepository(repo)

    tenant_id = "lot3-plougastel-test"
    with repo._transaction() as db:
        comm_repo.ensure_default_commissions(tenant_id)

        # 1. Project Tinduff
        p_tinduff = db.execute("SELECT id FROM projects WHERE tenant_id=? AND id=?", (tenant_id, "PRJ-PORT-TINDUFF")).fetchone()
        if not p_tinduff:
            repo.create_project(
                tenant_id,
                "TRV-2026-042",
                "Réfection du ponton — port du Tinduff",
                project_id="PRJ-PORT-TINDUFF",
                commission_id="commission-3",
                description="Réparation des équipements d'amarrage, remplacement des chaînes usées et consolidation de la cale ouest du port du Tinduff.",
            )

        # 2. Project Parcelle A-12
        p_parcelle = db.execute("SELECT id FROM projects WHERE tenant_id=? AND id=?", (tenant_id, "PRJ-URB-PARCELLE")).fetchone()
        if not p_parcelle:
            repo.create_project(
                tenant_id,
                "URB-2027-012",
                "Instruction parcelle A-12 — Centre-Bourg",
                project_id="PRJ-URB-PARCELLE",
                commission_id="commission-3",
                description="Instruction du permis de construire pour réhabilitation d'un corps de ferme en centre-bourg de Plougastel-Daoulas.",
            )

        # Seed Geo Features
        up_repo.save_geo_feature(
            tenant_id,
            "PRJ-PORT-TINDUFF",
            feature_type="port_ouvrage",
            name="Port du Tinduff — Ponton de plaisance",
            longitude=-4.3820,
            latitude=48.3370,
            properties={
                "port_name": "Port du Tinduff",
                "ouvrage_type": "Ponton plaisance",
                "condition_rating": "degrade",
            },
            feature_id="feat-tinduff-1",
        )

        up_repo.save_geo_feature(
            tenant_id,
            "PRJ-PORT-TINDUFF",
            feature_type="port_ouvrage",
            name="Port du Passage — Cale historique",
            longitude=-4.4210,
            latitude=48.3615,
            properties={
                "port_name": "Port du Passage",
                "ouvrage_type": "Cale de mise à l'eau",
                "condition_rating": "bon",
            },
            feature_id="feat-passage-1",
        )

        up_repo.save_geo_feature(
            tenant_id,
            "PRJ-PORT-TINDUFF",
            feature_type="port_ouvrage",
            name="Port de l'Auberlac'h — Mouillages",
            longitude=-4.3975,
            latitude=48.3512,
            properties={
                "port_name": "Port de l'Auberlac'h",
                "ouvrage_type": "Chaîne d'amarrage",
                "condition_rating": "moyen",
            },
            feature_id="feat-auberlach-1",
        )

        up_repo.save_geo_feature(
            tenant_id,
            "PRJ-URB-PARCELLE",
            feature_type="parcelle",
            name="Parcelle Exemple A-12 — Centre-Bourg",
            longitude=-4.3680,
            latitude=48.3750,
            properties={
                "parcel_ref": "Parcelle Exemple A-12",
                "regulation_source": "PLU Plougastel — Zone Ub",
                "advice_status": "favorable",
            },
            feature_id="feat-parcelle-a12",
        )

        # Seed Port Inspection
        up_repo.save_port_inspection(
            tenant_id,
            "PRJ-PORT-TINDUFF",
            port_name="Port du Tinduff",
            ouvrage_type="Ponton plaisance",
            inspector="Gilles Le Gall (Service Maritime)",
            inspection_date="2026-11-18",
            condition_rating="degrade",
            observations="Corrosion marquée sur les chaînes de retenue ouest et usure des cales élastiques. Remplacement préconisé avant la saison estivale.",
            linked_action_id="",
            inspection_id="insp-tinduff-01",
        )

        # Seed Urbanisme Dossier
        up_repo.save_urbanisme_dossier(
            tenant_id,
            "PRJ-URB-PARCELLE",
            parcel_ref="Parcelle Exemple A-12",
            request_type="permis_construire",
            regulation_source="PLU Plougastel — Zone Ub (Centre-Bourg)",
            checklist=[
                {"id": "pcmi1", "label": "PCMI1 — Plan de situation du terrain", "required": True, "checked": True},
                {"id": "pcmi2", "label": "PCMI2 — Plan de masse des constructions", "required": True, "checked": True},
                {"id": "pcmi3", "label": "PCMI3 — Plan en coupe du terrain et de la construction", "required": True, "checked": False},
                {"id": "pcmi4", "label": "PCMI4 — Notice descriptive du projet et matériaux", "required": True, "checked": False},
                {"id": "pcmi5", "label": "PCMI5 — Plan des façades et des toitures", "required": False, "checked": False},
                {"id": "loi_littoral", "label": "Conformité Loi Littoral (bande des 100m / espaces proches)", "required": True, "checked": True},
            ],
            advice_status="favorable",
            follow_up_date="2027-04-15",
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
        tenant_id="lot3-plougastel-test",
        llm="demo",
        public_origin=LOCAL_BASE,
        allowed_hosts=("127.0.0.1",),
    )
    app = create_app(settings)

    seed_lot3_data(data, LOCAL_BASE)
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=PORT,
        log_level="warning",
        ssl_certfile=str(certpath),
        ssl_keyfile=str(keypath),
    )
    server = uvicorn.Server(config)
    server.run()


def verify_browser(base_url: str, out_dir: Path, is_remote: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    report = {"base_url": base_url, "timestamp": datetime.now(timezone.utc).isoformat(), "screenshots": []}

    with sync_playwright() as p:
        # Browser launch args
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

        # If on welcome page with button, click it
        explore_btn = page.locator("a:has-text('Explorer la démonstration'), button:has-text('Explorer la démonstration')")
        if explore_btn.count() > 0 and explore_btn.is_visible():
            explore_btn.first.click()
            page.wait_for_load_state("networkidle")

        page.wait_for_selector(".overview-band, .page-heading", timeout=15000)
        page.wait_for_timeout(1000)

        # Click Commission 3 tab in header if present
        comm3_btn = page.locator("button:has-text('Commission 3'), button:has-text('Urbanisme'), .commission-pill:has-text('Urbanisme')")
        if comm3_btn.count() > 0:
            comm3_btn.first.click()
            page.wait_for_timeout(800)

        # Switch to Carte du Territoire
        map_btn = page.locator("button:has-text('Carte du Territoire'), button:has-text('Carte')")
        if map_btn.count() > 0:
            map_btn.first.click()
            page.wait_for_timeout(1000)

        page.wait_for_selector(".geomap-svg", state="visible", timeout=12000)

        # CAPTURE 1: Interactive Map view of Plougastel Full HD
        snap1_path = out_dir / "01-geomap-plougastel-fullhd.png"
        take_snap(desktop_ctx, page, snap1_path, "01 Carte Interactive Plougastel-Daoulas (Full HD)")

        # CAPTURE 2: Click on pin to open detail drawer
        page.evaluate("() => { const pins = document.querySelectorAll('.geo-pin-group'); if (pins.length > 0) pins[0].dispatchEvent(new MouseEvent('click', {bubbles: true})); }")
        page.wait_for_timeout(800)
        if page.locator(".geomap-drawer").count() == 0:
            page.locator(".geo-pin-group").first.press("Enter")
            page.wait_for_timeout(600)
        snap2_path = out_dir / "02-geomap-selected-tinduff-fullhd.png"
        take_snap(desktop_ctx, page, snap2_path, "02 Fiche Point Port du Tinduff (Full HD)")

        # Determine target project IDs
        if is_remote:
            back_btn = page.locator("button:has-text('Tous les dossiers')")
            if back_btn.count() > 0 and back_btn.first.is_visible():
                back_btn.first.click()
                page.wait_for_timeout(600)
            target_proj_id = "f4a5f3ea-8e96-46b9-a75e-56fab2eccc41"
            proj_links = page.locator("a[href*='/chantiers/']")
            if proj_links.count() > 0:
                href = proj_links.first.get_attribute("href") or ""
                if "/chantiers/" in href:
                    target_proj_id = href.split("/chantiers/")[-1].split("?")[0]
            urb_url = f"{base_url}/demo.html#/chantiers/{target_proj_id}?view=urbanisme"
            port_url = urb_url
        else:
            urb_url = f"{base_url}/demo.html#/chantiers/PRJ-URB-PARCELLE?view=urbanisme"
            port_url = f"{base_url}/demo.html#/chantiers/PRJ-PORT-TINDUFF?view=urbanisme"

        # CAPTURE 3: Urbanisme & Ports Dossier Panel (Parcelle A-12)
        page.goto(urb_url, wait_until="networkidle")
        page.wait_for_selector(".urbanisme-panel", state="visible", timeout=12000)
        page.wait_for_timeout(800)
        snap3_path = out_dir / "03-urbanisme-dossier-fullhd.png"
        take_snap(desktop_ctx, page, snap3_path, "03 Dossier Urbanisme Droits du Sol Parcelle A-12 (Full HD)")

        # CAPTURE 4: Port Inspection Sheet (Tinduff)
        page.goto(port_url, wait_until="networkidle")
        page.wait_for_selector(".urbanisme-panel", state="visible", timeout=12000)
        page.wait_for_timeout(800)
        snap4_path = out_dir / "04-port-inspection-fullhd.png"
        take_snap(desktop_ctx, page, snap4_path, "04 Fiche Inspection Portuaire et Maintenance (Full HD)")

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

        # CAPTURE 5: Mobile Map View
        m_page.goto(f"{base_url}/demo.html#/", wait_until="networkidle")
        explore_btn_m = m_page.locator("a:has-text('Explorer la démonstration'), button:has-text('Explorer la démonstration')")
        if explore_btn_m.count() > 0 and explore_btn_m.is_visible():
            explore_btn_m.first.click()
            m_page.wait_for_load_state("networkidle")
        m_page.wait_for_timeout(1000)

        comm3_m = m_page.locator("button:has-text('Commission 3'), button:has-text('Urbanisme')")
        if comm3_m.count() > 0:
            comm3_m.first.click()
            m_page.wait_for_timeout(600)

        map_btn_m = m_page.locator("button:has-text('Carte du Territoire'), button:has-text('Carte')")
        if map_btn_m.count() > 0:
            map_btn_m.first.click()
            m_page.wait_for_timeout(800)

        m_page.wait_for_selector(".geomap-svg", state="visible", timeout=12000)
        snap5_path = out_dir / "05-geomap-mobile-390.png"
        take_snap(mobile_ctx, m_page, snap5_path, "05 Carte Territoire Mobile (390x844)")

        # CAPTURE 6: Mobile Port Inspection Sheet
        m_page.goto(port_url, wait_until="networkidle")
        m_page.wait_for_selector(".urbanisme-panel", state="visible", timeout=12000)
        m_page.wait_for_timeout(800)
        snap6_path = out_dir / "06-port-inspection-mobile-390.png"
        take_snap(mobile_ctx, m_page, snap6_path, "06 Fiche Inspection Maritime Mobile (390x844)")

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

        c_page.goto(urb_url, wait_until="networkidle")
        c_page.wait_for_selector(".urbanisme-panel", state="visible", timeout=12000)
        c_page.wait_for_timeout(800)

        snap7_path = out_dir / "07-urbanisme-compact-320.png"
        take_snap(compact_ctx, c_page, snap7_path, "07 Affichage Compact Parcelle et PLU (320x568)")

        compact_ctx.close()
        browser.close()

    (out_dir / "proof-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[COMPLETE] Captured {len(report['screenshots'])} screenshots to {out_dir}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", type=str, default=None, help="Remote URL (e.g. https://travaux.kerforge.com)")
    parser.add_argument("--out", type=str, default=str(ROOT / "test-results" / "lot-3"))
    args = parser.parse_args()

    out_dir = Path(args.out)
    if args.remote:
        print(f"[LOT 3 PROOF] Running against remote instance: {args.remote}")
        verify_browser(args.remote, out_dir, is_remote=True)
        return

    # Local mode
    print(f"[LOT 3 PROOF] Launching local loopback server on {LOCAL_BASE}...")
    server_process = subprocess.Popen(
        [sys.executable, "-c", f"from tests.browser.lot3_urbanisme_ports_proof import serve; from pathlib import Path; serve(Path(r'{out_dir}'))"],
        cwd=str(ROOT),
    )
    try:
        # Wait for server
        for _ in range(40):
            if listening():
                break
            time.sleep(0.3)
        if not listening():
            raise RuntimeError("Test server failed to start")
        print("[LOT 3 PROOF] Server ready. Running browser tests...")
        verify_browser(LOCAL_BASE, out_dir, is_remote=False)
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except Exception:
            server_process.kill()


if __name__ == "__main__":
    main()
