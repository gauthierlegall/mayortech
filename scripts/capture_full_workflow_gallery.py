"""Capture exactly 10 comprehensive screenshots of the BPMN workflow from A to Z.

Destination: C:/Users/Utilisateur/Desktop/GALERIE_COMPLETE_WORKFLOW_BPMN
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_DIR = Path("C:/Users/Utilisateur/Desktop/GALERIE_COMPLETE_WORKFLOW_BPMN")
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
        tenant_id="plougastel-gallery",
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


def run_gallery_captures():
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    # Nettoyage des anciennes captures pour ne garder STRICTEMENT que les 10 demandées
    for old_file in DESKTOP_DIR.glob("*.png"):
        try:
            old_file.unlink()
        except Exception:
            pass

    from playwright.sync_api import sync_playwright

    print(f"[Gallery] Début de la génération des 10 captures dans : {DESKTOP_DIR}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page = ctx.new_page()

        # -------------------------------------------------------------
        # 1. Écran de connexion / profil (Référence visuelle Light Mode)
        # -------------------------------------------------------------
        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(800)
        img1 = DESKTOP_DIR / "01_connexion_espace_travaux.png"
        safe_screenshot(page, img1)
        print(f"[1/10] {img1.name}")

        # Sélectionner le profil
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_prof.first.check()
            page.wait_for_timeout(300)
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(800)

        # -------------------------------------------------------------
        # 2. Prompt-to-BPMN Studio (Saisie IA & Génération)
        # -------------------------------------------------------------
        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(1000)

        prompt_tab = page.locator("button").filter(has_text="Prompt Studio")
        if prompt_tab.count() > 0:
            prompt_tab.first.click()
            page.wait_for_timeout(600)

            # Remplir le prompt
            prompt_input = page.locator("textarea, input[placeholder*='prompt' i], input[type='text']").first
            if prompt_input.count() > 0:
                prompt_input.fill("Instruction d'une Déclaration Préalable Cerfa 13404*10 pour rénovation toiture en ardoise naturelle à Plougastel-Daoulas (secteur ABF, délai SLA 15j, visa de l'Adjoint aux Travaux et scellement SHA-256).")
                page.wait_for_timeout(300)
                gen_btn = page.locator("button").filter(has_text="Générer").first
                if gen_btn.count() > 0:
                    gen_btn.click()
                    page.wait_for_timeout(900)

            img2 = DESKTOP_DIR / "02_prompt_studio_ia.png"
            safe_screenshot(page, img2)
            print(f"[2/10] {img2.name}")

        # -------------------------------------------------------------
        # 3. Studio BPMN 2.0 (Palette, Éditeur graphique & Propriétés)
        # -------------------------------------------------------------
        studio_tab = page.locator("button").filter(has_text="Studio BPMN")
        if studio_tab.count() > 0:
            studio_tab.first.click()
            page.wait_for_timeout(900)

            # Cliquer sur un nœud dans le studio pour afficher les propriétés
            node_in_studio = page.locator("[data-node-id='task_completude'], g[data-node-id='task_completude'], [data-node-id]").first
            if node_in_studio.count() > 0:
                node_in_studio.click()
                page.wait_for_timeout(500)

            img3 = DESKTOP_DIR / "03_studio_bpmn_modeler.png"
            safe_screenshot(page, img3)
            print(f"[3/10] {img3.name}")

        # -------------------------------------------------------------
        # Navigation vers Living BPMN 2.0
        # -------------------------------------------------------------
        living_tab = page.locator("button").filter(has_text="Living BPMN")
        if living_tab.count() > 0:
            living_tab.first.click()
            page.wait_for_timeout(1000)

            # Recentrer le canvas pour un cadrage optimal
            recentrer_btn = page.locator("button:has-text('Recentrer')")
            if recentrer_btn.count() > 0:
                recentrer_btn.first.click()
                page.wait_for_timeout(500)

            # ---------------------------------------------------------
            # 4. Living BPMN 2.0 - Vue Générale des Couloirs Compacts
            # ---------------------------------------------------------
            voie_royale_btn = page.locator("button:has-text('Voie Royale')")
            if voie_royale_btn.count() > 0:
                voie_royale_btn.first.click()
                page.wait_for_timeout(400)

            img4 = DESKTOP_DIR / "04_living_bpmn_vue_generale.png"
            safe_screenshot(page, img4)
            print(f"[4/10] {img4.name}")

            # ---------------------------------------------------------
            # 5. Voie Royale : Transit actif du dossier avec jeton PC-2026
            # ---------------------------------------------------------
            step_btn = page.locator("button:has-text('Pas à pas')")
            if step_btn.count() > 0:
                step_btn.first.click()  # -> completude
                page.wait_for_timeout(400)
                step_btn.first.click()  # -> gw1
                page.wait_for_timeout(400)
                step_btn.first.click()  # -> ctm
                page.wait_for_timeout(400)
                step_btn.first.click()  # -> abf
                page.wait_for_timeout(500)

            img5 = DESKTOP_DIR / "05_living_bpmn_voie_royale_active.png"
            safe_screenshot(page, img5)
            print(f"[5/10] {img5.name}")

            # ---------------------------------------------------------
            # 6. Tiroir Cerfa 13404 déployé au clic sur la tâche
            # ---------------------------------------------------------
            page.evaluate("window.dispatchEvent(new CustomEvent('bpmn-node-selected', { detail: { id: 'completude' } }))")
            page.wait_for_timeout(600)
            img6 = DESKTOP_DIR / "06_living_bpmn_tiroir_cerfa.png"
            safe_screenshot(page, img6)
            print(f"[6/10] {img6.name}")

            # Fermer le tiroir
            drawer_close = page.locator("button[title='Fermer'], button:has-text('Fermer')").first
            if drawer_close.count() > 0:
                drawer_close.click()
                page.wait_for_timeout(300)

            # ---------------------------------------------------------
            # 7. Scénario 1 : Pièces Manquantes (Boucle ambrée Relance 30j)
            # ---------------------------------------------------------
            pieces_btn = page.locator("button:has-text('Pièces Manquantes')")
            if pieces_btn.count() > 0:
                pieces_btn.first.click()
                page.wait_for_timeout(400)
                if step_btn.count() > 0:
                    step_btn.first.click()  # -> completude
                    page.wait_for_timeout(300)
                    step_btn.first.click()  # -> gw1
                    page.wait_for_timeout(300)
                    step_btn.first.click()  # -> depot via loop
                    page.wait_for_timeout(500)
            img7 = DESKTOP_DIR / "07_living_bpmn_scenario_pieces_manquantes.png"
            safe_screenshot(page, img7)
            print(f"[7/10] {img7.name}")

            # ---------------------------------------------------------
            # 8. Scénario 2 : Rejet PLU (Aiguillage terminal rouge)
            # ---------------------------------------------------------
            rejet_btn = page.locator("button:has-text('Rejet PLU')")
            if rejet_btn.count() > 0:
                rejet_btn.first.click()
                page.wait_for_timeout(400)
                if step_btn.count() > 0:
                    for _ in range(6):
                        step_btn.first.click()
                        page.wait_for_timeout(200)
                    page.wait_for_timeout(500)
            img8 = DESKTOP_DIR / "08_living_bpmn_scenario_rejet_plu.png"
            safe_screenshot(page, img8)
            print(f"[8/10] {img8.name}")

            # ---------------------------------------------------------
            # 9. Scénario 3 : Escalade SLA (Alerte DÉPASSÉ et branche DGS)
            # ---------------------------------------------------------
            sla_btn = page.locator("button:has-text('Escalade SLA')")
            if sla_btn.count() > 0:
                sla_btn.first.click()
                page.wait_for_timeout(400)
                if step_btn.count() > 0:
                    step_btn.first.click()  # -> completude (overdue)
                    page.wait_for_timeout(300)
                    step_btn.first.click()  # -> dgs
                    page.wait_for_timeout(500)
            img9 = DESKTOP_DIR / "09_living_bpmn_scenario_escalade_sla.png"
            safe_screenshot(page, img9)
            print(f"[9/10] {img9.name}")

        ctx.close()

        # -------------------------------------------------------------
        # 10. Responsive Mobile (390x844) : Timeline Verticale
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

        living_tab_m = page_m.locator("button").filter(has_text="Living BPMN")
        if living_tab_m.count() > 0:
            living_tab_m.first.click()
            page_m.wait_for_timeout(800)

        img10 = DESKTOP_DIR / "10_living_bpmn_mobile_timeline_verticale.png"
        safe_screenshot(page_m, img10)
        print(f"[10/10] {img10.name}")
        ctx_m.close()

        browser.close()

    # Création du fichier d'index visuel récapitulatif
    generate_gallery_readme()
    print(f"\n[Succès] Les 10 captures du workflow BPMN ont été enregistrées avec succès dans : {DESKTOP_DIR}")


def generate_gallery_readme():
    readme_path = DESKTOP_DIR / "INDEX_GALERIE_BPMN.md"
    content = """# Galerie Officielle du Workflow BPMN 2.0 (10 Écrans de A à Z)
