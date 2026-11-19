import os
import sys
import time
import socket
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PORT = 19864
LOCAL_BASE = f"http://127.0.0.1:{PORT}"
OUTPUT_DIR = Path(r"C:\Users\Utilisateur\Desktop\AUDIT_MODULES_ONBOARDING")


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

    print(f"[Audit-Modules] Démarrage des 4 captures dans : {OUTPUT_DIR}")

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

        # -------------------------------------------------------------
        # 1. 01_wizard_creation_org_modules.png
        # Assistant de création d'organisation modulaire (Étape 2 Bento + Presets)
        # -------------------------------------------------------------
        print("Capture 1: 01_wizard_creation_org_modules.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Ouvrir le menu d'organisation puis le wizard
        org_switch = page.locator(".org-switch")
        if org_switch.count() > 0:
            org_switch.click()
            page.wait_for_timeout(400)
            btn_wizard = page.locator('button:has-text("Nouvelle organisation")')
            if btn_wizard.count() > 0:
                btn_wizard.click()
                page.wait_for_timeout(600)

        # S'assurer qu'on est sur l'étape 2 (Modules & Périmètre)
        step_2_btn = page.locator('button:has-text("Modules & Périmètre"), button:has-text("Périmètre")')
        if step_2_btn.count() > 0:
            step_2_btn.first.click()
            page.wait_for_timeout(600)

        safe_screenshot(page, OUTPUT_DIR / "01_wizard_creation_org_modules.png")
        print("  -> OK 01_wizard_creation_org_modules.png")

        # Fermer la modale du wizard
        close_btn = page.locator('button[title="Fermer"]')
        if close_btn.count() > 0:
            close_btn.first.click()
            page.wait_for_timeout(400)
        else:
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 2. 02_sidebar_mode_minimal_validation_pure.png
        # Sidebar et vue Dossiers en mode épuré (preset Circuits seuls: seuls les 3 modules socles sont actifs)
        # -------------------------------------------------------------
        print("Capture 2: 02_sidebar_mode_minimal_validation_pure.png...")
        page.evaluate('''async () => {
            await fetch('/api/v1/organizations/current/modules', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'Travaux' },
                body: JSON.stringify({ enabled_modules: ["core_directory", "core_workflows", "core_documents"] })
            });
            localStorage.setItem('mayortech_active_modules', JSON.stringify(["core_directory", "core_workflows", "core_documents"]));
        }''')
        page.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1200)

        safe_screenshot(page, OUTPUT_DIR / "02_sidebar_mode_minimal_validation_pure.png")
        print("  -> OK 02_sidebar_mode_minimal_validation_pure.png")

        # -------------------------------------------------------------
        # 3. 03_parametres_gestion_modules.png
        # Écran de configuration des modules dans Paramètres
        # -------------------------------------------------------------
        print("Capture 3: 03_parametres_gestion_modules.png...")
        page.goto(f"{LOCAL_BASE}/demo.html#/parametres", wait_until="networkidle")
        page.wait_for_timeout(800)

        # Cliquer sur l'onglet Modules & Périmètre
        tab_modules = page.locator('button:has-text("Modules & Périmètre")')
        if tab_modules.count() > 0:
            tab_modules.first.click()
            page.wait_for_timeout(800)

        safe_screenshot(page, OUTPUT_DIR / "03_parametres_gestion_modules.png")
        print("  -> OK 03_parametres_gestion_modules.png")

        # -------------------------------------------------------------
        # 4. 04_suivi_bpmn_polish_final.png
        # Living BPMN 2.0 avec étiquette Escalade SLA à x:135 et boutons 1 ligne
        # -------------------------------------------------------------
        print("Capture 4: 04_suivi_bpmn_polish_final.png...")
        # Réactiver tous les modules standards
        page.evaluate('''async () => {
            const all = ["core_directory","core_workflows","core_documents","urbanisme_ads","ports_littoral","travaux_terrain","enfance_ccas","finances_m57","conseil_seances","messagerie_eml","ai_assistant","connector_ctes","connector_eidas","mobile_alerts"];
            await fetch('/api/v1/organizations/current/modules', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'Travaux' },
                body: JSON.stringify({ enabled_modules: all })
            });
            localStorage.setItem('mayortech_active_modules', JSON.stringify(all));
        }''')
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Onglet Suivi & BPMN
        suivi_tab = page.locator("button").filter(has_text="Suivi & BPMN")
        if suivi_tab.count() > 0:
            suivi_tab.first.click()
            page.wait_for_timeout(1000)

        # Activer le Mode Démo / Simulation
        demo_btn = page.locator("button").filter(has_text="Mode démo / simulation")
        if demo_btn.count() > 0:
            demo_btn.first.click()
            page.wait_for_timeout(600)

        # Choisir le scénario Escalade SLA DGS
        sla_btn = page.locator("button").filter(has_text="Escalade SLA DGS")
        if sla_btn.count() > 0:
            sla_btn.first.click()
            page.wait_for_timeout(1200)

        safe_screenshot(page, OUTPUT_DIR / "04_suivi_bpmn_polish_final.png")
        print("  -> OK 04_suivi_bpmn_polish_final.png")

        browser.close()
        print("[Audit-Modules] Toutes les captures sont générées avec succès !")


if __name__ == "__main__":
    server_started = False
    if not is_port_in_use():
        print(f"Lancement du serveur Uvicorn sur le port {PORT}...")
        t = threading.Thread(target=serve, args=(ROOT / "temp_run",), daemon=True)
        t.start()
        server_started = True
        for _ in range(30):
            if is_port_in_use():
                break
            time.sleep(0.3)
    else:
        print(f"Serveur déjà actif sur le port {PORT}.")

    run_captures()
