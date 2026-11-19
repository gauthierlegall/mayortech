from dataclasses import dataclass, field
import ipaddress
import os
import re
from pathlib import Path
import sqlite3
from urllib.parse import urlparse


def normalize_organization_join_code(value):
    if (not isinstance(value, str) or len(value) > 256 or not value.isascii()
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError("Le code d’organisation doit contenir entre 6 et 64 lettres, chiffres ou tirets ASCII.")
    normalized = value.strip().upper()
    if re.fullmatch(r"[A-Z0-9-]{6,64}", normalized) is None:
        raise ValueError("Le code d’organisation doit contenir entre 6 et 64 lettres, chiffres ou tirets ASCII.")
    return normalized


@dataclass(frozen=True)
class Settings:
    mode: str = "demo"
    db_path: Path = Path("data/travaux.sqlite3")
    tenant_id: str = "demo-plougastel"
    password_hash: str = ""
    llm: str = "demo"
    mistral_url: str = ""
    mistral_model: str = ""
    mistral_key: str = ""
    egress_approved: bool = False
    appflowy_url: str = ""
    public_origin: str = ""
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "testserver")
    auth_mode: str = "password"
    mistral_document_model: str = ""
    mistral_chat_model: str = ""
    test_organization_self_join: bool = False
    private_access_origin: str = ""
    trusted_proxy_ips: tuple[str, ...] = ()
    organization_join_code: str = field(default="", repr=False)
    signature_workflow_enabled: bool = False

    def __post_init__(self):
        if self.organization_join_code != "":
            object.__setattr__(self, "organization_join_code", normalize_organization_join_code(self.organization_join_code))
        if self.mode not in {"demo", "pilot", "staging", "public_demo"}:
            raise ValueError("TRAVAUX_MODE doit valoir demo, public_demo, staging ou pilot")
        self.validate_public_demo_connectors()
        for proxy_ip in self.trusted_proxy_ips:
            if not isinstance(proxy_ip, str) or proxy_ip != proxy_ip.strip():
                raise ValueError("Chaque proxy de confiance doit être une adresse IP exacte")
            ipaddress.ip_address(proxy_ip)
        if self.private_access_origin:
            private_origin = urlparse(self.private_access_origin)
            if private_origin.scheme != "https" or not private_origin.hostname or private_origin.username is not None or private_origin.password is not None or private_origin.query or private_origin.fragment or private_origin.path not in {"", "/"} or private_origin.port not in {None, 443}:
                raise ValueError("L’adresse de connexion privée doit être une origine HTTPS explicite")
        if self.auth_mode not in {"password", "oidc"}:
            raise ValueError("TRAVAUX_AUTH_MODE doit valoir password ou oidc")
        if self.auth_mode == "oidc" and not self.auth_required:
            raise ValueError("L'identité OIDC exige un espace privé")
        if self.signature_workflow_enabled and (not self.auth_required or self.auth_mode != "oidc"):
            raise ValueError("Le circuit de signature exige des comptes individuels dans un espace privé")
        if self.test_organization_self_join and (self.mode != "staging" or self.auth_mode != "oidc" or self.llm != "demo" or self.egress_approved):
            raise ValueError("L'organisation test en libre accès est réservée au staging fictif sans fournisseur externe")
        if self.auth_required and self.auth_mode == "password" and not self.password_hash.startswith("scrypt$"):
            raise ValueError("TRAVAUX_PASSWORD_HASH obligatoire en mode staging ou pilot")
        if self.mode != "demo":
            origin = urlparse(self.public_origin)
            if origin.scheme != "https" or not origin.hostname or origin.username is not None or origin.password is not None or origin.query or origin.fragment or origin.path not in {"", "/"}:
                raise ValueError("TRAVAUX_PUBLIC_ORIGIN HTTPS obligatoire hors démo locale")
            if origin.hostname not in self.allowed_hosts or any("*" in h for h in self.allowed_hosts):
                raise ValueError("Hôte public explicite attendu dans TRAVAUX_ALLOWED_HOSTS")
        if self.llm not in {"demo", "mistral"}:
            raise ValueError("Fournisseur LLM inconnu")
        if self.mode == "pilot" and self.llm == "demo":
            raise ValueError("Le moteur fictif est réservé à la démonstration")
        if self.llm == "mistral":
            if not self.egress_approved:
                raise ValueError("Autorisation de sortie LLM explicite requise")
            url = urlparse(self.mistral_url)
            if url.scheme != "https" or not url.hostname or url.username or url.query or url.fragment:
                raise ValueError("Endpoint LLM HTTPS sans identifiants ni paramètres requis")
            if not any((self.mistral_model, self.mistral_document_model, self.mistral_chat_model)):
                raise ValueError("Identifiant de modèle LLM obligatoire")
        if self.appflowy_url:
            url = urlparse(self.appflowy_url)
            if url.scheme != "https" or not url.hostname or url.username:
                raise ValueError("URL AppFlowy HTTPS attendue")

    @classmethod
    def from_env(cls):
        mode = os.getenv("TRAVAUX_MODE", "demo")
        return cls(
            mode=mode,
            db_path=Path(os.getenv("TRAVAUX_DB", "data/public-demo.sqlite3" if mode == "public_demo" else "data/travaux.sqlite3")),
            tenant_id=os.getenv("TRAVAUX_TENANT", "demo-plougastel"),
            password_hash=os.getenv("TRAVAUX_PASSWORD_HASH", ""),
            llm=os.getenv("TRAVAUX_LLM", "demo"),
            mistral_url=os.getenv("TRAVAUX_MISTRAL_URL", ""),
            mistral_model=os.getenv("TRAVAUX_MISTRAL_MODEL", ""),
            mistral_key=os.getenv("TRAVAUX_MISTRAL_KEY", ""),
            egress_approved=os.getenv("TRAVAUX_LLM_EGRESS_APPROVED") == "true",
            appflowy_url=os.getenv("TRAVAUX_APPFLOWY_URL", ""),
            public_origin=os.getenv("TRAVAUX_PUBLIC_ORIGIN", ""),
            allowed_hosts=tuple(os.getenv("TRAVAUX_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")),
            auth_mode=os.getenv("TRAVAUX_AUTH_MODE", "password"),
            mistral_document_model=os.getenv("TRAVAUX_MISTRAL_DOCUMENT_MODEL", "mistral-large-4-0" if os.getenv("TRAVAUX_LLM", "demo") == "mistral" else ""),
            mistral_chat_model=os.getenv("TRAVAUX_MISTRAL_CHAT_MODEL", "zai-glm-5-3-flash" if os.getenv("TRAVAUX_LLM", "demo") == "mistral" else ""),
            test_organization_self_join=os.getenv("TRAVAUX_TEST_ORGANIZATION_SELF_JOIN") == "true",
            private_access_origin=os.getenv("TRAVAUX_PRIVATE_ACCESS_ORIGIN", "").rstrip("/"),
            trusted_proxy_ips=tuple(value.strip() for value in os.getenv("TRAVAUX_TRUSTED_PROXY_IPS", "").split(",") if value.strip()),
            organization_join_code=os.getenv("TRAVAUX_ORGANIZATION_JOIN_CODE", ""),
            signature_workflow_enabled=os.getenv("TRAVAUX_SIGNATURE_WORKFLOW_ENABLED") == "true",
        )

    @property
    def effective_organization_join_code(self):
        return self.organization_join_code or ("MAIRIE-TEST" if self.test_organization_self_join else "")

    @property
    def auth_required(self):
        return self.mode in {"staging", "pilot"}

    @property
    def document_model(self):
        return self.mistral_document_model or self.mistral_model or "mistral-large-4-0"

    @property
    def chat_model(self):
        return self.mistral_chat_model or self.mistral_model or "zai-glm-5-3-flash"

    @property
    def fixture_mode(self):
        return self.mode in {"demo", "staging", "public_demo"}

    def validate_public_demo_connectors(self):
        if self.mode != "public_demo":
            return
        configured = self.llm != "demo" or self.egress_approved or any((self.mistral_url, self.mistral_model, self.mistral_document_model, self.mistral_chat_model, self.mistral_key, self.appflowy_url))
        configured = configured or any(value for name, value in os.environ.items()
                                       if name.startswith(("TRAVAUX_MISTRAL_", "TRAVAUX_EWS_", "TRAVAUX_EXCHANGE_", "TRAVAUX_APPFLOWY_", "TRAVAUX_CONNECTOR_", "TRAVAUX_CALDAV_", "TRAVAUX_TELEGRAM_", "TRAVAUX_GOOGLE_", "TRAVAUX_MICROSOFT_")))
        if configured:
            raise ValueError("Le mode public_demo refuse les connexions externes et leurs secrets ; seul le moteur fictif est autorisé.")


