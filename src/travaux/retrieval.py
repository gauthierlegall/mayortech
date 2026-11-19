"""Permission-scoped retrieval over real dossier records using SQLite FTS5/BM25.

The ranking implementation is SQLite's unmodified open-source FTS5 extension,
not an application scoring heuristic. An ephemeral index avoids duplicating
municipal source data at rest and is rebuilt from the current revision.
"""

from __future__ import annotations

import re
import sqlite3

from .assistant_dossier import DossierAssistant
from .calendar_retrieval import calendar_documents, calendar_intent
from .domain import DomainError, evidence_span, normalized, require_text
from .project_access import access_scope

STOP_WORDS = {
    "les",
    "des",
    "une",
    "dans",
    "pour",
    "avec",
    "est",
    "que",
    "qui",
    "quoi",
    "quel",
    "quelle",
    "quelles",
    "quels",
    "comment",
    "pourquoi",
    "retrouve",
    "peux",
    "faire",
    "sur",
    "aux",
    "du",
    "de",
    "la",
    "le",
    "et",
    "en",
}


def fts_query(value: str) -> str:
    # MATCH has its own syntax. Only application-quoted alphanumeric words enter
    # it; user operators, quotes, column selectors and SQL never become syntax.
    words = list(dict.fromkeys(re.findall(r"[a-z0-9]{2,60}", normalized(value))))
    words = [word for word in words if word not in STOP_WORDS][:24]
    return " OR ".join(f'"{word}"*' for word in words)


