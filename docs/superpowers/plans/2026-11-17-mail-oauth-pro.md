# Mail OAuth professionnel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relier Microsoft 365 et Gmail par consentement OAuth, puis lire uniquement les dossiers choisis dans le circuit de preuves existant.

**Architecture:** Le service OAuth stocke les états à usage unique, les PKCE et les jetons dans le coffre existant ; il réutilise les connexions de ConnectionHub. Les lecteurs Graph/Gmail n’écrivent jamais dans la boîte distante et ne valident leur checkpoint local qu’après persistance des messages. Le callback est lié au navigateur et à l’acteur ayant démarré l’opération, avec contrôle des droits actuels.

**Tech Stack:** FastAPI, SQLite, httpx et SecretVault/cryptography déjà installés. Aucun token ID n’est employé pour authentifier les utilisateurs de Travaux.

**Spec:** Demande utilisateur du 17 novembre 2026 de développer les fonctions professionnelles manquantes ; plan de la racine pour l’identité et l’intégration de l’interface.

## Global Constraints

- Configuration par variables serveur, désactivée par défaut ; aucune clé ou connexion réelle dans les tests.
- Refus en démonstration publique ou sans identité protégée, autorisation de sortie et hôtes explicitement autorisés.
- Microsoft : tenant Entra explicite, permissions déléguées User.Read/Mail.Read/offline_access ; Google : gmail.readonly uniquement.
- Garder les adaptateurs EWS/CalDAV compatibles. Aucun envoi, suppression ou marquage de courriel distant.
- Sources techniques : documentation officielle Microsoft auth-code/Graph delta/MIME ; Google OAuth web-server/Gmail sync.

## Review Focus

- Callback rejoué, expiré, mauvais fournisseur ou navigateur : refus avant échange du code.
- Droits retirés après le démarrage : aucune connexion créée au callback.
- Renouvellement concurrent ou déconnexion pendant une réponse : aucun secret réintroduit ni rotation perdue.
- URL de pagination dirigée vers un autre serveur ou réponse excessive : refus, aucun bearer divulgué.
- Échec de persistance ou curseur expiré : pas d’avancement silencieux, aucune preuve supprimée.

### Task 1: Configuration et parcours OAuth

**Files:** créer `src/travaux/mail_oauth.py`, `tests/test_mail_oauth.py`.

**Interfaces:** `register_mail_oauth_routes(app, repo, tenant, actor, settings, *, hub, governance)` retourne `OAuthMailService`. POST `/api/v1/integrations/oauth/{provider}/start` retourne `authorization_url` et expire en 600 secondes. Callback GET correspondant : redirection fixe vers `/#/connexions` sans code, état ou jeton dans la destination.

- [x] Tester rouge configuration absente, démo, permissions, S256, TTL et liaison navigateur.
- [x] Implémenter flow state hashé, secret PKCE chiffré, consommation atomique et revalidation des habilitations, ainsi que la validité de la session de départ sans dépendre de son cookie Strict au retour.
- [x] Tester code échange, refus/rejeu/expiration et absence des secrets dans les DTO/erreurs.

### Task 2: Jetons chiffrés et renouvellement

**Files:** `src/travaux/mail_oauth.py`, `tests/test_mail_oauth.py`.

- [x] Tester rouge chiffrement, expiration, refus fournisseur et rafraîchissements concurrents, avec deux Repository indépendants sur la même base.
- [x] Implémenter lease SQLite et CAS du ciphertext pour protéger rotation et déconnexion concurrente.
- [x] Tester retrait local et révocation Google contrôlée ; distinguer déconnexion locale de révocation des consentements Microsoft. Journal organisationnel sans secret, déconnexion/audit atomiques.

### Task 3: Lecteurs Graph et Gmail

**Files:** créer `src/travaux/integrations/cloud_mail.py`, `tests/test_cloud_mail.py`.

**Interfaces:** `CloudMailReader.probe()`, `collect_mail(repo, tenant, connection_id, *, guard)`, `close()` ; fabrique via le service OAuth attaché au hub.

- [x] Tester rouge profils, dossiers/labels, MIME, pagination et URLs hostiles avec HTTP transport local déterministe.
- [x] Implémenter transport HTTPS borné et Graph delta par dossier ; Gmail bootstrap puis history, checkpoints chiffrés.
- [x] Tester checkpoint après persistance, rejeu idempotent et curseur périmé explicitement signalé. Reprise explicite protégée par révision, conservation des originaux vérifiée.

### Task 4: Raccordement au hub

**Files:** modifier uniquement `src/travaux/connection_hub.py` ; racine responsable de `api.py` et de l’interface.

- [x] Étendre les capacités et le lecteur aux fournisseurs canoniques `google` et `microsoft365` sans changer les comptes EWS. Les détails des comptes restent réservés aux administrateurs.
- [x] Tester les recettes existantes du hub et du backfill EWS.

### Task 5: Documentation et remise

**Files:** créer `docs/CONNECTEURS_MAIL_OAUTH_2026.md`.

- [x] Documenter les variables exactes, applications à enregistrer, URL de retour, scopes et restrictions, dont l’exclusion des query callbacks des journaux proxy.
- [x] Exécuter tests ciblés + compilation ; communiquer à la racine les tests et points d’intégration exacts. 56 tests du sous-lot et recettes existantes réussis, Ruff et compilation réussis.
- [x] Indiquer que les transports sont testés par contrats locaux, sans compte Microsoft/Google réel ni qualification de production.
