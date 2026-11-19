import sys
import time
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from travaux.api import create_app
from travaux.config import Settings
import uvicorn

PORT = 19862

def serve():
    data_dir = ROOT / ".agent" / "tmp" / "server-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        mode="demo",
        db_path=data_dir / "gallery.sqlite3",
        tenant_id="plougastel-audit",
        llm="demo",
        allowed_hosts=("127.0.0.1", "localhost"),
        password_hash="test-hash",
        auth_mode="password",
    )
    app = create_app(settings)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

if __name__ == "__main__":
    t = threading.Thread(target=serve, daemon=True)
    t.start()

    time.sleep(1.5)

    res = subprocess.run(
        ["node", ".agent/skills/visual-qa/scripts/audit.mjs", f"http://127.0.0.1:{PORT}/demo.html#/workflows"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

    sys.exit(res.returncode)
