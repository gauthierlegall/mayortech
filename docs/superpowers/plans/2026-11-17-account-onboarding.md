# Inscription et organisation test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre l’inscription chez l’IdP avec double authentification, puis le choix d’une organisation sans accorder d’accès aux données avant une adhésion autorisée.

**Architecture:** OIDC et SessionStore existants restent le socle. Une identité MFA valide encore inconnue reçoit uniquement une session opaque `onboarding:<tenant>` ; les routes de compte dédiées ne servent que l’annuaire de l’instance et l’adhésion. La démo test permet un rôle éditeur sur les dossiers fictifs ; les organisations réelles attendent l’approbation d’un administrateur.

**Tech Stack:** FastAPI, SQLite, OIDC/joserfc, SessionStore opaque existant ; exemple Keycloak pour inscription/vérification email/OTP.

**Spec:** Steering utilisateur transmis par la racine : création de compte réelle, double authentification, entrée dans une organisation test pour démonstration familiale. La racine garde les modifications globales de Settings/API et les blocages de mails/IA réels pour le mode test.

## Global Constraints

- Aucun mot de passe ou secret OTP dans Travaux ; inscription sur une URL HTTPS de l’IdP explicitement configurée.
- `finish(allow_onboarding=False)` garde le refus historique des membres inconnus ; callback HTTP utilise `allow_onboarding=True` seulement après validation OIDC complète.
- Session d’onboarding sans accès aux routes métier, limitée à 15 minutes ; aucune auto-affectation administrateur.
- Self-join seulement si `settings.test_organization_self_join` validé par Settings, en staging OIDC fictif sans sorties IA/messagerie réelles.
- Un membre révoqué ne se réactive pas par le self-join : celui-ci ne concerne que la première demande inactive, lecteur, révision 0.

## Review Focus

- Paramètre de création de compte non configuré, URL hostile ou intent inconnu : refus sans redirection arbitraire.
- MFA, signature ou nonce incorrects : aucune session, y compris d’onboarding.
- Session d’onboarding employée pour bootstrap/mail/projet : refus ; le choix d’organisation n’accorde rien implicitement.
- Autre tenant ou membre désactivé : aucune entrée automatique et aucune réactivation.
- Deux requêtes d’adhésion ou un échec de création de session : transaction et audit empêchent une adhésion partielle.

### Task 1: Intent OIDC et session d’onboarding

**Files:** modifier `src/travaux/oidc.py`, créer `tests/test_account_onboarding.py`.

- [x] Observer tests rouges pour intent signup, URL configurée, identité MFA inconnue et session d’onboarding.
- [x] Ajouter `TRAVAUX_OIDC_SIGNUP_URL`, validation HTTPS/hôte et intent `login|signup` ; conserver PKCE, nonce, état unique et politique MFA.
- [x] Ajouter `allow_onboarding=False` au service et émission d’une session d’onboarding au callback HTTP pour l’identité en attente.

### Task 2: Annuaire et adhésion

**Files:** créer `src/travaux/account_onboarding.py` ; racine responsable de son enregistrement dans API.

**Interfaces:** `register_account_onboarding_routes(app,repo,settings,sessions,members)` retourne le service ; GET `/api/v1/account/organizations`, POST `/api/v1/account/organizations/{id}/join` body `{}`.

- [x] Tester rouge session globale, annuaire unique, adhésion test, autre tenant, demande réelle et membre révoqué.
- [x] Implémenter annuaire borné au tenant de l’instance ; ne pas énumérer les organisations d’un autre déploiement.
- [x] Self-join test : rôle éditeur, grants explicites aux projets fictifs, audit et renouvellement de session atomiques. Réel : demande inactive en attente.

### Task 3: Exemple Keycloak et vérifications

**Files:** créer `deploy/keycloak/realm-test.example.json`, documentation et préparation Compose sans secret ni déploiement.

- [x] Vérifier les champs d’inscription, email et OTP sur la documentation/source officielle de la version choisie.
- [x] Fournir des redirect URI exactes, des références AMR reliées aux vraies exécutions OTP et aucune fausse assertion MFA statique.
- [x] Exécuter les tests ciblés et communiquer les résultats/limites à la racine et au frontend.

**Vérifications du lot :** 70 tests ciblés verts (onboarding unitaire et HTTP, OIDC, identité, rotation du coffre, OAuth mails et adaptateurs cloud), Ruff propre ; JSON du realm contrôlé. Ces tests emploient des identités et échanges de fournisseur contrôlés. L’import du realm et l’inscription dans un vrai processus Keycloak restent une recette séparée ; aucun déploiement distant n’est couvert.

### Task 4: Préparation persistante de l’organisation test

**Files:** `scripts/prepare_test_organization.py`, `tests/test_prepare_test_organization.py`.

- [x] Observer les tests rouges pour création persistante et réutilisation du tenant avant l’ajout du script.
- [x] Utiliser le vrai `create_app` et son markerDB, neutraliser l’environnement TRAVAUX hérité, ne créer aucun compte, secret ou serveur.
- [x] Vérifier création/idempotence, refus d’une base non marquée sans altération et refus d’un autre tenant : 3 tests verts et Ruff propre.
- [x] Préparer `.local/organisation-test/workspace.sqlite3` pour `organization-test` : 6 projets fictifs et 0 compte créé. L’IdP et l’origine HTTPS de présentation restent des paramètres opérateur séparés.

La recette réelle Keycloak est décrite dans `docs/RECETTE_KEYCLOAK_LOCALE_2026-11-17.md` : import et démarrage réussis, parcours signup/MFA arrêté au refus TLS lié à Avast, tous les PID du lab arrêtés. Le test global lancé à ce stade donnait 502 verts et deux refus anticipés dus aux variables TLS ambiantes dans les tests LLM ; la racine reprend la vérification globale dans un processus pytest sans ces variables.
