"""Delegated mailbox consent, separate from authentication to Travaux.

Authorization codes never authenticate an application user. Mail identity is
read from the provider's protected mailbox API, not from unverified JWT claims.
Only fixed Microsoft/Google endpoints are used; keys stay server side.
"""
from dataclasses import dataclass, field
import base64
import hashlib
import json
import os
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx

from .domain import DomainError, canonical_json, require_text, utc_now

PROVIDERS = {"google", "microsoft365"}
FLOW_SECONDS = 600
REFRESH_LEASE_SECONDS = 90
COOKIE_PATH = "/api/v1/integrations/oauth/"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _unavailable():
    return DomainError("integration_unavailable", "Le raccordement de cette messagerie doit être vérifié par l’administrateur.")


@dataclass(frozen=True)
class OAuthConfiguration:
    provider: str
    client_id: str
    client_secret: str = field(repr=False)
    authorization_url: str
    token_url: str
    api_base: str
    redirect_uri: str
    scopes: tuple[str, ...]
    domains: tuple[str, ...]

    @property
    def public_fingerprint(self):
        return _digest(canonical_json([self.provider, self.client_id, self.authorization_url, self.token_url, self.redirect_uri, self.scopes]))


def configuration(settings, provider):
    if provider not in PROVIDERS or not settings.auth_required or settings.mode == "public_demo":
        raise _unavailable()
    prefix = "TRAVAUX_GOOGLE_OAUTH_" if provider == "google" else "TRAVAUX_MICROSOFT_OAUTH_"
    client_id = os.getenv(prefix + "CLIENT_ID", "")
    client_secret = os.getenv(prefix + "CLIENT_SECRET", "")
    domains = tuple(dict.fromkeys(value.strip().lower() for value in os.getenv(prefix + "ALLOWED_DOMAINS", "").split(",") if value.strip()))
    if (not 6 <= len(client_id) <= 300 or not 1 <= len(client_secret) <= 4000
            or not client_id.isprintable() or not client_secret.isprintable()
            or not domains or len(domains) > 50
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\.[a-z]{2,63}", domain) or ".." in domain for domain in domains)):
        raise _unavailable()
    origin = settings.public_origin.rstrip("/")
    if provider == "google":
        if not re.fullmatch(r"[a-zA-Z0-9._-]+\.apps\.googleusercontent\.com", client_id):
            raise _unavailable()
        values = ("https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token", "https://gmail.googleapis.com/gmail/v1", (GOOGLE_SCOPE,))
    else:
        tenant = os.getenv(prefix + "TENANT_ID", "")
        if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", tenant):
            raise _unavailable()
        base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"
        values = (base + "/authorize", base + "/token", "https://graph.microsoft.com/v1.0", ("User.Read", "Mail.Read", "offline_access"))
    return OAuthConfiguration(provider, client_id, client_secret, values[0], values[1], values[2], origin + f"/api/v1/integrations/oauth/{provider}/callback", values[3], domains)


class OAuthMailService:
    def __init__(self, repo, settings, *, hub, governance, http_client=None, resolve_dns=True, clock=None):
        self.repo, self.settings, self.hub, self.governance = repo, settings, hub, governance
        self.http_client, self.resolve_dns, self.clock = http_client, resolve_dns, clock or time.time
        hub.oauth_service = self
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS mail_oauth_flows(
                state_hash TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,
                provider TEXT NOT NULL,browser_hash TEXT NOT NULL,secret_ciphertext TEXT NOT NULL,
                expires REAL NOT NULL,consumed INTEGER NOT NULL DEFAULT 0)""")
            db.execute("""CREATE TABLE IF NOT EXISTS mail_oauth_refresh_leases(
                tenant_id TEXT NOT NULL,connection_id TEXT NOT NULL,owner TEXT NOT NULL,expires REAL NOT NULL,
                PRIMARY KEY(tenant_id,connection_id))""")

    def _authorize(self, actor):
        self.hub._actor(actor, manage=True, external=True)
        self.governance.require_authorized(actor, "organization", "write")

    def _audit(self, db, action, actor_id, connection_id, provider):
        # Reuse the existing organizational journal; never include mailbox
        # contents, OAuth codes, tokens, URLs with cursors or client secrets.
        db.execute("INSERT INTO organization_audit VALUES(?,?,?,?,?,?,?)", (str(uuid4()), self.settings.tenant_id, action, actor_id, "{}", canonical_json({"connection_id": connection_id, "provider": provider}), utc_now()))

    def _configuration(self, provider):
        config = configuration(self.settings, provider)
        for endpoint in (config.authorization_url, config.token_url, config.api_base):
            self.hub.policy.endpoint(endpoint)
        if not self.hub.policy.egress_approved:
            raise _unavailable()
        return config

    def provider_status(self, provider):
        try:
            self._configuration(provider)
            available = True
        except DomainError:
            available = False
        return {"available": available, "status": "available" if available else "requires_server_configuration", "requires_server_configuration": not available, "reason": "" if available else "Le raccordement OAuth est disponible après configuration de l’application et autorisation du serveur par l’administrateur.", "authorization": "oauth2", "mail_only": True}

    def start(self, actor, provider, *, label, browser_binding, session_digest=None):
        self._authorize(actor)
        config = self._configuration(provider)
        label = require_text(label, "label", maximum=200).strip()
        if not label or not label.isprintable() or not isinstance(browser_binding, str) or not 16 <= len(browser_binding) <= 200:
            raise DomainError("invalid_input", "Nom de connexion ou liaison navigateur invalide.")
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
        if session_digest is not None and not re.fullmatch(r"[a-f0-9]{64}", session_digest):
            raise DomainError("forbidden", "La session de départ ne peut pas être vérifiée.")
        encrypted = self.hub.vault.encrypt({"pkce": verifier, "label": label, "config": config.public_fingerprint, "session_hash": session_digest})
        now = self.clock()
        with self.repo._transaction() as db:
            db.execute("DELETE FROM mail_oauth_flows WHERE expires<?", (now - 86400,))
            active = db.execute("SELECT count(*) FROM mail_oauth_flows WHERE tenant_id=? AND actor_id=? AND expires>? AND consumed=0", (self.settings.tenant_id, actor["actor_id"], now)).fetchone()[0]
            if active >= 10:
                raise DomainError("integration_busy", "Terminez ou attendez l’expiration des connexions déjà ouvertes.")
            db.execute("INSERT INTO mail_oauth_flows VALUES(?,?,?,?,?,?,?,0)", (_digest(state), self.settings.tenant_id, actor["actor_id"], provider, _digest(browser_binding), encrypted, now + FLOW_SECONDS))
        query = {"client_id": config.client_id, "redirect_uri": config.redirect_uri, "response_type": "code", "scope": " ".join(config.scopes), "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
        if provider == "google":
            query.update(access_type="offline", prompt="consent", include_granted_scopes="false")
            if len(config.domains) == 1:
                query["hd"] = config.domains[0]  # Hint only: enforced again on the returned mailbox.
        else:
            query["response_mode"] = "query"
            query["prompt"] = "select_account"
        return {"authorization_url": config.authorization_url + "?" + urlencode(query), "expires_in": FLOW_SECONDS}

    def _consume(self, provider, state, browser_binding):
        if (provider not in PROVIDERS or not isinstance(state, str) or not 30 <= len(state) <= 200
                or not isinstance(browser_binding, str) or not 16 <= len(browser_binding) <= 200):
            raise DomainError("forbidden", "Ce retour de connexion est invalide ou expiré. Recommencez depuis l’espace.")
        with self.repo._transaction() as db:
            row = db.execute("SELECT * FROM mail_oauth_flows WHERE state_hash=? AND tenant_id=?", (_digest(state), self.settings.tenant_id)).fetchone()
            if row is None or row["provider"] != provider or row["browser_hash"] != _digest(browser_binding) or row["consumed"] or row["expires"] <= self.clock():
                raise DomainError("forbidden", "Ce retour de connexion est invalide ou expiré. Recommencez depuis l’espace.")
            db.execute("UPDATE mail_oauth_flows SET consumed=1,secret_ciphertext='' WHERE state_hash=? AND consumed=0", (row["state_hash"],))
            result = dict(row)
        current = {"actor_id": result["actor_id"], "tenant_id": result["tenant_id"]}
        self.governance.require_authorized(current, "organization", "write")
        self._authorize({**current, "permissions": self.governance.permissions(current)})
        self._check_starting_session(self.hub.vault.decrypt(result["secret_ciphertext"]), current)
        return result

    def _check_starting_session(self, flow, current):
        digest = flow.get("session_hash")
        if digest is None:  # Trusted non-HTTP callers can supply their own identity boundary.
            return
        with self.repo._lock:
            found = self.repo._db.execute("SELECT 1 FROM sessions WHERE digest=? AND actor_id=? AND tenant_id=? AND expires>?", (digest, current["actor_id"], current["tenant_id"], self.clock())).fetchone()
        if found is None:
            raise DomainError("forbidden", "La session de départ a expiré. Reconnectez-vous puis recommencez.")

    def _request(self, method, url, *, data=None, token=None, expected_host=None, max_bytes=4_000_000, raw=False):
        """TLS, no redirects/environment proxy, bounded body, sanitized failures."""
        if os.getenv("SSLKEYLOGFILE") or os.getenv("QUICLOGDIR"):
            raise _unavailable()
        try:
            parsed = urlsplit(url)
            if parsed.fragment or parsed.username is not None or parsed.password is not None or len(url) > 100_000:
                raise ValueError("url")
            base = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
            self.hub.policy.endpoint(base, resolve=self.resolve_dns, same_host=expected_host)
            if method not in {"GET", "POST"}:
                raise ValueError("method")
            if method == "POST" and url not in {
                "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/revoke",
                *([self._configuration("microsoft365").token_url] if urlsplit(url).hostname == "login.microsoftonline.com" else []),
            }:
                raise ValueError("post_endpoint")
            headers = {"Accept": "*/*" if raw else "application/json"}
            if parsed.hostname == "graph.microsoft.com":
                headers["Prefer"] = "odata.maxpagesize=5"
            if token:
                if not isinstance(token, str) or not token or len(token) > 20_000 or any(char in token for char in "\r\n"):
                    raise ValueError("token")
                headers["Authorization"] = "Bearer " + token
            own_client = self.http_client is None
            client = self.http_client or httpx.Client(timeout=20, follow_redirects=False, trust_env=False)
            try:
                with client.stream(method, url, data=data, headers=headers, timeout=20, follow_redirects=False) as response:
                    if response.status_code not in {200, 201}:
                        if response.status_code == 401:
                            raise DomainError("connection_authorization_required", "L’autorisation de cette messagerie a expiré. Reconnectez le compte.")
                        if response.status_code in {404, 410}:
                            raise DomainError("mail_cursor_expired", "Le serveur ne reconnaît plus ce repère de lecture. Vérifiez la reprise avant de réinitialiser la synchronisation.")
                        raise _unavailable()
                    declared_size = response.headers.get("content-length")
                    if declared_size is not None and (not declared_size.isdecimal() or int(declared_size) > max_bytes):
                        raise _unavailable()
                    content = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        content.extend(chunk)
                        if len(content) > max_bytes:
                            raise _unavailable()
                    if raw:
                        return bytes(content)
                    value = json.loads(content)
                    if not isinstance(value, dict):
                        raise ValueError("object_required")
                    return value
            finally:
                if own_client:
                    client.close()
        except DomainError:
            raise
        except Exception:
            raise _unavailable() from None

    def _token(self, config, form, previous=None):
        body = self._request("POST", config.token_url, data={"client_id": config.client_id, "client_secret": config.client_secret, **form}, expected_host=urlsplit(config.token_url).hostname)
        access = body.get("access_token")
        refresh = body.get("refresh_token") or (previous or {}).get("refresh_token")
        expires = body.get("expires_in")
        if (not isinstance(access, str) or not 1 <= len(access) <= 20_000
                or not isinstance(refresh, str) or not 1 <= len(refresh) <= 20_000
                or str(body.get("token_type", "")).lower() != "bearer"
                or isinstance(expires, bool) or not isinstance(expires, (int, float)) or not 60 <= expires <= 86400
                or any(char in access + refresh for char in "\r\n")):
            raise _unavailable()
        if "scope" in body:
            if not isinstance(body["scope"], str):
                raise _unavailable()
            granted = {scope.removeprefix("https://graph.microsoft.com/") for scope in body["scope"].split()}
            required = set(config.scopes) - {"offline_access"}
            if not required <= granted:
                raise DomainError("connection_authorization_required", "La messagerie n’a pas accordé les accès de lecture demandés.")
        return {"kind": "oauth2", "provider": config.provider, "client_id": config.client_id, "access_token": access, "refresh_token": refresh, "expires_at": self.clock() + expires}

    def complete(self, provider, *, state, code, browser_binding):
        row = self._consume(provider, state, browser_binding)
        config = self._configuration(provider)
        flow = self.hub.vault.decrypt(row["secret_ciphertext"])
        if flow.get("config") != config.public_fingerprint or not isinstance(code, str) or not 1 <= len(code) <= 20_000:
            raise _unavailable()
        payload = self._token(config, {"grant_type": "authorization_code", "code": code, "redirect_uri": config.redirect_uri, "code_verifier": flow["pkce"]})
        url = config.api_base + ("/users/me/profile" if provider == "google" else "/me?$select=id,mail,userPrincipalName")
        profile = self._request("GET", url, token=payload["access_token"], expected_host=urlsplit(config.api_base).hostname)
        mailbox = profile.get("emailAddress") if provider == "google" else profile.get("mail") or profile.get("userPrincipalName")
        if not isinstance(mailbox, str) or len(mailbox) > 320 or not re.fullmatch(r"[^@\s<>]+@[^@\s<>]+", mailbox) or mailbox.rsplit("@", 1)[1].lower() not in config.domains:
            raise DomainError("forbidden", "Cette boîte ne fait pas partie des domaines de messagerie autorisés pour la collectivité.")
        ident, now = str(uuid4()), utc_now()
        payload["mailbox"] = mailbox.lower()
        encrypted = self.hub.vault.encrypt(payload)
        current = {"actor_id": row["actor_id"], "tenant_id": row["tenant_id"]}
        with self.repo._transaction() as db:
            self.governance.require_authorized(current, "organization", "write")
            self._check_starting_session(flow, current)
            duplicate = db.execute("SELECT 1 FROM connector_connections WHERE tenant_id=? AND provider=? AND lower(mailbox)=? AND status<>'disconnected'", (self.settings.tenant_id, provider, mailbox.lower())).fetchone()
            count = db.execute("SELECT count(*) FROM connector_connections WHERE tenant_id=?", (self.settings.tenant_id,)).fetchone()[0]
            if duplicate or count >= 20:
                raise DomainError("conflict", "Ce compte est déjà relié ou la limite des connexions est atteinte. Vérifiez les comptes existants.")
            db.execute("""INSERT INTO connector_connections(id,tenant_id,provider,label,endpoint,username,mailbox,secret_ciphertext,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (ident, self.settings.tenant_id, provider, flow["label"], config.api_base, mailbox, mailbox, encrypted, "not_tested", now, now))
            db.execute("UPDATE mail_oauth_flows SET secret_ciphertext='' WHERE state_hash=?", (row["state_hash"],))
            self._audit(db, "mail.oauth.connected", row["actor_id"], ident, provider)
        return self.hub._dto(self.hub._row(self.settings.tenant_id, ident))

    def cancel(self, provider, *, state, browser_binding):
        row = self._consume(provider, state, browser_binding)
        with self.repo._transaction() as db:
            db.execute("UPDATE mail_oauth_flows SET secret_ciphertext='' WHERE state_hash=?", (row["state_hash"],))

    def access_token(self, connection_id):
        owner = secrets.token_urlsafe(24)
        with self.repo._transaction() as db:
            row = self.hub._row(self.settings.tenant_id, connection_id)
            if row["provider"] not in PROVIDERS or row["status"] == "disconnected" or not row["secret_ciphertext"]:
                raise DomainError("connection_authorization_required", "Reconnectez cette messagerie avant de la lire.")
            config = self._configuration(row["provider"])
            token = self.hub.vault.decrypt(row["secret_ciphertext"])
            if token.get("provider") != config.provider or token.get("client_id") != config.client_id or token.get("mailbox") != row["mailbox"].lower():
                raise _unavailable()
            if token.get("expires_at", 0) > self.clock() + 60:
                return token["access_token"]
            lease = db.execute("SELECT expires FROM mail_oauth_refresh_leases WHERE tenant_id=? AND connection_id=?", (self.settings.tenant_id, connection_id)).fetchone()
            if lease is not None and lease["expires"] > self.clock():
                raise DomainError("integration_busy", "Une actualisation de l’autorisation est déjà en cours. Réessayez dans un instant.")
            db.execute("INSERT INTO mail_oauth_refresh_leases VALUES(?,?,?,?) ON CONFLICT(tenant_id,connection_id) DO UPDATE SET owner=excluded.owner,expires=excluded.expires", (self.settings.tenant_id, connection_id, owner, self.clock() + REFRESH_LEASE_SECONDS))
        try:
            refreshed = self._token(config, {"grant_type": "refresh_token", "refresh_token": token["refresh_token"]}, previous=token)
            refreshed["mailbox"] = token["mailbox"]
            ciphertext = self.hub.vault.encrypt(refreshed)
            with self.repo._transaction() as db:
                lease = db.execute("SELECT owner,expires FROM mail_oauth_refresh_leases WHERE tenant_id=? AND connection_id=?", (self.settings.tenant_id, connection_id)).fetchone()
                if lease is None or lease["owner"] != owner or lease["expires"] <= self.clock():
                    raise DomainError("integration_busy", "Le renouvellement doit être repris avant une nouvelle lecture.")
                updated = db.execute("UPDATE connector_connections SET secret_ciphertext=?,updated_at=? WHERE tenant_id=? AND id=? AND secret_ciphertext=? AND status<>'disconnected'", (ciphertext, utc_now(), self.settings.tenant_id, connection_id, row["secret_ciphertext"]))
                if updated.rowcount != 1:
                    raise DomainError("stale_revision", "La connexion a changé pendant son renouvellement. Rechargez-la.")
                self._audit(db, "mail.oauth.authorization_refreshed", "mail-oauth-service", connection_id, row["provider"])
            return refreshed["access_token"]
        finally:
            with self.repo._transaction() as db:
                db.execute("DELETE FROM mail_oauth_refresh_leases WHERE tenant_id=? AND connection_id=? AND owner=?", (self.settings.tenant_id, connection_id, owner))

    def audit_disconnect(self, db, row, actor_id):
        self._audit(db, "mail.oauth.disconnected", actor_id, row["id"], row["provider"])

    def revoke_after_disconnect(self, row):
        """Local erasure already committed. No Graph write scope is requested."""
        if row["provider"] != "google" or not row["secret_ciphertext"]:
            return "local_only"
        try:
            token = self.hub.vault.decrypt(row["secret_ciphertext"])
            self._request("POST", "https://oauth2.googleapis.com/revoke", data={"token": token["refresh_token"]}, expected_host="oauth2.googleapis.com", raw=True)
            return "revoked"
        except DomainError:
            return "local_only"

    def reader(self, row):
        from .integrations.cloud_mail import CloudMailReader
        self._configuration(row["provider"])
        return CloudMailReader(row, self)

    def reset_sync(self, actor, ident, *, expected_revision, confirm):
        self._authorize(actor)
        if confirm is not True:
            raise DomainError("invalid_input", "Confirmez la reprise intégrale ; les originaux locaux seront conservés.")
        with self.repo._transaction() as db:
            row = self.hub._row(self.settings.tenant_id, ident)
            self.hub._revision(row, expected_revision)
            if row["provider"] not in PROVIDERS or row["status"] not in {"verified", "synced"} or not row["secret_ciphertext"]:
                raise DomainError("invalid_state", "Vérifiez cette connexion avant de reprendre sa lecture.")
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cloud_mail_checkpoints'").fetchone()
            if exists:
                db.execute("DELETE FROM cloud_mail_checkpoints WHERE tenant_id=? AND connection_id=?", (self.settings.tenant_id, ident))
            db.execute("UPDATE connector_connections SET status='verified',last_mail_sync_at=NULL,revision=revision+1,updated_at=? WHERE tenant_id=? AND id=?", (utc_now(), self.settings.tenant_id, ident))
            self._audit(db, "mail.oauth.sync_reset", actor["actor_id"], ident, row["provider"])
            return self.hub._dto(self.hub._row(self.settings.tenant_id, ident))


def register_mail_oauth_routes(app, repo, tenant, actor, settings, *, hub, governance):
    from fastapi import Depends, Request
    from fastapi.responses import RedirectResponse
    from pydantic import BaseModel, ConfigDict, Field

    service = OAuthMailService(repo, settings, hub=hub, governance=governance)

    class Start(BaseModel):
        model_config = ConfigDict(extra="forbid")
        label: str = Field(default="Messagerie du service", min_length=1, max_length=200)

    class Reset(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int = Field(ge=0, strict=True)
        confirm: bool = Field(strict=True)

    @app.post("/api/v1/integrations/oauth/{provider}/start")
    def start(provider: str, body: Start, request: Request, current=Depends(actor)):
        from fastapi.responses import JSONResponse
        binding = secrets.token_urlsafe(32)
        session_token = request.cookies.get("travaux_session", "")
        if not session_token or len(session_token) > 256:
            raise DomainError("forbidden", "Connectez-vous avant de relier une messagerie.")
        result = service.start(current, provider, label=body.label, browser_binding=binding, session_digest=_digest(session_token))
        response = JSONResponse(result)
        response.set_cookie("travaux_mail_oauth_" + provider, binding, max_age=FLOW_SECONDS, httponly=True, secure=True, samesite="lax", path=COOKIE_PATH)
        return response

    @app.get("/api/v1/integrations/oauth/{provider}/callback")
    def callback(provider: str, request: Request):
        outcome = "failed"
        connection_id = ""
        try:
            if provider not in PROVIDERS or len(request.query_params.getlist("state")) != 1:
                raise DomainError("forbidden", "Retour invalide.")
            state = request.query_params.get("state", "")
            binding = request.cookies.get("travaux_mail_oauth_" + provider, "")
            if request.query_params.get("error"):
                service.cancel(provider, state=state, browser_binding=binding)
                outcome = "cancelled"
            else:
                if len(request.query_params.getlist("code")) != 1:
                    raise DomainError("forbidden", "Retour invalide.")
                connection = service.complete(provider, state=state, code=request.query_params["code"], browser_binding=binding)
                connection_id = connection.get("id")
                if not isinstance(connection_id, str) or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", connection_id):
                    raise _unavailable()
                outcome = "connected"
        except DomainError:
            pass
        destination = "/espace.html#/connexions?oauth=" + outcome
        if outcome == "connected":
            destination += "&connection=" + connection_id
        response = RedirectResponse(destination, status_code=303)
        if provider in PROVIDERS:
            response.delete_cookie("travaux_mail_oauth_" + provider, path=COOKIE_PATH, httponly=True, secure=True, samesite="lax")
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        return response

    @app.post("/api/v1/integrations/connections/{ident}/reset-mail-sync")
    def reset_sync(ident: str, body: Reset, current=Depends(actor)):
        return service.reset_sync(current, ident, expected_revision=body.expected_revision, confirm=body.confirm)

    return service
