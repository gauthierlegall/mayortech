import subprocess
import time
import socket
import sys
from pathlib import Path

PORT = 19860

def listening():
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", PORT)) == 0

def main():
    server = None
    if not listening():
        print(f"Starting server on port {PORT}...")
        server = subprocess.Popen(
            [sys.executable, "scripts/capture_audit_epuration.py", "--serve-only"],
            cwd=str(Path(__file__).resolve().parents[1])
        )
        for _ in range(50):
            if listening():
                break
            time.sleep(0.2)
        if not listening():
            raise RuntimeError("Server failed to start")

    try:
        print("Running node .agent/skills/visual-qa/scripts/audit.mjs...")
        res = subprocess.run(
            ["node", ".agent/skills/visual-qa/scripts/audit.mjs", f"http://127.0.0.1:{PORT}/demo.html"],
            capture_output=True,
            text=True
        )
        print("STDOUT:")
        print(res.stdout)
        if res.stderr:
            print("STDERR:")
            print(res.stderr)
        if res.returncode != 0:
            sys.exit(res.returncode)
    finally:
        if server:
            server.terminate()

if __name__ == "__main__":
    main()
