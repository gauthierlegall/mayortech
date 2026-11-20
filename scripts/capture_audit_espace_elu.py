import subprocess
import time
import socket
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(r"C:\Users\Utilisateur\Desktop\AUDIT_ESPACE_ELU")
PORT = 19860
LOCAL_BASE = f"http://127.0.0.1:{PORT}"

def listening():
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", PORT)) == 0

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server = None
    if not listening():
        print(f"Starting server on port {PORT}...")
        server = subprocess.Popen(
            [sys.executable, "scripts/capture_audit_epuration.py", "--serve-only"],
            cwd=str(ROOT)
        )
        for _ in range(50):
            if listening():
                break
            time.sleep(0.2)
        if not listening():
            raise RuntimeError("Server failed to start")

    try:
        print(f"[Audit-Espace-Elu] Generating captures into {OUTPUT_DIR}...")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)

            # =========================================================================
            # Capture 1 : 01_header_agent_epure_sans_focus_elu.png (Desktop 1920x1080)
            # =========================================================================
            ctx_agent = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page_agent = ctx_agent.new_page()

            page_agent.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page_agent.wait_for_timeout(800)

            # Ensure profile choice or select commission-1 (Valérie Gestin)
            radio_c1 = page_agent.locator('input[value="commission-1"]')
            if radio_c1.count() > 0:
                radio_c1.check()
                open_btn = page_agent.locator('button:has-text("Ouvrir mon espace")')
                if open_btn.count() > 0:
                    open_btn.click()
                    page_agent.wait_for_timeout(1000)

            # Switch to commission-1 via sidebar select if present
            sidebar_sel = page_agent.locator("#sidebar-commission-select")
            if sidebar_sel.count() > 0:
                sidebar_sel.select_option("commission-1")
                page_agent.wait_for_timeout(800)

            # Navigate to Accueil
            page_agent.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
            page_agent.wait_for_timeout(1000)

            # Assert Focus Élu button is completely absent
            focus_btn = page_agent.locator('button:has-text("Focus Élu"), span:has-text("Focus Élu")')
            print(f"Focus Élu button count in agent view: {focus_btn.count()} (must be 0)")
            assert focus_btn.count() == 0, "Focus Élu button must NOT exist in agent header!"

            shot1 = OUTPUT_DIR / "01_header_agent_epure_sans_focus_elu.png"
            page_agent.screenshot(path=str(shot1), full_page=False)
            print(f"[Capture 1] Enregistrée: {shot1}")
            ctx_agent.close()

            # =========================================================================
            # Capture 2 : 02_espace_elu_natif_maire_desktop.png (Desktop 1920x1080)
            # =========================================================================
            ctx_maire = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page_maire = ctx_maire.new_page()

            page_maire.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page_maire.wait_for_timeout(800)

            # Switch to elu-maire
            sidebar_sel = page_maire.locator("#sidebar-commission-select")
            if sidebar_sel.count() > 0:
                sidebar_sel.select_option("elu-maire")
                page_maire.wait_for_timeout(1000)
            else:
                radio_elu = page_maire.locator('input[value="elu-maire"]')
                if radio_elu.count() > 0:
                    radio_elu.check()
                    page_maire.locator('button:has-text("Ouvrir mon espace")').click()
                    page_maire.wait_for_timeout(1000)

            page_maire.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
            page_maire.wait_for_timeout(1000)

            # Check that ElectedWorkspaceLayout is active
            header_tabs = page_maire.locator('button:has-text("À signer")')
            print(f"Espace Élu 'À signer' tab found: {header_tabs.count() > 0}")

            # Check that the act MP-2026-008 is unfolded
            unfold_btn = page_maire.locator('button:has-text("Lire l\'acte complet")')
            if unfold_btn.count() > 0:
                unfold_btn.first.click()
                page_maire.wait_for_timeout(400)

            shot2 = OUTPUT_DIR / "02_espace_elu_natif_maire_desktop.png"
            page_maire.screenshot(path=str(shot2), full_page=False)
            print(f"[Capture 2] Enregistrée: {shot2}")
            ctx_maire.close()

            # =========================================================================
            # Capture 3 : 03_espace_elu_natif_maire_mobile_390x844.png (Mobile 390x844)
            # =========================================================================
            ctx_mobile = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                has_touch=True,
                locale="fr-FR"
            )
            page_mobile = ctx_mobile.new_page()

            # Navigate directly with elu-maire active in localStorage or select it
            page_mobile.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page_mobile.wait_for_timeout(800)

            # Check if we need to switch or if already in elu-maire
            sidebar_sel = page_mobile.locator("#sidebar-commission-select")
            if sidebar_sel.count() > 0:
                sidebar_sel.select_option("elu-maire")
                page_mobile.wait_for_timeout(1000)
            else:
                radio_elu = page_mobile.locator('input[value="elu-maire"]')
                if radio_elu.count() > 0:
                    radio_elu.check()
                    page_mobile.locator('button:has-text("Ouvrir mon espace")').click()
                    page_mobile.wait_for_timeout(1000)

            page_mobile.goto(f"{LOCAL_BASE}/demo.html#/", wait_until="networkidle")
            page_mobile.wait_for_timeout(1000)

            # Verify no horizontal scrollbar / overflow
            scroll_width = page_mobile.evaluate("() => document.documentElement.scrollWidth")
            client_width = page_mobile.evaluate("() => document.documentElement.clientWidth")
            print(f"Mobile layout widths: scrollWidth={scroll_width}, clientWidth={client_width}")

            shot3 = OUTPUT_DIR / "03_espace_elu_natif_maire_mobile_390x844.png"
            page_mobile.screenshot(path=str(shot3), full_page=False)
            print(f"[Capture 3] Enregistrée: {shot3}")
            ctx_mobile.close()

            browser.close()

    finally:
        if server:
            server.terminate()

if __name__ == "__main__":
    main()
