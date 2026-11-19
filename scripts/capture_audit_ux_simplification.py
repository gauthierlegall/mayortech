import os
import sys
import time
import socket
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PORT = 19868
LOCAL_BASE = f"http://127.0.0.1:{PORT}"
OUTPUT_DIR = Path(r"C:\Users\Utilisateur\Desktop\AUDIT_UX_SIMPLIFICATION")


def is_port_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
        db_path=data_dir / "ux_simplification.sqlite3",
        tenant_id="plougastel-ux",
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
        log_level="error",
        access_log=False,
    )


def safe_screenshot(target_page, path: Path, full_page: bool = False):
    img_bytes = target_page.screenshot(full_page=full_page)
    for attempt in range(8):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(img_bytes)
            return
        except Exception:
            time.sleep(0.5)
    with open(path, "wb") as f:
        f.write(img_bytes)


def run_captures():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit-UX-Simplification] Démarrage des 7 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # -------------------------------------------------------------
        # Desktop Context (1920x1080)
        # -------------------------------------------------------------
        ctx_desktop = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx_desktop.new_page()

        # Initialisation session
        print("Initialisation de la session Desktop...")
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_prof.first.check()
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(800)

        # S'assurer que le mode focus est désactivé par défaut
        page.evaluate("() => { localStorage.removeItem('mayortech_focus_elu_mode'); }")

        # -------------------------------------------------------------
        # 1. 01_sidebar_epuree_desktop.png
        # Sidebar épurée avec Validations (3) en tête, Tâches & Suivi,
        # section TERRAIN & AGENDA, Responsable de pôle, et Ctrl+K dans le header
        # -------------------------------------------------------------
        print("Capture 1: 01_sidebar_epuree_desktop.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        img1 = OUTPUT_DIR / "01_sidebar_epuree_desktop.png"
        safe_screenshot(page, img1)
        print(f"[1/7] {img1.name} capturé.")

        # -------------------------------------------------------------
        # 2. 02_nav_mobile_acces_valider.png
        # Mobile viewport 390x844 avec barre de navigation basse et bouton À valider (3)
        # -------------------------------------------------------------
        print("Capture 2: 02_nav_mobile_acces_valider.png...")
        ctx_mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="fr-FR")
        page_mobile = ctx_mobile.new_page()

        page_mobile.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page_mobile.wait_for_timeout(600)
        radio_prof_m = page_mobile.locator('input[name="work-profile"]')
        if radio_prof_m.count() > 0:
            radio_prof_m.first.check()
            open_btn_m = page_mobile.locator('button:has-text("Ouvrir mon espace")')
            if open_btn_m.count() > 0:
                open_btn_m.click()
                page_mobile.wait_for_timeout(800)

        page_mobile.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page_mobile.wait_for_timeout(1000)

        img2 = OUTPUT_DIR / "02_nav_mobile_acces_valider.png"
        safe_screenshot(page_mobile, img2)
        print(f"[2/7] {img2.name} capturé.")
        ctx_mobile.close()

        # -------------------------------------------------------------
        # 3. 03_accueil_ma_journee.png
        # Dashboard Ma Journée avec salutation, 3 KPI, 65% priorités et 35% séances/raccourcis
        # -------------------------------------------------------------
        print("Capture 3: 03_accueil_ma_journee.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(1000)

        img3 = OUTPUT_DIR / "03_accueil_ma_journee.png"
        safe_screenshot(page, img3)
        print(f"[3/7] {img3.name} capturé.")

        # -------------------------------------------------------------
        # 4. 04_mode_focus_elu.png
        # Vue Simplifiée Élu : bandeau minimal et parapheur aéré
        # -------------------------------------------------------------
        print("Capture 4: 04_mode_focus_elu.png...")
        btn_focus = page.locator('button:has-text("Mode Focus Élu")').first
        if btn_focus.count() > 0:
            btn_focus.click()
            page.wait_for_timeout(800)
        else:
            page.evaluate("() => { localStorage.setItem('mayortech_focus_elu_mode', 'true'); window.location.reload(); }")
            page.wait_for_timeout(1000)

        img4 = OUTPUT_DIR / "04_mode_focus_elu.png"
        safe_screenshot(page, img4)
        print(f"[4/7] {img4.name} capturé.")

        # Quitter le mode focus
        btn_quit = page.locator('button:has-text("Quitter le mode focus"), button:has-text("vue complète")').first
        if btn_quit.count() > 0:
            btn_quit.click()
            page.wait_for_timeout(600)
        else:
            page.evaluate("() => { localStorage.removeItem('mayortech_focus_elu_mode'); window.location.reload(); }")
            page.wait_for_timeout(800)

        # -------------------------------------------------------------
        # 5. 05_palette_ctrl_k.png
        # Palette de recherche universelle Ctrl+K ouverte avec requête
        # -------------------------------------------------------------
        print("Capture 5: 05_palette_ctrl_k.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(600)

        search_btn = page.locator('button:has-text("Rechercher un dossier")').first
        if search_btn.count() > 0:
            search_btn.click()
            page.wait_for_timeout(400)
        else:
            page.keyboard.press("Control+k")
            page.wait_for_timeout(400)

        palette_input = page.locator('input[placeholder*="Rechercher"]').first
        if palette_input.count() > 0:
            palette_input.click()
            palette_input.fill("Ajoncs")
            page.wait_for_timeout(500)

        img5 = OUTPUT_DIR / "05_palette_ctrl_k.png"
        safe_screenshot(page, img5)
        print(f"[5/7] {img5.name} capturé.")

        # Fermer la palette
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 6. 06_edition_coquille_en_ligne.png
        # Édition en ligne d'une coquille dans l'acte municipal (À valider)
        # -------------------------------------------------------------
        print("Capture 6: 06_edition_coquille_en_ligne.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows?dossier=PC-2026-042", wait_until="networkidle")
        page.wait_for_timeout(1000)

        btn_coquille = page.locator('button:has-text("Corriger une coquille")').first
        if btn_coquille.count() > 0:
            btn_coquille.click()
            page.wait_for_timeout(500)

        img6 = OUTPUT_DIR / "06_edition_coquille_en_ligne.png"
        safe_screenshot(page, img6)
        print(f"[6/7] {img6.name} capturé.")

        # Fermer le mode édition pour ne pas polluer l'écran suivant
        btn_annuler = page.locator('button:has-text("Annuler")').first
        if btn_annuler.count() > 0:
            btn_annuler.click()
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 7. 07_surlignage_corrections_apres_renvoi.png
        # Dossier ARR-2026-019 avec bandeau de correction et paragraphe surligné
        # -------------------------------------------------------------
        print("Capture 7: 07_surlignage_corrections_apres_renvoi.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows?dossier=ARR-2026-019", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Vérifier si l'édition est active et l'annuler si présent
        btn_annuler_arr = page.locator('button:has-text("Annuler")').first
        if btn_annuler_arr.count() > 0:
            btn_annuler_arr.click()
            page.wait_for_timeout(400)

        # Si le bouton "Voir les modifications" est présent, cliquer dessus
        btn_voir_modifs = page.locator('button:has-text("Voir les modifications")').first
        if btn_voir_modifs.count() > 0:
            btn_voir_modifs.click()
            page.wait_for_timeout(400)

        img7 = OUTPUT_DIR / "07_surlignage_corrections_apres_renvoi.png"
        safe_screenshot(page, img7)
        print(f"[7/7] {img7.name} capturé.")

        browser.close()

    print("[Audit-UX-Simplification] Fin des 7 captures avec succès !")


def main():
    server_thread = None
    if not is_port_in_use():
        print(f"Démarrage du serveur FastAPI de test sur le port {PORT}...")
        server_thread = threading.Thread(target=serve, args=(ROOT / "test-ux-run",), daemon=True)
        server_thread.start()
        for _ in range(30):
            if is_port_in_use():
                break
            time.sleep(0.3)
    else:
        print(f"Serveur déjà actif sur le port {PORT}.")

    try:
        run_captures()
    except Exception as e:
        print(f"Erreur durant les captures : {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
