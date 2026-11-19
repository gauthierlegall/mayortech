"""Exercise the vendored renderer with real Chromium SVG/DOMTokenList APIs."""
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend-lovable/src"


def test_gantt_renders_unknown_and_completed_progress_without_invalid_class_tokens():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        def serve_source(route):
            path = urlparse(route.request.url).path
            if path == "/":
                route.fulfill(
                    content_type="text/html",
                    body='<link rel="stylesheet" href="/vendor/frappe-gantt/styles/gantt.css">'
                    '<link rel="stylesheet" href="/features/workspace/planning.css">'
                    '<main class="planning-gantt" id="chart"></main>',
                )
                return
            target = SOURCE / path.lstrip("/")
            if not target.suffix:
                target = target.with_suffix(".js")
            assert target.resolve().is_relative_to(SOURCE.resolve())
            content = target.read_text(encoding="utf-8")
            # Vite extracts this CSS import into a stylesheet in production.
            if target.name == "index.js":
                content = content.replace("import './styles/gantt.css';", "")
            route.fulfill(
                content_type="text/css" if target.suffix == ".css" else "text/javascript",
                body=content,
            )

        page.route("http://gantt.test/**", serve_source)
        page.goto("http://gantt.test/", wait_until="networkidle")
        result = page.evaluate("""async () => {
            const {default:Gantt}=await import('/vendor/frappe-gantt/index.js');
            const {ganttTasks}=await import('/features/workspace/planning-model.mjs');
            const rows=[
                {id:'unknown',title:'Avancement non renseigné',start:'2026-11-16',due:'2026-11-17'},
                {id:'zero',title:'Zéro explicite',start:'2026-11-18',due:'2026-11-19',progress:0},
                {id:'complete',title:'Terminé <image onerror="alert(1)">',start:'2026-11-20',due:'2026-11-20',status:'Terminé'},
            ];
            const chart=new Gantt(document.querySelector('#chart'),ganttTasks(rows).tasks,{
                language:'fr',view_mode:'Day',infinite_padding:false,popup:false,
                today_button:false,view_mode_select:false,scroll_to:'start',
            });
            const bars=[...document.querySelectorAll('.bar-wrapper')].map(element=>({
                classes:[...element.classList],label:element.querySelector('.bar-label').textContent,
                progressHandle:!!element.querySelector('.handle.progress')&&getComputedStyle(element.querySelector('.handle.progress')).display!=='none',
            }));
            const injectedImages=document.querySelectorAll('svg image').length;
            chart.destroy();
            return {bars,injectedImages};
        }""")
        assert len(result["bars"]) == 3
        assert "progress-unknown" in result["bars"][0]["classes"]
        assert result["bars"][0]["progressHandle"] is False
        assert "progress-unknown" not in result["bars"][1]["classes"]
        assert "task-complete" in result["bars"][2]["classes"]
        assert result["bars"][2]["label"] == 'Terminé <image onerror="alert(1)">'
        assert result["injectedImages"] == 0
        browser.close()