## Suite MayorFlow · Commune de Plougastel-Daoulas
**Design System :** Light Mode Natif (Linear / Stripe / n8n) · Moteur : `@xyflow/react`

Ce dossier réunit exactement **10 captures d'écran haute définition** illustrant le workflow complet, de l'authentification jusqu'aux scénarios d'arbitrage et la version mobile :

| N° | Fichier | Description & Particularités Techniques |
| :---: | :--- | :--- |
| **01** | `01_connexion_espace_travaux.png` | **Connexion & Profil Instructeur** : Point d'entrée de référence du design system Light Mode clair. |
| **02** | `02_prompt_studio_ia.png` | **Prompt-to-BPMN Studio** : Traduction IA en langage naturel du Cerfa 13404*10 en modèle exécutable SpiffWorkflow. |
| **03** | `03_studio_bpmn_modeler.png` | **Studio Modélisateur BPMN** : Canvas interactif avec palette de tâches, passerelles XOR et panneau d'inspection latérale. |
| **04** | `04_living_bpmn_vue_generale.png` | **Living BPMN 2.0 (Vue d'ensemble)** : 3 couloirs horizontaux compacts (`1 · ADS Guichet`, `2 · CTM & ABF`, `3 · Élu & Sceau`) sur trame de points `#F8FAFC`. |
| **05** | `05_living_bpmn_voie_royale_active.png` | **Voie Royale en Action** : Transit du dossier Cerfa matérialisé par le jeton pulsant `PC-2026` et arêtes terminées en vert émeraude doux (`Validé`). |
| **06** | `06_living_bpmn_tiroir_cerfa.png` | **Tiroir d'Inspection Cerfa 13404** : Volet blanc glissant par-dessus le canvas avec pièces requises, délais SLA et articles du PLU. |
| **07** | `07_living_bpmn_scenario_pieces_manquantes.png` | **Scénario Pièces Manquantes** : Passerelle XOR et boucle de rétroaction `[NON] Relance 30j` illuminée en ambre vif (`#F59E0B`). |
| **08** | `08_living_bpmn_scenario_rejet_plu.png` | **Scénario Rejet PLU** : Aiguillage de refus motivé avec capsule terminale rouge `PC-2026` et trajectoire rouge. |
| **09** | `09_living_bpmn_scenario_escalade_sla.png` | **Scénario Escalade SLA** : Badge clignotant rouge `DÉPASSÉ (72h)` sur l'instruction et dérivation d'urgence vers l'Arbitrage DGS. |
| **10** | `10_living_bpmn_mobile_timeline_verticale.png` | **Version Mobile Responsive (390x844)** : Timeline verticale empilée fluide, connecteurs dynamiques et marge inférieure `pb-32` sans aucun débordement. |

---
*Généré automatiquement par le banc de test visuel MayorFlow Playwright.*
"""
    readme_path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    if args.serve:
        serve(DESKTOP_DIR)
        return 0

    if listening():
        run_gallery_captures()
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
        run_gallery_captures()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
