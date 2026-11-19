"""Local liveness only; no external service, content or credentials are queried."""
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener


def app_healthy():
    hostname = urlsplit(os.environ["TRAVAUX_PUBLIC_ORIGIN"]).hostname
    if not hostname:
        return False
    request = Request("http://127.0.0.1:8765/health/live", headers={"Host": hostname})
    with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
        return response.status == 200 and json.loads(response.read(4096)) == {"status": "ok"}


def worker_healthy():
    found = False
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            command = path.read_bytes().rstrip(b"\0").split(b"\0")
        except OSError:
            continue
        if len(command) == 4 and command[1:] == [b"-m", b"travaux", b"worker"]:
            found = True
            break
    if not found:
        return False
    database = Path(os.environ["TRAVAUX_DB"]).resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(database, uri=True, timeout=2) as connection:
        connection.execute("SELECT 1 FROM jobs LIMIT 1").fetchone()
    return True


if __name__ == "__main__":
    try:
        mode = sys.argv[1] if len(sys.argv) == 2 else ""
        healthy = app_healthy() if mode == "app" else worker_healthy() if mode == "worker" else False
    except Exception:
        healthy = False
    raise SystemExit(0 if healthy else 1)
