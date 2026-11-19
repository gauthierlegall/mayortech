# Organization Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Livrer création de compte → code d’organisation → décision, avec Mairie test automatiquement accueillante.

**Architecture:** Réutiliser l’identité Keycloak, les sessions d’accueil isolées, `account_join_requests`, les membres et les droits par dossier. Valider le code et la décision dans le service serveur. Garder le profil test distinct des organisations réelles.

**Tech Stack:** FastAPI, SQLite, Keycloak, React/TypeScript, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-18-organization-code.md`

## Global Constraints

- « Mairie test », code « MAIRIE-TEST », acceptation automatique uniquement pour le profil fictif.
- Email vérifié et 2FA conservés ; pas d’accès métier avant accord ; aucune réactivation autonome d’un compte retiré.
- Approbation humaine des organisations réelles ; contrôle du tenant et des révisions ; aucun envoi de message par ce lot.
- Conserver le style Lovable et DM Sans ; clavier et affichage 390 × 844 / 1920 × 1080.
- Aucune lecture de secret brut en sortie, aucun changement des comptes réels pendant les essais.

## Review Focus

- Un mauvais code, un corps manquant et le chemin historique ne doivent pas activer un compte.
- Un éditeur, une session d’accueil ou un administrateur étranger ne doivent pas approuver une demande.
- Un refus ou retrait ne doit pas devenir un accord automatique de test.
- Une révision périmée ou une erreur d’écriture ne doit pas laisser activation, statut et sessions en désaccord.
- Le formulaire conserve la saisie en erreur, évite les doubles envois et ne confond pas compte personnel et connexion mail.

### Task 1: Service et contrats serveur

**Files:** `src/travaux/account_onboarding.py`, `src/travaux/config.py`, `src/travaux/api.py`, `tests/test_account_onboarding.py`, nouveau `tests/test_organization_codes.py`.

**Interfaces:** Les routes et DTO exacts sont dans la spécification. Le code réel vient de la configuration serveur ; aucun code de test ne fonctionne dans une instance réelle sans sa configuration explicite.

- [x] Écrire puis exécuter les tests rouges de code, refus, décision et isolement.
- [x] Implémenter les routes, limiter les tentatives et conserver les transactions/sessions.
- [x] Mettre à jour les anciens tests d’adhésion pour fournir un code lors d’une première demande.
- [x] Vérifier les tests ciblés, compilation et revue de sécurité indépendante.

### Task 2: Interface de demande et validation

**Files:** `frontend-lovable/src/features/workspace/OrganizationJoin.tsx`, `organization-join-model.mjs`, `organization-join.css`, tests associés ; nouveau `OrganizationRequests.tsx`, intégration `Settings.tsx` et méthodes `web/api.js`.

**Interfaces:** Consommer les routes de la spécification. Garder `joinOrganization(id, payload)` pour l’entrée déjà autorisée et ajouter `joinOrganizationCode(code)`, `organizationJoinRequests()`, `decideOrganizationJoin(id, payload)`.

- [x] Tests rouges des nouveaux états et de validation de DTO, puis implémentation minimale.
- [x] Saisie du code, erreur, attente, refus, entrée existante et changement de compte ; pas de catalogue à parcourir à la première visite.
- [x] Section administrateur pour accepter/refuser ; conserver les autres réglages des membres.
- [x] TypeScript, tests JS et captures navigateur des états à 1920/390.

### Task 3: Intégration et publication

**Files:** scripts de recette sous `work/`, opérateurs existants `deploy/hetzner/deploy.py` et `deploy/private-site/app_update.py`, documentation de livraison.

- [x] Tests Python/JS/natifs et build du paquet final ; vérifier les sources autorisées par le déploiement.
- [x] Déployer la version publique puis mettre à jour seulement l’application et le worker privés avec sauvegarde vérifiée et plan frais.
- [x] Essayer sur HTTPS réel avec une identité jetable prévalidée : mauvais code refusé, MAIRIE-TEST accepté, accès aux dossiers fictifs, déconnexion et révocation.
- [x] Captures Full HD/mobile et rapport limité à ce qui a été réellement validé ; actualiser l’archive source.

No Git repository is present; the existing SSH/Docker deployment operators provide release receipts instead of commits.
