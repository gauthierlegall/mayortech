"""Institutional OIDC code flow with PKCE and explicitly validated ID tokens.

Only public discovery/JWK documents are cached. Provider tokens are never sent
to the browser or persisted. Durable opaque sessions refer to approved members.
"""
from dataclasses import dataclass, field
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry

from .connection_hub import IntegrationPolicy, SecretVault
from .domain import DomainError, canonical_json
from .identity import issuer_url

FLOW_SECONDS = 600
COOKIE = "travaux_identity_flow"
COOKIE_PATH = "/api/v1/auth/"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class OIDCConfiguration:
    issuer: str
    client_id: str
    client_secret: str = field(repr=False)
    allowed_hosts: tuple[str, ...] = ()
    private_hosts: tuple[str, ...] = ()
    required_acr: tuple[str, ...] = ()
    required_amr: tuple[str, ...] = ()
    signup_url: str = ""
    reset_url: str = ""

    def __post_init__(self):
        try:
            if issuer_url(self.issuer) != self.issuer or not self.client_id or not self.client_secret or len(self.client_id) > 500 or len(self.client_secret) > 8000:
                raise ValueError()
            IntegrationPolicy(True, self.allowed_hosts, self.private_hosts).endpoint(self.issuer)
            if self.signup_url:
                IntegrationPolicy(True, self.allowed_hosts, self.private_hosts).endpoint(self.signup_url)
            if self.reset_url:
                IntegrationPolicy(True, self.allowed_hosts, self.private_hosts).endpoint(self.reset_url)
            if not self.required_acr and not self.required_amr:
                raise ValueError()
            for item in (*self.required_acr, *self.required_amr):
                if not isinstance(item, str) or not item or len(item) > 500 or not item.isprintable():
                    raise ValueError()
        except (DomainError, ValueError, TypeError):
            raise ValueError("OIDC exige issuer HTTPS autorisé, client et politique MFA explicite") from None

    @classmethod
    def from_env(cls, settings):
        if settings.auth_mode != "oidc" or os.getenv("TRAVAUX_OIDC_EGRESS_APPROVED") != "true":
            return None
        values = [os.getenv("TRAVAUX_OIDC_" + item, "") for item in ("ISSUER", "CLIENT_ID", "CLIENT_SECRET")]
        if not all(values):
            return None
        def items(name):
            return tuple(x.strip() for x in os.getenv("TRAVAUX_OIDC_"+name, "").split(",") if x.strip())
        return cls(*values, allowed_hosts=items("ALLOWED_HOSTS"), private_hosts=items("PRIVATE_HOSTS"), required_acr=items("REQUIRED_ACR"), required_amr=items("REQUIRED_AMR"), signup_url=os.getenv("TRAVAUX_OIDC_SIGNUP_URL", ""), reset_url=os.getenv("TRAVAUX_OIDC_RESET_URL", ""))

    @property
    def fingerprint(self):
        return digest(canonical_json({"issuer": self.issuer, "client_id": self.client_id, "acr": self.required_acr, "amr": self.required_amr, "signup_url": self.signup_url, "reset_url": self.reset_url}))


