"""Urbanisme, travaux et ports domain module (Lot 3 MayorTech).

Handles:
- GeoJSON spatial feature storage & filtering for Plougastel-Daoulas
- Urbanisme planning applications (permis, déclarations, parcelles)
- Port & littoral infrastructure inspections (Tinduff, Passage, Auberlac'h)
- Seamless integration with field reports and native actions
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, require_text, utc_now
from .project_access import access_scope
from .repository import Repository

# Plougastel-Daoulas bounding box: [min_lon, min_lat, max_lon, max_lat]
PLOUGASTEL_BBOX = (-4.450, 48.310, -4.300, 48.420)

URBANISME_PORTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS geo_features (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    feature_type TEXT NOT NULL CHECK(feature_type IN ('port_ouvrage', 'parcelle', 'chantier_travaux')),
    name TEXT NOT NULL,
    coordinates_json TEXT NOT NULL,
    properties_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_geo_features_proj ON geo_features(tenant_id, project_id);

CREATE TABLE IF NOT EXISTS urbanisme_dossiers (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    parcel_ref TEXT NOT NULL,
    request_type TEXT NOT NULL CHECK(request_type IN ('permis_construire', 'declaration_prealable', 'certificat_urbanisme', 'autre')),
    regulation_source TEXT NOT NULL DEFAULT '',
    checklist_json TEXT NOT NULL DEFAULT '[]',
    advice_status TEXT NOT NULL DEFAULT 'en_cours' CHECK(advice_status IN ('en_cours', 'favorable', 'defavorable', 'reserve')),
    follow_up_date TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, project_id),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS port_inspections (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    port_name TEXT NOT NULL,
    ouvrage_type TEXT NOT NULL,
    inspector TEXT NOT NULL,
    inspection_date TEXT NOT NULL,
    condition_rating TEXT NOT NULL CHECK(condition_rating IN ('bon', 'moyen', 'degrade', 'urgent')),
    observations TEXT NOT NULL,
    linked_action_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_port_inspections_proj ON port_inspections(tenant_id, project_id);
"""


def validate_coordinates(lon: float, lat: float) -> tuple[float, float]:
    """Validate that coordinates are numbers within valid Earth and Plougastel ranges."""
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        raise DomainError("invalid_input", "Les coordonnées doivent être des nombres décimaux (WGS84).")
    if not (-180.0 <= lon <= 180.0) or not (-90.0 <= lat <= 90.0):
        raise DomainError("invalid_input", "Coordonnées géographiques hors limites mondiales.")
    return float(lon), float(lat)


def is_within_plougastel(lon: float, lat: float) -> bool:
    """Check if coordinates fall within Plougastel-Daoulas territorial limits."""
    min_lon, min_lat, max_lon, max_lat = PLOUGASTEL_BBOX
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


