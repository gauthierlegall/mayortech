"""Public candidate contract; no credentials or network access at import."""
from pathlib import Path
import copy
import ipaddress

PROJECT = "mayortech-private"
BASE = Path("/opt/apps/mayortech-private")
MARKER = "mayortech-private-v1\n"
APP_DOMAIN = "espace.kerforge.com"
IDP_DOMAIN = "identite.kerforge.com"
ISSUER = "https://identite.kerforge.com/realms/mayortech"
APP_IMAGE = "travaux-mairie:0.8.1-20261117T221755Z-6082cd"
KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak:26.8.2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0"
POSTGRES_IMAGE = "postgres:17-alpine@sha256:dc17045ccfd343b49600570ea734b9c4991cf1c3f3302e67df51e3b402dd55c4"


def admitted(disk_bytes, available_memory_bytes):
    return disk_bytes > 3 * 1024**3 and available_memory_bytes > 2.5 * 1024**3


def realm(template, client_secret, smtp_password):
    value = copy.deepcopy(template)
    value.update(realm="mayortech", displayName="MayorTech", loginTheme="mayortech", internationalizationEnabled=True,
                 supportedLocales=["fr", "en"], defaultLocale="fr", verifyEmail=True,
                 actionTokenGeneratedByUserLifespan=300, accessCodeLifespanLogin=300,
                 eventsEnabled=True, eventsExpiration=604800, adminEventsEnabled=True, adminEventsDetailsEnabled=False)
    value["users"] = []
    value["smtpServer"] = {"host": "smtp.resend.com", "port": "2465", "user": "resend", "password": smtp_password,
                           "from": "connexion@kerforge.com", "fromDisplayName": "MayorTech", "auth": "true",
                           "ssl": "true", "starttls": "false", "debug": "false"}
    client = value["clients"][0]
    client.update(clientId="mayortech-space", name="MayorTech — espace test privé", rootUrl="https://"+APP_DOMAIN,
                  baseUrl="https://"+APP_DOMAIN, redirectUris=["https://"+APP_DOMAIN+"/api/v1/auth/callback"],
                  webOrigins=["https://"+APP_DOMAIN], secret=client_secret)
    client["attributes"]["post.logout.redirect.uris"] = "https://"+APP_DOMAIN
    return value


def app_environment(client_secret, caddy_ip):
    caddy_ip = str(ipaddress.ip_address(caddy_ip))
    return {"TRAVAUX_MODE": "staging", "TRAVAUX_AUTH_MODE": "oidc", "TRAVAUX_TEST_ORGANIZATION_SELF_JOIN": "true",
            "TRAVAUX_DB": "/data/mayortech-test.sqlite3", "TRAVAUX_TENANT": "mayortech-test",
            "TRAVAUX_PUBLIC_ORIGIN": "https://"+APP_DOMAIN, "TRAVAUX_ALLOWED_HOSTS": APP_DOMAIN,
            "TRAVAUX_TRUSTED_PROXY_IPS": caddy_ip,
            "TRAVAUX_LLM": "demo", "TRAVAUX_LLM_EGRESS_APPROVED": "false", "TRAVAUX_PASSWORD_HASH": "",
            "TRAVAUX_CONNECTOR_KEY_FILE": "/run/secrets/connector-vault.keys",
            "TRAVAUX_CONNECTOR_SECRET_KEYS": "", "TRAVAUX_CONNECTOR_SECRET_KEY": "",
            "TRAVAUX_OIDC_ISSUER": ISSUER, "TRAVAUX_OIDC_CLIENT_ID": "mayortech-space",
            "TRAVAUX_OIDC_CLIENT_SECRET": client_secret, "TRAVAUX_OIDC_ALLOWED_HOSTS": IDP_DOMAIN,
            "TRAVAUX_OIDC_REQUIRED_AMR": "pwd,otp", "TRAVAUX_OIDC_REQUIRED_ACR": "",
            "TRAVAUX_OIDC_EGRESS_APPROVED": "true",
            "TRAVAUX_OIDC_SIGNUP_URL": ISSUER+"/protocol/openid-connect/registrations",
            "TRAVAUX_OIDC_RESET_URL": ISSUER+"/protocol/openid-connect/forgot-credentials",
            "SSLKEYLOGFILE": "", "QUICLOGDIR": ""}
