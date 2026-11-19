"""Iterative Headless Capture Script for Living BPMN Canvas.

Usage:
  python scripts/capture_iterative_pass.py --pass-num 1
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_DIR = Path("C:/Users/Utilisateur/Desktop/POLE_5_LIVING_BPMN")
PORT = 19840
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
        db_path=data_dir / "living_bpmn.sqlite3",
        tenant_id="plougastel-living",
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


def capture_pass(pass_num: int, scenario: str | None = None, steps: int = 0, click_card: str | None = None, is_mobile: bool = False, trigger_seal: bool = False):
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    pass_dir = DESKTOP_DIR / f"passe_{pass_num}"
    pass_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        viewport = {"width": 390, "height": 844} if is_mobile else {"width": 1920, "height": 1080}
        ctx = browser.new_context(viewport=viewport, locale="fr-FR")
        page = ctx.new_page()

        page.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Profile selection
        radio_prof = page.locator('input[name="work-profile"]')
        if radio_prof.count() > 0:
            radio_prof.first.check()
            page.wait_for_timeout(300)
            open_btn = page.locator('button:has-text("Ouvrir mon espace")')
            if open_btn.count() > 0:
                open_btn.click()
                page.wait_for_timeout(1000)

        page.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
        page.wait_for_timeout(1200)

        # Ensure we are on Simulateur tab
        sim_tab = page.locator("button").filter(has_text="Simulateur")
        if sim_tab.count() > 0:
            sim_tab.first.click()
            page.wait_for_timeout(800)

        # Robust Scenario Selection
        if scenario:
            sc_lower = scenario.lower()
            if "manquant" in sc_lower or "piece" in sc_lower:
                target_btn = page.locator("button").filter(has_text="Manquantes").first
            elif "rejet" in sc_lower:
                target_btn = page.locator("button").filter(has_text="Rejet").first
            elif "sla" in sc_lower or "escalade" in sc_lower:
                target_btn = page.locator("button").filter(has_text="Escalade").first
            else:
                target_btn = page.locator("button").filter(has_text="Voie Royale").first

            if target_btn.count() > 0:
                target_btn.click()
                page.wait_for_timeout(600)

        # Optional Step advance
        if steps > 0:
            # First pause if running
            pause_btn = page.locator("button").filter(has_text="PAUSE")
            if pause_btn.count() > 0:
                pause_btn.first.click()
                page.wait_for_timeout(400)

            step_btn = page.locator("button").filter(has_text="PAS À PAS")
            for _ in range(steps):
                if step_btn.count() > 0 and not step_btn.first.is_disabled():
                    step_btn.first.click()
                    page.wait_for_timeout(400)

        # Optional Card inspection click
        if click_card:
            card_el = page.get_by_text(click_card).first
            if card_el.count() > 0:
                card_el.click()
                page.wait_for_timeout(1000)

        # Optional Trigger Seal celebration
        if trigger_seal:
            seal_btn = page.locator("button").filter(has_text="Simuler le Scellement")
            if seal_btn.count() > 0:
                seal_btn.first.click()
                page.wait_for_timeout(400)

        target_name = f"01_mobile_passe_{pass_num}.png" if is_mobile else f"01_fullhd_passe_{pass_num}.png"
        target = pass_dir / target_name
        page.screenshot(path=str(target), full_page=is_mobile)
        print(f"Capture Passe {pass_num} enregistrée : {target}")

        if is_mobile:
            # Also capture the fullhd equivalent for complete conformity
            target_fullhd = pass_dir / f"01_fullhd_passe_{pass_num}.png"
            ctx_hd = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
            page_hd = ctx_hd.new_page()
            page_hd.goto(f"{LOCAL_BASE}/demo.html", wait_until="networkidle")
            page_hd.wait_for_timeout(600)
            radio_prof_hd = page_hd.locator('input[name="work-profile"]')
            if radio_prof_hd.count() > 0:
                radio_prof_hd.first.check()
                page_hd.wait_for_timeout(300)
                open_btn_hd = page_hd.locator('button:has-text("Ouvrir mon espace")')
                if open_btn_hd.count() > 0:
                    open_btn_hd.click()
                    page_hd.wait_for_timeout(800)
            page_hd.goto(f"{LOCAL_BASE}/demo.html#/workflows", wait_until="networkidle")
            page_hd.wait_for_timeout(1000)
            sim_hd = page_hd.locator("button").filter(has_text="Simulateur")
            if sim_hd.count() > 0:
                sim_hd.first.click()
                page_hd.wait_for_timeout(800)
            page_hd.screenshot(path=str(target_fullhd), full_page=False)
            ctx_hd.close()
            print(f"Capture Full HD Passe {pass_num} enregistrée : {target_fullhd}")

        ctx.close()
        browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--pass-num", type=int, default=1)
    parser.add_argument("--scenario", type=str, default=None)
    parser.add_argument("--steps", type=int, default=0)
    parser.add_argument("--click-card", type=str, default=None)
    parser.add_argument("--trigger-seal", action="store_true")
    parser.add_argument("--mobile", action="store_true")
    args = parser.parse_args()

    if args.serve:
        serve(DESKTOP_DIR)
        return 0

    if listening():
        capture_pass(args.pass_num, args.scenario, args.steps, args.click_card, args.mobile, args.trigger_seal)
        return 0

    server = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve"],
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
        capture_pass(args.pass_num, args.scenario, args.steps, args.click_card, args.mobile, args.trigger_seal)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
