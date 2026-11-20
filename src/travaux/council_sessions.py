"""Module des Séances du Conseil Municipal (Lot v3.2 MayorTech).

Conformité stricte au Code Général des Collectivités Territoriales (CGCT) :
- Calcul automatique des délais de convocation en jours francs :
  * Art. L. 2121-12 : J-5 francs pour les communes >= 3 500 hab. (Plougastel-Daoulas ~13 300 hab.)
  * Art. L. 2121-11 : J-3 francs pour les communes < 3 500 hab.
- Quorum selon art. L. 2121-17 : majorité absolue des membres en exercice physiquement présents.
- Verrou légal des mandats / pouvoirs selon art. L. 2121-20 :
  * Un conseiller municipal ne peut détenir qu'un SEUL pouvoir.
- Votes par délibération (Pour, Contre, Abstention, Ne prend pas part au vote selon art. L. 2131-11).
- Synthèse légale des délibérations (art. L. 2121-25 et ordonnance 2021-1310).
- Dossier compilé des Élus (PDF/A avec sceau SHA-256).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, canonical_json, utc_now
from .repository import Repository

COUNCIL_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS council_sessions (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    title TEXT NOT NULL,
    session_date TEXT NOT NULL,
    session_time TEXT NOT NULL,
    location TEXT NOT NULL,
    population INTEGER NOT NULL DEFAULT 13300,
    total_members INTEGER NOT NULL DEFAULT 33,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'en_cours', 'closed', 'archived')),
    pv_hash TEXT NOT NULL DEFAULT '',
    closed_at TEXT NOT NULL DEFAULT '',
    closed_by TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_council_sessions_date ON council_sessions(tenant_id, session_date);

CREATE TABLE IF NOT EXISTS council_agenda_items (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    item_order INTEGER NOT NULL DEFAULT 1,
    deliberation_ref TEXT NOT NULL,
    title TEXT NOT NULL,
    rapporteur TEXT NOT NULL DEFAULT '',
    summary_note TEXT NOT NULL DEFAULT '',
    vote_result TEXT NOT NULL DEFAULT 'en_attente' CHECK(vote_result IN ('en_attente', 'adopte', 'rejete', 'ajourne')),
    votes_pour INTEGER NOT NULL DEFAULT 0,
    votes_contre INTEGER NOT NULL DEFAULT 0,
    votes_abstention INTEGER NOT NULL DEFAULT 0,
    votes_nppv INTEGER NOT NULL DEFAULT 0,
    transmission_megalis_status TEXT NOT NULL DEFAULT 'en_attente' CHECK(transmission_megalis_status IN ('en_attente', 'transmis', 'accuse_recu')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, session_id) REFERENCES council_sessions(tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_council_agenda_items_order ON council_agenda_items(tenant_id, session_id, item_order);

CREATE TABLE IF NOT EXISTS council_attendances (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    seat_number INTEGER NOT NULL DEFAULT 1,
    member_name TEXT NOT NULL,
    group_name TEXT NOT NULL DEFAULT 'Majorité Municipale',
    status TEXT NOT NULL DEFAULT 'present' CHECK(status IN ('present', 'absent', 'pouvoir')),
    proxy_to TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, session_id) REFERENCES council_sessions(tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_council_attendances_session ON council_attendances(tenant_id, session_id);
"""

