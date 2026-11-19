from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Depends, Response, status
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError
from .municipal_directory import MunicipalDirectoryRepository


class OrganigramExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: str = Field(pattern="^(svg|json|html)$")
    commission_filter: Optional[str] = Field(default=None)


class MunicipalOrganigramEngine:
    def __init__(self, directory: MunicipalDirectoryRepository):
        self.directory = directory

    def get_topology(self, tenant_id: str) -> Dict[str, Any]:
        entries = self.directory.list_entries(tenant_id, active_only=True)
        delegations = self.directory.list_delegations(tenant_id, active_only=True)

        # Index entries by matricule and email
        by_matricule = {e["matricule"]: e for e in entries}

        # Structure the organigram tree
        nodes = []
        links = []

        # 1. Maire
        maire = by_matricule.get("ELU-001")
        maire_node = {
            "id": "node-maire",
            "type": "executive",
            "title": "Maire de Plougastel-Daoulas",
            "holder": maire["display_name"] if maire else "Dominique CAP",
            "matricule": "ELU-001",
            "niveau": 4,
            "role": "admin",
            "color": "#1e3a8a",
            "category": "Exécutif Délibératif",
            "email": maire["email"] if maire else "maire@ville-plougastel.bzh",
            "delegation_signature": True,
            "x": 600,
            "y": 40
        }
        nodes.append(maire_node)

        # 2. DGS
        dgs = by_matricule.get("AGT-001")
        dgs_node = {
            "id": "node-dgs",
            "type": "administration",
            "title": "Direction Générale des Services (DGS)",
            "holder": dgs["display_name"] if dgs else "DGS Titulaire",
            "matricule": "AGT-001",
            "niveau": 5,
            "role": "admin",
            "color": "#065f46",
            "category": "Administration & Sceau",
            "email": dgs["email"] if dgs else "dgs@ville-plougastel.bzh",
            "delegation_signature": True,
            "x": 600,
            "y": 160
        }
        nodes.append(dgs_node)
        links.append({"source": "node-maire", "target": "node-dgs", "type": "hierarchical"})

        # 3. The 4 Commissions & Services
        commissions_def = [
            {
                "id": "commission-1",
                "label": "1. Finances & Commande Publique",
                "elu_mat": "ELU-003",
                "color": "#c2410c",
                "x": 150,
                "services": [
                    {"code": "SRV-FIN", "label": "Comptabilité & Budget", "chef_mat": "AGT-020", "agents": ["AGT-022"]},
                    {"code": "SRV-MAR", "label": "Marchés Publics & CAO", "chef_mat": "AGT-021", "agents": []}
                ]
            },
            {
                "id": "commission-2",
                "label": "2. Enfance, Jeunesse & Solidarités",
                "elu_mat": "ELU-005",
                "color": "#be185d",
                "x": 450,
                "services": [
                    {"code": "SRV-CCAS", "label": "CCAS & Action Sociale", "chef_mat": "AGT-040", "agents": []},
                    {"code": "SRV-SCO", "label": "Affaires Scolaires & Restauration", "chef_mat": "AGT-041", "agents": ["AGT-042"]}
                ]
            },
            {
                "id": "commission-3",
                "label": "3. Urbanisme, Travaux & Ports",
                "elu_mat": "ELU-002",
                "color": "#15803d",
                "x": 750,
                "services": [
                    {"code": "SRV-URB", "label": "Urbanisme & Droit des Sols", "chef_mat": "AGT-010", "agents": ["AGT-011"]},
                    {"code": "SRV-POR", "label": "Ports du Tinduff & Cales", "chef_mat": "AGT-012", "agents": []},
                    {"code": "SRV-CTM", "label": "Centre Technique Municipal", "chef_mat": "AGT-013", "agents": []}
                ]
            },
            {
                "id": "commission-4",
                "label": "4. Culture, Sport & Associations",
                "elu_mat": "ELU-004",
                "color": "#6b21a8",
                "x": 1050,
                "services": [
                    {"code": "SRV-CUL", "label": "Pôle Culturel Avel Vor", "chef_mat": "AGT-030", "agents": ["AGT-032"]},
                    {"code": "SRV-ASS", "label": "Vie Associative & Salles", "chef_mat": "AGT-031", "agents": []}
                ]
            }
        ]

        for c_idx, c_def in enumerate(commissions_def):
            comm_node_id = f"node-{c_def['id']}"
            elu_agent = by_matricule.get(c_def["elu_mat"])
            nodes.append({
                "id": comm_node_id,
                "type": "commission",
                "title": c_def["label"],
                "holder": elu_agent["display_name"] if elu_agent else f"Adjoint Délégué ({c_def['elu_mat']})",
                "matricule": c_def["elu_mat"],
                "niveau": 4,
                "role": "admin",
                "color": c_def["color"],
                "category": "Commission Permanente",
                "email": elu_agent["email"] if elu_agent else "",
                "delegation_signature": True,
                "x": c_def["x"],
                "y": 290
            })
            links.append({"source": "node-dgs", "target": comm_node_id, "type": "functional"})

            # Services under this commission
            for s_idx, s_def in enumerate(c_def["services"]):
                srv_node_id = f"node-{s_def['code']}"
                chef_agent = by_matricule.get(s_def["chef_mat"])
                nodes.append({
                    "id": srv_node_id,
                    "type": "service",
                    "title": s_def["label"],
                    "holder": chef_agent["display_name"] if chef_agent else f"Chef de Service ({s_def['chef_mat']})",
                    "matricule": s_def["chef_mat"],
                    "niveau": chef_agent["niveau"] if chef_agent else 3,
                    "role": chef_agent["role"] if chef_agent else "editor",
                    "color": c_def["color"],
                    "category": "Service Opérationnel",
                    "email": chef_agent["email"] if chef_agent else "",
                    "delegation_signature": chef_agent["delegation_signature"] if chef_agent else False,
                    "x": c_def["x"],
                    "y": 420 + (s_idx * 110)
                })
                links.append({"source": comm_node_id, "target": srv_node_id, "type": "operational"})

                # Agents attached
                for a_idx, a_mat in enumerate(s_def["agents"]):
                    agent_rec = by_matricule.get(a_mat)
                    if agent_rec:
                        agt_node_id = f"node-{agent_rec['matricule']}"
                        nodes.append({
                            "id": agt_node_id,
                            "type": "agent",
                            "title": agent_rec["poste"],
                            "holder": agent_rec["display_name"],
                            "matricule": agent_rec["matricule"],
                            "niveau": agent_rec["niveau"],
                            "role": agent_rec["role"],
                            "color": c_def["color"],
                            "category": "Agent Métier",
                            "email": agent_rec["email"],
                            "delegation_signature": False,
                            "x": c_def["x"] + 40,
                            "y": 420 + (s_idx * 110) + 50 + (a_idx * 50)
                        })
                        links.append({"source": srv_node_id, "target": agt_node_id, "type": "subordinate"})

        return {
            "city": "Ville de Plougastel-Daoulas",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_nodes": len(nodes),
            "total_links": len(links),
            "active_delegations_count": len(delegations),
            "nodes": nodes,
            "links": links
        }

    def export_organigram_svg(self, tenant_id: str) -> str:
        topo = self.get_topology(tenant_id)
        width = 1300
        height = 950

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">',
            f'<defs>',
            f'  <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#1e3a8a"/><stop offset="100%" stop-color="#3b82f6"/></linearGradient>',
            f'  <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.08"/></filter>',
            f'</defs>',
            # Title Cartouche
            f'<rect x="20" y="15" width="380" height="70" rx="8" fill="#ffffff" stroke="#cbd5e1" stroke-width="1" filter="url(#shadow)"/>',
            f'<text x="35" y="42" font-size="16" font-weight="bold" fill="#0f172a">VILLE DE PLOUGASTEL-DAOULAS</text>',
            f'<text x="35" y="62" font-size="12" fill="#64748b">Organigramme & Matrice des Habilitations · MayorTech</text>',
            f'<g id="links">'
        ]

        # Draw links
        node_map = {n["id"]: n for n in topo["nodes"]}
        for l in topo["links"]:
            src = node_map.get(l["source"])
            tgt = node_map.get(l["target"])
            if src and tgt:
                sx, sy = src["x"] + 110, src["y"] + 40
                tx, ty = tgt["x"] + 110, tgt["y"]
                svg_parts.append(f'<path d="M {sx} {sy} C {sx} {(sy+ty)/2}, {tx} {(sy+ty)/2}, {tx} {ty}" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="{"4 4" if l["type"] == "functional" else "none"}"/>')
        svg_parts.append('</g>')

        # Draw nodes
        svg_parts.append('<g id="nodes">')
        for n in topo["nodes"]:
            x, y = n["x"], n["y"]
            w, h = 220, 65
            svg_parts.append(f'<g transform="translate({x}, {y})" filter="url(#shadow)">')
            svg_parts.append(f'  <rect width="{w}" height="{h}" rx="6" fill="#ffffff" stroke="{n["color"]}" stroke-width="2"/>')
            svg_parts.append(f'  <rect x="0" y="0" width="6" height="{h}" rx="2" fill="{n["color"]}"/>')
            svg_parts.append(f'  <text x="14" y="20" font-size="11" font-weight="bold" fill="#1e293b">{n["title"][:32]}</text>')
            svg_parts.append(f'  <text x="14" y="38" font-size="12" font-weight="600" fill="#0f172a">{n["holder"]}</text>')
            svg_parts.append(f'  <text x="14" y="54" font-size="10" fill="#64748b">{n["matricule"]} · Niv. {n["niveau"]}</text>')
            svg_parts.append(f'</g>')
        svg_parts.append('</g>')
        svg_parts.append('</svg>')
        return "\n".join(svg_parts)


