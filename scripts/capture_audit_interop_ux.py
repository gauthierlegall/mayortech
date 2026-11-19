import os
import sys
import time
import socket
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PORT = 19866
LOCAL_BASE = f"http://127.0.0.1:{PORT}"
OUTPUT_DIR = Path(r"C:\Users\Utilisateur\Desktop\AUDIT_INTEROP_UX")


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
        db_path=data_dir / "interop.sqlite3",
        tenant_id="plougastel-interop",
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

    print(f"[Audit-Interop-UX] Demarrage des 6 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # -------------------------------------------------------------
        # Desktop Context (1440x900)
        # -------------------------------------------------------------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="fr-FR")
        page = ctx.new_page()

        # Connexion & choix profil
        print("Initialisation de la session...")
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_prof.first.check()
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(800)

        # -------------------------------------------------------------
        # 1. 01_hub_connecteurs_souverains.png
        # Parametres > Connecteurs & Interoperabilite
        # -------------------------------------------------------------
        print("Capture 1: 01_hub_connecteurs_souverains.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/parametres?section=connectors", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Cliquer sur l'onglet "Connecteurs & Interopérabilité" au cas où
        conn_tab = page.locator('button:has-text("Connecteurs")').first
        if conn_tab.count() > 0:
            conn_tab.click()
            page.wait_for_timeout(500)

        # Cliquer sur "Tester la connexion" sur le parapheur pastell
        pastell_card = page.locator('div:has-text("Parapheur Réglementaire")').last
        test_btn = page.locator('button:has-text("Tester la connexion")')
        if test_btn.count() > 1:
            test_btn.nth(1).click()  # Deuxième carte: Parapheur Pastell
        elif test_btn.count() > 0:
            test_btn.first.click()
        page.wait_for_timeout(1000)

        img1 = OUTPUT_DIR / "01_hub_connecteurs_souverains.png"
        safe_screenshot(page, img1)
        print(f"[1/6] {img1.name} capture.")

        # -------------------------------------------------------------
        # 2. 02_mode_parapheur_rafale.png
        # Vue "A valider" avec overlay plein ecran Mode Parapheur
        # -------------------------------------------------------------
        print("Capture 2: 02_mode_parapheur_rafale.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(800)

        val_tab = page.locator("button").filter(has_text="À valider").first
        if val_tab.count() > 0:
            val_tab.click()
            page.wait_for_timeout(500)

        parapheur_btn = page.locator('button:has-text("Mode Parapheur")').first
        if parapheur_btn.count() > 0:
            parapheur_btn.click()
            page.wait_for_timeout(600)

        img2 = OUTPUT_DIR / "02_mode_parapheur_rafale.png"
        safe_screenshot(page, img2)
        print(f"[2/6] {img2.name} capture.")

        # Fermer le mode parapheur
        close_btn = page.locator('button[title="Fermer le mode parapheur"]').first
        if close_btn.count() > 0:
            close_btn.click()
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 3. 03_lien_magique_elu_mobile.png
        # Mobile viewport 390x844
        # -------------------------------------------------------------
        print("Capture 3: 03_lien_magique_elu_mobile.png...")
        ctx_mobile = browser.new_context(viewport={"width": 390, "height": 844}, locale="fr-FR")
        page_mobile = ctx_mobile.new_page()
        page_mobile.goto(f"{LOCAL_BASE}/espace.html#/quick-sign/ARR-2026-019.demo.token", wait_until="networkidle")
        page_mobile.wait_for_timeout(1000)

        img3 = OUTPUT_DIR / "03_lien_magique_elu_mobile.png"
        safe_screenshot(page_mobile, img3)
        print(f"[3/6] {img3.name} capture.")
        page_mobile.close()
        ctx_mobile.close()

        # -------------------------------------------------------------
        # 4. 04_messagerie_vers_circuit_1clic.png
        # Messagerie avec bouton "+ Lancer une validation" et modale pre-remplie
        # -------------------------------------------------------------
        print("Capture 4: 04_messagerie_vers_circuit_1clic.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/messagerie", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Cliquer sur le premier email de la liste pour l'ouvrir
        mail_row = page.locator('[data-inbox="open"]').first
        if mail_row.count() > 0:
            mail_row.click()
            page.wait_for_timeout(600)

        # Cliquer sur "+ Lancer une validation" dans la barre d'outils du message
        launch_val_btn = page.locator('button[data-inbox="launch-validation"], button:has-text("Lancer une validation")').first
        if launch_val_btn.count() > 0:
            launch_val_btn.click()
            page.wait_for_timeout(600)

        img4 = OUTPUT_DIR / "04_messagerie_vers_circuit_1clic.png"
        safe_screenshot(page, img4)
        print(f"[4/6] {img4.name} capture.")

        # Fermer la modale si ouverte
        close_launch_btn = page.locator('button:has-text("Annuler")').first
        if close_launch_btn.count() > 0:
            close_launch_btn.click()
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 5. 05_concepteur_vue_liste_et_connecteurs.png
        # Concepteur avec Vue Liste simple active & connecteur
        # -------------------------------------------------------------
        print("Capture 5: 05_concepteur_vue_liste_et_connecteurs.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Cliquer sur l'onglet "Concepteur"
        concepteur_tab = page.locator("button").filter(has_text="Concepteur").first
        if concepteur_tab.count() > 0:
            concepteur_tab.click()
            page.wait_for_timeout(600)

        # S'assurer que "Vue Liste simple" est sélectionnée
        vue_liste_btn = page.locator('button:has-text("Vue Liste simple")').first
        if vue_liste_btn.count() > 0:
            vue_liste_btn.click()
            page.wait_for_timeout(400)

        img5 = OUTPUT_DIR / "05_concepteur_vue_liste_et_connecteurs.png"
        safe_screenshot(page, img5)
        print(f"[5/6] {img5.name} capture.")

        # -------------------------------------------------------------
        # 6. 06_delegation_absence_suppleant.png
        # Modale "Absence & Suppléant" ouverte
        # -------------------------------------------------------------
        print("Capture 6: 06_delegation_absence_suppleant.png...")
        # Ouvrir la modale d'absence depuis la sidebar
        absence_btn = page.locator('button:has-text("Absence & Suppléant")').first
        if absence_btn.count() > 0:
            absence_btn.click()
            page.wait_for_timeout(600)
            # Activer la suppléance
            toggle_chk = page.locator('input[type="checkbox"]').first
            if toggle_chk.count() > 0 and not toggle_chk.is_checked():
                toggle_chk.click(force=True)
                page.wait_for_timeout(400)

        img6 = OUTPUT_DIR / "06_delegation_absence_suppleant.png"
        safe_screenshot(page, img6)
        print(f"[6/6] {img6.name} capture.")

        browser.close()

    print("[Audit-Interop-UX] Fin des captures avec succes !")


def main():
    server_thread = None
    if not is_port_in_use():
        print(f"Demarrage du serveur FastAPI de test sur le port {PORT}...")
        server_thread = threading.Thread(target=serve, args=(ROOT / "test-interop-run",), daemon=True)
        server_thread.start()
        # Attendre que le port soit actif
        for _ in range(30):
            if is_port_in_use():
                break
            time.sleep(0.3)
    else:
        print(f"Serveur deja actif sur le port {PORT}.")

    try:
        run_captures()
    except Exception as e:
        print(f"Erreur durant les captures : {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
