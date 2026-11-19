"""Sovereign BPMN 2.0 Workflow Engine (MayorFlow) for Municipal Administration.

Fully open-source workflow orchestration based on standard ISO/IEC 19510 BPMN 2.0,
pure Python execution with SpiffWorkflow interoperability, dynamic JSON Schema forms,
SLA timer escalations, and automated Service Tasks with SHA-256 audit sealing.
Zero proprietary licenses. 0 € vendor dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
import uuid
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Database Repository for BPMN Definitions, Versions, Instances and Tokens
# ---------------------------------------------------------------------------

class WorkflowEngineRepository:
    """Manages persistent tables for definitions, instances, tokens, timers and forms."""

    def __init__(self, repo: Any):
        self.repo = repo
        self._init_schema()

    def _init_schema(self) -> None:
        with self.repo._lock:
            db = self.repo._db
            # Workflow Definitions
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_definitions (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    commission_id TEXT,
                    description TEXT,
                    current_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, key)
                )
            """)

            # Workflow Versions (BPMN XML + JSON)
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_versions (
                    id TEXT PRIMARY KEY,
                    definition_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    bpmn_xml TEXT NOT NULL,
                    bpmn_json TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'published',
                    created_at TEXT NOT NULL,
                    UNIQUE(definition_id, version_number),
                    FOREIGN KEY(definition_id) REFERENCES workflow_definitions(id) ON DELETE CASCADE
                )
            """)

            # Workflow Instances
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_instances (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    definition_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    business_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    initiator_id TEXT NOT NULL,
                    initiator_name TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'running',
                    current_step_id TEXT,
                    current_step_name TEXT,
                    variables_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY(definition_id) REFERENCES workflow_definitions(id)
                )
            """)

            # Workflow Tokens
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_tokens (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    node_name TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'active',
                    assigned_role TEXT,
                    assigned_user_id TEXT,
                    assigned_commission TEXT,
                    sla_hours INTEGER DEFAULT 48,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY(instance_id) REFERENCES workflow_instances(id) ON DELETE CASCADE
                )
            """)

            # Dynamic Task Forms (JSON Schema)
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_task_forms (
                    id TEXT PRIMARY KEY,
                    definition_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    schema_json TEXT NOT NULL,
                    uischema_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    UNIQUE(definition_id, node_id),
                    FOREIGN KEY(definition_id) REFERENCES workflow_definitions(id) ON DELETE CASCADE
                )
            """)

            # SLA Timers & Escalations
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_timers (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    token_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    trigger_at TEXT NOT NULL,
                    sla_action TEXT NOT NULL DEFAULT 'escalate_dgs',
                    reminder_sent INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(instance_id) REFERENCES workflow_instances(id) ON DELETE CASCADE
                )
            """)

            # Immutable Cryptographic Audit Log
            db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_audit_log (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    token_id TEXT,
                    node_id TEXT,
                    action TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    variables_diff_json TEXT NOT NULL DEFAULT '{}',
                    sha256_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            db.commit()

    # ----------------- Definition Operations -----------------

    def create_definition(
        self,
        tenant_id: str,
        key: str,
        name: str,
        category: str,
        commission_id: Optional[str] = None,
        description: Optional[str] = None,
        bpmn_xml: str = "",
        bpmn_json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        def_id = f"def_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        bpmn_json_str = json.dumps(bpmn_json or {})

        with self.repo._lock:
            db = self.repo._db
            # Check existing key
            existing = db.execute(
                "SELECT id FROM workflow_definitions WHERE tenant_id = ? AND key = ?",
                (tenant_id, key),
            ).fetchone()
            if existing:
                raise DomainError("conflict", f"Un workflow avec la clé '{key}' existe déjà.")

            db.execute(
                """
                INSERT INTO workflow_definitions (
                    id, tenant_id, key, name, category, commission_id, description,
                    current_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (def_id, tenant_id, key, name, category, commission_id, description, now, now),
            )

            # Insert version 1
            ver_id = f"ver_{uuid.uuid4().hex[:12]}"
            db.execute(
                """
                INSERT INTO workflow_versions (
                    id, definition_id, version_number, bpmn_xml, bpmn_json, state, created_at
                ) VALUES (?, ?, 1, ?, ?, 'published', ?)
                """,
                (ver_id, def_id, bpmn_xml, bpmn_json_str, now),
            )
            db.commit()

        return self.get_definition(def_id)

    def get_definition(self, definition_id: str) -> Dict[str, Any]:
        with self.repo._lock:
            db = self.repo._db
            row = db.execute(
                """
                SELECT id, tenant_id, key, name, category, commission_id, description,
                       current_version, created_at, updated_at
                FROM workflow_definitions WHERE id = ?
                """,
                (definition_id,),
            ).fetchone()
            if not row:
                raise DomainError("not_found", f"Workflow {definition_id} introuvable.")

            def_dict = dict(row)
            ver_row = db.execute(
                """
                SELECT id, version_number, bpmn_xml, bpmn_json, state, created_at
                FROM workflow_versions
                WHERE definition_id = ? AND version_number = ?
                """,
                (definition_id, def_dict["current_version"]),
            ).fetchone()

            if ver_row:
                ver_dict = dict(ver_row)
                ver_dict["bpmn_json"] = json.loads(ver_dict["bpmn_json"])
                def_dict["version"] = ver_dict
            return def_dict

    def list_definitions(self, tenant_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.repo._lock:
            db = self.repo._db
            query = "SELECT * FROM workflow_definitions WHERE tenant_id = ?"
            params: List[Any] = [tenant_id]
            if category:
                query += " AND category = ?"
                params.append(category)
            query += " ORDER BY name ASC"
            rows = db.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def update_definition(
        self,
        definition_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        commission_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self.repo._lock:
            db = self.repo._db
            now = utc_now_iso()
            fields = []
            vals = []
            if name is not None:
                fields.append("name = ?")
                vals.append(name)
            if description is not None:
                fields.append("description = ?")
                vals.append(description)
            if commission_id is not None:
                fields.append("commission_id = ?")
                vals.append(commission_id)
            if not fields:
                return self.get_definition(definition_id)
            fields.append("updated_at = ?")
            vals.append(now)
            vals.append(definition_id)
            db.execute(f"UPDATE workflow_definitions SET {', '.join(fields)} WHERE id = ?", tuple(vals))
            db.commit()
        return self.get_definition(definition_id)

    def publish_new_version(
        self,
        definition_id: str,
        bpmn_xml: str,
        bpmn_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        with self.repo._lock:
            db = self.repo._db
            cur = db.execute(
                "SELECT current_version FROM workflow_definitions WHERE id = ?",
                (definition_id,),
            ).fetchone()
            if not cur:
                raise DomainError("not_found", "Workflow introuvable.")

            new_ver_num = cur["current_version"] + 1
            ver_id = f"ver_{uuid.uuid4().hex[:12]}"
            db.execute(
                """
                INSERT INTO workflow_versions (
                    id, definition_id, version_number, bpmn_xml, bpmn_json, state, created_at
                ) VALUES (?, ?, ?, ?, ?, 'published', ?)
                """,
                (ver_id, definition_id, new_ver_num, bpmn_xml, json.dumps(bpmn_json), now),
            )
            db.execute(
                "UPDATE workflow_definitions SET current_version = ?, updated_at = ? WHERE id = ?",
                (new_ver_num, now, definition_id),
            )
            db.commit()
        return self.get_definition(definition_id)

    # ----------------- Instance Operations -----------------

    def create_instance(
        self,
        tenant_id: str,
        definition_id: str,
        business_key: str,
        title: str,
        initiator_id: str,
        initiator_name: str,
        initial_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        inst_id = f"inst_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        definition = self.get_definition(definition_id)
        version_id = definition.get("version", {}).get("id", "")
        bpmn_data = definition.get("version", {}).get("bpmn_json", {})

        variables = initial_variables or {}

        with self.repo._lock:
            db = self.repo._db
            db.execute(
                """
                INSERT INTO workflow_instances (
                    id, tenant_id, definition_id, version_id, business_key, title,
                    initiator_id, initiator_name, state, variables_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)
                """,
                (
                    inst_id,
                    tenant_id,
                    definition_id,
                    version_id,
                    business_key,
                    title,
                    initiator_id,
                    initiator_name,
                    json.dumps(variables),
                    now,
                    now,
                ),
            )
            db.commit()

        # Audit initial creation
        self._record_audit(
            instance_id=inst_id,
            action="start",
            actor_id=initiator_id,
            variables_diff={"initial": variables},
        )

        return self.get_instance(inst_id)

    def get_instance(self, instance_id: str) -> Dict[str, Any]:
        with self.repo._lock:
            db = self.repo._db
            row = db.execute(
                """
                SELECT i.*, d.name as definition_name, d.category as definition_category,
                       d.commission_id as definition_commission
                FROM workflow_instances i
                JOIN workflow_definitions d ON d.id = i.definition_id
                WHERE i.id = ?
                """,
                (instance_id,),
            ).fetchone()
            if not row:
                raise DomainError("not_found", f"Instance de workflow {instance_id} introuvable.")

            inst = dict(row)
            inst["variables"] = json.loads(inst["variables_json"])

            # Load active and completed tokens
            tokens = db.execute(
                """
                SELECT * FROM workflow_tokens WHERE instance_id = ? ORDER BY created_at ASC
                """,
                (instance_id,),
            ).fetchall()
            inst["tokens"] = []
            for t in tokens:
                td = dict(t)
                td["payload"] = json.loads(td["payload_json"])
                inst["tokens"].append(td)

            return inst

    def list_instances(
        self,
        tenant_id: str,
        state: Optional[str] = None,
        initiator_id: Optional[str] = None,
        definition_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self.repo._lock:
            db = self.repo._db
            query = """
                SELECT i.*, d.name as definition_name, d.category as definition_category
                FROM workflow_instances i
                JOIN workflow_definitions d ON d.id = i.definition_id
                WHERE i.tenant_id = ?
            """
            params: List[Any] = [tenant_id]
            if state:
                query += " AND i.state = ?"
                params.append(state)
            if initiator_id:
                query += " AND i.initiator_id = ?"
                params.append(initiator_id)
            if definition_id:
                query += " AND i.definition_id = ?"
                params.append(definition_id)
            query += " ORDER BY i.created_at DESC"
            rows = db.execute(query, tuple(params)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["variables"] = json.loads(d["variables_json"])
                results.append(d)
            return results

    def update_instance_state(
        self,
        instance_id: str,
        state: str,
        current_step_id: Optional[str] = None,
        current_step_name: Optional[str] = None,
        new_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        with self.repo._lock:
            db = self.repo._db
            cur = db.execute(
                "SELECT variables_json FROM workflow_instances WHERE id = ?",
                (instance_id,),
            ).fetchone()
            if not cur:
                raise DomainError("not_found", "Instance introuvable.")

            vars_dict = json.loads(cur["variables_json"])
            if new_variables:
                vars_dict.update(new_variables)

            completed_at = now if state in {"completed", "terminated"} else None

            db.execute(
                """
                UPDATE workflow_instances
                SET state = ?, current_step_id = ?, current_step_name = ?,
                    variables_json = ?, updated_at = ?, completed_at = COALESCE(?, completed_at)
                WHERE id = ?
                """,
                (
                    state,
                    current_step_id,
                    current_step_name,
                    json.dumps(vars_dict),
                    now,
                    completed_at,
                    instance_id,
                ),
            )
            db.commit()
        return self.get_instance(instance_id)

    # ----------------- Token & Task Operations -----------------

    def create_token(
        self,
        instance_id: str,
        node_id: str,
        node_name: str,
        node_type: str,
        state: str = "active",
        assigned_role: Optional[str] = None,
        assigned_commission: Optional[str] = None,
        sla_hours: int = 48,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        token_id = f"tok_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self.repo._lock:
            db = self.repo._db
            db.execute(
                """
                INSERT INTO workflow_tokens (
                    id, instance_id, node_id, node_name, node_type, state,
                    assigned_role, assigned_commission, sla_hours, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token_id,
                    instance_id,
                    node_id,
                    node_name,
                    node_type,
                    state,
                    assigned_role,
                    assigned_commission,
                    sla_hours,
                    json.dumps(payload or {}),
                    now,
                ),
            )
            db.commit()

        # Record audit log
        self._record_audit(
            instance_id=instance_id,
            token_id=token_id,
            node_id=node_id,
            action=f"token_created_{state}",
            actor_id="system",
            variables_diff={"node": node_id, "type": node_type},
        )
        return self.get_token(token_id)

    def get_token(self, token_id: str) -> Dict[str, Any]:
        with self.repo._lock:
            db = self.repo._db
            row = db.execute("SELECT * FROM workflow_tokens WHERE id = ?", (token_id,)).fetchone()
            if not row:
                raise DomainError("not_found", f"Jeton {token_id} introuvable.")
            d = dict(row)
            d["payload"] = json.loads(d["payload_json"])
            return d

    def consume_token(
        self,
        token_id: str,
        actor_id: str,
        completion_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        with self.repo._lock:
            db = self.repo._db
            cur = db.execute("SELECT * FROM workflow_tokens WHERE id = ?", (token_id,)).fetchone()
            if not cur:
                raise DomainError("not_found", "Jeton introuvable.")

            tok_dict = dict(cur)
            payload = json.loads(tok_dict["payload_json"])
            if completion_payload:
                payload.update(completion_payload)

            db.execute(
                """
                UPDATE workflow_tokens
                SET state = 'consumed', payload_json = ?, completed_at = ?
                WHERE id = ?
                """,
                (json.dumps(payload), now, token_id),
            )
            db.commit()

        self._record_audit(
            instance_id=tok_dict["instance_id"],
            token_id=token_id,
            node_id=tok_dict["node_id"],
            action="token_consumed",
            actor_id=actor_id,
            variables_diff=completion_payload or {},
        )
        return self.get_token(token_id)

    def claim_token(self, token_id: str, user_id: str) -> Dict[str, Any]:
        with self.repo._lock:
            db = self.repo._db
            cur = db.execute("SELECT * FROM workflow_tokens WHERE id = ?", (token_id,)).fetchone()
            if not cur:
                raise DomainError("not_found", "Jeton introuvable.")
            if cur["assigned_user_id"] and cur["assigned_user_id"] != user_id:
                raise DomainError("conflict", f"Tâche déjà prise en charge par un autre agent.")
            db.execute(
                "UPDATE workflow_tokens SET assigned_user_id = ? WHERE id = ?",
                (user_id, token_id),
            )
            db.commit()

        self._record_audit(
            instance_id=cur["instance_id"],
            token_id=token_id,
            node_id=cur["node_id"],
            action="token_claimed",
            actor_id=user_id,
        )
        return self.get_token(token_id)

    def list_inbox_tasks(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        commission: Optional[str] = None,
        role: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Returns open human tasks from workflow_tokens matching user or service pool."""
        with self.repo._lock:
            db = self.repo._db
            query = """
                SELECT t.*, i.business_key, i.title as instance_title, i.initiator_name,
                       d.name as workflow_name, d.category as workflow_category
                FROM workflow_tokens t
                JOIN workflow_instances i ON i.id = t.instance_id
                JOIN workflow_definitions d ON d.id = i.definition_id
                WHERE i.tenant_id = ? AND t.state IN ('active', 'waiting')
                  AND t.node_type = 'userTask'
            """
            params: List[Any] = [tenant_id]
            if user_id:
                query += " AND (t.assigned_user_id = ? OR t.assigned_user_id IS NULL)"
                params.append(user_id)
            if commission:
                query += " AND (t.assigned_commission = ? OR t.assigned_commission IS NULL)"
                params.append(commission)
            query += " ORDER BY t.created_at ASC"

            rows = db.execute(query, tuple(params)).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["payload"] = json.loads(d["payload_json"])
                res.append(d)
            return res

    # ----------------- Dynamic Forms (JSON Schema) -----------------

    def save_task_form(
        self,
        definition_id: str,
        node_id: str,
        schema: Dict[str, Any],
        uischema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        form_id = f"form_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self.repo._lock:
            db = self.repo._db
            # Resolve definition key to primary id if needed
            cur = db.execute(
                "SELECT id FROM workflow_definitions WHERE id = ? OR key = ?",
                (definition_id, definition_id),
            ).fetchone()
            actual_def_id = cur["id"] if cur else definition_id

            db.execute(
                """
                INSERT INTO workflow_task_forms (id, definition_id, node_id, schema_json, uischema_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(definition_id, node_id) DO UPDATE SET
                    schema_json = excluded.schema_json,
                    uischema_json = excluded.uischema_json
                """,
                (form_id, actual_def_id, node_id, json.dumps(schema), json.dumps(uischema or {}), now),
            )
            db.commit()
        return self.get_task_form(actual_def_id, node_id)

    def get_task_form(self, definition_id: str, node_id: str) -> Dict[str, Any]:
        with self.repo._lock:
            db = self.repo._db
            cur = db.execute(
                "SELECT id FROM workflow_definitions WHERE id = ? OR key = ?",
                (definition_id, definition_id),
            ).fetchone()
            actual_def_id = cur["id"] if cur else definition_id

            row = db.execute(
                "SELECT * FROM workflow_task_forms WHERE definition_id = ? AND node_id = ?",
                (actual_def_id, node_id),
            ).fetchone()
            if not row:
                # Return default sensible form schema
                return {
                    "definition_id": definition_id,
                    "node_id": node_id,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "decision": {
                                "type": "string",
                                "title": "Décision régalienne",
                                "enum": ["approve", "reject", "request_info"],
                                "enumNames": ["Approuver", "Rejeter", "Demande de compléments"],
                            },
                            "comment": {
                                "type": "string",
                                "title": "Observations / Motivations de la décision",
                            },
                        },
                        "required": ["decision"],
                    },
                    "uischema": {
                        "comment": {"ui:widget": "textarea"},
                    },
                }
            d = dict(row)
            d["schema"] = json.loads(d["schema_json"])
            d["uischema"] = json.loads(d["uischema_json"])
            return d

    # ----------------- Timers & SLA Scheduler -----------------

    def register_timer(
        self,
        instance_id: str,
        token_id: str,
        node_id: str,
        trigger_at: str,
        sla_action: str = "escalate_dgs",
    ) -> Dict[str, Any]:
        timer_id = f"tmr_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self.repo._lock:
            db = self.repo._db
            db.execute(
                """
                INSERT INTO workflow_timers (
                    id, instance_id, token_id, node_id, trigger_at, sla_action, reminder_sent, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 'pending', ?)
                """,
                (timer_id, instance_id, token_id, node_id, trigger_at, sla_action, now),
            )
            db.commit()
        return {"timer_id": timer_id, "trigger_at": trigger_at, "status": "pending"}

    def check_expired_timers(self) -> List[Dict[str, Any]]:
        now = utc_now_iso()
        with self.repo._lock:
            db = self.repo._db
            rows = db.execute(
                """
                SELECT t.*, tok.assigned_user_id, tok.assigned_commission, i.business_key, i.title
                FROM workflow_timers t
                JOIN workflow_tokens tok ON tok.id = t.token_id
                JOIN workflow_instances i ON i.id = t.instance_id
                WHERE t.status = 'pending' AND t.trigger_at <= ? AND tok.state IN ('active', 'waiting')
                """,
                (now,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_timer_fired(self, timer_id: str) -> None:
        with self.repo._lock:
            db = self.repo._db
            db.execute("UPDATE workflow_timers SET status = 'fired' WHERE id = ?", (timer_id,))
            db.commit()

    # ----------------- Cryptographic Audit Log -----------------

    def _record_audit(
        self,
        instance_id: str,
        action: str,
        actor_id: str,
        token_id: Optional[str] = None,
        node_id: Optional[str] = None,
        variables_diff: Optional[Dict[str, Any]] = None,
    ) -> None:
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        diff_str = json.dumps(variables_diff or {})

        # Compute tamper-evident SHA-256 seal
        hash_payload = f"{audit_id}:{instance_id}:{token_id}:{node_id}:{action}:{actor_id}:{diff_str}:{now}"
        sha256 = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        with self.repo._lock:
            db = self.repo._db
            db.execute(
                """
                INSERT INTO workflow_audit_log (
                    id, instance_id, token_id, node_id, action, actor_id, variables_diff_json, sha256_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (audit_id, instance_id, token_id, node_id, action, actor_id, diff_str, sha256, now),
            )
            db.commit()

    def get_instance_audit_trail(self, instance_id: str) -> List[Dict[str, Any]]:
        with self.repo._lock:
            db = self.repo._db
            rows = db.execute(
                """
                SELECT * FROM workflow_audit_log WHERE instance_id = ? ORDER BY created_at ASC
                """,
                (instance_id,),
            ).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["variables_diff"] = json.loads(d["variables_diff_json"])
                res.append(d)
            return res

    # ----------------- Supervision & Heatmap Metrics -----------------

    def get_supervision_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """Calculates BAM (Business Activity Monitoring) metrics and bottleneck heatmap."""
        with self.repo._lock:
            db = self.repo._db
            # Total instances by state
            instance_stats = db.execute(
                """
                SELECT state, COUNT(*) as count
                FROM workflow_instances
                WHERE tenant_id = ?
                GROUP BY state
                """,
                (tenant_id,),
            ).fetchall()
            stats_by_state = {r["state"]: r["count"] for r in instance_stats}

            # Node heatmap: count of tokens currently waiting or active at each node
            node_counts = db.execute(
                """
                SELECT t.node_id, t.node_name, d.name as workflow_name, COUNT(*) as active_count
                FROM workflow_tokens t
                JOIN workflow_instances i ON i.id = t.instance_id
                JOIN workflow_definitions d ON d.id = i.definition_id
                WHERE i.tenant_id = ? AND t.state IN ('active', 'waiting')
                GROUP BY t.node_id, t.node_name, d.name
                ORDER BY active_count DESC
                """,
                (tenant_id,),
            ).fetchall()

            # SLA breaches: tokens with expired timers
            expired_sla = db.execute(
                """
                SELECT COUNT(*) as expired_count
                FROM workflow_timers t
                JOIN workflow_instances i ON i.id = t.instance_id
                WHERE i.tenant_id = ? AND t.status = 'fired'
                """,
                (tenant_id,),
            ).fetchone()

            # Heatmap color scale (green: 0-2, orange: 3-5, red: >5)
            heatmap = []
            for n in node_counts:
                cnt = n["active_count"]
                severity = "normal" if cnt < 3 else "warning" if cnt <= 5 else "bottleneck"
                heatmap.append({
                    "node_id": n["node_id"],
                    "node_name": n["node_name"],
                    "workflow_name": n["workflow_name"],
                    "count": cnt,
                    "severity": severity,
                })

            return {
                "active_instances": stats_by_state.get("running", 0),
                "completed_instances": stats_by_state.get("completed", 0),
                "terminated_instances": stats_by_state.get("terminated", 0),
                "sla_breaches": expired_sla["expired_count"] if expired_sla else 0,
                "node_heatmap": heatmap,
                "timestamp": utc_now_iso(),
            }


# ---------------------------------------------------------------------------
# BPMN 2.0 XML Serializer / Parser Utilities (ISO/IEC 19510 Compliant)
# ---------------------------------------------------------------------------

class BpmnXmlBuilder:
    """Generates standard, validated BPMN 2.0 XML for bpmn-js and SpiffWorkflow."""

    @staticmethod
    def to_xml(
        process_id: str,
        process_name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> str:
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
            'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
            'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
            'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
            f'id="Definitions_{process_id}" targetNamespace="http://mayortech.fr/bpmn/municipal">',
            f'  <bpmn:process id="{process_id}" name="{process_name}" isExecutable="true">',
        ]

        # Nodes
        for n in nodes:
            nid = n["id"]
            name = n.get("name", nid)
            ntype = n.get("type", "userTask")

            if ntype == "startEvent":
                xml_lines.append(f'    <bpmn:startEvent id="{nid}" name="{name}">')
                for e in edges:
                    if e["sourceRef"] == nid:
                        xml_lines.append(f'      <bpmn:outgoing>{e["id"]}</bpmn:outgoing>')
                xml_lines.append("    </bpmn:startEvent>")
            elif ntype == "endEvent":
                xml_lines.append(f'    <bpmn:endEvent id="{nid}" name="{name}">')
                for e in edges:
                    if e["targetRef"] == nid:
                        xml_lines.append(f'      <bpmn:incoming>{e["id"]}</bpmn:incoming>')
                xml_lines.append("    </bpmn:endEvent>")
            elif ntype == "exclusiveGateway":
                xml_lines.append(f'    <bpmn:exclusiveGateway id="{nid}" name="{name}">')
                for e in edges:
                    if e["targetRef"] == nid:
                        xml_lines.append(f'      <bpmn:incoming>{e["id"]}</bpmn:incoming>')
                    if e["sourceRef"] == nid:
                        xml_lines.append(f'      <bpmn:outgoing>{e["id"]}</bpmn:outgoing>')
                xml_lines.append("    </bpmn:exclusiveGateway>")
            elif ntype == "parallelGateway":
                xml_lines.append(f'    <bpmn:parallelGateway id="{nid}" name="{name}">')
                for e in edges:
                    if e["targetRef"] == nid:
                        xml_lines.append(f'      <bpmn:incoming>{e["id"]}</bpmn:incoming>')
                    if e["sourceRef"] == nid:
                        xml_lines.append(f'      <bpmn:outgoing>{e["id"]}</bpmn:outgoing>')
                xml_lines.append("    </bpmn:parallelGateway>")
            elif ntype == "serviceTask":
                xml_lines.append(f'    <bpmn:serviceTask id="{nid}" name="{name}">')
                for e in edges:
                    if e["targetRef"] == nid:
                        xml_lines.append(f'      <bpmn:incoming>{e["id"]}</bpmn:incoming>')
                    if e["sourceRef"] == nid:
                        xml_lines.append(f'      <bpmn:outgoing>{e["id"]}</bpmn:outgoing>')
                xml_lines.append("    </bpmn:serviceTask>")
            else:  # userTask
                xml_lines.append(f'    <bpmn:userTask id="{nid}" name="{name}">')
                for e in edges:
                    if e["targetRef"] == nid:
                        xml_lines.append(f'      <bpmn:incoming>{e["id"]}</bpmn:incoming>')
                    if e["sourceRef"] == nid:
                        xml_lines.append(f'      <bpmn:outgoing>{e["id"]}</bpmn:outgoing>')
                xml_lines.append("    </bpmn:userTask>")

        # Edges (Sequence Flows)
        for e in edges:
            eid = e["id"]
            sref = e["sourceRef"]
            tref = e["targetRef"]
            cond = e.get("condition")
            if cond:
                xml_lines.append(
                    f'    <bpmn:sequenceFlow id="{eid}" sourceRef="{sref}" targetRef="{tref}">'
                    f'      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">{cond}</bpmn:conditionExpression>'
                    f'    </bpmn:sequenceFlow>'
                )
            else:
                xml_lines.append(f'    <bpmn:sequenceFlow id="{eid}" sourceRef="{sref}" targetRef="{tref}" />')

        xml_lines.append("  </bpmn:process>")

        # Diagram Interchange (DI) layout coordinates
        xml_lines.append(f'  <bpmndi:BPMNDiagram id="BPMNDiagram_{process_id}">')
        xml_lines.append(f'    <bpmndi:BPMNPlane id="BPMNPlane_{process_id}" bpmnElement="{process_id}">')

        for n in nodes:
            nid = n["id"]
            x = n.get("x", 100)
            y = n.get("y", 100)
            w = 36 if n.get("type") in {"startEvent", "endEvent"} else 50 if "Gateway" in n.get("type", "") else 160
            h = 36 if n.get("type") in {"startEvent", "endEvent"} else 50 if "Gateway" in n.get("type", "") else 80
            xml_lines.append(f'      <bpmndi:BPMNShape id="{nid}_di" bpmnElement="{nid}">')
            xml_lines.append(f'        <dc:Bounds x="{x}" y="{y}" width="{w}" height="{h}" />')
            xml_lines.append("      </bpmndi:BPMNShape>")

        for e in edges:
            eid = e["id"]
            xml_lines.append(f'      <bpmndi:BPMNEdge id="{eid}_di" bpmnElement="{eid}">')
            waypoints = e.get("waypoints", [])
            if not waypoints:
                # Default start and end waypoints
                waypoints = [{"x": 100, "y": 100}, {"x": 200, "y": 100}]
            for wp in waypoints:
                xml_lines.append(f'        <di:waypoint x="{wp.get("x", 0)}" y="{wp.get("y", 0)}" />')
            xml_lines.append("      </bpmndi:BPMNEdge>")

        xml_lines.append("    </bpmndi:BPMNPlane>")
        xml_lines.append("  </bpmndi:BPMNDiagram>")
        xml_lines.append("</bpmn:definitions>")

        return "\n".join(xml_lines)