def register_organigram_routes(app: FastAPI, repo, tenant_id: str, actor_dep, organigram: MunicipalOrganigramEngine):
    @app.get("/api/v1/municipal/organigram/topology")
    def get_organigram_topology(current=Depends(actor_dep)):
        return organigram.get_topology(tenant_id)

    @app.post("/api/v1/municipal/organigram/export")
    def export_organigram(body: OrganigramExportRequest, current=Depends(actor_dep)):
        if body.format == "svg":
            svg_content = organigram.export_organigram_svg(tenant_id)
            return Response(
                content=svg_content,
                media_type="image/svg+xml",
                headers={"Content-Disposition": 'attachment; filename="organigramme-plougastel.svg"'}
            )
        elif body.format == "json":
            return organigram.get_topology(tenant_id)
        elif body.format == "html":
            svg_content = organigram.export_organigram_svg(tenant_id)
            html_doc = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Organigramme Officiel · Ville de Plougastel-Daoulas</title>
  <style>
    body {{ margin: 0; padding: 20px; background: #f8fafc; font-family: sans-serif; }}
    .container {{ max-width: 1300px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
    h1 {{ font-size: 20px; color: #1e3a8a; margin-top: 0; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Ville de Plougastel-Daoulas · Organigramme Réglementaire Certifié</h1>
    {svg_content}
  </div>
</body>
</html>"""
            return Response(
                content=html_doc,
                media_type="text/html",
                headers={"Content-Disposition": 'attachment; filename="organigramme-plougastel.html"'}
            )
        raise DomainError("invalid_input", "Format supporté : svg, json, html.")
