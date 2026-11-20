"""Script de capture pour l'Audit Visuel Civic Distill (Épuration Radicale).

Génère exactement 4 captures d'écran dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_CIVIC_DISTILL\\ :
1. 01_accueil_editorial_sans_boutons.png (Desktop 1920x1080: zéro carte imbriquée, zéro bouton répété, zéro gadget, zéro troncature)
2. 02_a_valider_un_seul_cta_et_progressive_disclosure.png (Desktop 1920x1080: logo rail propre, 1 seul CTA plein, zone observation masquée, édition directe, mentions juridiques exactes)
3. 03_focus_elu_papier_pur.png (Desktop 1920x1080: acte continu sans boîtes intérieures, zéro double flèche, zéro phrase filler)
4. 04_mobile_accueil_390x844_distille.png (Mobile 390x844: marges px-4, KPIs non coupés, liste aérée)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_CIVIC_DISTILL")
PORT = 19867
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
        db_path=data_dir / "civic_distill_audit.sqlite3",
        tenant_id="plougastel-civic-distill",
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


def run_audit_civic_distill():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit Civic Distill] Démarrage des 4 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # ---------------------------------------------------------------------
        # Captures 1, 2, 3: Desktop (1920x1080)
        # ---------------------------------------------------------------------
        ctx_desktop = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx_desktop.new_page()

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

        # Disable Focus Elu for Capture 1
        page.evaluate("() => { localStorage.removeItem('mayortech_focus_elu_mode'); }")

        # ---------------------------------------------------------------------
        # Capture 1: 01_accueil_editorial_sans_boutons.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 1 : Accueil éditorial sans boutons répétés ni cartes imbriquées ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(1500)
        safe_screenshot(page, OUTPUT_DIR / "01_accueil_editorial_sans_boutons.png")

        # ---------------------------------------------------------------------
        # Capture 2: 02_a_valider_un_seul_cta_et_progressive_disclosure.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 2 : À valider (1 seul CTA plein, observation masquée, logo rail propre) ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows?dossier=PC-2026-042", wait_until="networkidle")
        page.wait_for_timeout(1500)
        safe_screenshot(page, OUTPUT_DIR / "02_a_valider_un_seul_cta_et_progressive_disclosure.png")

        # ---------------------------------------------------------------------
        # Capture 3: 03_focus_elu_papier_pur.png
        # ---------------------------------------------------------------------
        print("\n--- Capture 3 : Mode Focus Élu papier pur (sans boîtes intérieures) ---")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Switch to Focus Elu
        focus_btn = page.locator('button:has-text("Focus Élu")')
        if focus_btn.count() > 0:
            focus_btn.click()
            page.wait_for_timeout(800)
        else:
            page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'true'); window.location.reload(); }")
            page.wait_for_timeout(1500)

        # Unfold first dossier accordion
        expand_btn = page.locator('button:has-text("Lire l\'acte complet")').first
        if expand_btn.count() > 0:
            expand_btn.click()
            page.wait_for_timeout(600)

        safe_screenshot(page, OUTPUT_DIR / "03_focus_elu_papier_pur.png")

        ctx_desktop.close()

        # ---------------------------------------------------------------------
        # Capture 4: Mobile (390x844)
        # ---------------------------------------------------------------------
        print("\n--- Capture 4 : Mobile 390x844 distillé ---")
        ctx_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            locale="fr-FR",
        )
        page_mobile = ctx_mobile.new_page()

        # Connect on demo space
        page_mobile.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page_mobile.wait_for_timeout(800)

        radio_prof_m = page_mobile.locator('input[name="work-profile"]')
        if radio_prof_m.count() > 0:
            radio_c1_m = page_mobile.locator('input[value="commission-1"]')
            if radio_c1_m.count() > 0:
                radio_c1_m.check()
            else:
                radio_prof_m.first.check()
            open_btn_m = page_mobile.locator('button:has-text("Ouvrir mon espace")')
            if open_btn_m.count() > 0:
                open_btn_m.click()
                page_mobile.wait_for_timeout(1000)

        page_mobile.evaluate("() => { localStorage.removeItem('mayortech_focus_elu_mode'); }")
        page_mobile.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page_mobile.wait_for_timeout(1500)

        safe_screenshot(page_mobile, OUTPUT_DIR / "04_mobile_accueil_390x844_distille.png")

        ctx_mobile.close()
        browser.close()

    print(f"\n[Audit Civic Distill] Les 4 captures ont été générées avec succès dans {OUTPUT_DIR} !")


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
        run_audit_civic_distill()
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
