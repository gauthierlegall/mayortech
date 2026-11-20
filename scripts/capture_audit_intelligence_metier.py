"""Script de capture et vérification pour l'Audit Visuel du LOT :
Intelligence Juridique & Productivité Invisible sur MayorTech.

Génère les 6 captures dans C:\\Users\\Utilisateur\\Desktop\\AUDIT_INTELLIGENCE_METIER\\ :
1. 01_modele_acte_variables_et_seuil_delegation.png
   - Modale "+ Nouvelle validation" avec choix gabarit Marché Public, variables, alerte seuil > 10 000 € HT et aperçu Source Serif 4.
2. 02_messagerie_transformer_en_circuit.png
   - Messagerie avec le bouton sobre "Transformer en circuit" dans l'en-tête du courriel sélectionné.
3. 03_a_valider_delai_suspendu_et_menu_preuve_zip.png
   - Vue "À valider" avec badge de délai suspendu/décision tacite et menu "Autres actions ▾" ouvert affichant "Télécharger le dossier de preuve (.zip)".
4. 04_modale_raccourcis_clavier.png
   - Modale des raccourcis clavier (J/K navigation, V validation, R renvoi, P pièces, ? aide).
5. 05_registre_public_actes_et_qrcode.png
   - Page autonome /registre-public avec acte certifié et QR code vectoriel souverain d'authenticité.
6. 06_espace_elu_suppleance_signature.png
   - Espace Élu natif en mode suppléance active, avec mention légale de substitution dans le bloc signature officiel de l'acte déplié.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_INTELLIGENCE_METIER")
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
        db_path=data_dir / "intelligence_audit.sqlite3",
        tenant_id="plougastel-intelligence",
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


def safe_screenshot(page, path: Path, full_page: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    img_bytes = page.screenshot(full_page=full_page)
    with open(path, "wb") as f:
        f.write(img_bytes)
    print(f"Captured: {path.name} -> {path}")


def ensure_logged_in(page):
    try:
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
                page.wait_for_timeout(800)
    except Exception as e:
        print(f"Login notice: {e}")


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
        print(f"Starting server on port {PORT}...")
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
            # CAPTURE 1: Modèle d'acte à variables & Seuil de délégation
            # -------------------------------------------------------------
            ctx1 = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page1 = ctx1.new_page()
            page1.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle", timeout=30000)
            page1.wait_for_timeout(800)
            ensure_logged_in(page1)

            page1.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
            page1.wait_for_timeout(1000)

            # Click "+ Nouvelle validation"
            new_val_btn = page1.locator('button:has-text("Nouvelle validation")')
            if new_val_btn.count() > 0:
                new_val_btn.click()
                page1.wait_for_timeout(600)

                # Select "Marché Public" model button
                marche_btn = page1.locator('button:has-text("Marché Public")')
                if marche_btn.count() > 0:
                    marche_btn.click()
                    page1.wait_for_timeout(400)

                # Wait for threshold warning notice
                page1.wait_for_selector('text=Escalade automatique vers le Maire requise', timeout=5000)
                page1.wait_for_timeout(600)

                safe_screenshot(page1, OUTPUT_DIR / "01_modele_acte_variables_et_seuil_delegation.png")
            ctx1.close()

            # -------------------------------------------------------------
            # CAPTURE 2: Messagerie avec "Transformer en circuit"
            # -------------------------------------------------------------
            ctx2 = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page2 = ctx2.new_page()
            page2.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page2.wait_for_timeout(600)
            ensure_logged_in(page2)

            page2.goto(f"{LOCAL_BASE}/demo.html#/mail", wait_until="networkidle")
            page2.wait_for_timeout(1200)

            # Click first message if list has items
            msg_item = page2.locator('button[data-inbox="open"], .mail-item, tr[data-mail-id], .mail-row').first
            if msg_item.count() > 0:
                msg_item.click()
                page2.wait_for_timeout(800)

            # Verify "Transformer en circuit" button is visible
            page2.wait_for_selector('button:has-text("Transformer en circuit"), button[data-inbox="launch-validation"]', timeout=5000)
            page2.wait_for_timeout(400)
            safe_screenshot(page2, OUTPUT_DIR / "02_messagerie_transformer_en_circuit.png")
            ctx2.close()

            # -------------------------------------------------------------
            # CAPTURE 3: À valider (Délai suspendu & Menu Preuve ZIP)
            # -------------------------------------------------------------
            ctx3 = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page3 = ctx3.new_page()
            page3.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page3.wait_for_timeout(600)
            ensure_logged_in(page3)

            page3.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
            page3.wait_for_timeout(1000)

            # Select a dossier with suspended deadline or standard dossier
            dossier_card = page3.locator('text=ARR-2026-089').first
            if dossier_card.count() > 0:
                dossier_card.click()
                page3.wait_for_timeout(600)

            # Open "Autres actions ▾"
            more_actions_btn = page3.locator('button:has-text("Autres actions")')
            if more_actions_btn.count() > 0:
                more_actions_btn.click()
                page3.wait_for_timeout(500)

            # Verify "Télécharger le dossier de preuve (.zip)" is visible in dropdown
            page3.wait_for_selector('text=Télécharger le dossier de preuve (.zip)', timeout=5000)
            safe_screenshot(page3, OUTPUT_DIR / "03_a_valider_delai_suspendu_et_menu_preuve_zip.png")
            ctx3.close()

            # -------------------------------------------------------------
            # CAPTURE 4: Modale Raccourcis Clavier (?)
            # -------------------------------------------------------------
            ctx4 = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page4 = ctx4.new_page()
            page4.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page4.wait_for_timeout(600)
            ensure_logged_in(page4)

            page4.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
            page4.wait_for_timeout(1000)

            # Click "Raccourcis : ?" footer button or press ?
            shortcut_btn = page4.locator('button:has-text("Raccourcis : ?")')
            if shortcut_btn.count() > 0:
                shortcut_btn.click()
            else:
                page4.keyboard.press("?")
            page4.wait_for_timeout(600)

            # Wait for modal title
            page4.wait_for_selector('text=Raccourcis Clavier', timeout=5000)
            safe_screenshot(page4, OUTPUT_DIR / "04_modale_raccourcis_clavier.png")
            ctx4.close()

            # -------------------------------------------------------------
            # CAPTURE 5: Registre Public des Actes & QR Code Souverain
            # -------------------------------------------------------------
            ctx5 = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page5 = ctx5.new_page()
            page5.goto(f"{LOCAL_BASE}/demo.html#/registre-public", wait_until="networkidle")
            page5.wait_for_timeout(1000)

            # Click on act ARR-2026-019
            act_link = page5.locator('text=ARR-2026-019').first
            if act_link.count() > 0:
                act_link.click()
                page5.wait_for_timeout(800)

            # Verify official act display with vector QR code
            page5.wait_for_selector('text=RÉPUBLIQUE FRANÇAISE', timeout=5000)
            page5.wait_for_selector('text=Affichage légal vérifié', timeout=5000)
            safe_screenshot(page5, OUTPUT_DIR / "05_registre_public_actes_et_qrcode.png")
            ctx5.close()

            # -------------------------------------------------------------
            # CAPTURE 6: Espace Élu Natif avec Suppléance Active & Signature
            # -------------------------------------------------------------
            ctx6 = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page6 = ctx6.new_page()

            # Setup delegation active in localStorage before navigation
            page6.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page6.evaluate("""
                localStorage.setItem('mayortech_absence_delegation', JSON.stringify({
                    active: true,
                    delegate: 'Loïc KERBRAT · 1er Adjoint (Travaux & Voirie)'
                }));
            """)
            page6.wait_for_timeout(300)

            # Switch to elu-maire profile
            sidebar_sel = page6.locator("#sidebar-commission-select")
            if sidebar_sel.count() > 0:
                sidebar_sel.select_option("elu-maire")
                page6.wait_for_timeout(1000)
            else:
                radio_elu = page6.locator('input[value="elu-maire"]')
                if radio_elu.count() > 0:
                    radio_elu.check()
                    page6.locator('button:has-text("Ouvrir mon espace")').click()
                    page6.wait_for_timeout(1000)

            page6.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
            page6.wait_for_timeout(1000)

            # Expand act MP-2026-008 if needed
            examine_btn = page6.locator('button:has-text("Examiner & Viser l\'acte")').first
            if examine_btn.count() > 0:
                examine_btn.click()
                page6.wait_for_timeout(600)

            # Ensure substitution mention is rendered
            page6.wait_for_selector('text=Pour le Maire empêché et par délégation', timeout=5000)
            safe_screenshot(page6, OUTPUT_DIR / "06_espace_elu_suppleance_signature.png")
            ctx6.close()

            browser.close()

        print("\nAll 6 captures successfully generated in:", OUTPUT_DIR)

    finally:
        if server:
            server.terminate()


if __name__ == "__main__":
    main()
