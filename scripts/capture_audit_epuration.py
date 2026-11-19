"""Capture the 4 audit screenshots for the Visual Decluttering (Audit Épuration) pass.

Output folder: C:\\Users\\Utilisateur\\Desktop\\AUDIT_EPURATION\\

1. 01_accueil_finances_epure.png
   - Desktop 1920x1080
   - Profile: 1. Fonctions supports et transitions
   - Sidebar aérée non coupée, bande métrique fine 1 ligne, 1 seul bouton Traiter blanc lisible, zéro donnée Travaux
2. 02_a_valider_compact.png
   - Desktop 1920x1080
   - Circuits de validation : 2 barres max, zéro #2563EB, panneau droit à 2 actions + menu, zéro FAB flottant
3. 03_focus_elu_minimal.png
   - Desktop 1920x1080
   - Mode Focus Élu : zéro carte KPI, salut compact, compteur synchronisé
4. 04_mobile_accueil_epure.png
   - Mobile 390x844
   - Bouton Traiter pleine largeur blanc lisible, compteur synchronisé, zéro superposition
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_EPURATION")
PORT = 19860
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
        db_path=data_dir / "gallery.sqlite3",
        tenant_id="plougastel-audit",
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
    print(f"Captured: {path.name}")


def run_epuration_audit():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit-Épuration] Démarrage des 4 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # =============================================================
        # 1. Desktop Context (1920x1080)
        # =============================================================
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx.new_page()

        # Connect and select initial profile
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Select Commission 1 (Fonctions supports et transitions)
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            # Look for commission-1 radio or click first
            radio_c1 = page.locator('input[value="commission-1"]')
            if radio_c1.count() > 0:
                radio_c1.check()
            else:
                radio_prof.first.check()
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(1000)

        # Switch to commission-1 via the sidebar select if not already active
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(800)

        commission_select = page.locator("#sidebar-commission-select")
        if commission_select.count() > 0:
            commission_select.select_option("commission-1")
            page.wait_for_timeout(800)

        # Reset any leftover focus mode in localStorage
        page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'false'); }")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # -------------------------------------------------------------
        # 1. 01_accueil_finances_epure.png
        # -------------------------------------------------------------
        # Contrast & styling assertions on the Traiter buttons
        contrast_check = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('a, button')).filter(el => {
                const text = el.textContent || '';
                return text.includes('Traiter');
            });
            return btns.map(b => {
                const cs = window.getComputedStyle(b);
                const span = b.querySelector('span') || b;
                const spanCs = window.getComputedStyle(span);
                return {
                    text: b.textContent.trim(),
                    bg: cs.backgroundColor,
                    color: cs.color,
                    spanColor: spanCs.color
                };
            });
        }""")
        print("[Visual-QA Check Contrast Traiter Buttons]:", contrast_check)

        img1 = OUTPUT_DIR / "01_accueil_finances_epure.png"
        safe_screenshot(page, img1)

        # -------------------------------------------------------------
        # 2. 02_a_valider_compact.png
        # -------------------------------------------------------------
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(1200)

        # Ensure "À valider" tab is active
        val_tab = page.locator("button:visible:has-text('À valider')")
        if val_tab.count() > 0:
            val_tab.first.click()
            page.wait_for_timeout(800)

        # Verify no floating assistant FAB is visible
        fab_count = page.locator(".assistant-launcher:visible").count()
        print(f"[Visual-QA Check Floating FAB count]: {fab_count} (Must be 0)")

        img2 = OUTPUT_DIR / "02_a_valider_compact.png"
        safe_screenshot(page, img2)

        # -------------------------------------------------------------
        # 3. 03_focus_elu_minimal.png
        # -------------------------------------------------------------
        # Enable Focus Élu mode
        focus_btn = page.locator("button:visible:has-text('Focus Élu')")
        if focus_btn.count() > 0:
            focus_btn.first.click()
            page.wait_for_timeout(800)
        else:
            page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'true'); window.dispatchEvent(new CustomEvent('mayortech:focus-elu-changed', {detail: {active: true}})); }")
            page.wait_for_timeout(800)

        # Navigate to home in focus mode
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        img3 = OUTPUT_DIR / "03_focus_elu_minimal.png"
        safe_screenshot(page, img3)

        # Exit focus mode
        page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'false'); }")
        ctx.close()

        # =============================================================
        # 4. Mobile Context (390x844 - iPhone 14/15)
        # =============================================================
        mobile_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="fr-FR",
            is_mobile=True,
            has_touch=True,
        )
        mobile_page = mobile_ctx.newPage() if hasattr(mobile_ctx, "newPage") else mobile_ctx.new_page()

        mobile_page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        mobile_page.wait_for_timeout(1000)

        # Check radio commission-1 and click Ouvrir mon espace if on selection screen
        radio_prof = mobile_page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_c1 = mobile_page.locator('input[value="commission-1"]')
            if radio_c1.count() > 0:
                radio_c1.check()
            else:
                radio_prof.first.check()
            open_btn = mobile_page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                mobile_page.wait_for_timeout(1200)

        mobile_page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        mobile_page.wait_for_timeout(1000)

        img4 = OUTPUT_DIR / "04_mobile_accueil_epure.png"
        safe_screenshot(mobile_page, img4)

        mobile_ctx.close()
        browser.close()

    print("[Audit-Épuration] Toutes les 4 captures sont enregistrées avec succès !")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-only", action="store_true")
    args = parser.parse_args()

    if args.serve_only:
        serve(OUTPUT_DIR)
        return

    server_process = None
    if not listening():
        print(f"Starting background server on port {PORT}...")
        server_process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve-only"],
            cwd=str(ROOT),
        )
        for _ in range(50):
            if listening():
                break
            time.sleep(0.2)
        if not listening():
            raise RuntimeError("Le serveur uvicorn n'a pas pu démarrer.")

    try:
        run_epuration_audit()
    finally:
        if server_process:
            server_process.terminate()


if __name__ == "__main__":
    main()
