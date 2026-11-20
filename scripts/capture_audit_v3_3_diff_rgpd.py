"""Script de capture pour l'Audit Visuel du LOT v3.3 (Comparateur Juridique Diff & Anonymisation RGPD).

Génère exactement 2 captures d'écran dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_V3_3_DIFF_RGPD\\ :
1. 01_comparatif_juridique_diff.png (Desktop 1920x1080: Feuille d'acte avec sélecteur Comparatif, suppressions barrées carmin et ajouts vert sceau)
2. 02_modale_anonymisation_rgpd.png (Desktop 1920x1080: Modale RGPD avec détection déterministe, aperçu publiable en direct et doubles hashs SHA-256)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_V3_3_DIFF_RGPD")
PORT = 19868
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
        db_path=data_dir / "v3_3_audit.sqlite3",
        tenant_id="plougastel-v3-3",
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


def run_audit_v3_3():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit v3.3] Démarrage des 2 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx.new_page()

        # Connect on demo space
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Select work profile (Commission 3 - Urbanisme, travaux & ports)
        radio_c3 = page.locator('input[value="commission-3"]')
        if radio_c3.count() > 0:
            radio_c3.check()
        else:
            radio_prof = page.locator('input[name="work-profile"]')
            if radio_prof.count() > 0:
                radio_prof.first.check()

        page.wait_for_timeout(400)
        open_btn = page.locator('button:has-text("Ouvrir mon espace")')
        if open_btn.count() > 0 and open_btn.is_enabled():
            open_btn.click()
            page.wait_for_timeout(1000)

        # Navigate to Validations (À valider)
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Click on filter "En attente DGS" or "Service / Pool" if needed
        tab_dgs = page.locator('button:has-text("En attente DGS")')
        if tab_dgs.count() > 0:
            tab_dgs.click()
            page.wait_for_timeout(400)

        # Click on dossier PC-2026-042 if needed
        pc_dossier = page.locator('text=PC-2026-042')
        if pc_dossier.count() > 0:
            pc_dossier.first.click()
            page.wait_for_timeout(500)

        # ---------------------------------------------------------------------
        # Capture 1: 01_comparatif_juridique_diff.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 1 : Comparatif Juridique Diff (v1.0 <-> v1.1) ---")

        # Click on the selector "Comparatif des modifications"
        diff_btn = page.locator('button:has-text("Comparatif des modifications")')
        if diff_btn.count() > 0:
            print("Activation du mode Comparatif des modifications...")
            diff_btn.first.click()
            page.wait_for_timeout(600)
        else:
            print("Bouton diff introuvable directement...")

        safe_screenshot(page, OUTPUT_DIR / "01_comparatif_juridique_diff.png")

        # ---------------------------------------------------------------------
        # Capture 2: 02_modale_anonymisation_rgpd.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 2 : Modale d'Anonymisation RGPD (Ordonnance 2021-1310) ---")

        # Click on "Publiable RGPD" button
        rgpd_btn = page.locator('button:has-text("Publiable RGPD")')
        if rgpd_btn.count() > 0:
            print("Ouverture de la modale RGPD via bouton Publiable RGPD...")
            rgpd_btn.first.click()
            page.wait_for_timeout(800)
        else:
            # Try via "Autres actions ▾"
            more_btn = page.locator('button:has-text("Autres actions")')
            if more_btn.count() > 0:
                more_btn.first.click()
                page.wait_for_timeout(300)
                more_rgpd = page.locator('button:has-text("Préparer la version publiable (RGPD)")')
                if more_rgpd.count() > 0:
                    more_rgpd.first.click()
                    page.wait_for_timeout(800)

        safe_screenshot(page, OUTPUT_DIR / "02_modale_anonymisation_rgpd.png")

        browser.close()
        print("\n[Audit v3.3] Captures terminées avec succès.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-only", action="store_true")
    args = parser.parse_args()

    if args.serve_only:
        serve(OUTPUT_DIR)
        return

    srv = None
    if not listening():
        print(f"Lancement du serveur sur {LOCAL_BASE}...")
        srv = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve-only"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(50):
            if listening():
                break
            time.sleep(0.2)
        else:
            print("Erreur: le serveur n'a pas répondu à temps.")
            sys.exit(1)

    try:
        run_audit_v3_3()
    finally:
        if srv:
            srv.terminate()
            try:
                srv.wait(timeout=2)
            except Exception:
                srv.kill()


if __name__ == "__main__":
    main()
