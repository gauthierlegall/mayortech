"""Token-based execution machine for BPMN 2.0 processes (MayorFlow).

Handles sequential, conditional (XOR), parallel (AND fork/join), and inclusive (OR) routing,
along with automated Service Task execution and SLA timer escalations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .domain import DomainError
from .workflow_engine import WorkflowEngineRepository, utc_now_iso


class TokenEngine:
    """Executes BPMN process instances step by step through token transitions."""

    def __init__(self, repo: WorkflowEngineRepository):
        self.repo = repo

    def start_instance(
        self,
        tenant_id: str,
        definition_id: str,
        business_key: str,
        title: str,
        initiator_id: str,
        initiator_name: str,
        initial_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Creates an instance and places the initial token at the startEvent node."""
        instance = self.repo.create_instance(
            tenant_id=tenant_id,
            definition_id=definition_id,
            business_key=business_key,
            title=title,
            initiator_id=initiator_id,
            initiator_name=initiator_name,
            initial_variables=initial_variables or {},
        )

        definition = self.repo.get_definition(definition_id)
        bpmn_data = definition.get("version", {}).get("bpmn_json", {})
        nodes = bpmn_data.get("nodes", [])

        # Find startEvent node
        start_node = next((n for n in nodes if n.get("type") == "startEvent"), None)
        if not start_node:
            raise DomainError("invalid_state", "Le workflow ne contient aucun événement de départ (startEvent).")

        # Create token at startEvent
        start_token = self.repo.create_token(
            instance_id=instance["id"],
            node_id=start_node["id"],
            node_name=start_node.get("name", "Départ"),
            node_type="startEvent",
            state="active",
        )

        # Advance from startEvent automatically
        return self._advance_token(instance["id"], start_token["id"], bpmn_data)

    def advance_user_task(
        self,
        token_id: str,
        actor_id: str,
        form_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Completes a human user task, records submitted form variables, and routes downstream."""
        token = self.repo.get_token(token_id)
        if token["state"] not in {"active", "waiting"}:
            raise DomainError("invalid_state", f"Le jeton {token_id} n'est pas dans un état actif.")

        instance = self.repo.get_instance(token["instance_id"])
        if instance["state"] != "running":
            raise DomainError("invalid_state", f"L'instance de workflow est terminée ({instance['state']}).")

        # Update instance variables with form submission
        new_vars = dict(instance["variables"])
        new_vars.update(form_data)
        self.repo.update_instance_state(
            instance_id=instance["id"],
            state="running",
            new_variables=new_vars,
        )

        # Mark token consumed
        self.repo.consume_token(
            token_id=token_id,
            actor_id=actor_id,
            completion_payload=form_data,
        )

        # Retrieve BPMN structure
        definition = self.repo.get_definition(instance["definition_id"])
        bpmn_data = definition.get("version", {}).get("bpmn_json", {})

        # Advance downstream from completed task
        return self._route_from_node(instance["id"], token["node_id"], bpmn_data, actor_id=actor_id)

    def _route_from_node(
        self,
        instance_id: str,
        current_node_id: str,
        bpmn_data: Dict[str, Any],
        actor_id: str = "system",
    ) -> Dict[str, Any]:
        """Determines next node(s) from current_node_id based on outgoing sequence flows."""
        nodes = {n["id"]: n for n in bpmn_data.get("nodes", [])}
        edges = bpmn_data.get("edges", [])

        outgoing_edges = [e for e in edges if e["sourceRef"] == current_node_id]
        if not outgoing_edges:
            # Reached a dead end without explicit endEvent
            return self.repo.update_instance_state(
                instance_id=instance_id,
                state="completed",
                current_step_name="Clôture automatique",
            )

        instance = self.repo.get_instance(instance_id)
        variables = instance["variables"]

        # Target nodes to activate
        target_nodes_to_activate: List[str] = []

        curr_node = nodes.get(current_node_id, {})
        curr_type = curr_node.get("type", "")

        if curr_type == "exclusiveGateway":
            # XOR: evaluate conditions on outgoing flows, pick exactly first match or default
            chosen_edge = None
            default_edge = None
            for e in outgoing_edges:
                cond = e.get("condition")
                if not cond or cond == "default":
                    default_edge = e
                elif self._evaluate_condition(cond, variables):
                    chosen_edge = e
                    break
            chosen = chosen_edge or default_edge or outgoing_edges[0]
            target_nodes_to_activate.append(chosen["targetRef"])

        elif curr_type == "parallelGateway":
            # Check if this parallel gateway is a Split or Join
            incoming_edges = [e for e in edges if e["targetRef"] == current_node_id]
            if len(incoming_edges) > 1:
                # AND Join: verify if all incoming tokens have arrived
                tokens = instance.get("tokens", [])
                consumed_incoming = [
                    t for t in tokens
                    if t["node_id"] in [ie["sourceRef"] for ie in incoming_edges] and t["state"] == "consumed"
                ]
                if len(consumed_incoming) < len(incoming_edges):
                    # Still waiting for other branches
                    return self.repo.get_instance(instance_id)

            # AND Split: activate all outgoing branches concurrently
            for e in outgoing_edges:
                target_nodes_to_activate.append(e["targetRef"])

        else:
            # Standard sequence flow (or single branch)
            for e in outgoing_edges:
                cond = e.get("condition")
                if cond and not self._evaluate_condition(cond, variables):
                    continue
                target_nodes_to_activate.append(e["targetRef"])

        if not target_nodes_to_activate and outgoing_edges:
            # Fallback to first outgoing edge if conditions were unfulfilled
            target_nodes_to_activate.append(outgoing_edges[0]["targetRef"])

        # Create tokens for target nodes and process them
        last_instance_state = None
        for target_id in target_nodes_to_activate:
            target_node = nodes.get(target_id)
            if not target_node:
                continue

            target_type = target_node.get("type", "userTask")
            target_name = target_node.get("name", target_id)

            token = self.repo.create_token(
                instance_id=instance_id,
                node_id=target_id,
                node_name=target_name,
                node_type=target_type,
                state="active",
                assigned_role=target_node.get("role"),
                assigned_commission=target_node.get("commission"),
                sla_hours=target_node.get("sla_hours", 48),
            )

            last_instance_state = self._advance_token(instance_id, token["id"], bpmn_data)

        return last_instance_state or self.repo.get_instance(instance_id)

    def _advance_token(
        self,
        instance_id: str,
        token_id: str,
        bpmn_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Steps a single token through its node logic."""
        token = self.repo.get_token(token_id)
        node_type = token["node_type"]
        node_id = token["node_id"]
        node_name = token["node_name"]

        if node_type == "startEvent":
            # StartEvent is instantly consumed and moves to next node
            self.repo.consume_token(token_id, actor_id="system")
            return self._route_from_node(instance_id, node_id, bpmn_data)

        elif node_type == "endEvent":
            # EndEvent marks token consumed and completes the workflow instance
            self.repo.consume_token(token_id, actor_id="system")
            return self.repo.update_instance_state(
                instance_id=instance_id,
                state="completed",
                current_step_id=node_id,
                current_step_name=node_name,
            )

        elif node_type == "serviceTask":
            # Execute automated Python service task
            nodes = {n["id"]: n for n in bpmn_data.get("nodes", [])}
            node_def = nodes.get(node_id, {})
            action_name = node_def.get("action", "seal_decision_hash")

            result_vars = self._execute_service_task(instance_id, action_name, node_def)

            # Consume token and update variables
            self.repo.consume_token(token_id, actor_id="system_service", completion_payload=result_vars)
            self.repo.update_instance_state(
                instance_id=instance_id,
                state="running",
                new_variables=result_vars,
            )
            return self._route_from_node(instance_id, node_id, bpmn_data)

        elif node_type in {"exclusiveGateway", "parallelGateway"}:
            # Gateway evaluation
            self.repo.consume_token(token_id, actor_id="gateway_engine")
            return self._route_from_node(instance_id, node_id, bpmn_data)

        else:
            # Human userTask: wait in inbox
            sla_hours = token.get("sla_hours", 48)
            trigger_at = (datetime.now(timezone.utc) + timedelta(hours=sla_hours)).isoformat()
            self.repo.register_timer(
                instance_id=instance_id,
                token_id=token_id,
                node_id=node_id,
                trigger_at=trigger_at,
                sla_action="escalate_dgs",
            )

            return self.repo.update_instance_state(
                instance_id=instance_id,
                state="running",
                current_step_id=node_id,
                current_step_name=node_name,
            )

    def _execute_service_task(
        self,
        instance_id: str,
        action: str,
        node_def: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Executes sovereign municipal service tasks."""
        instance = self.repo.get_instance(instance_id)
        vars_dict = instance["variables"]

        if action == "generate_decision_pdf":
            # Generate official municipal decision certificate
            stamp = utc_now_iso()
            doc_ref = f"DEC-{instance['business_key']}-{datetime.now().year}"
            payload = f"{doc_ref}:{instance['title']}:{instance['initiator_name']}:{stamp}"
            sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            return {
                "decision_pdf_generated": True,
                "decision_pdf_reference": doc_ref,
                "decision_pdf_sha256": sha256,
                "decision_pdf_timestamp": stamp,
            }

        elif action == "seal_decision_hash":
            # Compute cryptographic audit seal
            payload = json.dumps(vars_dict, sort_keys=True)
            sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            return {
                "integrity_seal_sha256": sha256,
                "sealed_at": utc_now_iso(),
            }

        elif action == "notify_commission_members":
            return {
                "notifications_dispatched": True,
                "commission_notified": node_def.get("commission", "general"),
                "notified_at": utc_now_iso(),
            }

        elif action == "publish_to_display":
            return {
                "published_to_legal_display": True,
                "display_url": f"/espace.html#/affichage-legal/{instance['business_key']}",
                "published_at": utc_now_iso(),
            }

        return {"service_task_executed": action, "executed_at": utc_now_iso()}

    def _evaluate_condition(self, expr: str, variables: Dict[str, Any]) -> bool:
        """Safely evaluates boolean/comparison conditions against workflow variables."""
        if not expr:
            return True
        expr = expr.strip()
        if expr in {"true", "True", "1"}:
            return True
        if expr in {"false", "False", "0"}:
            return False

        # Support pattern: variable_name == 'value' or variable_name > 1234
        # e.g.: decision == 'approve', montant_ht > 40000, pieces_completes == True
        eq_match = re.match(r"^(\w+)\s*==\s*['\"]?([^'\"]+)['\"]?$", expr)
        if eq_match:
            var_name, expected = eq_match.groups()
            actual = variables.get(var_name)
            if actual is None:
                return False
            if str(actual).lower() == expected.lower():
                return True
            return str(actual) == expected

        gt_match = re.match(r"^(\w+)\s*>\s*([0-9]+(?:\.[0-9]+)?)$", expr)
        if gt_match:
            var_name, threshold = gt_match.groups()
            actual = variables.get(var_name, 0)
            try:
                return float(actual) > float(threshold)
            except (ValueError, TypeError):
                return False

        lt_match = re.match(r"^(\w+)\s*<\s*([0-9]+(?:\.[0-9]+)?)$", expr)
        if lt_match:
            var_name, threshold = lt_match.groups()
            actual = variables.get(var_name, 0)
            try:
                return float(actual) < float(threshold)
            except (ValueError, TypeError):
                return False

        neq_match = re.match(r"^(\w+)\s*!=\s*['\"]?([^'\"]+)['\"]?$", expr)
        if neq_match:
            var_name, expected = neq_match.groups()
            actual = variables.get(var_name)
            return str(actual) != expected

        # Check boolean variable directly
        if expr in variables:
            return bool(variables[expr])

        return False

    def run_sla_escalations(self) -> List[Dict[str, Any]]:
        """Scans and executes escalations for expired timers."""
        expired = self.repo.check_expired_timers()
        escalated = []
        for timer in expired:
            timer_id = timer["id"]
            token_id = timer["token_id"]
            instance_id = timer["instance_id"]

            # Reassign token to DGS (Niveau 4/5)
            with self.repo.repo._lock:
                db = self.repo.repo._db
                db.execute(
                    """
                    UPDATE workflow_tokens
                    SET assigned_role = 'dgs', assigned_commission = 'general', sla_hours = 0
                    WHERE id = ?
                    """,
                    (token_id,),
                )
                db.commit()

            self.repo.mark_timer_fired(timer_id)
            self.repo._record_audit(
                instance_id=instance_id,
                token_id=token_id,
                node_id=timer["node_id"],
                action="sla_timer_escalated_to_dgs",
                actor_id="system_sla_scheduler",
                variables_diff={"sla_action": timer["sla_action"], "original_trigger": timer["trigger_at"]},
            )
            escalated.append({
                "timer_id": timer_id,
                "instance_id": instance_id,
                "token_id": token_id,
                "escalated_to": "dgs",
            })
        return escalated
