"""Collaboration metadata subordinate to canonical Yjs action references.

No title, action status or current action date is mirrored here. Native row IDs
are references supplied by the client; Python does not parse opaque Yjs state.
"""
from __future__ import annotations

import json
import re
import calendar
from datetime import date, timedelta
from uuid import uuid4

from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, canonical_json, require_text, utc_now
from .project_access import access_scope


def _invalid(message):
    raise DomainError('invalid_input', message)


def _native_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value):
        _invalid('La référence native de cette action est invalide.')
    return value


def _revision(value):
    if type(value) is not int or value < 0:
        _invalid('La version exacte relue est requise.')


def _pagination(limit, offset):
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 100_000:
        _invalid('La pagination doit rester comprise dans les limites prévues.')


class ActionCollaboration:
    def __init__(self, repo, settings):
        self.repo, self.settings = repo, settings
        with repo._transaction() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS action_collaboration(
                tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,page_id TEXT NOT NULL,action_id TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0,assignee_id TEXT,checklist_json TEXT NOT NULL DEFAULT '[]',
                updated_by TEXT NOT NULL,updated_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,project_id,page_id,action_id),
                FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id),
                FOREIGN KEY(tenant_id,page_id) REFERENCES native_pages(tenant_id,id))''')
            db.execute('''CREATE TABLE IF NOT EXISTS action_comments(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,
                tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,page_id TEXT NOT NULL,action_id TEXT NOT NULL,
                author_id TEXT NOT NULL,client_id TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,
                UNIQUE(tenant_id,project_id,page_id,action_id,author_id,client_id),
                FOREIGN KEY(tenant_id,project_id,page_id,action_id)
                    REFERENCES action_collaboration(tenant_id,project_id,page_id,action_id))''')
            db.execute('CREATE INDEX IF NOT EXISTS action_comments_reference ON action_comments(tenant_id,project_id,page_id,action_id,sequence)')
            db.execute('''CREATE TABLE IF NOT EXISTS action_recurrence_rules(
                id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,page_id TEXT NOT NULL,action_id TEXT NOT NULL,
                revision INTEGER NOT NULL,unit TEXT NOT NULL,interval INTEGER NOT NULL,anchor_start TEXT NOT NULL,
                span_days INTEGER NOT NULL,month_end INTEGER NOT NULL,active INTEGER NOT NULL,
                created_by TEXT NOT NULL,updated_by TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                UNIQUE(tenant_id,id),UNIQUE(tenant_id,project_id,page_id,action_id),
                FOREIGN KEY(tenant_id,project_id,page_id,action_id)
                    REFERENCES action_collaboration(tenant_id,project_id,page_id,action_id))''')
            db.execute('''CREATE TABLE IF NOT EXISTS action_occurrences(
                operation_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,rule_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,rule_revision INTEGER NOT NULL,plan_start TEXT NOT NULL,plan_due TEXT NOT NULL,
                phase TEXT NOT NULL CHECK(phase IN ('prepared','confirmed')),prepared_by TEXT NOT NULL,created_at TEXT NOT NULL,
                confirmed_page_id TEXT,row_id TEXT,page_revision_hash TEXT,confirmed_by TEXT,confirmed_at TEXT,
                UNIQUE(tenant_id,rule_id,ordinal),
                FOREIGN KEY(tenant_id,rule_id) REFERENCES action_recurrence_rules(tenant_id,id))''')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS action_occurrence_native_row ON action_occurrences(tenant_id,confirmed_page_id,row_id) WHERE row_id IS NOT NULL')
            db.execute('CREATE INDEX IF NOT EXISTS action_occurrence_plan ON action_occurrences(tenant_id,project_id,rule_id,ordinal)')

    def _guard(self, tenant, actor, project_id, *, write=False):
        if not isinstance(actor, dict) or actor.get('tenant_id') != tenant or actor.get('permissions', {}).get('workspace', {}).get('write' if write else 'read') is not True:
            raise DomainError('forbidden', 'Votre accès ne permet pas cette opération sur l’action.')
        identity = require_text(actor.get('actor_id'), 'actor_id', maximum=200)
        access_scope(self.repo, actor).require_project_contents(project_id, write=write)
        self.repo.get_project(tenant, project_id)
        return identity

    def _reference(self, tenant, actor, project_id, page_id, action_id, *, write=False):
        identity = self._guard(tenant, actor, project_id, write=write)
        _native_id(page_id), _native_id(action_id)
        page = self.repo._db.execute('SELECT 1 FROM native_pages WHERE tenant_id=? AND project_id=? AND id=?', (tenant, project_id, page_id)).fetchone()
        if page is None:
            raise DomainError('not_found', 'Cette page ne fait pas partie du dossier autorisé.')
        return identity

    def _member(self, tenant, actor, project_id, member_id):
        if getattr(self.settings, 'auth_mode', None) == 'oidc':
            row = self.repo._db.execute('SELECT actor_id,display_name,role FROM identity_members WHERE tenant_id=? AND actor_id=? AND active=1', (tenant, member_id)).fetchone()
            if row and access_scope(self.repo, {'tenant_id': tenant, 'actor_id': member_id}).permits_project(project_id):
                return {'id': row['actor_id'], 'display_name': row['display_name'], 'role': row['role']}
        elif not self.settings.auth_required and member_id == actor['actor_id']:
            return {'id': member_id, 'display_name': 'Visiteur de démonstration', 'role': 'visitor'}
        return None

    def participants(self, tenant, actor, project_id, *, limit=50, offset=0):
        _pagination(limit, offset)
        with self.repo._lock:
            self._guard(tenant, actor, project_id)
            if getattr(self.settings, 'auth_mode', None) != 'oidc':
                item = self._member(tenant, actor, project_id, actor['actor_id'])
                items = [item] if item else []
                return {'items': items[offset:offset+limit], 'total': len(items), 'limit': limit, 'offset': offset}
            where = """m.tenant_id=? AND m.active=1 AND (
                EXISTS (SELECT 1 FROM project_grants g WHERE g.tenant_id=m.tenant_id AND g.actor_id=m.actor_id AND g.project_id=?)
                OR EXISTS (
                    SELECT 1 FROM commission_members cm
                    JOIN projects p ON p.tenant_id=cm.tenant_id AND p.commission_id=cm.commission_id
                    WHERE cm.tenant_id=m.tenant_id AND cm.actor_id=m.actor_id AND p.id=? AND p.visibility != 'restricted'
                )
                OR (
                    m.role='admin' AND EXISTS (
                        SELECT 1 FROM projects p
                        WHERE p.tenant_id=m.tenant_id AND p.id=? AND (p.commission_id='commission-3' OR p.commission_id IS NULL) AND p.visibility != 'restricted'
                    )
                )
            )"""
            args = (tenant, project_id, project_id, project_id)
            total = self.repo._db.execute('SELECT count(*) FROM identity_members m WHERE '+where, args).fetchone()[0]
            rows = self.repo._db.execute('SELECT m.actor_id AS id,m.display_name,m.role FROM identity_members m WHERE '+where+' ORDER BY m.display_name,m.actor_id LIMIT ? OFFSET ?', (*args, limit, offset)).fetchall()
            return {'items': [dict(row) for row in rows], 'total': total, 'limit': limit, 'offset': offset}

    def _ensure(self, db, tenant, actor_id, project_id, page_id, action_id):
        db.execute('INSERT OR IGNORE INTO action_collaboration(tenant_id,project_id,page_id,action_id,updated_by,updated_at) VALUES(?,?,?,?,?,?)', (tenant, project_id, page_id, action_id, actor_id, utc_now()))

    def _state(self, tenant, actor, project_id, page_id, action_id):
        row = self.repo._db.execute('SELECT revision,assignee_id,checklist_json FROM action_collaboration WHERE tenant_id=? AND project_id=? AND page_id=? AND action_id=?', (tenant, project_id, page_id, action_id)).fetchone()
        member = self._member(tenant, actor, project_id, row['assignee_id']) if row and row['assignee_id'] else None
        rule = self.repo._db.execute('SELECT * FROM action_recurrence_rules WHERE tenant_id=? AND project_id=? AND page_id=? AND action_id=?', (tenant, project_id, page_id, action_id)).fetchone()
        return {'project_id': project_id, 'page_id': page_id, 'action_id': action_id, 'revision': row['revision'] if row else 0, 'assignee_id': row['assignee_id'] if row else None, 'assignee': member, 'checklist': json.loads(row['checklist_json']) if row else [], 'recurrence': self._rule_dto(rule) if rule else None}

    def get(self, tenant, actor, project_id, *, page_id, action_id):
        with self.repo._lock:
            self._reference(tenant, actor, project_id, page_id, action_id)
            return self._state(tenant, actor, project_id, page_id, action_id)

    @staticmethod
    def _checklist(value):
        if not isinstance(value, list) or len(value) > 100:
            _invalid('Une checklist contient au maximum cent éléments.')
        result, seen = [], set()
        for item in value:
            if not isinstance(item, dict) or set(item) != {'id', 'text', 'checked'} or type(item['checked']) is not bool:
                _invalid('Chaque élément doit comporter une référence, un texte et une case cochée ou non.')
            ident = require_text(item['id'], 'checklist_id', maximum=100)
            if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', ident) or ident in seen:
                _invalid('Les références des éléments doivent être uniques et valides.')
            text = require_text(item['text'], 'checklist_text', maximum=1000).strip()
            if not text or '\x00' in text: _invalid('Le texte de l’élément est invalide.')
            seen.add(ident); result.append({'id': ident, 'text': text, 'checked': item['checked']})
        if sum(len(item['text']) for item in result) > 40_000:
            _invalid('La checklist est trop volumineuse.')
        return result

    def patch(self, tenant, actor, project_id, *, page_id, action_id, expected_revision, changes):
        _revision(expected_revision)
        if not isinstance(changes, dict) or not changes or set(changes) - {'assignee_id', 'checklist'}:
            _invalid('Seules l’affectation individuelle et la checklist peuvent être modifiées ici.')
        checklist = self._checklist(changes['checklist']) if 'checklist' in changes else None
        with self.repo._transaction() as db:
            identity = self._reference(tenant, actor, project_id, page_id, action_id, write=True)
            self._ensure(db, tenant, identity, project_id, page_id, action_id)
            before = self._state(tenant, actor, project_id, page_id, action_id)
            if before['revision'] != expected_revision:
                raise DomainError('stale_revision', 'Cette collaboration a changé. Rechargez-la avant de confirmer votre saisie.')
            assignee = changes.get('assignee_id', before['assignee_id'])
            if assignee is not None and (not isinstance(assignee, str) or not 1 <= len(assignee) <= 200):
                _invalid('La référence du membre est invalide.')
            if assignee is not None and self._member(tenant, actor, project_id, assignee) is None:
                _invalid('Choisissez un membre actif autorisé à consulter ce dossier.')
            values = checklist if checklist is not None else before['checklist']
            if assignee != before['assignee_id'] or values != before['checklist']:
                db.execute('UPDATE action_collaboration SET revision=revision+1,assignee_id=?,checklist_json=?,updated_by=?,updated_at=? WHERE tenant_id=? AND project_id=? AND page_id=? AND action_id=?', (assignee, canonical_json(values), identity, utc_now(), tenant, project_id, page_id, action_id))
                self.repo._audit(db, tenant, project_id, 'action.collaboration.changed', identity, action_id, {'page_id': page_id, 'action_id': action_id})
            return self._state(tenant, actor, project_id, page_id, action_id)

    def _comment(self, row):
        member = self.repo._db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='identity_members'").fetchone()
        author = self.repo._db.execute('SELECT display_name,role FROM identity_members WHERE tenant_id=? AND actor_id=?', (row['tenant_id'], row['author_id'])).fetchone() if member else None
        return {'id': row['id'], 'body': row['body'], 'created_at': row['created_at'], 'author': {'id': row['author_id'], 'display_name': author['display_name'] if author else 'Visiteur de démonstration' if not self.settings.auth_required else 'Compte du service', 'role': author['role'] if author else None}}

    def list_comments(self, tenant, actor, project_id, *, page_id, action_id, limit=50, offset=0):
        _pagination(limit, offset)
        with self.repo._lock:
            self._reference(tenant, actor, project_id, page_id, action_id)
            where, args = 'tenant_id=? AND project_id=? AND page_id=? AND action_id=?', (tenant, project_id, page_id, action_id)
            total = self.repo._db.execute('SELECT count(*) FROM action_comments WHERE '+where, args).fetchone()[0]
            rows = self.repo._db.execute('SELECT * FROM action_comments WHERE '+where+' ORDER BY sequence LIMIT ? OFFSET ?', (*args, limit, offset)).fetchall()
            return {'items': [self._comment(row) for row in rows], 'total': total, 'limit': limit, 'offset': offset}

    def add_comment(self, tenant, actor, project_id, *, page_id, action_id, client_id, body):
        body = require_text(body, 'comment', maximum=4000).strip()
        if not body or '\x00' in body: _invalid('Renseignez un commentaire de quatre mille caractères maximum.')
        if not isinstance(client_id, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', client_id):
            _invalid('L’identifiant de ce commentaire est invalide.')
        with self.repo._transaction() as db:
            identity = self._reference(tenant, actor, project_id, page_id, action_id, write=True)
            self._ensure(db, tenant, identity, project_id, page_id, action_id)
            args = (tenant, project_id, page_id, action_id, identity, client_id)
            old = db.execute('SELECT * FROM action_comments WHERE tenant_id=? AND project_id=? AND page_id=? AND action_id=? AND author_id=? AND client_id=?', args).fetchone()
            if old:
                if old['body'] != body: raise DomainError('idempotency_conflict', 'Cet identifiant appartient déjà à un autre commentaire.')
                return self._comment(old)
            ident = str(uuid4())
            db.execute('INSERT INTO action_comments(id,tenant_id,project_id,page_id,action_id,author_id,client_id,body,created_at) VALUES(?,?,?,?,?,?,?,?,?)', (ident, *args, body, utc_now()))
            self.repo._audit(db, tenant, project_id, 'action.comment.added', identity, ident, {'page_id': page_id, 'action_id': action_id, 'comment_id': ident})
            return self._comment(db.execute('SELECT * FROM action_comments WHERE id=?', (ident,)).fetchone())

    @staticmethod
    def _rule_values(rule):
        keys = {'unit', 'interval', 'anchor_start', 'span_days', 'month_end', 'active'}
        if not isinstance(rule, dict) or set(rule) != keys or not isinstance(rule['unit'], str) or rule['unit'] not in {'week', 'month', 'year'}:
            _invalid('Renseignez une récurrence structurée par semaine, mois ou année.')
        if type(rule['interval']) is not int or not 1 <= rule['interval'] <= 52 or type(rule['span_days']) is not int or not 0 <= rule['span_days'] <= 366:
            _invalid('L’intervalle doit aller de un à cinquante-deux et la durée de zéro à 366 jours.')
        if type(rule['month_end']) is not bool or type(rule['active']) is not bool or (rule['unit'] == 'week' and rule['month_end']):
            _invalid('Les options de récurrence doivent être explicites et cohérentes.')
        if not isinstance(rule['anchor_start'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', rule['anchor_start']):
            _invalid('La date d’ancrage attend le format AAAA-MM-JJ.')
        try: date.fromisoformat(rule['anchor_start'])
        except ValueError: _invalid('La date d’ancrage doit exister dans le calendrier.')
        return dict(rule)

    @staticmethod
    def _rule_dto(row):
        result = {key: row[key] for key in ('id', 'project_id', 'page_id', 'action_id', 'revision', 'unit', 'interval', 'anchor_start', 'span_days', 'month_end', 'active')}
        result.update(month_end=bool(result['month_end']), active=bool(result['active']), timezone='Europe/Paris')
        return result

    def set_rule(self, tenant, actor, project_id, *, page_id, action_id, expected_revision, rule):
        _revision(expected_revision)
        values = self._rule_values(rule)
        with self.repo._transaction() as db:
            identity = self._reference(tenant, actor, project_id, page_id, action_id, write=True)
            self._ensure(db, tenant, identity, project_id, page_id, action_id)
            before = db.execute('SELECT * FROM action_recurrence_rules WHERE tenant_id=? AND project_id=? AND page_id=? AND action_id=?', (tenant, project_id, page_id, action_id)).fetchone()
            if (before['revision'] if before else 0) != expected_revision:
                raise DomainError('stale_revision', 'Cette règle a changé. Rechargez-la avant de confirmer votre modification.')
            ident, now = before['id'] if before else str(uuid4()), utc_now()
            args = (values['unit'], values['interval'], values['anchor_start'], values['span_days'], int(values['month_end']), int(values['active']))
            if before:
                db.execute('UPDATE action_recurrence_rules SET revision=revision+1,unit=?,interval=?,anchor_start=?,span_days=?,month_end=?,active=?,updated_by=?,updated_at=? WHERE tenant_id=? AND id=?', (*args, identity, now, tenant, ident))
            else:
                db.execute('INSERT INTO action_recurrence_rules VALUES(?,?,?,?,?,1,?,?,?,?,?,?,?,?,?,?)', (ident, tenant, project_id, page_id, action_id, *args, identity, identity, now, now))
            self.repo._audit(db, tenant, project_id, 'action.recurrence.changed', identity, ident, {'page_id': page_id, 'action_id': action_id})
            return self._rule_dto(db.execute('SELECT * FROM action_recurrence_rules WHERE id=?', (ident,)).fetchone())

    def _rule(self, tenant, actor, project_id, rule_id, *, write=False):
        self._guard(tenant, actor, project_id, write=write)
        row = self.repo._db.execute('SELECT * FROM action_recurrence_rules WHERE tenant_id=? AND project_id=? AND id=?', (tenant, project_id, rule_id)).fetchone()
        if row is None: raise DomainError('not_found', 'Cette règle n’existe pas dans le dossier autorisé.')
        self._reference(tenant, actor, project_id, row['page_id'], row['action_id'], write=write)
        return row

    @staticmethod
    def _plan(rule, ordinal):
        anchor = date.fromisoformat(rule['anchor_start'])
        step = ordinal * rule['interval']
        try:
            if rule['unit'] == 'week':
                start = anchor + timedelta(weeks=step)
            else:
                months = step if rule['unit'] == 'month' else step * 12
                year, month = divmod(anchor.year * 12 + anchor.month - 1 + months, 12)
                last = calendar.monthrange(year, month + 1)[1]
                start = date(year, month + 1, last if rule['month_end'] else min(anchor.day, last))
            return start.isoformat(), (start + timedelta(days=rule['span_days'])).isoformat()
        except (ValueError, OverflowError):
            _invalid('Cette occurrence dépasse les dates prises en charge par le calendrier.')

    @staticmethod
    def _operation(row):
        confirmation = None if row['phase'] == 'prepared' else {'page_id': row['confirmed_page_id'], 'row_id': row['row_id'], 'page_revision_hash': row['page_revision_hash'], 'confirmed_at': row['confirmed_at'], 'verification': 'client_receipt_for_saved_page'}
        return {'operation_id': row['operation_id'], 'rule_id': row['rule_id'], 'rule_revision': row['rule_revision'], 'ordinal': row['ordinal'], 'source_key': 'recurrence:'+row['operation_id'], 'plan': {'startDate': row['plan_start'], 'dueDate': row['plan_due']}, 'phase': row['phase'], 'created_at': row['created_at'], 'confirmation': confirmation}

    def prepare_occurrence(self, tenant, actor, project_id, *, rule_id, ordinal, expected_rule_revision):
        _revision(expected_rule_revision)
        if type(ordinal) is not int or not 1 <= ordinal <= 10_000:
            _invalid('Le numéro d’occurrence doit aller de un à dix mille.')
        with self.repo._transaction() as db:
            rule = self._rule(tenant, actor, project_id, rule_id, write=True)
            if rule['revision'] != expected_rule_revision:
                raise DomainError('stale_revision', 'La règle a changé. Relisez-la avant de préparer une occurrence.')
            old = db.execute('SELECT * FROM action_occurrences WHERE tenant_id=? AND rule_id=? AND ordinal=?', (tenant, rule_id, ordinal)).fetchone()
            if old: return self._operation(old)
            if not rule['active']: raise DomainError('invalid_state', 'Cette règle est désactivée ; aucune nouvelle occurrence ne sera préparée.')
            start, due = self._plan(rule, ordinal)
            ident = str(uuid4())
            db.execute("INSERT INTO action_occurrences(operation_id,tenant_id,project_id,rule_id,ordinal,rule_revision,plan_start,plan_due,phase,prepared_by,created_at) VALUES(?,?,?,?,?,?,?,?,'prepared',?,?)", (ident, tenant, project_id, rule_id, ordinal, rule['revision'], start, due, actor['actor_id'], utc_now()))
            self.repo._audit(db, tenant, project_id, 'action.occurrence.prepared', actor['actor_id'], ident, {'rule_id': rule_id, 'ordinal': ordinal})
            return self._operation(db.execute('SELECT * FROM action_occurrences WHERE operation_id=?', (ident,)).fetchone())

    def list_occurrences(self, tenant, actor, project_id, *, rule_id, limit=50, offset=0):
        _pagination(limit, offset)
        with self.repo._lock:
            self._rule(tenant, actor, project_id, rule_id)
            args = (tenant, project_id, rule_id)
            where = 'tenant_id=? AND project_id=? AND rule_id=?'
            total = self.repo._db.execute('SELECT count(*) FROM action_occurrences WHERE '+where, args).fetchone()[0]
            rows = self.repo._db.execute('SELECT * FROM action_occurrences WHERE '+where+' ORDER BY ordinal LIMIT ? OFFSET ?', (*args, limit, offset)).fetchall()
            return {'items': [self._operation(row) for row in rows], 'total': total, 'limit': limit, 'offset': offset}

    def confirm_occurrence(self, tenant, actor, project_id, operation_id, *, page_id, row_id, page_revision_hash):
        _native_id(page_id), _native_id(row_id)
        if not isinstance(page_revision_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', page_revision_hash):
            _invalid('L’empreinte de la version native enregistrée est requise.')
        with self.repo._transaction() as db:
            self._guard(tenant, actor, project_id, write=True)
            operation = db.execute('SELECT * FROM action_occurrences WHERE tenant_id=? AND project_id=? AND operation_id=?', (tenant, project_id, operation_id)).fetchone()
            if operation is None: raise DomainError('not_found', 'Cette préparation n’existe pas dans le dossier autorisé.')
            rule = self._rule(tenant, actor, project_id, operation['rule_id'], write=True)
            if page_id != rule['page_id'] or row_id == rule['action_id']:
                _invalid('Une occurrence doit être une nouvelle action dans la page native prévue.')
            if operation['phase'] == 'confirmed':
                if (operation['confirmed_page_id'], operation['row_id'], operation['page_revision_hash']) != (page_id, row_id, page_revision_hash):
                    raise DomainError('conflict', 'Cette occurrence possède déjà un reçu natif différent.')
                return self._operation(operation)
            saved = db.execute('SELECT 1 FROM native_page_versions WHERE tenant_id=? AND page_id=? AND revision_hash=?', (tenant, page_id, page_revision_hash)).fetchone()
            if saved is None: raise DomainError('stale_revision', 'Enregistrez la page native avant de confirmer son occurrence.')
            duplicate = db.execute('SELECT 1 FROM action_occurrences WHERE tenant_id=? AND confirmed_page_id=? AND row_id=?', (tenant, page_id, row_id)).fetchone()
            if duplicate: raise DomainError('conflict', 'Cette action native est déjà liée à une autre occurrence.')
            db.execute("UPDATE action_occurrences SET phase='confirmed',confirmed_page_id=?,row_id=?,page_revision_hash=?,confirmed_by=?,confirmed_at=? WHERE operation_id=?", (page_id, row_id, page_revision_hash, actor['actor_id'], utc_now(), operation_id))
            self.repo._audit(db, tenant, project_id, 'action.occurrence.confirmed', actor['actor_id'], operation_id, {'rule_id': rule['id'], 'page_id': page_id, 'action_id': row_id, 'page_revision_hash': page_revision_hash})
            return self._operation(db.execute('SELECT * FROM action_occurrences WHERE operation_id=?', (operation_id,)).fetchone())


class CollaborationBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page_id: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=160)


class CollaborationPatch(CollaborationBody):
    expected_revision: int = Field(ge=0, strict=True)
    changes: dict


class CommentBody(CollaborationBody):
    client_id: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=4000)


class RecurrenceBody(CollaborationBody):
    expected_revision: int = Field(ge=0, strict=True)
    rule: dict


class OccurrenceBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rule_id: str = Field(min_length=1, max_length=160)
    ordinal: int = Field(ge=1, le=10_000, strict=True)
    expected_rule_revision: int = Field(ge=0, strict=True)


class ConfirmationBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page_id: str = Field(min_length=1, max_length=160)
    row_id: str = Field(min_length=1, max_length=160)
    page_revision_hash: str = Field(pattern='^[a-f0-9]{64}$')


def register_action_collaboration_routes(app, repo, tenant, actor, settings):
    service = ActionCollaboration(repo, settings)
    base = '/api/v1/projects/{project_id}/action-collaboration'

    @app.get(base+'/participants')
    def participants(project_id: str, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0, le=100_000), current=Depends(actor)):
        return service.participants(tenant, current, project_id, limit=limit, offset=offset)

    @app.get(base)
    def state(project_id: str, page_id: str, action_id: str, current=Depends(actor)):
        return service.get(tenant, current, project_id, page_id=page_id, action_id=action_id)

    @app.patch(base)
    def patch(project_id: str, body: CollaborationPatch, current=Depends(actor)):
        return service.patch(tenant, current, project_id, **body.model_dump())

    @app.get(base+'/comments')
    def comments(project_id: str, page_id: str, action_id: str, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0, le=100_000), current=Depends(actor)):
        return service.list_comments(tenant, current, project_id, page_id=page_id, action_id=action_id, limit=limit, offset=offset)

    @app.post(base+'/comments', status_code=201)
    def add_comment(project_id: str, body: CommentBody, current=Depends(actor)):
        return service.add_comment(tenant, current, project_id, **body.model_dump())

    @app.put(base+'/recurrence')
    def recurrence(project_id: str, body: RecurrenceBody, current=Depends(actor)):
        return service.set_rule(tenant, current, project_id, **body.model_dump())

    @app.get(base+'/occurrences')
    def occurrences(project_id: str, rule_id: str, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0, le=100_000), current=Depends(actor)):
        return service.list_occurrences(tenant, current, project_id, rule_id=rule_id, limit=limit, offset=offset)

    @app.post(base+'/occurrences', status_code=201)
    def prepare(project_id: str, body: OccurrenceBody, current=Depends(actor)):
        return service.prepare_occurrence(tenant, current, project_id, **body.model_dump())

    @app.post(base+'/occurrences/{operation_id}/confirm')
    def confirm(project_id: str, operation_id: str, body: ConfirmationBody, current=Depends(actor)):
        return service.confirm_occurrence(tenant, current, project_id, operation_id, **body.model_dump())

    return service