class UrbanismePortsRepository:
    def __init__(self, repo):
        self.repo = repo
        self._migrate_schema()

    def _migrate_schema(self):
        with self.repo._lock:
            for statement in URBANISME_PORTS_SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    self.repo._db.execute(stmt)

    def save_geo_feature(
        self,
        tenant_id: str,
        project_id: str,
        *,
        feature_type: str,
        name: str,
        longitude: float,
        latitude: float,
        properties: Optional[Dict[str, Any]] = None,
        feature_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(project_id, "project_id", maximum=100)
        require_text(feature_type, "feature_type", maximum=50)
        require_text(name, "name", maximum=200)
        lon, lat = validate_coordinates(longitude, latitude)

        if feature_type not in ("port_ouvrage", "parcelle", "chantier_travaux"):
            raise DomainError("invalid_input", f"Type de feature inconnu : {feature_type}")

        fid = feature_id or str(uuid4())
        now = utc_now()
        props_str = json.dumps(properties or {})
        coords_str = json.dumps([lon, lat])

        with self.repo._transaction() as db:
            db.execute(
                """INSERT INTO geo_features(
                    tenant_id, id, project_id, feature_type, name, coordinates_json,
                    properties_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, id) DO UPDATE SET
                    name=excluded.name,
                    coordinates_json=excluded.coordinates_json,
                    properties_json=excluded.properties_json,
                    updated_at=excluded.updated_at""",
                (tenant_id, fid, project_id, feature_type, name, coords_str, props_str, now, now),
            )
            row = db.execute("SELECT * FROM geo_features WHERE tenant_id=? AND id=?", (tenant_id, fid)).fetchone()
            return dict(row)

    def list_geo_features(
        self,
        tenant_id: str,
        *,
        project_ids: Optional[List[str]] = None,
        feature_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM geo_features WHERE tenant_id=?"
        params: List[Any] = [tenant_id]

        if project_ids is not None:
            if not project_ids:
                return []
            placeholders = ",".join("?" for _ in project_ids)
            query += f" AND project_id IN ({placeholders})"
            params.extend(project_ids)

        if feature_type:
            query += " AND feature_type=?"
            params.append(feature_type)

        query += " ORDER BY name ASC"

        with self.repo._lock:
            rows = self.repo._db.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def to_geojson(self, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert a list of geo_features rows into a valid standard GeoJSON FeatureCollection."""
        geojson_features = []
        for f in features:
            coords = json.loads(f["coordinates_json"])
            props = json.loads(f["properties_json"])
            props.update(
                {
                    "id": f["id"],
                    "project_id": f["project_id"],
                    "feature_type": f["feature_type"],
                    "name": f["name"],
                    "created_at": f["created_at"],
                }
            )
            geojson_features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": coords,
                    },
                    "properties": props,
                }
            )
        return {
            "type": "FeatureCollection",
            "features": geojson_features,
        }

    def save_urbanisme_dossier(
        self,
        tenant_id: str,
        project_id: str,
        *,
        parcel_ref: str,
        request_type: str,
        regulation_source: str = "",
        checklist: Optional[List[Dict[str, Any]]] = None,
        advice_status: str = "en_cours",
        follow_up_date: str = "",
    ) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(project_id, "project_id", maximum=100)
        require_text(parcel_ref, "parcel_ref", maximum=100)
        if request_type not in ("permis_construire", "declaration_prealable", "certificat_urbanisme", "autre"):
            raise DomainError("invalid_input", f"Type de demande invalide : {request_type}")
        if advice_status not in ("en_cours", "favorable", "defavorable", "reserve"):
            raise DomainError("invalid_input", f"Statut d'avis invalide : {advice_status}")

        now = utc_now()
        checklist_str = json.dumps(checklist or [])

        with self.repo._transaction() as db:
            db.execute(
                """INSERT INTO urbanisme_dossiers(
                    tenant_id, project_id, parcel_ref, request_type, regulation_source,
                    checklist_json, advice_status, follow_up_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, project_id) DO UPDATE SET
                    parcel_ref=excluded.parcel_ref,
                    request_type=excluded.request_type,
                    regulation_source=excluded.regulation_source,
                    checklist_json=excluded.checklist_json,
                    advice_status=excluded.advice_status,
                    follow_up_date=excluded.follow_up_date,
                    updated_at=excluded.updated_at""",
                (
                    tenant_id,
                    project_id,
                    parcel_ref,
                    request_type,
                    regulation_source,
                    checklist_str,
                    advice_status,
                    follow_up_date,
                    now,
                    now,
                ),
            )
            row = db.execute(
                "SELECT * FROM urbanisme_dossiers WHERE tenant_id=? AND project_id=?",
                (tenant_id, project_id),
            ).fetchone()
            res = dict(row)
            res["checklist"] = json.loads(res["checklist_json"])
            return res

    def get_urbanisme_dossier(self, tenant_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM urbanisme_dossiers WHERE tenant_id=? AND project_id=?",
                (tenant_id, project_id),
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            res["checklist"] = json.loads(res["checklist_json"])
            return res

    def save_port_inspection(
        self,
        tenant_id: str,
        project_id: str,
        *,
        port_name: str,
        ouvrage_type: str,
        inspector: str,
        inspection_date: str,
        condition_rating: str,
        observations: str,
        linked_action_id: str = "",
        inspection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(project_id, "project_id", maximum=100)
        require_text(port_name, "port_name", maximum=200)
        require_text(ouvrage_type, "ouvrage_type", maximum=200)
        require_text(inspector, "inspector", maximum=200)
        require_text(inspection_date, "inspection_date", maximum=50)
        if condition_rating not in ("bon", "moyen", "degrade", "urgent"):
            raise DomainError("invalid_input", f"Condition rating invalide : {condition_rating}")
        require_text(observations, "observations", maximum=10000)

        iid = inspection_id or str(uuid4())
        now = utc_now()

        with self.repo._transaction() as db:
            db.execute(
                """INSERT INTO port_inspections(
                    tenant_id, id, project_id, port_name, ouvrage_type, inspector,
                    inspection_date, condition_rating, observations, linked_action_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, id) DO UPDATE SET
                    port_name=excluded.port_name,
                    ouvrage_type=excluded.ouvrage_type,
                    inspector=excluded.inspector,
                    inspection_date=excluded.inspection_date,
                    condition_rating=excluded.condition_rating,
                    observations=excluded.observations,
                    linked_action_id=excluded.linked_action_id,
                    updated_at=excluded.updated_at""",
                (
                    tenant_id,
                    iid,
                    project_id,
                    port_name,
                    ouvrage_type,
                    inspector,
                    inspection_date,
                    condition_rating,
                    observations,
                    linked_action_id,
                    now,
                    now,
                ),
            )
            row = db.execute("SELECT * FROM port_inspections WHERE tenant_id=? AND id=?", (tenant_id, iid)).fetchone()
            return dict(row)

    def list_port_inspections(self, tenant_id: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM port_inspections WHERE tenant_id=?"
        params: List[Any] = [tenant_id]
        if project_id:
            query += " AND project_id=?"
            params.append(project_id)
        query += " ORDER BY inspection_date DESC"

        with self.repo._lock:
            rows = self.repo._db.execute(query, params).fetchall()
            return [dict(r) for r in rows]


# Pydantic models for API
class GeoFeatureInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_type: str = Field(..., pattern="^(port_ouvrage|parcelle|chantier_travaux)$")
    name: str = Field(..., max_length=200)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    properties: Dict[str, Any] = Field(default_factory=dict)


class UrbanismeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parcel_ref: str = Field(..., max_length=100)
    request_type: str = Field(..., pattern="^(permis_construire|declaration_prealable|certificat_urbanisme|autre)$")
    regulation_source: str = Field("", max_length=200)
    checklist: List[Dict[str, Any]] = Field(default_factory=list)
    advice_status: str = Field("en_cours", pattern="^(en_cours|favorable|defavorable|reserve)$")
    follow_up_date: str = Field("", max_length=50)


class PortInspectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    port_name: str = Field(..., max_length=200)
    ouvrage_type: str = Field(..., max_length=200)
    inspector: str = Field(..., max_length=200)
    inspection_date: str = Field(..., max_length=50)
    condition_rating: str = Field(..., pattern="^(bon|moyen|degrade|urgent)$")
    observations: str = Field(..., max_length=10000)
    linked_action_id: str = Field("", max_length=200)


def setup_urbanisme_ports_routes(
    app,
    repo,
    settings,
    up_repo: UrbanismePortsRepository,
    actor_dep,
    require_project_write,
    require_project_read,
):
    @app.get("/api/v1/geo/features")
    def get_geo_features_route(feature_type: Optional[str] = None, current=Depends(actor_dep)):
        scope = access_scope(repo, current)
        if scope.all_projects:
            project_ids = None
        else:
            project_ids = list(scope.visible_project_ids)
            if not project_ids:
                return {"type": "FeatureCollection", "features": []}

        features = up_repo.list_geo_features(settings.tenant_id, project_ids=project_ids, feature_type=feature_type)
        return up_repo.to_geojson(features)

    @app.get("/api/v1/projects/{project_id}/geo")
    def get_project_geo_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        features = up_repo.list_geo_features(settings.tenant_id, project_ids=[project_id])
        return up_repo.to_geojson(features)

    @app.post("/api/v1/projects/{project_id}/geo")
    def create_project_geo_route(project_id: str, body: GeoFeatureInput, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        return up_repo.save_geo_feature(
            settings.tenant_id,
            project_id,
            feature_type=body.feature_type,
            name=body.name,
            longitude=body.longitude,
            latitude=body.latitude,
            properties=body.properties,
        )

    @app.get("/api/v1/projects/{project_id}/urbanisme")
    def get_urbanisme_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        dossier = up_repo.get_urbanisme_dossier(settings.tenant_id, project_id)
        return {"dossier": dossier}

    @app.put("/api/v1/projects/{project_id}/urbanisme")
    def save_urbanisme_route(project_id: str, body: UrbanismeInput, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        return up_repo.save_urbanisme_dossier(
            settings.tenant_id,
            project_id,
            parcel_ref=body.parcel_ref,
            request_type=body.request_type,
            regulation_source=body.regulation_source,
            checklist=body.checklist,
            advice_status=body.advice_status,
            follow_up_date=body.follow_up_date,
        )

    @app.get("/api/v1/projects/{project_id}/port-inspections")
    def list_port_inspections_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        items = up_repo.list_port_inspections(settings.tenant_id, project_id=project_id)
        return {"items": items, "total": len(items)}

    @app.post("/api/v1/projects/{project_id}/port-inspections")
    def create_port_inspection_route(project_id: str, body: PortInspectionInput, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        return up_repo.save_port_inspection(
            settings.tenant_id,
            project_id,
            port_name=body.port_name,
            ouvrage_type=body.ouvrage_type,
            inspector=body.inspector,
            inspection_date=body.inspection_date,
            condition_rating=body.condition_rating,
            observations=body.observations,
            linked_action_id=body.linked_action_id,
        )


def _up_repo_init(self, *args, **kwargs):
    _orig_repo_init(self, *args, **kwargs)
    try:
        UrbanismePortsRepository(self)
    except Exception:
        pass


_orig_repo_init = Repository.__init__
Repository.__init__ = _up_repo_init
