from travaux.jobs import JobQueue


def test_durable_idempotent_enqueue_and_expired_worker_cannot_ack(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    queue = JobQueue(path)
    first = queue.enqueue("tenant-a", "extract", {"source_id":"a"}, "mail-a")
    assert queue.enqueue("tenant-a", "extract", {"source_id":"a"}, "mail-a") == first
    assert queue.enqueue("tenant-b", "extract", {"source_id":"b"}, "mail-a") != first
    old = queue.claim("worker-old", lease_seconds=-1)
    queue = JobQueue(path)
    replacement = queue.claim("worker-new")
    assert replacement["id"] == old["id"]
    assert not queue.complete(old["id"], old["lease_token"], {})
    assert queue.complete(replacement["id"], replacement["lease_token"], {"ok":True})
    assert queue.get("tenant-a", first)["status"] == "done"
    assert queue.get("other-tenant", first) is None
