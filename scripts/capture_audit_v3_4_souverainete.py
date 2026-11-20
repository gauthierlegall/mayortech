"""Script de capture pour l'Audit Visuel du LOT v3.4 (Souveraineté des Données & Chaîne d'Audit SHA-256).

Génère la capture d'écran dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_V3_4_SOUVERAINETE\\ :
- 01_parametres_export_et_integrite.png (Desktop 1920x1080 : Paramètres > Organisation avec carte Souveraineté & Audit SHA-256 certifiée, Head Hash, contrôle mathématique réussi et bouton d'export souverain au format ouvert).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_V3_4_SOUVERAINETE")
PORT = 19869
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
        db_path=data_dir / "v3_4_audit.sqlite3",
        tenant_id="plougastel-v3-4",
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-only", action="store_true")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.serve_only:
        serve(OUTPUT_DIR)
        return

    server = None
    if not listening():
        server = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve-only"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        started = time.time()
        while time.time() - started < 15:
            if listening():
                break
            time.sleep(0.3)
        if not listening():
            if server:
                server.terminate()
            raise RuntimeError(f"Le serveur n'a pas répondu sur le port {PORT}")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                locale="fr-FR",
            )
            page = context.new_page()

            # Connexion espace démo
            page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)

            # Sélection d'un profil de travail si l'écran de profil est affiché
            radio_prof = page.locator('input[name="work-profile"]')
            if radio_prof.count() > 0:
                radio_prof.first.check()
                page.wait_for_timeout(300)
                open_btn = page.locator('button:has-text("Ouvrir mon espace")')
                if open_btn.count() > 0:
                    open_btn.first.click()
                    page.wait_for_timeout(1500)

            # Navigation vers la section Paramètres > Organisation
            page.goto(f"{LOCAL_BASE}/demo.html#/settings/organization", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)

            # Cliquer sur "Organisation" dans les onglets paramètres si besoin
            org_tab_btn = page.locator('button:has-text("Organisation")')
            if org_tab_btn.count() > 0:
                org_tab_btn.first.click()
                page.wait_for_timeout(1000)

            # Cliquer sur "Vérifier l’intégrité" pour lancer le contrôle mathématique
            verify_btn = page.locator('button:has-text("Vérifier l’intégrité")')
            if verify_btn.count() > 0:
                verify_btn.first.click()
                page.wait_for_timeout(1200)

            # Capture d'écran 01 : Paramètres avec carte Souveraineté & Chaîne SHA-256
            safe_screenshot(
                page,
                OUTPUT_DIR / "01_parametres_export_et_integrite.png",
                full_page=False,
            )

            context.close()
            browser.close()

    finally:
        if server:
            server.terminate()
            server.wait()


if __name__ == "__main__":
    main()
