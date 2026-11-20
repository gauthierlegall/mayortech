"""Script de capture pour l'Audit Visuel du LOT v3.1 (Hub d'Interopérabilité Souveraine).

Génère exactement 3 captures d'écran dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_V3_1_INTEROP\\:
1. 01_parametres_connexions_civic_craft.png (Desktop 1920x1080: Hub 6 cartes, badges bac à sable/eIDAS, boutons Tester/Configurer)
2. 02_a_valider_retour_iparapheur_ctes.png (Desktop 1920x1080: Dossier avec poussée i-Parapheur et bandeau vert récépissé @CTES)
3. 03_messagerie_vers_validation_1clic.png (Desktop 1920x1080: Courriel ouvert avec bouton #102A4C texte blanc et modale préremplie)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_V3_1_INTEROP")
PORT = 19864
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
        db_path=data_dir / "interop_audit.sqlite3",
        tenant_id="plougastel-v3-1",
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


def run_audit_v3_1():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit v3.1] Démarrage des 3 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx.new_page()

        # Connect on demo space
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Select work profile
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
        # Capture 1: 01_parametres_connexions_civic_craft.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 1 : Paramètres > Connexions & Interopérabilité ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/parametres?section=connexions", wait_until="networkidle")
        page.wait_for_timeout(1200)

        # Click on Tester for Gotenberg or Parapheur to show active response
        test_buttons = page.locator('button:has-text("Tester")')
        if test_buttons.count() >= 3:
            # Click Gotenberg test (index 2)
            try:
                test_buttons.nth(2).click()
                page.wait_for_timeout(600)
            except Exception as e:
                print(f"Note test button click: {e}")

        safe_screenshot(page, OUTPUT_DIR / "01_parametres_connexions_civic_craft.png")

        # ---------------------------------------------------------------------
        # Capture 2: 02_a_valider_retour_iparapheur_ctes.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 2 : À valider > Retour i-Parapheur @CTES ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(1200)

        # Switch filter to "Service / Pool" or "En attente DGS" to show active dossiers on the left
        pool_btn = page.locator('button:has-text("Service / Pool"), button:has-text("En attente DGS")')
        if pool_btn.count() > 0:
            pool_btn.first.click()
            page.wait_for_timeout(600)

        # Click on "Autres actions"
        autres_actions = page.locator('button:has-text("Autres actions")')
        if autres_actions.count() > 0:
            autres_actions.first.click()
            page.wait_for_timeout(400)

            # Click on "Pousser vers i-Parapheur (Bac à sable)"
            push_btn = page.locator('button:has-text("Pousser vers i-Parapheur")')
            if push_btn.count() > 0:
                push_btn.first.click()
                page.wait_for_timeout(1000)

        safe_screenshot(page, OUTPUT_DIR / "02_a_valider_retour_iparapheur_ctes.png")

        # ---------------------------------------------------------------------
        # Capture 3: 03_messagerie_vers_validation_1clic.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 3 : Messagerie > Lancer une validation (1 clic) ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/mail", wait_until="networkidle")
        page.wait_for_timeout(1200)

        # Click on the first message in the list using data-inbox="open"
        mail_open_btn = page.locator('button[data-inbox="open"]')
        if mail_open_btn.count() > 0:
            mail_open_btn.first.click()
            page.wait_for_timeout(800)

        # Click on the button "Lancer une validation" in the toolbar
        launch_val_btn = page.locator('button[data-inbox="launch-validation"], button:has-text("Lancer une validation")')
        if launch_val_btn.count() > 0:
            launch_val_btn.first.click()
            page.wait_for_timeout(800)

        safe_screenshot(page, OUTPUT_DIR / "03_messagerie_vers_validation_1clic.png")

        browser.close()
        print("\n[Audit v3.1] Les 3 captures sont générées avec succès !")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-only", action="store_true")
    args = parser.parse_args()

    if args.serve_only:
        serve(OUTPUT_DIR)
        sys.exit(0)

    server_process = None
    if not listening():
        print(f"Lancement du serveur sur {LOCAL_BASE}...")
        server_process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve-only"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            if listening():
                break
            time.sleep(0.3)

    try:
        run_audit_v3_1()
    finally:
        if server_process:
            server_process.terminate()
            server_process.wait()
