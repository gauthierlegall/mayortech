"""Capture the 4 requested screenshots for the new 'Circuits de validation' (Iterop style) architecture.

1. L'onglet À valider avec un dossier ouvert et le panneau Valider & Signer / Renvoyer à une étape visible.
2. La modale/menu Renvoyer à une étape ouvert.
3. L'onglet Suivi & BPMN (avec titres complets non tronqués et sélecteur de dossier réel).
4. La version mobile 390x844.
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
OUTPUT_DIR = Path("C:/Users/Utilisateur/Desktop/GALERIE_CIRCUITS_VALIDATION")
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
        tenant_id="plougastel-validation",
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


def run_validation_captures():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print(f"[Validation-Gallery] Début de la capture dans : {OUTPUT_DIR}")

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
        # 1. Onglet "À valider" avec dossier ouvert et panneau de décision
        # -------------------------------------------------------------
        val_tab = page.locator("button").filter(has_text="À valider")
        if val_tab.count() > 0:
            val_tab.first.click()
            page.wait_for_timeout(800)

        img1 = OUTPUT_DIR / "01_onglet_a_valider_dossier_ouvert.png"
        safe_screenshot(page, img1)
        print(f"[1/4] {img1.name} capturé.")

        # -------------------------------------------------------------
        # 2. Modale "Renvoyer à une étape" ouvert
        # -------------------------------------------------------------
        rollback_btn = page.locator("button:has-text('Renvoyer à une étape amont'), button:has-text('Renvoyer')").first
        if rollback_btn.count() > 0:
            rollback_btn.click()
            page.wait_for_timeout(600)

        img2 = OUTPUT_DIR / "02_modale_renvoyer_a_une_etape.png"
        safe_screenshot(page, img2)
        print(f"[2/4] {img2.name} capturé.")

        # Fermer la modale
        close_modal = page.locator("button:has-text('Annuler'), button[aria-label='Fermer']").first
        if close_modal.count() > 0:
            close_modal.click()
            page.wait_for_timeout(400)

        # -------------------------------------------------------------
        # 3. Onglet "Suivi & BPMN" (Titres complets, sélecteur de dossier réel)
        # -------------------------------------------------------------
        suivi_tab = page.locator("button").filter(has_text="Suivi & BPMN")
        if suivi_tab.count() > 0:
            suivi_tab.first.click()
            page.wait_for_timeout(1000)

            recentrer_btn = page.locator("button:has-text('Recentrer')")
            if recentrer_btn.count() > 0:
                recentrer_btn.first.click()
                page.wait_for_timeout(500)

        img3 = OUTPUT_DIR / "03_onglet_suivi_bpmn_metier.png"
        safe_screenshot(page, img3)
        print(f"[3/4] {img3.name} capturé.")

        ctx.close()

        # -------------------------------------------------------------
        # 4. Version Mobile (390x844)
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

        val_tab_m = page_m.locator("button").filter(has_text="À valider")
        if val_tab_m.count() > 0:
            val_tab_m.first.click()
            page_m.wait_for_timeout(800)

        img4 = OUTPUT_DIR / "04_version_mobile_390x844.png"
        safe_screenshot(page_m, img4)
        print(f"[4/4] {img4.name} capturé.")

        ctx_m.close()
        browser.close()

    print(f"\n[Succès] Les 4 captures demandées ont été enregistrées avec succès dans : {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    if args.serve:
        serve(OUTPUT_DIR)
        return 0

    if listening():
        run_validation_captures()
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
        run_validation_captures()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
