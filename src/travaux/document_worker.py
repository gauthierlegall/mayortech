"""Sous-processus sans secrets pour les parseurs PDF/DOCX, jamais un shell."""
import base64
import json
import sys


def main():
    if sys.platform != "win32":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    from .documents import _extract_document
    payload = json.loads(sys.stdin.read(7_000_000))
    data = base64.b64decode(payload["data"], validate=True)
    result = _extract_document(payload["filename"], data)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
