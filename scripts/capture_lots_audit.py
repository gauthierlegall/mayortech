import os
import sys
import time
import socket
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PORT = 19890
LOCAL_BASE = f"http://127.0.0.1:{PORT}"
DESKTOP_DIR = Path("C:/Users/Utilisateur/Desktop")
AUDIT_DIR = DESKTOP_DIR / "AUDIT_LOTS_A_B_C"


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
        db_path=data_dir / "lots_audit.sqlite3",
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
        log_level="error",
        access_log=False,
    )


def safe_screenshot(target_page, path: Path):
    img_bytes = target_page.screenshot(full_page=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(img_bytes)
    # Also save to Desktop directly
    with open(DESKTOP_DIR / path.name, "wb") as f:
        f.write(img_bytes)


def run_captures():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit-Lots] Démarrage des captures dans : {AUDIT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx.new_page()

        # Connexion & choix profil
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(600)
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_prof.first.check()
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(800)

        # 1. Structure & Enrôlement - Organigramme interactif
        print("Capture: 11_lot_b_structure_organigramme.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/parametres?section=structure", wait_until="networkidle")
        page.wait_for_timeout(1200)
        safe_screenshot(page, AUDIT_DIR / "11_lot_b_structure_organigramme.png")

        # 2. Structure & Enrôlement - Assistant Wizard 4 étapes
        print("Capture: 12_lot_b_wizard_enrolement.png...")
        wiz_tab = page.locator("button:visible").filter(has_text="Assistant d’Enrôlement").first
        if wiz_tab.count() > 0:
            wiz_tab.click()
            page.wait_for_timeout(800)
        safe_screenshot(page, AUDIT_DIR / "12_lot_b_wizard_enrolement.png")

        # 3. Structure & Enrôlement - Référentiel des Postes & Habilitations
        print("Capture: 13_lot_b_referentiel_postes_droits.png...")
        postes_tab = page.locator("button:visible").filter(has_text="Référentiel des Postes").first
        if postes_tab.count() > 0:
            postes_tab.click()
            page.wait_for_timeout(800)
        safe_screenshot(page, AUDIT_DIR / "13_lot_b_referentiel_postes_droits.png")

        # 4. Connecteurs & Interopérabilité Souveraine (Lot C)
        print("Capture: 14_lot_c_connecteurs_souverains.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/parametres?section=connectors", wait_until="networkidle")
        page.wait_for_timeout(1000)
        safe_screenshot(page, AUDIT_DIR / "14_lot_c_connecteurs_souverains.png")

        # 5. Modules & Périmètre Mairie (Lot B)
        print("Capture: 15_lot_b_modules_perimetre.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/parametres?section=modules", wait_until="networkidle")
        page.wait_for_timeout(1000)
        safe_screenshot(page, AUDIT_DIR / "15_lot_b_modules_perimetre.png")

        ctx.close()
        browser.close()

    print("[Audit-Lots] Captures des Lots B & C terminées avec succès !")


def main():
    server_thread = None
    if not is_port_in_use():
        print(f"Démarrage du serveur sur port {PORT}...")
        server_thread = threading.Thread(target=serve, args=(ROOT / "temp_run",), daemon=True)
        server_thread.start()
        for _ in range(30):
            if is_port_in_use():
                break
            time.sleep(0.3)
    else:
        print(f"Port {PORT} déjà actif.")

    try:
        run_captures()
    except Exception as e:
        print(f"Erreur durant les captures : {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
