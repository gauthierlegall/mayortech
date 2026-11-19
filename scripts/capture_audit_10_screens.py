"""Capture the 10 precise audit screenshots for MayorTech Circuits de validation.

Output folder: C:\\Users\\Utilisateur\\Desktop\\AUDIT_10_SCREENS\\

1. 01_onglet_a_valider_split_view.png
2. 02_modale_renvoyer_etape.png
3. 03_modale_lancer_validation.png
4. 04_suivi_bpmn_vue_metier.png
5. 05_suivi_bpmn_tiroir_actionnable.png
6. 06_suivi_bpmn_pieces_manquantes.png
7. 07_suivi_bpmn_rejet_plu.png
8. 08_suivi_bpmn_escalade_sla.png
9. 09_onglet_concepteur_prompt_ia.png
10. 10_mobile_390x844_terrain.png
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
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/AUDIT_10_SCREENS")
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
        access_log=False,
        log_level="warning",
    )


DESKTOP_DIR = Path("C:/Users/Utilisateur/Desktop")


def safe_screenshot(target_page, path: Path, full_page: bool = False):
    img_bytes = target_page.screenshot(full_page=full_page)
    for attempt in range(8):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(img_bytes)
            # Also save directly on Desktop
            desktop_target = DESKTOP_DIR / path.name
            with open(desktop_target, "wb") as f:
                f.write(img_bytes)
            return
        except Exception:
            time.sleep(0.5)
    with open(path, "wb") as f:
        f.write(img_bytes)
    with open(DESKTOP_DIR / path.name, "wb") as f:
        f.write(img_bytes)


def run_10_captures():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Audit-10] Demarrage des 10 captures dans : {OUTPUT_DIR}")

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
        # 1. 01_onglet_a_valider_split_view.png
        # -------------------------------------------------------------
        val_tab = page.locator("button").filter(has_text="À valider")
        if val_tab.count() > 0:
            val_tab.first.click()
            page.wait_for_timeout(800)

        img1 = OUTPUT_DIR / "01_onglet_a_valider_split_view.png"
        safe_screenshot(page, img1)
        print(f"[1/10] {img1.name} capture.")

        # -------------------------------------------------------------
        # 2. 02_modale_renvoyer_etape.png
        # -------------------------------------------------------------
        rollback_btn = page.locator("button:has-text('Renvoyer à une étape amont'), button:has-text('Renvoyer')").first
        if rollback_btn.count() > 0:
            rollback_btn.click()
            page.wait_for_timeout(600)

        img2 = OUTPUT_DIR / "02_modale_renvoyer_etape.png"
        safe_screenshot(page, img2)
        print(f"[2/10] {img2.name} capture.")

        # Fermer la modale de renvoi
        close_modal = page.locator("button:has-text('Annuler'), button[aria-label='Fermer']").first
        if close_modal.count() > 0:
            close_modal.click()
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 3. 03_modale_lancer_validation.png
        # -------------------------------------------------------------
        launch_btn = page.locator("button:has-text('Lancer une validation')").first
        if launch_btn.count() > 0:
            launch_btn.click()
            page.wait_for_timeout(600)

        img3 = OUTPUT_DIR / "03_modale_lancer_validation.png"
        safe_screenshot(page, img3)
        print(f"[3/10] {img3.name} capture.")

        # Fermer la modale de lancement
        close_launch = page.locator("button:has-text('Annuler'), button[title='Fermer']").first
        if close_launch.count() > 0:
            close_launch.click()
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 4. 04_suivi_bpmn_vue_metier.png
        # (Onglet Suivi du circuit par defaut, mode demo masque, AND CTM/ABF)
        # -------------------------------------------------------------
        suivi_tab = page.locator("button").filter(has_text="Suivi").first
        if suivi_tab.count() > 0:
            suivi_tab.click()
            page.wait_for_timeout(1200)

        img4 = OUTPUT_DIR / "04_suivi_bpmn_vue_metier.png"
        safe_screenshot(page, img4)
        print(f"[4/10] {img4.name} capture.")

        # -------------------------------------------------------------
        # 5. 05_suivi_bpmn_tiroir_actionnable.png
        # (Clic sur le noeud Vérification Complétude pour ouvrir le tiroir)
        # -------------------------------------------------------------
        completude_node = page.locator("[data-node-id='completude'], [data-testid='bpmn-task-completude']").first
        if completude_node.count() > 0:
            completude_node.click()
            page.wait_for_timeout(800)

        img5 = OUTPUT_DIR / "05_suivi_bpmn_tiroir_actionnable.png"
        safe_screenshot(page, img5)
        print(f"[5/10] {img5.name} capture.")

        # Fermer le tiroir
        close_drawer = page.locator("button[title='Fermer'], button:has-text('Fermer l\\'inspecteur')").first
        if close_drawer.count() > 0:
            close_drawer.click()
            page.wait_for_timeout(500)

        # -------------------------------------------------------------
        # 6. 06_suivi_bpmn_pieces_manquantes.png
        # (Activer Mode demo, selectionner 'Pièces Manquantes', pas a pas)
        # -------------------------------------------------------------
        demo_btn = page.locator("button:visible:has-text('Mode démo / simulation'), button:visible:has-text('démo'), button:visible:has-text('simulation')").first
        if demo_btn.count() > 0:
            demo_btn.click()
            page.wait_for_timeout(800)

        missing_scenario = page.locator("button:visible:has-text('Pièces Manquantes')").first
        if missing_scenario.count() > 0:
            missing_scenario.click()
            page.wait_for_timeout(600)

        # Step forward 3 times to activate return loop to depot
        step_btn = page.locator("button:visible:has-text('Pas à pas')").first
        if step_btn.count() > 0:
            step_btn.click()
            page.wait_for_timeout(300)
            step_btn.click()
            page.wait_for_timeout(300)
            step_btn.click()
            page.wait_for_timeout(300)

        img6 = OUTPUT_DIR / "06_suivi_bpmn_pieces_manquantes.png"
        safe_screenshot(page, img6)
        print(f"[6/10] {img6.name} capture.")

        # -------------------------------------------------------------
        # 7. 07_suivi_bpmn_rejet_plu.png
        # (Scenario 'Rejet PLU', avancer jusqu'au noeud rouge)
        # -------------------------------------------------------------
        rejet_scenario = page.locator("button:visible:has-text('Rejet PLU')").first
        if rejet_scenario.count() > 0:
            rejet_scenario.click()
            page.wait_for_timeout(500)

        if step_btn.count() > 0:
            for _ in range(8):
                step_btn.click()
                page.wait_for_timeout(200)

        img7 = OUTPUT_DIR / "07_suivi_bpmn_rejet_plu.png"
        safe_screenshot(page, img7)
        print(f"[7/10] {img7.name} capture.")

        # -------------------------------------------------------------
        # 8. 08_suivi_bpmn_escalade_sla.png
        # (Scenario 'Escalade SLA DGS', connecteur gauche ne coupant pas CTM)
        # -------------------------------------------------------------
        escalade_scenario = page.locator("button:visible:has-text('Escalade SLA')").first
        if escalade_scenario.count() > 0:
            escalade_scenario.click()
            page.wait_for_timeout(500)

        if step_btn.count() > 0:
            step_btn.click()
            page.wait_for_timeout(300)
            step_btn.click()
            page.wait_for_timeout(300)

        img8 = OUTPUT_DIR / "08_suivi_bpmn_escalade_sla.png"
        safe_screenshot(page, img8)
        print(f"[8/10] {img8.name} capture.")

        # -------------------------------------------------------------
        # 9. 09_onglet_concepteur_prompt_ia.png
        # (Onglet Concepteur avec React Flow, generation d'un prompt extrait)
        # -------------------------------------------------------------
        concepteur_tab = page.locator("button:visible").filter(has_text="Concepteur")
        if concepteur_tab.count() > 0:
            concepteur_tab.first.click()
            page.wait_for_timeout(1000)

        # Click on preset button Permis de Construire (ADS & ABF 15j)
        preset_btn = page.locator("button:visible:has-text('Permis de Construire'), button:visible:has-text('Générer le circuit')").first
        if preset_btn.count() > 0:
            preset_btn.click()
            page.wait_for_timeout(1000)

        img9 = OUTPUT_DIR / "09_onglet_concepteur_prompt_ia.png"
        safe_screenshot(page, img9)
        print(f"[9/10] {img9.name} capture.")

        ctx.close()

        # -------------------------------------------------------------
        # 10. 10_mobile_390x844_terrain.png
        # (Mobile 390x844 : fil conducteur continu, pas d'assistant collision)
        # -------------------------------------------------------------
        ctx_m = browser.new_context(viewport={"width": 390, "height": 844}, locale="fr-FR", is_mobile=True)
        page_m = ctx_m.new_page()

        page_m.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page_m.wait_for_timeout(500)
        radio_prof_m = page_m.locator('input[name="work-profile"]')
        if radio_prof_m.count() > 0:
            radio_prof_m.first.check()
            open_btn_m = page_m.locator('button:has-text("Ouvrir mon espace")')
            if open_btn_m.count() > 0:
                open_btn_m.click()
                page_m.wait_for_timeout(600)

        page_m.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page_m.wait_for_timeout(1000)

        # Switch to Suivi tab on mobile
        suivi_tab_m = page_m.locator("button").filter(has_text="Suivi").first
        if suivi_tab_m.count() > 0:
            suivi_tab_m.click()
            page_m.wait_for_timeout(800)

        img10 = OUTPUT_DIR / "10_mobile_390x844_terrain.png"
        safe_screenshot(page_m, img10)
        print(f"[10/10] {img10.name} capture.")

        ctx_m.close()
        browser.close()

    print(f"\n[Succès] Les 10 captures d'audit demandées ont été enregistrées avec succès dans : {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    if args.serve:
        serve(OUTPUT_DIR)
        return 0

    if listening():
        run_10_captures()
        return 0

    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    py_exec = str(venv_python) if venv_python.exists() else sys.executable

    server = subprocess.Popen(
        [py_exec, str(Path(__file__).resolve()), "--serve"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError("Le serveur s'est arrêté de façon inattendue.")
        if listening():
            try:
                req = Request(f"{LOCAL_BASE}/demo.html")
                with urlopen(req, timeout=1) as res:
                    if res.status == 200:
                        break
            except Exception:
                pass
        time.sleep(0.3)
    else:
        raise RuntimeError("Délai dépassé pour le serveur.")

    try:
        run_10_captures()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