class OIDCService:
    def __init__(self, repo, settings, sessions, members, *, configuration=None, http=None):
        self.repo, self.settings, self.sessions, self.members = repo, settings, sessions, members
        self.configuration = configuration if configuration is not None else OIDCConfiguration.from_env(settings)
        self.http, self.owns_http = http, http is None
        self.vault = SecretVault(settings)
        if self.configuration:
            self.policy = IntegrationPolicy(True, self.configuration.allowed_hosts, self.configuration.private_hosts)
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS identity_flows(
                state_hash TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, binding_hash TEXT NOT NULL,
                secret_ciphertext TEXT NOT NULL, configuration_hash TEXT NOT NULL, expires REAL NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0)""")

    @property
    def available(self):
        return bool(self.configuration and self.settings.auth_required and self.settings.auth_mode == "oidc")

    @property
    def signup_available(self):
        return bool(self.available and self.configuration.signup_url)

    @property
    def recovery_available(self):
        return bool(self.available and self.configuration.reset_url)

    def close(self):
        if self.http is not None and self.owns_http:
            self.http.close()

    def _read(self, method, url, data=None):
        if os.getenv("SSLKEYLOGFILE") or os.getenv("QUICLOGDIR"):
            raise DomainError("integration_unavailable", "Le diagnostic TLS doit être désactivé pour la connexion institutionnelle.")
        self.policy.endpoint(url, resolve=self.owns_http)
        if self.http is None:
            self.http = httpx.Client(timeout=httpx.Timeout(15, connect=5), follow_redirects=False, trust_env=False)
        try:
            with self.http.stream(method, url, data=data, headers={"Accept": "application/json"}) as response:
                if response.status_code != 200:
                    raise ValueError()
                content = bytearray()
                for part in response.iter_bytes():
                    content.extend(part)
                    if len(content) > 256_000:
                        raise ValueError()
                result = json.loads(content)
                if not isinstance(result, dict):
                    raise ValueError()
                return result
        except Exception:
            raise DomainError("integration_unavailable", "Le service d’identité est indisponible. Réessayez ou contactez votre administrateur.") from None

    def metadata(self):
        if not self.available:
            raise DomainError("integration_unavailable", "La connexion institutionnelle doit être configurée par l’administrateur.")
        config = self.configuration
        metadata = self._read("GET", config.issuer.rstrip("/") + "/.well-known/openid-configuration")
        if metadata.get("issuer") != config.issuer:
            raise DomainError("integration_unavailable", "L’autorité d’identité ne correspond pas à la configuration de cet espace.")
        for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            self.policy.endpoint(metadata.get(key))
        return metadata

    def start(self, *, intent="login", login_hint=""):
        if intent not in {"login", "signup", "recovery"}:
            raise DomainError("invalid_input", "Choisissez la connexion, la création ou la récupération de compte.")
        # A bounded email hint only pre-fills the IdP form. It conveys no identity
        # authority and is never stored in the encrypted flow or other table.
        if not isinstance(login_hint, str) or len(login_hint) > 254 or (login_hint and (
            not login_hint.isprintable() or not re.fullmatch(r'[^@\s<>\",;:()\\]+@[^@\s<>\",;:()\\]+\.[^@\s<>\",;:()\\]+', login_hint)
        )):
            raise DomainError("invalid_input", "Renseignez une adresse e-mail valide, de 254 caractères au maximum.")
        if intent == "signup" and not self.signup_available:
            raise DomainError("integration_unavailable", "La création de compte doit être activée par l’administrateur de votre collectivité.")
        if intent == "recovery" and not self.recovery_available:
            raise DomainError("integration_unavailable", "La récupération de compte doit être configurée par l’administrateur de votre collectivité.")
        metadata = self.metadata()
        state, binding, nonce, verifier = secrets.token_urlsafe(48), secrets.token_urlsafe(48), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        now = time.time()
        encrypted = self.vault.encrypt({"nonce": nonce, "verifier": verifier, "intent": intent})
        with self.repo._transaction() as db:
            db.execute("DELETE FROM identity_flows WHERE expires<? OR consumed=1", (now,))
            if db.execute("SELECT count(*) FROM identity_flows WHERE tenant_id=?", (self.settings.tenant_id,)).fetchone()[0] >= 500:
                raise DomainError("integration_unavailable", "Trop de connexions en attente. Réessayez dans quelques minutes.")
            db.execute("INSERT INTO identity_flows VALUES(?,?,?,?,?,?,0)", (digest(state), self.settings.tenant_id, digest(binding), encrypted, self.configuration.fingerprint, now+FLOW_SECONDS))
        params = {"client_id": self.configuration.client_id, "redirect_uri": self.settings.public_origin.rstrip("/")+"/api/v1/auth/callback", "response_type": "code", "response_mode": "query", "scope": "openid profile email", "state": state, "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256", "max_age": "3600"}
        if intent == "login":
            params["prompt"] = "login"
        if self.configuration.required_acr:
            params["acr_values"] = " ".join(self.configuration.required_acr)
        if login_hint:
            params["login_hint"] = login_hint
        endpoint = self.configuration.signup_url if intent == "signup" else self.configuration.reset_url if intent == "recovery" else metadata["authorization_endpoint"]
        return {"authorization_url": endpoint+"?"+urlencode(params), "binding": binding, "expires_in": FLOW_SECONDS}

    def finish(self, *, state, code, binding, allow_onboarding=False):
        if type(allow_onboarding) is not bool:
            raise DomainError("invalid_input", "Le périmètre de connexion doit être explicite.")
        if not self.available or not all(isinstance(x, str) and x and len(x) <= limit for x, limit in [(state, 200), (binding, 200), (code, 8000)]):
            raise DomainError("unauthenticated", "La connexion a expiré. Recommencez depuis cet espace.")
        with self.repo._transaction() as db:
            row = db.execute("SELECT * FROM identity_flows WHERE state_hash=? AND tenant_id=?", (digest(state), self.settings.tenant_id)).fetchone()
            if row is None or row["consumed"] or row["expires"] < time.time() or row["configuration_hash"] != self.configuration.fingerprint or not hmac.compare_digest(row["binding_hash"], digest(binding)):
                raise DomainError("unauthenticated", "La connexion a expiré. Recommencez depuis cet espace.")
            db.execute("UPDATE identity_flows SET consumed=1,secret_ciphertext='' WHERE state_hash=?", (digest(state),))
            encrypted = row["secret_ciphertext"]
        # Consume before network. An uncertain exchange is never automatically replayed.
        flow = self.vault.decrypt(encrypted)
        metadata = self.metadata()
        tokens = self._read("POST", metadata["token_endpoint"], {"grant_type": "authorization_code", "code": code, "client_id": self.configuration.client_id, "client_secret": self.configuration.client_secret, "redirect_uri": self.settings.public_origin.rstrip("/")+"/api/v1/auth/callback", "code_verifier": flow["verifier"]})
        encoded = tokens.get("id_token")
        try:
            if not isinstance(encoded, str) or len(encoded) > 32_000:
                raise ValueError()
            keys = self._read("GET", metadata["jwks_uri"])
            if not isinstance(keys.get("keys"), list) or not 1 <= len(keys["keys"]) <= 30:
                raise ValueError()
            token = jwt.decode(encoded, KeySet.import_key_set(keys), algorithms=["RS256", "ES256"])
            claims = token.claims
            registry = JWTClaimsRegistry(leeway=30, iss={"essential": True, "value": self.configuration.issuer}, aud={"essential": True, "value": self.configuration.client_id}, sub={"essential": True}, exp={"essential": True}, iat={"essential": True}, nonce={"essential": True, "value": flow["nonce"]}, auth_time={"essential": True})
            registry.validate(claims)
            now = time.time()
            if isinstance(claims["auth_time"], bool) or not isinstance(claims["auth_time"], (int, float)) or not now-3630 <= claims["auth_time"] <= now+30:
                raise ValueError()
            if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and claims.get("azp") != self.configuration.client_id:
                raise ValueError()
            if claims.get("azp", self.configuration.client_id) != self.configuration.client_id:
                raise ValueError()
            if self.configuration.required_acr and claims.get("acr") not in self.configuration.required_acr:
                raise ValueError()
            mfa_required = bool(self.configuration.required_amr and (not isinstance(claims.get("amr"), list) or not set(self.configuration.required_amr).issubset(claims["amr"])))
            if flow.get("intent") == "signup" and claims.get("email_verified") is not True:
                raise ValueError()
        except Exception:
            raise DomainError("unauthenticated", "La connexion n’a pas pu être validée. Recommencez depuis cet espace.") from None
        if mfa_required:
            # A native enrollment/recovery may complete without executing the
            # OTP authenticator. Only a fresh signed MFA flow can issue access.
            raise DomainError("identity_mfa_required", "Confirmez votre connexion avec votre mot de passe et votre code de double authentification.")
        if allow_onboarding and claims.get("email_verified") is True and isinstance(claims.get("email"), str):
            # Provision only contact metadata attested by the verified IdP.
            # Existing members remain unchanged; no browser claim assigns a role.
            self.members.provision(self.configuration.issuer, claims["sub"],
                                   claims.get("name") or "Demande d’accès", "reader",
                                   email=claims["email"], active=False)
        try:
            member = self.members.authenticate(self.configuration.issuer, claims)
        except DomainError as error:
            if error.code != "identity_pending" or not allow_onboarding:
                raise
            actor_id = self.members.actor_id(self.configuration.issuer, claims["sub"])
            return self.sessions.issue(actor_id, "onboarding:" + self.settings.tenant_id, ttl=900)
        return self.sessions.issue(member["actor_id"], self.settings.tenant_id)


def register_identity_routes(app, repo, settings, sessions, members):
    from typing import Literal
    from pydantic import BaseModel, ConfigDict, Field

    service = OIDCService(repo, settings, sessions, members)

    class AuthStartInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        intent: Literal["login", "signup", "recovery"] = "login"
        login_hint: str = Field(default="", max_length=254, strict=True)

    @app.post("/api/v1/auth/start")
    def start_identity(request: Request, body: AuthStartInput | None = None):
        if not sessions.allow_attempt("oidc:"+(request.client.host if request.client else "unknown")):
            return JSONResponse({"error": {"code": "rate_limit", "message": "Trop de tentatives. Réessayez dans cinq minutes."}}, status_code=429)
        started = service.start(intent=body.intent if body else "login", login_hint=body.login_hint if body else "")
        response = JSONResponse({key: started[key] for key in ("authorization_url", "expires_in")})
        response.set_cookie(COOKIE, started["binding"], secure=True, httponly=True, samesite="lax", path=COOKIE_PATH, max_age=FLOW_SECONDS)
        return response

    @app.get("/api/v1/auth/callback")
    def finish_identity(request: Request):
        token, status = None, "failed"
        try:
            if request.query_params.get("error"):
                raise DomainError("unauthenticated", "Connexion annulée.")
            if len(request.query_params.getlist("state")) != 1 or len(request.query_params.getlist("code")) != 1:
                raise DomainError("unauthenticated", "Retour de connexion invalide.")
            token = service.finish(state=request.query_params.get("state"), code=request.query_params.get("code"), binding=request.cookies.get(COOKIE), allow_onboarding=True)
            status = "connected"
        except DomainError as error:
            status = "pending" if error.code == "identity_pending" else "reauthenticate" if error.code == "identity_mfa_required" else "failed"
        except Exception:
            pass
        response = RedirectResponse("/connexion.html?auth="+status, status_code=303)
        response.delete_cookie(COOKIE, path=COOKIE_PATH, secure=True, httponly=True, samesite="lax")
        if token:
            response.set_cookie("travaux_session", token, secure=True, httponly=True, samesite="strict", max_age=8*3600)
        return response

    return service
