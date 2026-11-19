import os
import sys
import time
import socket
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PORT = 19872
LOCAL_BASE = f"http://127.0.0.1:{PORT}"
OUTPUT_DIR = Path(r"C:\Users\Utilisateur\Desktop\AUDIT_CIVIC_CRAFT_METIER")


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
        db_path=data_dir / "civic_craft.sqlite3",
        tenant_id="plougastel-civic",
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

    print(f"[Audit-Civic-Craft] Démarrage des 6 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # -------------------------------------------------------------
        # Desktop Context (1440x900)
        # -------------------------------------------------------------
        ctx_desktop = browser.new_context(viewport={"width": 1440, "height": 900}, locale="fr-FR")
        page = ctx_desktop.new_page()

        # Initialisation session
        print("Initialisation de la session Desktop...")
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(800)
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_prof.first.check()
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(1000)

        # Désactiver mode focus au départ
        page.evaluate("() => { localStorage.removeItem('mayortech_focus_elu_mode'); }")

        # -------------------------------------------------------------
        # 1. 01_commission_finances_civic_craft.png
        # Commission 1 (Valérie Gourmelon - Finances)
        # -------------------------------------------------------------
        print("Capture 1: 01_commission_finances_civic_craft.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(600)
        
        # Basculer vers Commission 1
        select_elem = page.locator("#sidebar-commission-select")
        if select_elem.count() > 0:
            select_elem.select_option("commission-1")
            page.wait_for_timeout(1200)

        img1 = OUTPUT_DIR / "01_commission_finances_civic_craft.png"
        safe_screenshot(page, img1)
        print(f"[1/6] {img1.name} capturé.")

        # -------------------------------------------------------------
        # 2. 02_commission_travaux_avec_chantiers.png
        # Commission 3 (Loïc Kermarrec - Urbanisme, Travaux & Ports)
        # -------------------------------------------------------------
        print("Capture 2: 02_commission_travaux_avec_chantiers.png...")
        if select_elem.count() > 0:
            select_elem.select_option("commission-3")
            page.wait_for_timeout(1200)

        img2 = OUTPUT_DIR / "02_commission_travaux_avec_chantiers.png"
        safe_screenshot(page, img2)
        print(f"[2/6] {img2.name} capturé.")

        # -------------------------------------------------------------
        # 3. 03_commission_social_ccas_cloisonne.png
        # Commission 2 (Nolwenn Prigent - Action Sociale & CCAS)
        # -------------------------------------------------------------
        print("Capture 3: 03_commission_social_ccas_cloisonne.png...")
        if select_elem.count() > 0:
            select_elem.select_option("commission-2")
            page.wait_for_timeout(1200)

        img3 = OUTPUT_DIR / "03_commission_social_ccas_cloisonne.png"
        safe_screenshot(page, img3)
        print(f"[3/6] {img3.name} capturé.")

        # -------------------------------------------------------------
        # 4. 04_a_valider_acte_editorial_et_panneau_dynamique.png
        # Validation d'un arrêté (ARR-2026-019) avec panneau CTM dynamique
        # et acte officiel au rendu papier vélin avec filet tricolore et tampon
        # -------------------------------------------------------------
        print("Capture 4: 04_a_valider_acte_editorial_et_panneau_dynamique.png...")
        # Rebasculer en commission-3 pour voir ARR-2026-019
        if select_elem.count() > 0:
            select_elem.select_option("commission-3")
            page.wait_for_timeout(800)
        
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows?dossier=ARR-2026-019", wait_until="networkidle")
        page.wait_for_timeout(1500)

        img4 = OUTPUT_DIR / "04_a_valider_acte_editorial_et_panneau_dynamique.png"
        safe_screenshot(page, img4)
        print(f"[4/6] {img4.name} capturé.")

        # -------------------------------------------------------------
        # 5. 05_mode_focus_elu_sans_doublons.png
        # Mode Focus Élu activé, sans doublons d'onglets ni de boutons
        # -------------------------------------------------------------
        print("Capture 5: 05_mode_focus_elu_sans_doublons.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/today?focus=1", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.evaluate("""() => {
            localStorage.setItem('mayortech_focus_elu_mode', 'true');
            window.dispatchEvent(new CustomEvent('mayortech:focus-elu-changed', { detail: { active: true } }));
        }""")
        page.wait_for_timeout(1000)

        img5 = OUTPUT_DIR / "05_mode_focus_elu_sans_doublons.png"
        safe_screenshot(page, img5)
        print(f"[5/6] {img5.name} capturé.")

        # Fermer le contexte Desktop
        ctx_desktop.close()

        # -------------------------------------------------------------
        # 6. 06_mobile_accueil_390x844.png
        # Mobile Context (390x844) iPhone style
        # -------------------------------------------------------------
        print("Capture 6: 06_mobile_accueil_390x844.png...")
        ctx_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            locale="fr-FR"
        )
        page_mobile = ctx_mobile.new_page()

        # Initialisation session mobile
        page_mobile.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page_mobile.wait_for_timeout(600)
        radio_prof_m = page_mobile.locator('input[name="work-profile"]')
        if radio_prof_m.count() > 0:
            radio_prof_m.first.check()
            open_btn_m = page_mobile.locator('button:has-text("Ouvrir mon espace")')
            if open_btn_m.count() > 0:
                open_btn_m.click()
                page_mobile.wait_for_timeout(1000)

        # S'assurer que le focus mode est off
        page_mobile.evaluate("() => { localStorage.removeItem('mayortech_focus_elu_mode'); }")
        page_mobile.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page_mobile.wait_for_timeout(1500)

        img6 = OUTPUT_DIR / "06_mobile_accueil_390x844.png"
        safe_screenshot(page_mobile, img6)
        print(f"[6/6] {img6.name} capturé.")

        ctx_mobile.close()
        browser.close()

    print("[Audit-Civic-Craft] Fin des 6 captures avec succès !")


def main():
    server_thread = None
    if not is_port_in_use():
        print(f"Démarrage du serveur FastAPI de test sur le port {PORT}...")
        server_thread = threading.Thread(target=serve, args=(ROOT / "test-civic-run",), daemon=True)
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
