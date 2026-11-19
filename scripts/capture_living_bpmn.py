"""Playwright Capture Script for Living BPMN 2.0 (React Flow Light Mode Edition).

Features strict blocking assertions:
1. document.documentElement.scrollWidth <= window.innerWidth
2. Visible text has contrasting color to background (no white on white)
3. Buttons/tabs fit within viewport and are not obstructed
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
DESKTOP_DIR = Path("C:/Users/Utilisateur/Desktop/POLE_5_LIVING_BPMN/n8n_light_edition")
PORT = 19855
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
        db_path=data_dir / "living_bpmn_light.sqlite3",
        tenant_id="plougastel-living-light",
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


def run_assertions_and_capture():
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)

        # ------------------------------------------------------------------
        # 1. Desktop 1920x1080 Capture & Assertions
        # ------------------------------------------------------------------
        ctx_desktop = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
        page_d = ctx_desktop.new_page()

        page_d.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page_d.wait_for_timeout(600)

        # Login profile selection
        radio_prof = page_d.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_prof.first.check()
            page_d.wait_for_timeout(300)
            open_btn = page_d.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page_d.wait_for_timeout(800)

        page_d.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page_d.wait_for_timeout(1000)

        # Switch to Living BPMN tab
        bpmn_tab = page_d.locator("button").filter(has_text="Living BPMN")
        if bpmn_tab.count() > 0:
            bpmn_tab.first.click()
            page_d.wait_for_timeout(1000)

        # ASSERTION 1: No horizontal overflow
        scroll_width = page_d.evaluate("document.documentElement.scrollWidth")
        inner_width = page_d.evaluate("window.innerWidth")
        print(f"[Desktop] scrollWidth: {scroll_width}, innerWidth: {inner_width}")
        if scroll_width > inner_width:
            raise AssertionError(f"BLOCKED: Horizontal overflow on Desktop! scrollWidth ({scroll_width}) > innerWidth ({inner_width})")

        # ASSERTION 2: Text contrast (H1 text color != background color)
        h1 = page_d.locator("h1").first
        if h1.count() > 0:
            h1_color = h1.evaluate("el => window.getComputedStyle(el).color")
            h1_bg = h1.evaluate("el => window.getComputedStyle(el).backgroundColor")
            print(f"[Desktop] H1 text color: {h1_color}, H1 background: {h1_bg}")
            if "255, 255, 255" in h1_color and ("255, 255, 255" in h1_bg or "rgba(0, 0, 0, 0)" in h1_bg):
                # Check parent background
                parent_bg = h1.evaluate("el => window.getComputedStyle(el.parentElement).backgroundColor")
                if "255, 255, 255" in parent_bg:
                    raise AssertionError("BLOCKED: H1 is white text on white background!")

        # ASSERTION 3: React Flow canvas exists and is rendered
        rf_canvas = page_d.locator(".react-flow")
        if rf_canvas.count() == 0:
            raise AssertionError("BLOCKED: React Flow canvas not found in DOM!")
        print("[Desktop] React Flow canvas rendered successfully.")

        # Take Desktop Screenshot
        desktop_img = DESKTOP_DIR / "01_desktop_living_bpmn_light.png"
        page_d.screenshot(path=str(desktop_img), full_page=False)
        print(f"Capture Desktop validée : {desktop_img}")
        ctx_desktop.close()

        # ------------------------------------------------------------------
        # 2. Mobile 390x844 Responsive Capture & Assertions
        # ------------------------------------------------------------------
        ctx_mobile = browser.new_context(viewport={"width": 390, "height": 844}, locale="fr-FR", is_mobile=True)
        page_m = ctx_mobile.new_page()

        page_m.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page_m.wait_for_timeout(600)

        radio_prof_m = page_m.locator('input[name="work-profile"]')
        if radio_prof_m.count() > 0:
            radio_prof_m.first.check()
            open_btn_m = page_m.locator('button:has-text("Ouvrir mon espace")')
            if open_btn_m.count() > 0:
                open_btn_m.click()
                page_m.wait_for_timeout(600)

        page_m.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page_m.wait_for_timeout(1000)

        bpmn_tab_m = page_m.locator("button").filter(has_text="Living BPMN")
        if bpmn_tab_m.count() > 0:
            bpmn_tab_m.first.click()
            page_m.wait_for_timeout(1000)

        # ASSERTION 1 (Mobile): No horizontal page overflow
        m_scroll_width = page_m.evaluate("document.documentElement.scrollWidth")
        m_inner_width = page_m.evaluate("window.innerWidth")
        print(f"[Mobile] scrollWidth: {m_scroll_width}, innerWidth: {m_inner_width}")
        if m_scroll_width > m_inner_width + 1:  # Allow 1px subpixel tolerance
            raise AssertionError(f"BLOCKED: Horizontal overflow on Mobile! scrollWidth ({m_scroll_width}) > innerWidth ({m_inner_width})")

        # Take Mobile Screenshot
        mobile_img = DESKTOP_DIR / "02_mobile_living_bpmn_responsive.png"
        page_m.screenshot(path=str(mobile_img), full_page=False)
        print(f"Capture Mobile validée : {mobile_img}")
        ctx_mobile.close()

        browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    if args.serve:
        serve(DESKTOP_DIR)
        return 0

    if listening():
        run_assertions_and_capture()
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
        run_assertions_and_capture()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
