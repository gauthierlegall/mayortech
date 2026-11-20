"""Script de capture pour l'Audit Visuel Zero Gadget / Zéro Ornement Tech.

Génère exactement 3 captures d'écran dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_ZERO_GADGET\\ :
1. 01_accueil_epure_sans_gadgets.png (Desktop 1920x1080: zéro point vert sidebar, zéro Temps réel, zéro Sparkles, zéro répétition commune/fonction)
2. 02_palette_ctrl_k_propre.png (Desktop 1920x1080: palette Ctrl+K sans < 50 ms)
3. 03_focus_elu_sobre.png (Desktop 1920x1080: sans phrase de remplissage ni paillettes)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_ZERO_GADGET")
PORT = 19866
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
        db_path=data_dir / "zero_gadget_audit.sqlite3",
        tenant_id="plougastel-zero-gadget",
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


def run_audit_zero_gadget():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit Zero Gadget] Démarrage des 3 captures dans : {OUTPUT_DIR}")

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

        # Ensure Focus Elu mode is disabled for Capture 1
        page.evaluate("() => { localStorage.removeItem('mayortech_focus_elu_mode'); }")

        # ---------------------------------------------------------------------
        # Capture 1: 01_accueil_epure_sans_gadgets.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 1 : Accueil épuré sans gadgets ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(1500)

        safe_screenshot(page, OUTPUT_DIR / "01_accueil_epure_sans_gadgets.png")

        # ---------------------------------------------------------------------
        # Capture 2: 02_palette_ctrl_k_propre.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 2 : Palette Ctrl+K propre (sans < 50 ms) ---")
        # Trigger Ctrl+K shortcut
        page.keyboard.press("Control+k")
        page.wait_for_timeout(800)
        try:
            page.wait_for_selector('input[placeholder*="Rechercher"]', timeout=3000)
        except Exception:
            pass

        safe_screenshot(page, OUTPUT_DIR / "02_palette_ctrl_k_propre.png")

        # Close palette modal with Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # ---------------------------------------------------------------------
        # Capture 3: 03_focus_elu_sobre.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 3 : Mode Focus Élu sobre (sans remplissage ni paillettes) ---")
        focus_btn = page.locator('button:has-text("Focus Élu")')
        if focus_btn.count() > 0:
            focus_btn.click()
            page.wait_for_timeout(1000)
        else:
            page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'true'); window.location.reload(); }")
            page.wait_for_timeout(1500)

        safe_screenshot(page, OUTPUT_DIR / "03_focus_elu_sobre.png")

        browser.close()

    print("\n[Audit Zero Gadget] Toutes les captures ont été générées avec succès !")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-only", action="store_true")
    args = parser.parse_args()

    if args.serve_only:
        serve(OUTPUT_DIR)
        return

    server_proc = None
    if not listening():
        print(f"[Serveur] Lancement du backend local sur http://127.0.0.1:{PORT}...")
        server_proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve-only"],
            cwd=str(ROOT),
        )
        deadline = time.time() + 25.0
        while time.time() < deadline:
            if listening():
                break
            time.sleep(0.3)
        if not listening():
            raise RuntimeError(f"Le serveur sur {PORT} n'a pas répondu à temps.")
        print(f"[Serveur] Prêt sur http://127.0.0.1:{PORT} !")

    try:
        run_audit_zero_gadget()
    finally:
        if server_proc:
            print("[Serveur] Arrêt du backend local...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()


if __name__ == "__main__":
    main()