def source_chunks(body: str, maximum=1200):
    """Yield exact contiguous source passages with Unicode character offsets."""
    start = 0
    while start < len(body):
        end = min(start + maximum, len(body))
        if end < len(body):
            boundary = body.rfind("\n", start + maximum // 2, end)
            if boundary > start:
                end = boundary
        raw = body[start:end]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right > left:
            yield start + left, start + right, body[start + left : start + right]
        start = max(end, start + 1)
        while start < len(body) and body[start].isspace():
            start += 1


class DossierRetrieval:
    def __init__(self, repo, settings, *, assistant=None, calendars=None):
        self.repo, self.settings = repo, settings
        self.assistant = assistant or DossierAssistant(repo, settings)
        self.calendars = calendars

    def search(self, tenant, query, *, project_id=None, limit=8, actor=None):
        scope = access_scope(self.repo, actor)
        if project_id:
            scope.require_project(project_id)
        query = require_text(query, "question", maximum=2000)
        if not 1 <= limit <= 12:
            raise DomainError("invalid_input", "Limiter la recherche à douze passages.")
        warnings, documents, revisions = [], [], {}
        with self.repo._lock:
            projects = (
                [self.repo.get_project(tenant, project_id)] if project_id else
                [self.repo.get_project(tenant, ident) for ident in scope.visible_project_ids]
                if scope.restricted else self.repo.list_projects(tenant)
            )
            if len(projects) > 200:
                warnings.append("La recherche est limitée à 200 dossiers ; choisissez un chantier.")
                projects = projects[:200]
            for project in projects:
                memory = scope.sanitize_memory(self.repo.get_memory(tenant, project["id"]))
                revisions[project["id"]] = memory["revision"]
                candidates = memory["facts"] + memory["pending"]
                for source in memory["sources"]:
                    if source.get("metadata", {}).get("source_kind") == "demo_document_catalog":
                        continue
                    if (
                        len(source["body"]) > 100_000
                        and "Certains documents volumineux sont partiellement indexés ; ouvrez leur original pour une lecture complète."
                        not in warnings
                    ):
                        warnings.append(
                            "Certains documents volumineux sont partiellement indexés ; ouvrez leur original pour une lecture complète."
                        )
                    for start, end, quote in source_chunks(source["body"][:100_000]):
                        proof = evidence_span(source, quote, start, end, source["body_hash"])
                        documents.append(
                            {
                                **proof,
                                "kind": "source",
                                "title": source["subject"],
                                "project_id": project["id"],
                                "project_name": project["name"],
                                "project_reference": project["reference"],
                                "project_revision": memory["revision"],
                                "relations": [
                                    {
                                        "candidate_id": item["id"],
                                        "field": item["field"],
                                        "status": item["status"],
                                    }
                                    for item in candidates
                                    if item["source_id"] == source["id"]
                                    and any(
                                        span.get("quote") and span["quote"] in quote
                                        for span in item["evidence"]
                                    )
                                ],
                            }
                        )
                        if len(documents) >= 5000:
                            break
                    if len(documents) >= 5000:
                        break
                if len(documents) >= 5000:
                    warnings.append("Le volume consulté est limité ; affinez la recherche par chantier.")
                    break
        calendar_revisions, period, appointments = {}, None, []
        if self.calendars is not None:
            appointments, calendar_revisions, period = calendar_documents(
                self.calendars, tenant, actor, query, project_id=project_id, projects=projects
            )
            documents.extend(appointments)
        expression = fts_query(query)
        result = {
            "engine": "sqlite-fts5-bm25",
            "query": query,
            "items": [],
            "project_revisions": revisions,
            "calendar_revisions": calendar_revisions,
            "calendar_range": period,
            "warnings": warnings,
        }
        if period and period["direct"]:
            result["items"] = [{**item, "rank": None} for item in appointments[:limit]]
            return result
        if not expression or not documents:
            return result
        # This connection contains only records already selected through the
        # tenant/project repository boundary. No cross-tenant rank statistics.
        with sqlite3.connect(":memory:") as index:
            index.execute(
                "CREATE VIRTUAL TABLE passages USING fts5(title, quote, tokenize='unicode61 remove_diacritics 2')"
            )
            index.executemany(
                "INSERT INTO passages(rowid,title,quote) VALUES(?,?,?)",
                [
                    (
                        number + 1,
                        f"{item['project_reference']} {item['project_name']} {item['title']}",
                        item["quote"],
                    )
                    for number, item in enumerate(documents)
                ],
            )
            # Canonical FTS5 MATCH / BM25 query from sqlite.org/fts5.html §5.1.1.
            hits = index.execute(
                "SELECT rowid,bm25(passages,2.0,1.0) FROM passages WHERE passages MATCH ? ORDER BY bm25(passages,2.0,1.0),rowid LIMIT ?",
                (expression, limit),
            ).fetchall()
        result["items"] = [{**documents[rowid - 1], "rank": rank} for rowid, rank in hits]
        return result

    def answer(self, tenant, query, *, project_id=None, actor=None, previous_query=""):
        retrieval_query = query
        if previous_query and len(fts_query(query).split(" OR ")) < 2:
            retrieval_query = f"{query} {previous_query[-800:]}"
        found = self.search(tenant, retrieval_query, project_id=project_id, actor=actor)
        scope = access_scope(self.repo, actor)
        context = {
            "engine": found["engine"],
            "project_revisions": found["project_revisions"],
            "calendar_revisions": found["calendar_revisions"],
            "calendar_range": found["calendar_range"],
            "scope_project_id": project_id,
            "source_ids": list(
                dict.fromkeys(item["source_id"] for item in found["items"] if item.get("source_id"))
            ),
        }
        if (
            project_id
            and not calendar_intent(query)
            and self.assistant._intent(query) in {"summary", "dates", "documents", "report"}
        ):
            answer = self.assistant.ask(tenant, project_id, query, actor=actor)
            return {
                "content": answer["answer"],
                "citations": answer["citations"],
                "mode": answer["mode"],
                "context": context,
                "warnings": found["warnings"] + answer["warnings"],
            }
        citations = found["items"][:6]
        mode = "sqlite_fts5"
        source_citations = [item for item in citations if item.get("source_id")]
        if source_citations and self.settings.mode != "public_demo" and self.settings.llm == "mistral":
            scope.require_context(context, citations)
            # Reuse the existing constrained passage selector: exact source/hash
            # validation, fixed endpoint, bounded response, no tools or SQL.
            sources = {
                item["source_id"]: self.repo.get_source(tenant, item["source_id"])
                for item in source_citations
            }
            selected = self.assistant._select(query, source_citations, sources)
            by_source = {item["source_id"]: item for item in source_citations}
            citations = [{**by_source[item["source_id"]], **item} for item in selected] + [
                item for item in citations if item.get("kind") == "calendar"
            ]
            mode = "mistral_extraits"
        scope.require_context(context, citations)
        content = (
            (
                "Voici les passages retrouvés dans les dossiers autorisés. Les annonces citées ne valent pas validation de la mairie.\n\n"
                + "\n\n".join(
                    f"{item.get('project_name', '')} — {item['title']}\n{item['quote']}" for item in citations
                )
            )
            if citations
            else (
                "Je n’ai pas retrouvé de passage probant dans ce périmètre. Choisissez un chantier ou précisez votre question."
            )
        )
        if any(item.get("kind") == "calendar" for item in citations):
            content += "\n\nLes rendez-vous d’agenda ne confirment pas la livraison ni les faits du chantier."
        return {
            "content": content,
            "citations": citations,
            "mode": mode,
            "context": context,
            "warnings": found["warnings"],
        }
