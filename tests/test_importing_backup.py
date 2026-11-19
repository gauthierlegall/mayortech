from email.message import EmailMessage

from travaux.cli import backup
from travaux.importing import import_mail
from travaux.jobs import JobQueue
from travaux.llm import DemoExtractor
from travaux.pipeline import process_one
from travaux.repository import Repository


def test_mail_attachment_is_a_separate_source_and_reply_retains_project(tmp_path):
    repo = Repository(tmp_path / "db.sqlite3")
    queue = JobQueue(tmp_path / "db.sqlite3")
    try:
        project = repo.create_project("town", "TR-99", "Un chantier fictif")
        message = EmailMessage()
        message["Subject"] = "[TR-99] Point de chantier"
        message["From"] = "test@fictif.invalid"
        message["Message-ID"] = "<first@fictif.invalid>"
        message["Date"] = "Sat, 14 Nov 2026 09:00:00 +0100"
        message.set_content("Avancement : Terrassement fini")
        message.add_attachment(b"Livraison : 2026-12-04", maintype="text", subtype="plain", filename="compte-rendu-fictif.txt")
        result = import_mail(repo, queue, "town", message.as_bytes())
        assert len(result["related_sources"]) == 1
        assert result["related_sources"][0]["project_id"] == project["id"]
        while process_one(queue, repo, DemoExtractor()):
            pass
        candidates = repo.list_candidates("town", project["id"])
        delivery = next(c for c in candidates if c["field"] == "delivery_date")
        assert delivery["evidence"][0]["quote"] == "Livraison : 2026-12-04"
        assert delivery["source_id"] != result["source"]["id"]
        replay = import_mail(repo, queue, "town", message.as_bytes())
        assert replay["source"]["id"] == result["source"]["id"]
        reply = EmailMessage()
        reply["Subject"] = "Re: Point de chantier"
        reply["Message-ID"] = "<reply@fictif.invalid>"
        reply["References"] = "<first@fictif.invalid>"
        reply.set_content("Action : Vérifier le passage piéton")
        assert import_mail(repo, queue, "town", reply.as_bytes())["source"]["project_id"] == project["id"]
    finally:
        repo.close()


def test_online_backup_and_restore_preserve_memory_and_pending_queue(tmp_path):
    path = tmp_path / "live.sqlite3"
    repo = Repository(path)
    try:
        project = repo.create_project("town", "TR-99", "Chantier fictif")
        repo.add_note("town", project["id"], "Note à conserver au redémarrage")
        job_id = JobQueue(path).enqueue("town", "extract", {"source_id":"pending"}, "pending")
        backup(path, tmp_path / "copy.sqlite3")
        restored = Repository(tmp_path / "copy.sqlite3")
        try:
            assert restored.get_memory("town", project["id"])["notes"][0]["content"] == "Note à conserver au redémarrage"
            assert JobQueue(tmp_path / "copy.sqlite3").get("town", job_id)["status"] == "queued"
        finally:
            restored.close()
    finally:
        repo.close()