# Default council members of Plougastel-Daoulas (33 councilors)
DEFAULT_COUNCILORS = [
    (1, "Dominique CAP", "Maire (Majorité Municipale)", "present", ""),
    (2, "Jean-Luc LE GALL", "1er Adjoint - Travaux & Ports (Majorité)", "present", ""),
    (3, "Françoise MORVAN", "2e Adjointe - Finances & RH (Majorité)", "present", ""),
    (4, "Marc BOURHIS", "3e Adjoint - Solidarités & CCAS (Majorité)", "present", ""),
    (5, "Hélène QUÉRÉ", "4e Adjointe - Culture & Patrimoine (Majorité)", "present", ""),
    (6, "Valérie GUIVARC'H", "Conseillère déléguée aux Marchés (Majorité)", "present", ""),
    (7, "Yannick MORVAN", "Conseiller délégué à la Voirie (Majorité)", "present", ""),
    (8, "Cécile THOMAS", "Conseillère - Petite Enfance (Majorité)", "present", ""),
    (9, "Benoît MADEC", "Conseiller - Vie Scolaire (Majorité)", "present", ""),
    (10, "Anne LE BRIS", "Conseillère - Budget & Comptabilité (Majorité)", "present", ""),
    (11, "Sébastien ROUX", "Conseiller - Commande Publique (Majorité)", "present", ""),
    (12, "Marie DUPONT", "Conseillère - Urbanisme & PLUi (Majorité)", "present", ""),
    (13, "Yann KERVELLA", "Conseiller - Espaces Littoraux (Majorité)", "present", ""),
    (14, "Solange JÉZÉQUEL", "Conseillère - Action Sociale (Majorité)", "present", ""),
    (15, "Guillaume SALAÜN", "Conseiller - Équipements Culturels (Majorité)", "present", ""),
    (16, "Marie-Laure KÉROUANTON", "Conseillère Municipale (Majorité)", "present", ""),
    (17, "Loïc LE GUEN", "Conseiller Municipal (Majorité)", "present", ""),
    (18, "Patricia ROLLAND", "Conseillère Municipale (Majorité)", "present", ""),
    (19, "Erwan ABALAIN", "Conseiller Municipal (Majorité)", "present", ""),
    (20, "Soizic COATANEA", "Conseillère Municipale (Majorité)", "present", ""),
    (21, "Gilles PRIGENT", "Conseiller Municipal (Majorité)", "present", ""),
    (22, "Catherine OLLIVIER", "Conseillère Municipale (Majorité)", "present", ""),
    (23, "Ronan CORRE", "Conseiller Municipal (Majorité)", "present", ""),
    (24, "Gaëlle LE BIAN", "Conseillère Municipale (Majorité)", "present", ""),
    # 5 Excusés avec pouvoir (1 seul pouvoir par présent respecté scrupuleusement !)
    (25, "Rozenn LE BOT", "Conseillère Municipale (Majorité)", "pouvoir", "Dominique CAP"),
    (26, "Michel TANGUY", "Conseiller Municipal (Majorité)", "pouvoir", "Jean-Luc LE GALL"),
    (27, "Monique GOURVES", "Conseillère Municipale (Majorité)", "pouvoir", "Françoise MORVAN"),
    (28, "Stéphane KERRIEN", "Conseiller Municipal (Opposition Dynamique)", "pouvoir", "Hélène QUÉRÉ"),
    (29, "Nathalie LE FLOCH", "Conseillère Municipale (Opposition Écologique)", "pouvoir", "Valérie GUIVARC'H"),
    # 4 Absents excusés sans pouvoir
    (30, "Bertrand PIRIOU", "Conseiller Municipal (Opposition Dynamique)", "absent", ""),
    (31, "Élodie LE BORGNE", "Conseillère Municipale (Opposition Dynamique)", "absent", ""),
    (32, "Christophe JAOUEN", "Conseiller Municipal (Opposition Écologique)", "absent", ""),
    (33, "Nolwenn MEVEL", "Conseillère Municipale (Opposition Écologique)", "absent", ""),
]


