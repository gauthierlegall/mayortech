"""Capture the 5 exact screenshots for the Visual Decluttering (Audit Épuration V2) pass.

Output folder: C:\\Users\\Utilisateur\\Desktop\\AUDIT_EPURATION_V2\\

1. 01_accueil_finances_epure.png
   - Desktop 1920x1080
   - Profile: 1. Fonctions supports et transitions
   - 3 piliers dans la sidebar, sous-titre commune cliquable, zéro Tâches & Suivi isolé
   - En-tête éditorial sans boîte, bande métrique fine 1 ligne, priorités sans troncature '...',
     bouton Traiter #102A4C texte blanc, zéro donnée travaux
2. 02_accueil_ccas_etanche.png
   - Desktop 1920x1080
   - Profile: 2. Action sociale, solidarités & CCAS
   - Colonne droite et activités 100% étanches CCAS (zéro Rue des Ajoncs, zéro ADS)
3. 03_a_valider_rail_et_frise_compacte.png
   - Desktop 1920x1080
   - Circuits de validation : rail automatique w-16, 2 barres max, frise horizontale 1 ligne,
     surlignage discret, panneau droit à 2 actions + dropdown, zéro bleu #2563EB
4. 04_focus_elu_editorial_depliable.png
   - Desktop 1920x1080
   - Mode Focus Élu : zéro carte KPI, zéro grande boîte englobante, zéro triple bordure,
     zéro méta-badge, compteur synchronisé, 1 dossier déplié avec visas et sceau eIDAS
5. 05_mobile_accueil_390x844.png
   - Mobile 390x844 (iPhone 14/15)
   - 3 KPIs 1 ligne, priorités immédiatement visibles above the fold, bouton Traiter blanc lisible,
     pastille badge barre basse '2' synchronisée, zéro FAB flottant
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_EPURATION_V2")
PORT = 19862
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
        tenant_id="plougastel-audit-v2",
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


def run_epuration_audit_v2():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit-Épuration V2] Démarrage des 5 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # =============================================================
        # Context 1: Desktop (1920x1080)
        # =============================================================
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx.new_page()

        # Connect and select initial profile
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Select Commission 1 (Fonctions supports et transitions)
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

        # Navigate to home
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Switch to commission-1 via the sidebar select to guarantee profile
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
        print("[01 Contrast Traiter Buttons]:", contrast_check)

        img1 = OUTPUT_DIR / "01_accueil_finances_epure.png"
        safe_screenshot(page, img1)

        # -------------------------------------------------------------
        # 2. 02_accueil_ccas_etanche.png
        # -------------------------------------------------------------
        commission_select = page.locator("#sidebar-commission-select")
        if commission_select.count() > 0:
            commission_select.select_option("commission-2")
            page.wait_for_timeout(1000)

        # Verify Commission 2 content
        img2 = OUTPUT_DIR / "02_accueil_ccas_etanche.png"
        safe_screenshot(page, img2)

        # -------------------------------------------------------------
        # 3. 03_a_valider_rail_et_frise_compacte.png
        # -------------------------------------------------------------
        # Switch to commission-3 (Travaux) to see the rich workflow with frise and multiple steps
        commission_select = page.locator("#sidebar-commission-select")
        if commission_select.count() > 0:
            commission_select.select_option("commission-3")
            page.wait_for_timeout(800)

        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(1200)

        # Check that rail is active or auto-collapsed
        rail_class = page.evaluate("() => document.querySelector('.workspace')?.classList.contains('nav-rail')")
        print("[03 Rail class active]:", rail_class)

        # Ensure "À valider" tab is active
        val_tab = page.locator("button:visible:has-text('À valider')")
        if val_tab.count() > 0:
            val_tab.first.click()
            page.wait_for_timeout(800)

        # Verify floating FAB count is 0
        fab_count = page.locator(".assistant-launcher:visible").count()
        print(f"[03 Floating FAB count]: {fab_count} (Must be 0)")

        img3 = OUTPUT_DIR / "03_a_valider_rail_et_frise_compacte.png"
        safe_screenshot(page, img3)

        # -------------------------------------------------------------
        # 4. 04_focus_elu_editorial_depliable.png
        # -------------------------------------------------------------
        # Enable Focus Élu mode
        focus_btn = page.locator("button:visible:has-text('Focus Élu')")
        if focus_btn.count() > 0:
            focus_btn.first.click()
            page.wait_for_timeout(800)
        else:
            page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'true'); window.dispatchEvent(new CustomEvent('mayortech:focus-elu-changed', {detail: {active: true}})); }")
            page.wait_for_timeout(800)

        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Ensure first dossier is expanded or click 'Lire l'acte complet ▾'
        expand_btn = page.locator("button:visible:has-text(\"Lire l'acte complet\")")
        if expand_btn.count() > 0:
            expand_btn.first.click()
            page.wait_for_timeout(600)

        img4 = OUTPUT_DIR / "04_focus_elu_editorial_depliable.png"
        safe_screenshot(page, img4)

        # Exit focus mode
        page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'false'); }")
        ctx.close()

        # =============================================================
        # Context 2: Mobile (390x844 - iPhone 14/15)
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

        # Ensure commission-1 is active via localStorage and page reload
        mobile_page.evaluate("() => { localStorage.setItem('mayortech_active_commission', 'commission-1'); }")
        mobile_page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        mobile_page.wait_for_timeout(1000)

        img5 = OUTPUT_DIR / "05_mobile_accueil_390x844.png"
        safe_screenshot(mobile_page, img5)

        mobile_ctx.close()
        browser.close()

    print("[Audit-Épuration V2] Les 5 captures ont été générées avec succès dans :", OUTPUT_DIR)


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
        run_epuration_audit_v2()
    finally:
        if server_process:
            server_process.terminate()


if __name__ == "__main__":
    main()
