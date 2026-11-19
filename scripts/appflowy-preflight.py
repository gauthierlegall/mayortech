"""Run with the project's installed Python environment; no writes to AppFlowy."""
from travaux.integrations.preflight import main

if __name__ == "__main__":
    raise SystemExit(main())