def ensure_test_organization_database(settings: Settings):
    path = Path(settings.db_path)
    if not settings.test_organization_self_join and not path.is_file():
        return
    if str(path) == ":memory:":
        raise ValueError("L'organisation test exige une base durable séparée")
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        marker = "test_organization_metadata"
        if not settings.test_organization_self_join:
            if marker in tables:
                raise ValueError("Cette base est réservée à l'organisation fictive ; utiliser une nouvelle base privée")
            return
        if tables and marker not in tables:
            raise ValueError("L'organisation test refuse une base préexistante non marquée")
        with db:
            if marker not in tables:
                db.execute("CREATE TABLE test_organization_metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1),tenant_id TEXT NOT NULL,schema_version INTEGER NOT NULL)")
                db.execute("INSERT INTO test_organization_metadata VALUES(1,?,1)", (settings.tenant_id,))
            elif db.execute("SELECT tenant_id,schema_version FROM test_organization_metadata WHERE singleton=1").fetchone() != (settings.tenant_id, 1):
                raise ValueError("Le marqueur de l'organisation test ne correspond pas à cet espace")
    finally:
        db.close()


def ensure_public_demo_database(settings: Settings):
    ensure_test_organization_database(settings)
    """Never make a protected database public by merely changing an environment flag.

    A new database receives a server-controlled mode/tenant marker. Existing
    unmarked files are refused without reading or changing their application data.
    """
    if settings.mode != "public_demo":
        if settings.db_path.is_file():
            existing = sqlite3.connect(settings.db_path.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                if existing.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='public_demo_metadata'").fetchone():
                    raise ValueError("Cette base est réservée au mode public_demo ; utiliser une base séparée pour les modes protégés ou locaux.")
            finally:
                existing.close()
        return
    settings.validate_public_demo_connectors()
    if str(settings.db_path) == ":memory:":
        raise ValueError("Le mode public_demo exige une base séparée persistante.")
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.db_path, isolation_level=None, timeout=15)
    try:
        connection.execute("BEGIN IMMEDIATE")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if tables and "public_demo_metadata" not in tables:
            raise ValueError("Une base séparée neuve est obligatoire pour la démonstration publique. La base protégée existante reste inchangée.")
        if "public_demo_metadata" in tables:
            marker = connection.execute("SELECT mode,tenant_id,schema_version FROM public_demo_metadata WHERE singleton=1").fetchone()
            if marker != ("public_demo", settings.tenant_id, 1):
                raise ValueError("La base séparée de démonstration ne correspond pas au mode et au périmètre configurés.")
        else:
            connection.execute("CREATE TABLE public_demo_metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1),mode TEXT NOT NULL,tenant_id TEXT NOT NULL,schema_version INTEGER NOT NULL)")
            connection.execute("INSERT INTO public_demo_metadata VALUES(1,?,?,1)", ("public_demo", settings.tenant_id))
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
