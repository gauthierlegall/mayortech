from __future__ import annotations

import json
from pathlib import Path
from datetime import date


def detect_road_traffic_conflict(
    axis_a: str,
    start_a: str,
    end_a: str,
    axis_b: str,
    start_b: str,
    end_b: str,
) -> dict[str, any]:
    """Domain logic detecting overlapping road interventions on identical traffic axes."""
    if axis_a.strip().lower() != axis_b.strip().lower():
        return {"has_conflict": False, "overlap_days": 0}
    
    d_start_a = date.fromisoformat(start_a)
    d_end_a = date.fromisoformat(end_a)
    d_start_b = date.fromisoformat(start_b)
    d_end_b = date.fromisoformat(end_b)

    overlap_start = max(d_start_a, d_start_b)
    overlap_end = min(d_end_a, d_end_b)

    if overlap_start <= overlap_end:
        days = (overlap_end - overlap_start).days + 1
        return {
            "has_conflict": True,
            "axis": axis_a,
            "overlap_start": overlap_start.isoformat(),
            "overlap_end": overlap_end.isoformat(),
            "overlap_days": days,
        }
    return {"has_conflict": False, "overlap_days": 0}


def test_pwa_manifest_exists_and_conforms():
    root = Path(__file__).resolve().parent.parent
    manifest_path = root / "web" / "manifest.json"
    assert manifest_path.exists(), "web/manifest.json must be present for PWA terrain"

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["display"] == "standalone"
    assert data["background_color"] == "#F7F7F5"
    assert data["theme_color"] == "#102A4C"
    assert "terrain" in data["start_url"]


def test_road_traffic_conflict_detection_and_arbitration():
    # Simulation: ARR-2026-019 (Quai du Tinduff / Rue des Ajoncs) vs TRV-2026-038
    axis = "Rue des Ajoncs ↔ Quai du Tinduff"
    conflict = detect_road_traffic_conflict(
        axis_a=axis,
        start_a="2026-11-24",
        end_a="2026-11-28",
        axis_b=axis,
        start_b="2026-11-25",
        end_b="2026-11-30",
    )
    assert conflict["has_conflict"] is True
    assert conflict["overlap_days"] == 4
    assert conflict["overlap_start"] == "2026-11-25"
    assert conflict["overlap_end"] == "2026-11-28"

    # Arbitration: post-shift of TRV-2026-038 to 2026-12-02
    resolved = detect_road_traffic_conflict(
        axis_a=axis,
        start_a="2026-11-24",
        end_a="2026-11-28",
        axis_b=axis,
        start_b="2026-12-02",
        end_b="2026-12-07",
    )
    assert resolved["has_conflict"] is False
    assert resolved["overlap_days"] == 0


def test_track_and_trace_public_bundle_exists():
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "web" / "product" / "assets"
    assert assets_dir.exists(), "web/product/assets must exist"
    
    # Verify TrackAndTracePage chunk was bundled
    chunks = list(assets_dir.glob("TrackAndTracePage-*.js"))
    assert len(chunks) >= 1, "TrackAndTracePage must be bundled in web/product/assets"
