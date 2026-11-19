"""Use Windows/system trust roots while preserving TLS validation for the audit."""
import importlib.metadata

import truststore

truststore.inject_into_ssl()
entry = next(point for point in importlib.metadata.distribution("pip-audit").entry_points if point.name == "pip-audit")
raise SystemExit(entry.load()())