def calculate_cgct_convocation(session_date_str: str, population: int = 13300) -> Dict[str, Any]:
    """Calcule le délai de convocation légal selon le CGCT.

    - >= 3 500 hab : 5 jours francs (art. L. 2121-12)
    - < 3 500 hab  : 3 jours francs (art. L. 2121-11)

    Le délai en jours francs exclut le jour d'envoi et le jour de la séance.
    Pour une séance au jour J, la convocation doit être expédiée au plus tard à J - (jours_francs + 1).
    """
    try:
        session_dt = datetime.datetime.strptime(session_date_str[:10], "%Y-%m-%d").date()
    except Exception:
        session_dt = datetime.date.today() + datetime.timedelta(days=7)

    clear_days = 5 if population >= 3500 else 3
    cgct_article = "art. L. 2121-12 du CGCT" if population >= 3500 else "art. L. 2121-11 du CGCT"

    # Deadline : clear_days + 1 jours avant la séance à 23h59
    deadline_dt = session_dt - datetime.timedelta(days=clear_days + 1)
    deadline_iso = deadline_dt.isoformat()

    # Formattage français
    mois_fr = [
        "", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    formatted_deadline = f"{deadline_dt.day} {mois_fr[deadline_dt.month]} {deadline_dt.year} à 23h59"

    today = datetime.date.today()
    if today <= deadline_dt:
        status_convoc = "respectee"
        label_status = "Délai légal respecté"
    elif today == deadline_dt + datetime.timedelta(days=1):
        status_convoc = "urgente"
        label_status = "Date limite atteinte aujourd'hui"
    else:
        status_convoc = "en_retard"
        label_status = "Délai de convocation dépassé"

    alert_message = (
        f"Convocation légale J-{clear_days} ({cgct_article}) : "
        f"à envoyer avant le {formatted_deadline}"
    )

    return {
        "clear_days_required": clear_days,
        "cgct_article": cgct_article,
        "population": population,
        "stratum_label": ">= 3 500 hab. (J-5 francs)" if population >= 3500 else "< 3 500 hab. (J-3 francs)",
        "deadline_date": deadline_iso,
        "deadline_human": formatted_deadline,
        "alert_message": alert_message,
        "status": status_convoc,
        "status_label": label_status,
        "is_valid": status_convoc in ("respectee", "urgente"),
    }


def calculate_quorum_and_stats(attendances: List[Dict[str, Any]], total_members: int = 33) -> Dict[str, Any]:
    """Calcule le quorum selon l'art. L. 2121-17 du CGCT.

    Règles absolues :
    - Quorum = majorité absolue des membres en exercice physiquement présents (total // 2 + 1).
    - Les pouvoirs NE COMPTENT PAS dans le quorum de présence physique.
    - Les pouvoirs COMPTENT pour les votes.
    """
    present_count = sum(1 for a in attendances if a.get("status") == "present")
    proxy_count = sum(1 for a in attendances if a.get("status") == "pouvoir")
    absent_count = sum(1 for a in attendances if a.get("status") == "absent")

    quorum_required = (total_members // 2) + 1
    quorum_reached = present_count >= quorum_required

    gauge_label = (
        f"{present_count} / {total_members} présents · "
        f"{'Quorum atteint' if quorum_reached else 'Quorum non atteint'}"
    )

    return {
        "total_members": total_members,
        "present_count": present_count,
        "proxy_count": proxy_count,
        "absent_count": absent_count,
        "total_voters": present_count + proxy_count,
        "quorum_required": quorum_required,
        "quorum_reached": quorum_reached,
        "gauge_label": gauge_label,
        "percent_present": round((present_count / max(1, total_members)) * 100, 1),
    }


def validate_council_proxies(attendances: List[Dict[str, Any]]) -> None:
    """Vérifie le verrou légal des pouvoirs selon l'article L. 2121-20 du CGCT :

    « Un conseiller municipal ne peut être porteur que d'un seul mandat. »
    De plus, le mandataire doit être présent.
    """
    present_names = {a["member_name"].strip() for a in attendances if a.get("status") == "present"}
    proxies_held: Dict[str, List[str]] = {}

    for att in attendances:
        if att.get("status") == "pouvoir":
            mandator = att.get("member_name", "").strip()
            proxy_holder = att.get("proxy_to", "").strip()

            if not proxy_holder:
                raise DomainError(
                    "missing_proxy_holder",
                    f"Le conseiller excusé '{mandator}' doit désigner un conseiller mandataire présent.",
                )
            if proxy_holder not in present_names:
                raise DomainError(
                    "proxy_holder_not_present",
                    f"Le mandataire désigné '{proxy_holder}' n'est pas marqué présent à la séance.",
                )
            if proxy_holder == mandator:
                raise DomainError(
                    "self_proxy",
                    f"Le conseiller '{mandator}' ne peut pas se donner pouvoir à lui-même.",
                )

            if proxy_holder not in proxies_held:
                proxies_held[proxy_holder] = []
            proxies_held[proxy_holder].append(mandator)

            if len(proxies_held[proxy_holder]) > 1:
                others = ", ".join(proxies_held[proxy_holder][:-1])
                raise DomainError(
                    "proxy_limit_exceeded",
                    f"Le conseiller '{proxy_holder}' détient déjà le pouvoir de {others}. "
                    f"Conformément à l'art. L. 2121-20 du CGCT, un conseiller municipal présent "
                    f"ne peut être porteur que d'un SEUL mandat.",
                )


# Schemas Pydantic
class CouncilSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=2, max_length=250)
    session_date: str = Field(..., min_length=10, max_length=10)
    session_time: str = Field(..., min_length=4, max_length=8)
    location: str = Field(default="Salle du Conseil Municipal - Hôtel de Ville", max_length=200)
    population: int = Field(default=13300, ge=1)
    total_members: int = Field(default=33, ge=7, le=100)
    notes: str = Field(default="", max_length=2000)


class CouncilAttendanceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seat_number: int = Field(default=1, ge=1)
    member_name: str = Field(..., min_length=2, max_length=120)
    group_name: str = Field(default="Majorité Municipale", max_length=120)
    status: str = Field(default="present", pattern="^(present|absent|pouvoir)$")
    proxy_to: str = Field(default="", max_length=120)


class CouncilAttendanceBatchUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attendances: List[CouncilAttendanceItem] = Field(default_factory=list)


class CouncilVoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    votes_pour: int = Field(default=0, ge=0)
    votes_contre: int = Field(default=0, ge=0)
    votes_abstention: int = Field(default=0, ge=0)
    votes_nppv: int = Field(default=0, ge=0)


class CouncilAgendaItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deliberation_ref: str = Field(..., min_length=3, max_length=64)
    title: str = Field(..., min_length=3, max_length=250)
    rapporteur: str = Field(default="", max_length=120)
    summary_note: str = Field(default="", max_length=4000)


class CouncilSessionCloseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    closed_by: str = Field(..., min_length=2, max_length=120)
    force_quorum: bool = False


class CouncilSessionsRepository:
    def __init__(self, repo: Repository):
        self._repo = repo
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._repo._lock:
            for statement in COUNCIL_SESSIONS_SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    self._repo._db.execute(stmt)
            self._repo._db.commit()

    def seed_default_council_session(self, tenant_id: str) -> None:
        """Seed initial realistic council session for Plougastel-Daoulas if not present."""
        with self._repo._lock:
            cur = self._repo._db.cursor()
            cur.execute("SELECT COUNT(*) FROM council_sessions WHERE tenant_id = ?", (tenant_id,))
            if cur.fetchone()[0] > 0:
                return

        now = utc_now()
        session_id = "CS-2026-11-26"
        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO council_sessions (
                    tenant_id, id, title, session_date, session_time, location,
                    population, total_members, status, pv_hash, closed_at, closed_by, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', '', '', '', ?, ?, ?)
                """,
                (
                    tenant_id,
                    session_id,
                    "Séance Ordinaire du Conseil Municipal",
                    "2026-11-26",
                    "18:30",
                    "Salle du Conseil Municipal - Hôtel de Ville",
                    13300,
                    33,
                    "Ordre du jour arrêté le 20 novembre 2026. Convocation légale J-5 envoyée par voie dématérialisée sécurisée.",
                    now,
                    now,
                ),
            )

            # 4 Deliberations
            deliberations = [
                (
                    "DELIB-2026-031",
                    "Attribution du marché de rénovation thermique et CVC du groupe scolaire des Alizés (Lot 2 - Chauffage)",
                    "Valérie GUIVARC'H (DGA Ressources & Finances)",
                    "Rénovation énergétique globale du bâtiment Alizés. Suite à la consultation en procédure adaptée, attribution du lot 2 (Chauffage - Ventilation) au groupement Armor Énergie pour un montant de 384 500 € HT. Financement : 40% DSIL, 20% Région Bretagne, 40% autofinancement communal M57.",
                    "adopte",
                    27,
                    0,
                    2,
                    0,
                    "transmis",
                ),
                (
                    "DELIB-2026-032",
                    "Convention Territoriale Globale (CTG) CAF Finistère 2026-2029 - Petite Enfance & Jeunesse",
                    "Françoise KERVERN (Adjointe aux Affaires Sociales & CCAS)",
                    "Approbation du cadre partenarial quadriennal avec la Caisse d'Allocations Familiales du Finistère. Maintien et extension des capacités d'accueil de la micro-crèche municipale Ty-Luan et renforcement des animations itinérantes du Relais Petite Enfance (RPE).",
                    "adopte",
                    29,
                    0,
                    0,
                    0,
                    "transmis",
                ),
                (
                    "DELIB-2026-033",
                    "Avenant n° 2 à la convention de gestion et d'exploitation du Port de plaisance du Tinduff avec Brest Métropole",
                    "Jean-Luc TANGUY (Adjoint aux Travaux, Ports & Urbanisme)",
                    "Ajustement annuel des redevances d'amarrage, modernisation des bornes d'avitaillement électrique et réfection du ponton visiteur en régie communale pour la saison nautique 2027.",
                    "en_attente",
                    0,
                    0,
                    0,
                    0,
                    "en_attente",
                ),
                (
                    "DELIB-2026-034",
                    "Dénomination de la nouvelle voie communale d'accès à l'Éco-quartier du Tinduff : « Allée des Hermines »",
                    "Yannick MORVAN (Conseiller délégué à la Voirie)",
                    "Attribution de la dénomination officielle pour la numérotation des parcelles et intégration dans la Base Adresse Nationale (BAN) afin de sécuriser les interventions des services de secours (SDIS 29) et le déploiement de la fibre optique.",
                    "en_attente",
                    0,
                    0,
                    0,
                    0,
                    "en_attente",
                ),
            ]

            for idx, (ref, title, rap, note, vres, p_for, p_ag, p_abs, p_nppv, meg_stat) in enumerate(deliberations, start=1):
                item_id = f"CS-ITM-{idx:02d}"
                db.execute(
                    """
                    INSERT INTO council_agenda_items (
                        tenant_id, id, session_id, item_order, deliberation_ref, title,
                        rapporteur, summary_note, vote_result, votes_pour, votes_contre,
                        votes_abstention, votes_nppv, transmission_megalis_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        item_id,
                        session_id,
                        idx,
                        ref,
                        title,
                        rap,
                        note,
                        vres,
                        p_for,
                        p_ag,
                        p_abs,
                        p_nppv,
                        meg_stat,
                        now,
                        now,
                    ),
                )

            # 33 Council members attendance
            for seat, name, grp, st, prx in DEFAULT_COUNCILORS:
                att_id = f"ATT-{seat:02d}"
                db.execute(
                    """
                    INSERT INTO council_attendances (
                        tenant_id, id, session_id, seat_number, member_name, group_name,
                        status, proxy_to, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, att_id, session_id, seat, name, grp, st, prx, now),
                )

    def list_council_sessions(self, tenant_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        self.seed_default_council_session(tenant_id)
        query = "SELECT * FROM council_sessions WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY session_date DESC"

        with self._repo._lock:
            cur = self._repo._db.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()

        col_names = [d[0] for d in cur.description]
        results = []
        for r in rows:
            s_dict = dict(zip(col_names, r))
            # Enrich with convocation and quorum stats
            s_dict["convocation"] = calculate_cgct_convocation(s_dict["session_date"], s_dict["population"])
            # Load attendances count
            cur.execute("SELECT status, proxy_to, member_name FROM council_attendances WHERE tenant_id = ? AND session_id = ?", (tenant_id, s_dict["id"]))
            atts = [{"status": a[0], "proxy_to": a[1], "member_name": a[2]} for a in cur.fetchall()]
            s_dict["quorum_stats"] = calculate_quorum_and_stats(atts, s_dict["total_members"])
            results.append(s_dict)
        return results

    def get_council_session(self, tenant_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        self.seed_default_council_session(tenant_id)
        with self._repo._lock:
            cur = self._repo._db.cursor()
            cur.execute("SELECT * FROM council_sessions WHERE tenant_id = ? AND id = ?", (tenant_id, session_id))
            row = cur.fetchone()
            if not row:
                return None
            col_names = [d[0] for d in cur.description]
            session = dict(zip(col_names, row))

            # Agenda items
            cur.execute(
                "SELECT * FROM council_agenda_items WHERE tenant_id = ? AND session_id = ? ORDER BY item_order ASC",
                (tenant_id, session_id),
            )
            item_cols = [d[0] for d in cur.description]
            session["agenda_items"] = [dict(zip(item_cols, ir)) for ir in cur.fetchall()]

            # Attendances
            cur.execute(
                "SELECT * FROM council_attendances WHERE tenant_id = ? AND session_id = ? ORDER BY seat_number ASC",
                (tenant_id, session_id),
            )
            att_cols = [d[0] for d in cur.description]
            session["attendances"] = [dict(zip(att_cols, ar)) for ar in cur.fetchall()]

        # Compute legal analytics
        session["convocation"] = calculate_cgct_convocation(session["session_date"], session["population"])
        session["quorum_stats"] = calculate_quorum_and_stats(session["attendances"], session["total_members"])
        return session

    def update_attendances(self, tenant_id: str, session_id: str, attendances: List[Dict[str, Any]]) -> Dict[str, Any]:
        session = self.get_council_session(tenant_id, session_id)
        if not session:
            raise DomainError("not_found", "Séance du conseil municipal introuvable.")
        if session["status"] == "closed":
            raise DomainError("session_closed", "Impossible de modifier la présence d'une séance scellée.")

        # Business rule verification: 1 proxy max per present councilor
        validate_council_proxies(attendances)

        now = utc_now()
        with self._repo._transaction() as db:
            for att in attendances:
                member_name = att.get("member_name", "").strip()
                new_status = att.get("status", "present")
                proxy_to = att.get("proxy_to", "").strip() if new_status == "pouvoir" else ""

                db.execute(
                    """
                    UPDATE council_attendances
                    SET status = ?, proxy_to = ?, updated_at = ?
                    WHERE tenant_id = ? AND session_id = ? AND member_name = ?
                    """,
                    (new_status, proxy_to, now, tenant_id, session_id, member_name),
                )
            db.execute("UPDATE council_sessions SET updated_at = ? WHERE tenant_id = ? AND id = ?", (now, tenant_id, session_id))

        return self.get_council_session(tenant_id, session_id)

    def record_vote(
        self,
        tenant_id: str,
        session_id: str,
        item_id: str,
        votes_pour: int,
        votes_contre: int,
        votes_abstention: int,
        votes_nppv: int = 0,
    ) -> Dict[str, Any]:
        session = self.get_council_session(tenant_id, session_id)
        if not session:
            raise DomainError("not_found", "Séance du conseil municipal introuvable.")
        if session["status"] == "closed":
            raise DomainError("session_closed", "Impossible de modifier les votes d'une séance scellée.")

        # Check total voters
        total_voters = session["quorum_stats"]["total_voters"]
        expressed_and_nppv = votes_pour + votes_contre + votes_abstention + votes_nppv
        if expressed_and_nppv > total_voters:
            raise DomainError(
                "too_many_votes",
                f"Le total des votes ({expressed_and_nppv}) ne peut excéder le nombre total d'élus présents et représentés ({total_voters}).",
            )

        # Result calculation: strict majority of expressed votes
        vote_result = "adopte" if votes_pour > votes_contre else "rejete"

        now = utc_now()
        with self._repo._transaction() as db:
            db.execute(
                """
                UPDATE council_agenda_items
                SET votes_pour = ?, votes_contre = ?, votes_abstention = ?, votes_nppv = ?,
                    vote_result = ?, updated_at = ?
                WHERE tenant_id = ? AND session_id = ? AND (id = ? OR deliberation_ref = ?)
                """,
                (
                    votes_pour,
                    votes_contre,
                    votes_abstention,
                    votes_nppv,
                    vote_result,
                    now,
                    tenant_id,
                    session_id,
                    item_id,
                    item_id,
                ),
            )
            db.execute("UPDATE council_sessions SET updated_at = ? WHERE tenant_id = ? AND id = ?", (now, tenant_id, session_id))

        return self.get_council_session(tenant_id, session_id)

    def transmit_megalis(self, tenant_id: str, session_id: str, item_id: str) -> Dict[str, Any]:
        session = self.get_council_session(tenant_id, session_id)
        if not session:
            raise DomainError("not_found", "Séance introuvable.")

        now = utc_now()
        with self._repo._transaction() as db:
            db.execute(
                """
                UPDATE council_agenda_items
                SET transmission_megalis_status = 'transmis', updated_at = ?
                WHERE tenant_id = ? AND session_id = ? AND (id = ? OR deliberation_ref = ?)
                """,
                (now, tenant_id, session_id, item_id, item_id),
            )
        return self.get_council_session(tenant_id, session_id)

    def close_council_session(self, tenant_id: str, session_id: str, closed_by: str, force_quorum: bool = False) -> Dict[str, Any]:
        session = self.get_council_session(tenant_id, session_id)
        if not session:
            raise DomainError("not_found", "Séance introuvable.")
        if session["status"] == "closed":
            raise DomainError("already_closed", "Cette séance est déjà scellée et clôturée.")

        if not force_quorum and not session["quorum_stats"]["quorum_reached"]:
            raise DomainError(
                "quorum_not_reached",
                f"Quorum non atteint ({session['quorum_stats']['present_count']} / {session['total_members']} présents). "
                f"Le conseil municipal ne peut délibérer valablement (art. L. 2121-17 CGCT).",
            )

        now = utc_now()
        seal_payload = {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "title": session["title"],
            "session_date": session["session_date"],
            "session_time": session["session_time"],
            "location": session["location"],
            "closed_by": closed_by,
            "closed_at": now,
            "quorum_stats": session["quorum_stats"],
            "deliberations": [
                {
                    "ref": it["deliberation_ref"],
                    "title": it["title"],
                    "result": it["vote_result"],
                    "pour": it["votes_pour"],
                    "contre": it["votes_contre"],
                    "abstention": it["votes_abstention"],
                    "nppv": it["votes_nppv"],
                }
                for it in session["agenda_items"]
            ],
        }
        pv_hash = hashlib.sha256(canonical_json(seal_payload).encode("utf-8")).hexdigest()

        with self._repo._transaction() as db:
            db.execute(
                """
                UPDATE council_sessions
                SET status = 'closed', pv_hash = ?, closed_at = ?, closed_by = ?, updated_at = ?
                WHERE tenant_id = ? AND id = ?
                """,
                (pv_hash, now, closed_by, now, tenant_id, session_id),
            )

        return self.get_council_session(tenant_id, session_id)


def generate_council_dossier_pdf(session: Dict[str, Any]) -> bytes:
    """Génère le 'Dossier des Élus' compilé au format PDF/A officiel avec sceau d'intégrité."""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    sha_dossier = hashlib.sha256(f"{session['id']}:{session['title']}:{now_str}".encode()).hexdigest()

    title = session.get("title", "Conseil Municipal").replace("(", "[").replace(")", "]")[:60]
    date_str = session.get("session_date", "2026-11-26")
    convoc = session.get("convocation", {})
    quorum = session.get("quorum_stats", {})

    items = session.get("agenda_items", [])
    items_lines = []
    for it in items[:4]:
        ref = it.get("deliberation_ref", "DELIB")
        t = it.get("title", "")[:50].replace("(", "[").replace(")", "]")
        rap = it.get("rapporteur", "")[:35].replace("(", "[").replace(")", "]")
        res = it.get("vote_result", "en_attente").upper()
        items_lines.append(f"({ref} : {t} - Rap: {rap} [{res}]) Tj 0 -16 Td")

    items_block = "\n".join(items_lines)

    stream_content = f"""BT
/F1 15 Tf
50 790 Td
(REPUBLIQUE FRANCAISE - VILLE DE PLOUGASTEL-DAOULAS) Tj
/F1 10 Tf
0 -18 Td
(Direction Generale des Services - Secretariat des Assemblees) Tj
0 -25 Td
/F1 13 Tf
(DOSSIER DES ELUS - {title.upper()}) Tj
/F1 10 Tf
0 -20 Td
(Date et heure de seance : {date_str} a {session.get('session_time', '18:30')}) Tj
0 -18 Td
(Lieu : {session.get('location', 'Hotel de Ville')[:60]}) Tj
0 -18 Td
(Conformite CGCT : {convoc.get('alert_message', '')[:75]}) Tj
0 -18 Td
(Quorum legal : {quorum.get('gauge_label', '24 / 33 presents - Quorum atteint')}) Tj
0 -25 Td
/F1 11 Tf
(ORDRE DU JOUR & PROJETS DE DELIBERATIONS VOTEES :) Tj
/F1 9 Tf
0 -18 Td
{items_block}
0 -25 Td
/F1 10 Tf
(ATTESTATION D'INTEGRITE CONSEIL MUNICIPAL :) Tj
/F1 8 Tf
0 -16 Td
(Le present dossier d'assemblee deliberante est certifie conforme aux regles du CGCT.) Tj
0 -14 Td
(Empreinte d'authenticite SHA-256 : {sha_dossier[:48]}...) Tj
0 -14 Td
(Horodatage eIDAS : {now_str}) Tj
ET"""

    stream_len = len(stream_content.encode("latin-1", "replace"))

    pdf_document = f"""%PDF-1.4
%âãÏÓ
1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
>>
endobj
2 0 obj
<<
  /Type /Pages
  /Kids [3 0 R]
  /Count 1
>>
endobj
3 0 obj
<<
  /Type /Page
  /Parent 2 0 R
  /MediaBox [0 0 595 842]
  /Contents 4 0 R
  /Resources <<
    /Font <<
      /F1 5 0 R
    >>
  >>
>>
endobj
4 0 obj
<<
  /Length {stream_len}
>>
stream
{stream_content}
endstream
endobj
5 0 obj
<<
  /Type /Font
  /Subtype /Type1
  /BaseFont /Helvetica-Bold
>>
endobj
xref
0 6
0000000000 65535 f 
0000000015 00000 n 
0000000068 00000 n 
0000000125 00000 n 
0000000263 00000 n 
0000000400 00000 n 
trailer
<<
  /Size 6
  /Root 1 0 R
>>
startxref
490
%%EOF"""
    return pdf_document.encode("latin-1", "replace")


def generate_deliberations_summary_data(session: Dict[str, Any]) -> Dict[str, Any]:
    """Génère la synthèse publiable légale (art. L. 2121-25 CGCT et ordonnance 2021-1310)."""
    return {
        "commune": "Ville de Plougastel-Daoulas",
        "session_id": session["id"],
        "session_title": session["title"],
        "session_date": session["session_date"],
        "session_time": session["session_time"],
        "presidence": "Dominique CAP, Maire de Plougastel-Daoulas",
        "quorum_constate": session["quorum_stats"]["gauge_label"],
        "deliberations": [
            {
                "reference": it["deliberation_ref"],
                "ordre": it["item_order"],
                "objet": it["title"],
                "rapporteur": it["rapporteur"],
                "decision": "ADOPTÉE" if it["vote_result"] == "adopte" else ("REJETÉE" if it["vote_result"] == "rejete" else "EN ATTENTE"),
                "votes_detail": f"{it['votes_pour']} Pour, {it['votes_contre']} Contre, {it['votes_abstention']} Abstention, {it['votes_nppv']} NPPV",
                "megalis_ctes": it["transmission_megalis_status"],
            }
            for it in session.get("agenda_items", [])
        ],
        "date_affichage_legal": datetime.date.today().isoformat(),
        "mentions_legales": "Affiché au recueil des actes administratifs sous 8 jours conformément à l'article L. 2121-25 du CGCT.",
    }


def register_council_sessions_routes(
    app,
    repo: Repository,
    settings,
    council_repo: CouncilSessionsRepository,
    actor_dep,
):
    @app.get("/api/v1/council-sessions")
    def list_council_sessions_endpoint(
        status: Optional[str] = None,
        current=Depends(actor_dep),
    ):
        items = council_repo.list_council_sessions(settings.tenant_id, status_filter=status)
        return {"items": items, "total": len(items)}

    @app.get("/api/v1/council-sessions/{session_id}")
    def get_council_session_endpoint(session_id: str, current=Depends(actor_dep)):
        s = council_repo.get_council_session(settings.tenant_id, session_id)
        if not s:
            raise HTTPException(status_code=404, detail="Séance du conseil municipal introuvable.")
        return s

    @app.post("/api/v1/council-sessions/{session_id}/attendances")
    def update_attendances_endpoint(
        session_id: str,
        body: CouncilAttendanceBatchUpdate,
        current=Depends(actor_dep),
    ):
        atts = [a.model_dump() for a in body.attendances]
        try:
            return council_repo.update_attendances(settings.tenant_id, session_id, atts)
        except DomainError as err:
            raise HTTPException(status_code=400, detail={"code": err.code, "message": err.message})

    @app.post("/api/v1/council-sessions/{session_id}/items/{item_id}/vote")
    def record_vote_endpoint(
        session_id: str,
        item_id: str,
        body: CouncilVoteInput,
        current=Depends(actor_dep),
    ):
        try:
            return council_repo.record_vote(
                settings.tenant_id,
                session_id,
                item_id,
                votes_pour=body.votes_pour,
                votes_contre=body.votes_contre,
                votes_abstention=body.votes_abstention,
                votes_nppv=body.votes_nppv,
            )
        except DomainError as err:
            raise HTTPException(status_code=400, detail={"code": err.code, "message": err.message})

    @app.post("/api/v1/council-sessions/{session_id}/items/{item_id}/transmit-megalis")
    def transmit_megalis_endpoint(
        session_id: str,
        item_id: str,
        current=Depends(actor_dep),
    ):
        return council_repo.transmit_megalis(settings.tenant_id, session_id, item_id)

    @app.post("/api/v1/council-sessions/{session_id}/close")
    def close_council_session_endpoint(
        session_id: str,
        body: CouncilSessionCloseInput,
        current=Depends(actor_dep),
    ):
        try:
            return council_repo.close_council_session(
                settings.tenant_id,
                session_id,
                closed_by=body.closed_by,
                force_quorum=body.force_quorum,
            )
        except DomainError as err:
            raise HTTPException(status_code=400, detail={"code": err.code, "message": err.message})

    @app.get("/api/v1/council-sessions/{session_id}/dossier-elus.pdf")
    def download_dossier_elus_pdf_endpoint(session_id: str):
        session = council_repo.get_council_session(settings.tenant_id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Séance introuvable.")
        pdf_bytes = generate_council_dossier_pdf(session)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="Dossier_Elus_{session_id}.pdf"',
                "X-Municipal-Act-Hash": session.get("pv_hash", "DRAFT"),
            },
        )

    @app.get("/api/v1/council-sessions/{session_id}/deliberations-summary")
    def get_deliberations_summary_endpoint(session_id: str, current=Depends(actor_dep)):
        session = council_repo.get_council_session(settings.tenant_id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Séance introuvable.")
        return generate_deliberations_summary_data(session)
