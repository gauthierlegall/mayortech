"""Script de capture pour l'Audit Visuel du LOT v3.2 (Séances du Conseil Municipal).

Génère exactement 2 captures d'écran dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_V3_2_CONSEIL\\ :
1. 01_conseil_ordre_du_jour_cgct.png (Desktop 1920x1080: Ordre du jour, bandeau CGCT J-5, bouton Dossier des Élus PDF)
2. 02_conseil_quorum_et_votes.png (Desktop 1920x1080: Jauge quorum 24/33, table des élus avec pouvoirs, saisie rapide des votes)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_V3_2_CONSEIL")
PORT = 19865
LOCAL_BASE = f"http://127.0.0.1:{PORT}"


def listening():
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def serve(out_dir: Path):
    sys.path.insert(0, str(ROOT / "src"))
    from travaux.api import create_app
    from travaux.config import Settings
    import uvicorn

    data_dir = out_dir / "server-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        mode="demo",
        db_path=data_dir / "conseil_audit.sqlite3",
        tenant_id="plougastel-v3-2",
        llm="demo",
        allowed_hosts=("127.0.0.1", "localhost"),
        password_hash="test-hash",
        auth_mode="password",
    )
    app = create_app(settings)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT,
        log_level="warning",
    )


def safe_screenshot(target_page, path: Path, full_page: bool = False):
    img_bytes = target_page.screenshot(full_page=full_page)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(img_bytes)
    print(f"Captured: {path.name} -> {path}")


def run_audit_v3_2():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit v3.2] Démarrage des 2 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx.new_page()

        # Connect on demo space
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Select work profile (Commission 1 - Finances & Moyens)
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_c1 = page.locator('input[value="commission-1"]')
            if radio_c1.count() > 0:
                radio_c1.check()
            else:
                radio_prof.first.check()
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(1000)

        # ---------------------------------------------------------------------
        # Capture 1: 01_conseil_ordre_du_jour_cgct.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 1 : Ordre du jour & Convocation CGCT J-5 ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/seances", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Ensure tab 1 is selected
        tab1_btn = page.locator('[data-testid="tab-convocation"]')
        if tab1_btn.count() > 0:
            tab1_btn.click()
            page.wait_for_timeout(600)

        page.wait_for_selector('[data-testid="cgct-alert-banner"]', timeout=8000)
        page.wait_for_selector('[data-testid="btn-generate-dossier-pdf"]', timeout=8000)

        cap1_path = OUTPUT_DIR / "01_conseil_ordre_du_jour_cgct.png"
        safe_screenshot(page, cap1_path)

        # ---------------------------------------------------------------------
        # Capture 2: 02_conseil_quorum_et_votes.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 2 : Tenue de séance & Quorum ---")
        tab2_btn = page.locator('[data-testid="tab-tenue"]')
        if tab2_btn.count() > 0:
            tab2_btn.click()
            page.wait_for_timeout(800)

        page.wait_for_selector('[data-testid="quorum-gauge-card"]', timeout=8000)
        page.wait_for_selector('[data-testid="btn-record-vote"]', timeout=8000)

        cap2_path = OUTPUT_DIR / "02_conseil_quorum_et_votes.png"
        safe_screenshot(page, cap2_path)

        browser.close()
        print("\n[Audit v3.2] Toutes les captures ont été générées avec succès !")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    args = parser.parse_args()

    if args.server:
        serve(OUTPUT_DIR)
        return

    # Check or spawn server
    server_proc = None
    if not listening():
        print(f"Lancement du serveur démo de test sur le port {PORT}...")
        server_proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(50):
            if listening():
                break
            time.sleep(0.2)

    try:
        run_audit_v3_2()
    finally:
        if server_proc:
            server_proc.terminate()
            server_proc.wait(timeout=5)


if __name__ == "__main__":
    main()
