"""Prompt-to-BPMN natural language parser and topological layout engine (MayorFlow).

Translates natural language municipal requests into formal BPMN 2.0 Logic-Core,
validates graph consistency with auto-repair, and computes clean spatial coordinates.
"""

from __future__ import annotations

from collections import defaultdict, deque
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .workflow_engine import BpmnXmlBuilder
from .workflow_graph_validator import WorkflowGraphValidator


class PromptToBpmnEngine:
    """Extracts business logic from natural language and synthesizes BPMN 2.0 graphs."""

    @classmethod
    def parse_prompt(
        cls,
        prompt: str,
        category_hint: Optional[str] = None,
        base_workflow: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Parses user prompt into a structured BPMN graph with auto-layout."""
        prompt_lower = prompt.lower()

        # If modifying an existing workflow incrementally
        if base_workflow and ("ajoute" in prompt_lower or "insère" in prompt_lower or "complète" in prompt_lower):
            return cls._apply_incremental_prompt(base_workflow, prompt)

        # Detect municipal domain/category
        category = category_hint or cls._detect_category(prompt_lower)

        # Detect process title
        title_match = re.search(r"(?:workflow|processus|procédure|instruction|circuit)\s+(?:d['’]|du|de\s+la|des|de)?\s*([^,\.]+)", prompt, re.IGNORECASE)
        name = title_match.group(0).strip().capitalize() if title_match else "Processus Municipal Optimisé"

        # Extract tasks and sequence
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # 1. Start event
        nodes.append({
            "id": "start",
            "type": "startEvent",
            "name": "Dépôt de la demande",
        })

        # 2. Extract step clauses
        sentences = [s.strip() for s in re.split(r"[\n\.;]|\s+puis\s+|\s+ensuite\s+", prompt) if s.strip()]

        step_idx = 1
        last_node_id = "start"

        # Check if there is a conditional branching mentioned
        has_condition = any(
            re.search(r"(?:si|quand|dès lors que|condition)\s+([^,]+)", s, re.IGNORECASE)
            for s in sentences
        )

        for sent in sentences:
            if not sent or len(sent) < 5:
                continue

            # Check if this sentence represents a gateway
            cond_match = re.search(r"(?:si|dans le cas où)\s+([^,]+)", sent, re.IGNORECASE)
            if cond_match:
                condition_text = cond_match.group(1).strip()
                gate_id = f"gate_{step_idx}"
                nodes.append({
                    "id": gate_id,
                    "type": "exclusiveGateway",
                    "name": f"Validation conditionnelle",
                })
                edges.append({
                    "id": f"flow_{last_node_id}_{gate_id}",
                    "sourceRef": last_node_id,
                    "targetRef": gate_id,
                })

                # Branch A (Condition met)
                task_a_id = f"task_{step_idx}_a"
                role_a = cls._extract_role(sent)
                nodes.append({
                    "id": task_a_id,
                    "type": "userTask",
                    "name": cls._clean_task_name(sent),
                    "role": role_a,
                    "commission": category,
                    "sla_hours": 48,
                })
                edges.append({
                    "id": f"flow_{gate_id}_{task_a_id}",
                    "sourceRef": gate_id,
                    "targetRef": task_a_id,
                    "condition": cls._normalize_condition(condition_text),
                })
                last_node_id = task_a_id
                step_idx += 1
                continue

            # Regular task
            task_id = f"task_{step_idx}"
            task_name = cls._clean_task_name(sent)
            role = cls._extract_role(sent)
            is_service = any(k in sent.lower() for k in ["générer", "génération", "pdf", "scellement", "automatique", "notifier", "notification", "affichage"])

            node_type = "serviceTask" if is_service else "userTask"
            action = "generate_decision_pdf" if "pdf" in sent.lower() else "seal_decision_hash" if "scellement" in sent.lower() else "notify_commission_members" if "notif" in sent.lower() else "publish_to_display" if "affich" in sent.lower() else None

            sla = cls._extract_sla_hours(sent) if node_type == "userTask" else 0
            node_def: Dict[str, Any] = {
                "id": task_id,
                "type": node_type,
                "name": task_name,
                "role": role,
                "commission": category,
                "sla_hours": sla,
            }
            if action:
                node_def["action"] = action

            nodes.append(node_def)
            edges.append({
                "id": f"flow_{last_node_id}_{task_id}",
                "sourceRef": last_node_id,
                "targetRef": task_id,
            })
            last_node_id = task_id
            step_idx += 1

        # If fewer than 2 tasks were extracted, create a comprehensive standard municipal chain
        if len(nodes) <= 2:
            nodes, edges = cls._build_standard_chain(category)
            last_node_id = nodes[-1]["id"]

        # Ensure service sealing task before end if not already present
        if not any(n.get("type") == "serviceTask" for n in nodes):
            seal_id = "service_scellement"
            nodes.append({
                "id": seal_id,
                "type": "serviceTask",
                "name": "Scellement Cryptographique SHA-256",
                "action": "seal_decision_hash",
            })
            edges.append({
                "id": f"flow_{last_node_id}_{seal_id}",
                "sourceRef": last_node_id,
                "targetRef": seal_id,
            })
            last_node_id = seal_id

        # 3. End event
        nodes.append({
            "id": "end",
            "type": "endEvent",
            "name": "Dossier instruit et clôturé",
        })
        edges.append({
            "id": f"flow_{last_node_id}_end",
            "sourceRef": last_node_id,
            "targetRef": "end",
        })

        # Validate and auto-repair
        repaired_nodes, repaired_edges = WorkflowGraphValidator.auto_repair(nodes, edges)

        # Compute topological layout (Sugiyama coordinates)
        layout_nodes, layout_edges = cls.compute_sugiyama_layout(repaired_nodes, repaired_edges)

        bpmn_key = f"flow_{re.sub(r'[^a-z0-9_]', '_', name.lower())[:20]}_{uuid.uuid4().hex[:6]}"
        bpmn_xml = BpmnXmlBuilder.to_xml(
            process_id=bpmn_key,
            process_name=name,
            nodes=layout_nodes,
            edges=layout_edges,
        )

        return {
            "key": bpmn_key,
            "name": name,
            "category": category,
            "description": f"Workflow généré automatiquement par prompting : « {prompt[:120]}... »",
            "bpmn_xml": bpmn_xml,
            "bpmn_json": {
                "nodes": layout_nodes,
                "edges": layout_edges,
            },
        }

    @classmethod
    def compute_sugiyama_layout(
        cls,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Calculates 2D coordinates for nodes and orthogonal waypoints for edges."""
        node_map = {n["id"]: dict(n) for n in nodes}
        adj = defaultdict(list)
        in_degree = defaultdict(int)

        for e in edges:
            adj[e["sourceRef"]].append(e["targetRef"])
            in_degree[e["targetRef"]] += 1

        # Layer assignment (Kahn's / topological ranks)
        start_nodes = [nid for nid in node_map if in_degree[nid] == 0]
        if not start_nodes and node_map:
            start_nodes = [next(iter(node_map))]

        ranks: Dict[str, int] = {}
        queue = deque([(nid, 0) for nid in start_nodes])
        while queue:
            curr, r = queue.popleft()
            if curr not in ranks or r > ranks[curr]:
                ranks[curr] = r
                for nxt in adj[curr]:
                    queue.append((nxt, r + 1))

        # Assign remaining unranked nodes
        max_r = max(ranks.values()) if ranks else 0
        for nid in node_map:
            if nid not in ranks:
                max_r += 1
                ranks[nid] = max_r

        # Group nodes by rank
        layers = defaultdict(list)
        for nid, r in ranks.items():
            layers[r].append(nid)

        # Coordinate calculation
        node_width = 160
        node_height = 80
        x_spacing = 240
        y_spacing = 130
        x_start = 80
        y_start = 120

        for r, layer_nodes in layers.items():
            x = x_start + (r * x_spacing)
            total_h = len(layer_nodes) * y_spacing
            y_base = y_start - (total_h // 2) + 60
            for idx, nid in enumerate(layer_nodes):
                y = y_base + (idx * y_spacing)
                node_map[nid]["x"] = x
                node_map[nid]["y"] = max(40, y)

        layout_nodes = list(node_map.values())

        # Edge waypoints (orthogonal routing)
        layout_edges = []
        for e in edges:
            ed = dict(e)
            s_node = node_map.get(e["sourceRef"])
            t_node = node_map.get(e["targetRef"])
            if s_node and t_node:
                s_w = 36 if s_node.get("type") in {"startEvent", "endEvent"} else 50 if "Gateway" in s_node.get("type", "") else 160
                s_h = 36 if s_node.get("type") in {"startEvent", "endEvent"} else 50 if "Gateway" in s_node.get("type", "") else 80
                t_h = 36 if t_node.get("type") in {"startEvent", "endEvent"} else 50 if "Gateway" in t_node.get("type", "") else 80

                p_start = {"x": s_node["x"] + s_w, "y": s_node["y"] + (s_h // 2)}
                p_end = {"x": t_node["x"], "y": t_node["y"] + (t_h // 2)}

                mid_x = (p_start["x"] + p_end["x"]) // 2
                ed["waypoints"] = [
                    p_start,
                    {"x": mid_x, "y": p_start["y"]},
                    {"x": mid_x, "y": p_end["y"]},
                    p_end,
                ]
            layout_edges.append(ed)

        return layout_nodes, layout_edges

    @classmethod
    def _apply_incremental_prompt(
        cls,
        base_workflow: Dict[str, Any],
        prompt: str,
    ) -> Dict[str, Any]:
        """Adds a conditional or sequential step into an existing workflow without resetting."""
        bpmn_data = base_workflow.get("version", {}).get("bpmn_json", {})
        nodes = [dict(n) for n in bpmn_data.get("nodes", [])]
        edges = [dict(e) for e in bpmn_data.get("edges", [])]

        new_step_id = f"task_inc_{uuid.uuid4().hex[:6]}"
        role = cls._extract_role(prompt)
        step_name = cls._clean_task_name(prompt)

        new_node = {
            "id": new_step_id,
            "type": "userTask",
            "name": step_name,
            "role": role,
            "commission": base_workflow.get("category", "general"),
            "sla_hours": 48,
        }

        # Find position to insert (before the last endEvent or service task)
        target_pre_end = next(
            (n for n in reversed(nodes) if n.get("type") in {"userTask", "serviceTask"}),
            None,
        )

        if target_pre_end:
            # Re-wire outgoing edge from target_pre_end
            old_outgoing = [e for e in edges if e["sourceRef"] == target_pre_end["id"]]
            if old_outgoing:
                first_out = old_outgoing[0]
                target_next = first_out["targetRef"]
                first_out["targetRef"] = new_step_id
                edges.append({
                    "id": f"flow_{new_step_id}_{target_next}",
                    "sourceRef": new_step_id,
                    "targetRef": target_next,
                })
            else:
                edges.append({
                    "id": f"flow_{target_pre_end['id']}_{new_step_id}",
                    "sourceRef": target_pre_end["id"],
                    "targetRef": new_step_id,
                })
        nodes.append(new_node)

        repaired_nodes, repaired_edges = WorkflowGraphValidator.auto_repair(nodes, edges)
        layout_nodes, layout_edges = cls.compute_sugiyama_layout(repaired_nodes, repaired_edges)

        bpmn_xml = BpmnXmlBuilder.to_xml(
            process_id=base_workflow.get("key", "workflow_modified"),
            process_name=base_workflow.get("name", "Workflow Modifié"),
            nodes=layout_nodes,
            edges=layout_edges,
        )

        return {
            "key": base_workflow.get("key"),
            "name": base_workflow.get("name"),
            "category": base_workflow.get("category"),
            "description": f"{base_workflow.get('description', '')} (Modifié: {prompt[:60]})",
            "bpmn_xml": bpmn_xml,
            "bpmn_json": {
                "nodes": layout_nodes,
                "edges": layout_edges,
            },
        }

    @staticmethod
    def _detect_category(text: str) -> str:
        if any(w in text for w in ["permis", "urbanisme", "cadastre", "sol", "abf", "zonage", "port"]):
            return "urbanisme"
        if any(w in text for w in ["finance", "marché", "devis", "budget", "dépense", "facture", "cao"]):
            return "finances"
        if any(w in text for w in ["social", "ccas", "secours", "aide", "famille", "enfance", "scolaire"]):
            return "ccas"
        if any(w in text for w in ["culture", "sport", "salle", "avel vor", "subvention", "association"]):
            return "culture"
        if any(w in text for w in ["voirie", "travaux", "ctm", "stationnement", "circulation", "chantier"]):
            return "voirie"
    @staticmethod
    def _extract_sla_hours(text: str) -> int:
        t = text.lower()
        day_match = re.search(r"(\d+)\s*(?:j|jours?)\b", t)
        if day_match:
            return int(day_match.group(1)) * 24
        hour_match = re.search(r"(\d+)\s*(?:h|heures?)\b", t)
        if hour_match:
            return int(hour_match.group(1))
        month_match = re.search(r"(\d+)\s*(?:mois)\b", t)
        if month_match:
            return int(month_match.group(1)) * 720
        if "abf" in t or "patrimoine" in t:
            return 360  # 15 days
        if "ctm" in t or "technique" in t:
            return 192  # 8 days
        if "visa" in t or "maire" in t or "adjoint" in t:
            return 72   # 72 hours
        return 48

    @staticmethod
    def _extract_role(text: str) -> str:
        t = text.lower()
        if "maire" in t and "adjoint" not in t:
            return "maire"
        if "adjoint" in t:
            return "adjoint_delegue"
        if "dgs" in t or "direction générale" in t:
            return "dgs"
        if "instructeur" in t or "urbanisme" in t:
            return "instructeur_ads"
        if "abf" in t:
            return "abf_consultant"
        if "ctm" in t or "travaux" in t:
            return "chef_ctm"
        return "instructeur_communal"

    @staticmethod
    def _clean_task_name(text: str) -> str:
        cleaned = re.sub(r"^(?:ajoute|insère|crée|puis|ensuite|si|dans le cas où)\s+", "", text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:50].capitalize() or "Validation municipale"

    @staticmethod
    def _normalize_condition(text: str) -> str:
        t = text.lower()
        val_match = re.search(r"(\d+[\s\d]*)\s*€?", t)
        if val_match and ("supérieur" in t or ">" in t or "dépasse" in t):
            num = re.sub(r"\s+", "", val_match.group(1))
            return f"montant_ht > {num}"
        if "incomplet" in t or "manque" in t:
            return "pieces_completes == False"
        if "urgence" in t:
            return "urgence == True"
        return "accord == True"

    @classmethod
    def _build_standard_chain(cls, category: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Provides robust 4-step municipal sequence if prompt was short."""
        nodes = [
            {"id": "start", "type": "startEvent", "name": "Dépôt initial"},
            {"id": "t1", "type": "userTask", "name": "Instruction technique", "role": "instructeur", "commission": category, "sla_hours": 48},
            {"id": "t2", "type": "userTask", "name": "Avis hiérarchique chef de service", "role": "chef_service", "commission": category, "sla_hours": 48},
            {"id": "t3", "type": "userTask", "name": "Visa Adjoint délégué", "role": "adjoint_delegue", "commission": category, "sla_hours": 24},
            {"id": "s1", "type": "serviceTask", "name": "Scellement électronique SHA-256", "action": "seal_decision_hash"},
        ]
        edges = [
            {"id": "f_start_t1", "sourceRef": "start", "targetRef": "t1"},
            {"id": "f_t1_t2", "sourceRef": "t1", "targetRef": "t2"},
            {"id": "f_t2_t3", "sourceRef": "t2", "targetRef": "t3"},
            {"id": "f_t3_s1", "sourceRef": "t3", "targetRef": "s1"},
        ]
        return nodes, edges
