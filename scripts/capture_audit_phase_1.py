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
OUTPUT_DIR = Path(r"C:\Users\Utilisateur\Desktop\AUDIT_PHASE_1")


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


def run_phase_1_captures():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit-Phase-1] Démarrage des 7 captures dans : {OUTPUT_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # -------------------------------------------------------------
        # Desktop Context (1920x1080)
        # -------------------------------------------------------------
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

        # Navigation vers Workflows / Circuits de validation
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # -------------------------------------------------------------
        # 1. 01_a_valider_historique_visas.png
        # -------------------------------------------------------------
        val_tab = page.locator("button").filter(has_text="À valider")
        if val_tab.count() > 0:
            val_tab.first.click()
            page.wait_for_timeout(800)

        # Scroll to ensure Historique des visas & empreintes is nicely visible
        history_block = page.locator("text=Historique des visas")
        if history_block.count() > 0:
            history_block.first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)

        img1 = OUTPUT_DIR / "01_a_valider_historique_visas.png"
        safe_screenshot(page, img1)
        print(f"[1/7] {img1.name} capturé.")

        # -------------------------------------------------------------
        # 2. 02_suivi_bpmn_nominal_propre.png
        # (Onglet Suivi & BPMN par défaut, mode démo masqué, AND CTM/ABF)
        # -------------------------------------------------------------
        suivi_tab = page.locator("button").filter(has_text="Suivi & BPMN")
        if suivi_tab.count() > 0:
            suivi_tab.first.click()
            page.wait_for_timeout(1000)

        img2 = OUTPUT_DIR / "02_suivi_bpmn_nominal_propre.png"
        safe_screenshot(page, img2)
        print(f"[2/7] {img2.name} capturé.")

        # -------------------------------------------------------------
        # 3. 03_suivi_bpmn_tiroir_sans_doublon.png
        # (Clic sur le nœud Vérification Complétude pour ouvrir le tiroir)
        # -------------------------------------------------------------
        completude_node = page.locator("[data-node-id='completude'], [data-testid='bpmn-task-completude']").first
        if completude_node.count() > 0:
            completude_node.click()
            page.wait_for_timeout(600)

        img3 = OUTPUT_DIR / "03_suivi_bpmn_tiroir_sans_doublon.png"
        safe_screenshot(page, img3)
        print(f"[3/7] {img3.name} capturé.")

        # Fermer le tiroir
        close_drawer = page.locator("button[title='Fermer'], button:has-text('Fermer l\\'inspecteur')").first
        if close_drawer.count() > 0:
            close_drawer.click()
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 4. 04_suivi_bpmn_pieces_manquantes_ambre.png
        # (Activer Mode démo, sélectionner 'Pièces Manquantes', pas à pas)
        # -------------------------------------------------------------
        demo_btn = page.locator("button:has-text('Mode démo / simulation')").first
        if demo_btn.count() > 0:
            demo_btn.click()
            page.wait_for_timeout(500)

        missing_scenario = page.locator("button:has-text('Pièces Manquantes')").first
        if missing_scenario.count() > 0:
            missing_scenario.click()
            page.wait_for_timeout(500)

        step_btn = page.locator("button:has-text('Pas à pas')").first
        if step_btn.count() > 0:
            step_btn.click()
            page.wait_for_timeout(300)
            step_btn.click()
            page.wait_for_timeout(300)
            step_btn.click()
            page.wait_for_timeout(300)

        img4 = OUTPUT_DIR / "04_suivi_bpmn_pieces_manquantes_ambre.png"
        safe_screenshot(page, img4)
        print(f"[4/7] {img4.name} capturé.")

        # -------------------------------------------------------------
        # 5. 05_suivi_bpmn_escalade_sla_sans_croisement.png
        # (Scénario 'Escalade SLA DGS', rail gauche sans croisement CTM/ABF)
        # -------------------------------------------------------------
        escalade_scenario = page.locator("button:has-text('Escalade SLA DGS'), button:has-text('Escalade SLA')").first
        if escalade_scenario.count() > 0:
            escalade_scenario.click()
            page.wait_for_timeout(500)

        if step_btn.count() > 0:
            step_btn.click()
            page.wait_for_timeout(300)
            step_btn.click()
            page.wait_for_timeout(300)

        img5 = OUTPUT_DIR / "05_suivi_bpmn_escalade_sla_sans_croisement.png"
        safe_screenshot(page, img5)
        print(f"[5/7] {img5.name} capturé.")

        # -------------------------------------------------------------
        # 6. 06_concepteur_textarea_et_palette.png
        # (Onglet Concepteur avec React Flow, textarea 2 lignes, mini palette)
        # -------------------------------------------------------------
        concepteur_tab = page.locator("button").filter(has_text="Concepteur")
        if concepteur_tab.count() > 0:
            concepteur_tab.first.click()
            page.wait_for_timeout(1000)

        preset_btn = page.locator("button:has-text('Permis de Construire (ADS & ABF 15j)'), button:has-text('Générer le circuit')").first
        if preset_btn.count() > 0:
            preset_btn.click()
            page.wait_for_timeout(1000)

        img6 = OUTPUT_DIR / "06_concepteur_textarea_et_palette.png"
        safe_screenshot(page, img6)
        print(f"[6/7] {img6.name} capturé.")

        ctx.close()

        # -------------------------------------------------------------
        # 7. 07_mobile_390x844_compact.png
        # (Mobile 390x844 : select 1 ligne, timeline visible, pas de bouton vert doublon)
        # -------------------------------------------------------------
        ctx_m = browser.new_context(viewport={"width": 390, "height": 844}, locale="fr-FR", is_mobile=True)
        page_m = ctx_m.new_page()

        page_m.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page_m.wait_for_timeout(600)
        radio_m = page_m.locator('input[name="work-profile"]')
        if radio_m.count() > 0:
            radio_m.first.check()
            open_btn_m = page_m.locator('button:has-text("Ouvrir mon espace")')
            if open_btn_m.count() > 0:
                open_btn_m.click()
                page_m.wait_for_timeout(800)

        page_m.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page_m.wait_for_timeout(1000)

        suivi_tab_m = page_m.locator("button").filter(has_text="Suivi & BPMN")
        if suivi_tab_m.count() > 0:
            suivi_tab_m.first.click()
            page_m.wait_for_timeout(800)

        img7 = OUTPUT_DIR / "07_mobile_390x844_compact.png"
        safe_screenshot(page_m, img7)
        print(f"[7/7] {img7.name} capturé.")

        ctx_m.close()
        browser.close()

    print(f"\n[Succès] Les 7 captures de la Phase 1 ont été enregistrées avec succès dans : {OUTPUT_DIR}")


def main():
    server_thread = None
    if not is_port_in_use():
        print(f"Lancement du serveur temporaire sur port {PORT}...")
        tmp_dir = ROOT / ".agent" / "tmp" / "phase1_captures"
        server_thread = threading.Thread(target=serve, args=(tmp_dir,), daemon=True)
        server_thread.start()
        for _ in range(30):
            if is_port_in_use():
                break
            time.sleep(0.3)
        time.sleep(1.0)
    else:
        print(f"Serveur local déjà actif sur port {PORT}")

    try:
        run_phase_1_captures()
    finally:
        pass


if __name__ == "__main__":
    main()
