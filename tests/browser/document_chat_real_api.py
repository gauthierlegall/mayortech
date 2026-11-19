"""Real loopback API, SQLite, upload parser and Yjs. Only provider transport is fake."""

import io
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from pypdf import PdfWriter
from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "test-results" / "document-chat-integration"
fixture = json.loads((OUT / "fixture.json").read_text())
BASE, project_id = fixture["origin"], fixture["project_id"]
if BASE != "http://127.0.0.1:18806":
    raise RuntimeError("This fixture is restricted to loopback port 18806.")
stamp = str(int(time.time()))
filename = "recette-terrain-" + stamp + ".pdf"
title = "Verifier les acces - recette " + stamp
report = {
    "kind": "Real local API/SQLite/PDF/Yjs; fake LLM transport; OIDC excluded",
    "viewport": [1920, 1080],
    "checks": [],
    "page_errors": [],
    "failed_requests": [],
}


def check(name, value):
    report["checks"].append({"name": name, "passed": bool(value)})
    assert value, name


def pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=300)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 14 Tf 20 200 Td (Avancement : Terrassement termine RECETTE_RAG_1711) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome", headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="fr-FR")
    page = context.new_page()
    page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
    page.on(
        "requestfailed",
        lambda request: report["failed_requests"].append(
            {"path": request.url.split(BASE)[-1].split("?")[0], "failure": request.failure}
        ),
    )
    try:
        created = page.request.post(
            BASE + "/api/v1/projects",
            headers={"X-Requested-With": "Travaux"},
            data={"reference": "QA-RAG-" + stamp, "name": "Recette documentaire et chatbot " + stamp},
        )
        check("QA uses a newly created real project", created.status == 201)
        project_id = created.json()["id"]
        report["project_id"] = project_id
        page.goto(BASE + "/#/chantiers/" + project_id + "?view=documents", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Documents", exact=False)).to_be_visible()
        original = pdf()
        page.get_by_label("Choisir un document à ajouter au dossier").set_input_files(
            {"name": filename, "mimeType": "application/pdf", "buffer": original}
        )
        with page.expect_response(
            lambda response: response.url.endswith("/documents/upload") and response.request.method == "POST"
        ) as upload:
            page.get_by_role("button", name="Ajouter au dossier", exact=True).click()
        receipt = upload.value.json()
        report["receipt"] = {
            key: receipt[key]
            for key in ["status", "job_status", "extraction_status", "candidate_count", "replayed"]
        }
        check(
            "UI upload commits original and completed extraction",
            upload.value.status == 201
            and receipt["candidate_count"] == 1
            and receipt["job_status"] == "done",
        )
        expect(page.get_by_role("button", name=filename, exact=True)).to_be_visible(timeout=15000)
        check(
            "download returns exactly the submitted PDF",
            page.request.get(BASE + "/api/v1/documents/" + receipt["document_id"] + "/download").body()
            == original,
        )
        detail = page.request.get(BASE + "/api/v1/projects/" + project_id).json()
        check(
            "document facts stay pending for human validation",
            any(row["source_id"] == receipt["source_id"] for row in detail["pending"])
            and not any(row["source_id"] == receipt["source_id"] for row in detail["facts"]),
        )
        page.screenshot(path=str(OUT / "01-document-1920x1080.png"))
        page.get_by_role("button", name="Ouvrir le chat Assistant", exact=True).click()
        question = page.get_by_label("Votre question", exact=True)
        expect(question).to_be_visible()
        question.fill("Quels travaux concernent le terrassement RECETTE_RAG_1711 ?")
        page.get_by_role("button", name="Envoyer la question", exact=True).click()
        answer = page.locator(".conversation-message.assistant").last
        expect(answer).to_contain_text("RECETTE_RAG_1711", timeout=20000)
        check(
            "RAG answer cites an actual stored source", answer.locator(".conversation-sources").count() == 1
        )
        page.screenshot(path=str(OUT / "02-rag-1920x1080.png"))
        page.get_by_label("Modifier le dossier", exact=True).check()
        page.get_by_label("Modification souhaitée", exact=True).fill("Mets le statut à Terminé")
        status_before = page.request.get(BASE + "/api/v1/projects/" + project_id).json()["status"]
        page.get_by_role("button", name="Préparer la modification", exact=True).click()
        expect(page.get_by_role("button", name="Confirmer la modification", exact=True)).to_be_visible(
            timeout=15000
        )
        check(
            "proposal leaves the project unchanged",
            page.request.get(BASE + "/api/v1/projects/" + project_id).json()["status"] == status_before,
        )
        page.screenshot(path=str(OUT / "03-proposal-1920x1080.png"))
        page.get_by_role("button", name="Confirmer la modification", exact=True).click()
        expect(page.get_by_role("heading", name="Modification appliquée", exact=True)).to_be_visible(
            timeout=15000
        )
        check(
            "human confirmation updates the real project table",
            page.request.get(BASE + "/api/v1/projects/" + project_id).json()["status"] == "completed",
        )
        page.get_by_label("Modification souhaitée", exact=True).fill("Crée une action : " + title)
        page.get_by_role("button", name="Préparer la modification", exact=True).click()
        expect(page.get_by_role("button", name="Confirmer la modification", exact=True)).to_be_visible(
            timeout=15000
        )
        check(
            "proposed action is not an accepted fact yet",
            not any(
                row["value"] == title
                for row in page.request.get(BASE + "/api/v1/projects/" + project_id).json()["actions"]
            ),
        )
        page.get_by_role("button", name="Confirmer la modification", exact=True).click()
        expect(page.get_by_role("heading", name="Modification appliquée", exact=True)).to_have_count(
            2, timeout=15000
        )
        check(
            "confirmed action exists exactly once as an accepted fact",
            sum(
                row["value"] == title
                for row in page.request.get(BASE + "/api/v1/projects/" + project_id).json()["actions"]
            )
            == 1,
        )
        page.locator(".assistant-launcher").click()
        page.get_by_role("tab", name="Actions", exact=False).click()
        expect(page.locator(".action-row").filter(has_text=title)).to_have_count(1, timeout=30000)
        page.screenshot(path=str(OUT / "04-action-1920x1080.png"))
        page.reload(wait_until="networkidle")
        expect(page.locator(".action-row").filter(has_text=title)).to_have_count(1, timeout=30000)
        check("native Yjs action survives a full reload without duplication", True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("button", name="Ouvrir le chat Assistant", exact=True).click()
        expect(page.get_by_role("heading", name="Assistant", exact=True)).to_be_visible()
        expect(page.get_by_label("Votre question", exact=True)).to_be_visible(timeout=15000)
        expect(page.get_by_role("heading", name="Modification appliquée", exact=True)).to_have_count(
            2, timeout=15000
        )
        check(
            "mobile popup stays inside the viewport",
            page.locator("#assistant-popup").evaluate(
                "(element)=>{const r=element.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.top>=0&&r.bottom<=innerHeight+1;}"
            ),
        )
        page.screenshot(path=str(OUT / "05-chat-390x844.png"))
        check("no browser JavaScript exceptions", not report["page_errors"])
    except Exception as failure:
        report["error"] = str(failure)
        page.screenshot(path=str(OUT / "failure.png"))
        (OUT / "failure-dom.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
        raise
    finally:
        browser.close()
        (OUT / "checks.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
print(json.dumps({"passed": len(report["checks"]), "errors": report["page_errors"]}, ensure_ascii=False))
