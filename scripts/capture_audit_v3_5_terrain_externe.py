"""Script de capture pour l'Audit Visuel du LOT v3.5 (Mode Terrain Hors-Ligne PWA, Conflits de Voirie & Suivi Externe).

Génère les captures d'écran dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_V3_5_TERRAIN_EXTERNE\\ :
- 01_mobile_terrain_hors_ligne_dictee.png (Mobile 390x844 : Terrain PWA en mode hors-ligne avec badge ambre et dialogue de constat avec dictée vocale)
- 02_conflit_voirie_commission_travaux.png (Desktop 1920x1080 : Planning avec bannière de détection de conflit de voirie Quai du Tinduff / Rue des Ajoncs)
- 03_suivi_externe_petitionnaire_mobile.png (Mobile 390x844 : Page publique Track & Trace pétitionnaire PC-2026-042 avec 4 jalons et zone de dépôt sécurisé)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_V3_5_TERRAIN_EXTERNE")
PORT = 19875
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
        db_path=data_dir / "v3_5_audit.sqlite3",
        tenant_id="plougastel-v3-5",
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

            # -------------------------------------------------------------
            # CAPTURE 1: Mobile Terrain Hors-Ligne + Dictée Vocale (390x844)
            # -------------------------------------------------------------
            mobile_context = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
                locale="fr-FR",
            )
            mobile_page = mobile_context.new_page()

            mobile_page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle", timeout=30000)
            mobile_page.wait_for_timeout(800)

            # Auto-sélection profil 3 (Urbanisme, travaux et ports)
            radio_prof = mobile_page.locator('input[name="work-profile"]')
            if radio_prof.count() > 0:
                radio_prof.nth(2).check()
                mobile_page.wait_for_timeout(200)
                open_btn = mobile_page.locator('button:has-text("Ouvrir mon espace")')
                if open_btn.count() > 0:
                    open_btn.first.click()
                    mobile_page.wait_for_timeout(1200)

            # Navigation vers /terrain
            mobile_page.goto(f"{LOCAL_BASE}/demo.html#/terrain", wait_until="networkidle", timeout=30000)
            mobile_page.wait_for_timeout(1000)

            # Activer la simulation hors-ligne
            offline_btn = mobile_page.locator('button:has-text("Simuler Hors-ligne")')
            if offline_btn.count() > 0:
                offline_btn.first.click()
                mobile_page.wait_for_timeout(400)

            # Ouvrir le modal "Nouveau constat"
            new_report_btn = mobile_page.locator('button:has-text("Nouveau constat")')
            if new_report_btn.count() > 0:
                new_report_btn.first.click()
                mobile_page.wait_for_timeout(600)

            # Déclencher le micro (dictée vocale) pour simuler la transcription vocale
            mic_btn = mobile_page.locator('button:has-text("Dictée vocale")')
            if mic_btn.count() > 0:
                mic_btn.first.click()
                mobile_page.wait_for_timeout(600)

            safe_screenshot(
                mobile_page,
                OUTPUT_DIR / "01_mobile_terrain_hors_ligne_dictee.png",
                full_page=False,
            )
            mobile_context.close()

            # -------------------------------------------------------------
            # CAPTURE 2: Desktop Planning - Conflit de Voirie (1920x1080)
            # -------------------------------------------------------------
            desktop_context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                locale="fr-FR",
            )
            desktop_page = desktop_context.new_page()

            desktop_page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle", timeout=30000)
            desktop_page.wait_for_timeout(800)

            # Auto-sélection profil 3 (Urbanisme, travaux et ports)
            radio_desktop = desktop_page.locator('input[name="work-profile"]')
            if radio_desktop.count() > 0:
                radio_desktop.nth(2).check()
                desktop_page.wait_for_timeout(200)
                open_btn_d = desktop_page.locator('button:has-text("Ouvrir mon espace")')
                if open_btn_d.count() > 0:
                    open_btn_d.first.click()
                    desktop_page.wait_for_timeout(1200)

            desktop_page.goto(f"{LOCAL_BASE}/demo.html#/planning", wait_until="networkidle", timeout=30000)
            desktop_page.wait_for_timeout(1500)

            # S'assurer que le bandeau de conflit est bien visible
            conflict_banner = desktop_page.locator('text=Conflit de circulation détecté')
            if conflict_banner.count() > 0:
                print("Banner found on planning!")

            safe_screenshot(
                desktop_page,
                OUTPUT_DIR / "02_conflit_voirie_commission_travaux.png",
                full_page=False,
            )
            desktop_context.close()

            # -------------------------------------------------------------
            # CAPTURE 3: Mobile Track & Trace Pétitionnaire (390x844)
            # -------------------------------------------------------------
            suivi_context = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
                locale="fr-FR",
            )
            suivi_page = suivi_context.new_page()

            suivi_page.goto(f"{LOCAL_BASE}/demo.html#/suivi/PC-2026-042-LE-GALL", wait_until="networkidle", timeout=30000)
            suivi_page.wait_for_timeout(1500)

            safe_screenshot(
                suivi_page,
                OUTPUT_DIR / "03_suivi_externe_petitionnaire_mobile.png",
                full_page=True,
            )
            suivi_context.close()

            browser.close()

    finally:
        if server:
            server.terminate()
            server.wait()


if __name__ == "__main__":
    main()
