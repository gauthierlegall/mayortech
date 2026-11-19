# Version professionnelle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Développer le raccordement mail Microsoft/Google, l’identité individuelle et les fonctions de suivi manquantes, avec un environnement privé distinct de la démonstration et des preuves de fonctionnement.

**Architecture:** Conserver FastAPI/SQLite, Casbin, les actions canoniques Yjs et l’interface actuelle. Ajouter des modules délimités pour OIDC, OAuth mail et accès par dossier ; stocker les secrets chiffrés côté serveur, sans authentification simulée dans l’espace privé. Les fonctions métier se rattachent aux mêmes dossiers/actions. Le serveur partagé actuel n’est pas modifié tant que son contrôle de capacité échoue.

**Tech Stack:** Python 3.11, FastAPI, httpx, cryptography, joserfc pour vérification JOSE, React/TypeScript, BlockSuite/Yjs, FullCalendar et Frappe Gantt existants.

**Spec:** demandes de la conversation et [audit des commissions](../../../../commissions-oss-2026-11-17/README.md) ; [écarts de la cible privée](../../cible-ovh-exchange-mistral-2026-11-16.md). L’utilisateur autorise le développement et demande de continuer ; pas d’attente de validation de plan.

**Point de situation — 17 novembre 2026 :** les cases portent sur le code et sa recette locale. La [notice privée](../../MISE_EN_SERVICE_PRIVEE_2026.md) distingue les fournisseurs contrôlés, le laboratoire Keycloak partiel et les activations réelles restantes. Aucun déploiement OVH ni raccordement municipal réel n'est annoncé. La demande complémentaire du jour est traitée : extraction Large4, chat GLM, compte puis organisation test, dépôt persistant et modifications du chat sur confirmation.

## Global Constraints

- Conserver la démo publique fictive, sans secrets, appels mail ou IA réels.
- Développer les intégrations ; leur activation réelle exige l’enregistrement des applications, les paramètres d’IdP et les autorisations de la collectivité. Aucun secret par chat.
- Identité par couple issuer/subject, inscription contrôlée, droits persistants, refus par défaut et révocation des sessions. Aucun rôle attribué depuis un nom, un courriel ou une sortie IA.
- Lecture seule des boîtes externes ; sélection explicite des dossiers ; curseur après persistance, reprise idempotente et révocation testées.
- Aucune copie de code Fair Use dans le produit. Préserver licences et provenance des dépendances.
- GLM servi par Mistral est le choix signalé ; pas de bascule implicite d’endpoint ou de fournisseur.
- Les validations institutionnelles, MFA chez l’IdP, contrat d’inférence, sauvegarde hors site et recette du serveur réel doivent être distingués du code livré. Aucune certification revendiquée.

## Review Focus

- Callback OAuth/OIDC repris, expiré, associé à un autre navigateur/acteur/fournisseur ou renvoyé après retrait d’un droit : refus sans divulgation.
- Jeton signé mais mauvais issuer/audience/nonce/algorithme/MFA : aucune session créée.
- Accès indirect par pièce, source, recherche, conversation, export, compteur ou calendrier : mêmes droits que le dossier, avant tout appel IA.
- Déconnexion pendant un renouvellement de jeton ou crash pendant import : aucune résurrection de secret, perte de mail ou duplication d’action.
- Nouvelle occurrence récurrente, édition simultanée et affectation inconnue : historique conservé, idempotence et conflit explicite.

## Lots et interfaces

### 1. Identité professionnelle et coffre — root

Fichiers : `src/travaux/identity.py`, `tests/test_identity.py`, `config.py`, `auth.py`, `governance.py`, `api.py`, `cli.py` ; partie `SecretVault` de `connection_hub.py` coordonnée avec l’agent OAuth.

- [x] Tests en échec pour état/PKCE/nonce, vraie signature JOSE, issuer/audience/expiration, membre inconnu/inactif, rôle retiré et révocation de session.
- [x] OIDC configurable, autorisations de membres préalables, session opaque individuelle, désactivation immédiate, gestion durable des rôles et journal sans contenu sensible.
- [x] Clés explicites dans l’espace OIDC, lecture des anciennes clés et rotation atomique ; pas de clé créée à côté des données pour ce profil.
- [x] Route `POST /api/v1/auth/start` → `authorization_url`, callback GET avec cookie de liaison Lax distinct ; cookie de session Strict après retour.
- [x] `GET /api/v1/session` ajoute `auth:{method,sso_available,label}`. Désactiver la phrase de passe partagée lorsque la méthode OIDC est choisie.

### 2. Microsoft 365 et Google — agent pro_oauth

Fichiers : `mail_oauth.py`, `integrations/cloud_mail.py`, tests et documentation dédiés ; modifications étroites de `connection_hub.py`.

- [x] Plan spécialisé et tests en échec.
- [x] Authorization code + PKCE, état consommable une fois, liaison acteur/tenant/navigateur, permissions revalidées au callback.
- [x] Jetons chiffrés, renouvellement sérialisé et compatible avec déconnexion ; scopes lecture seule.
- [x] Profil, choix de dossiers, collecte Graph/Gmail MIME avec reprise durable et erreurs actionnables.
- [x] Routes start/callback ; provider disponible seulement lorsque les paramètres serveur sont présents. Pas de fausse disponibilité dans la démo.

Preuves et limites : [plan OAuth](2026-11-17-mail-oauth-pro.md), 56 tests du sous-lot et des recettes existantes ; transports HTTP contrôlés, aucun compte fournisseur réel. La recette DSI reste ouverte.

### 3. Accès par dossier — agent final_review, intégration root

Fichiers précis arrêtés après cartographie des points d’entrée, dans `project_access.py` et les services consommateurs ; root garde la propriété de `api.py`.

- [x] Tests négatifs entre deux membres, deux dossiers et deux tenants, accès direct/indirect et révocation.
- [x] Grants persistants par dossier, admin d’espace explicite et refus par défaut pour les autres membres.
- [x] Filtrage des listes et compteurs avant retour ; filtres de recherche et citations avant appel IA, exports et pièces inclus.

Preuves : [plan ACL](2026-11-17-project-access.md) et tests négatifs dédiés ; la revue indépendante de l'assistant a en plus fait fermer l'accès aux plans opaques quand une source est partagée avec un dossier dont le grant a été retiré.

### 4. Connexion et configuration dans l’interface — agent calendar_integrations puis root

Fichiers : `AuthGate.tsx`, `pro-auth-client.mjs` et son test ; root complète `web/api.js` et le parcours mail.

- [x] Bouton de connexion institutionnelle, aucun mot de passe partagé en OIDC ; URL de redirection HTTPS validée et erreur générique.
- [x] Parcours Microsoft/Google câblé selon capacités serveur : autoriser, choisir les dossiers, lancer la lecture, révoquer ; recette fournisseur réel encore requise.
- [x] Gestion des membres et droits de dossier ; affichage d’erreurs utiles, sans pastilles décoratives permanentes.

### 5. Suivi professionnel et commissions

- [x] Définir et tester checklist structurée par action, commentaires et affectation à un membre réel, liés aux identifiants existants.
- [x] Occurrences récurrentes distinctes avec clé d’idempotence et dates structurées ; ne pas interpréter silencieusement une phrase libre.
- [ ] Dossiers de séance : ordre du jour, pièces, avis relu, actions liées ; vues adaptées aux quatre commissions et Gantt réservé aux dépendances.

Le [module de collaboration](2026-11-17-action-collaboration.md) dispose de 24 tests dédiés ; les deux cases cochées portent sur le contrat backend. L'interface finale et la création native d'occurrences restent à recetter. L'[import de documents](2026-11-17-document-uploads.md), la recherche dynamique et la confirmation du chat disposent d'une preuve HTTP intégrée avec fournisseur contrôlé ; aucun fait n'est accepté automatiquement.

### 6. Exploitation et passage réel

- [x] Notice de mise en service privée et exemples d'environnement sans secrets, distincts pour organisation fictive et candidat OVH réel ; noms vérifiés dans le code, aucun fichier runtime modifié.
- [ ] Configuration privée OVH reproductible, clés séparées, sorties autorisées, quarantaine/analyse des pièces, journaux sans secrets, sauvegarde chiffrée et restauration.
- [x] Recettes locales Python/frontend/éditeur, scénarios d’injection et droits, navigateur FullHD/mobile, revue indépendante ; qualification externe séparée.
- [ ] Rapport exact : code implémenté, intégrations testées sur fournisseur simulé, configurations et recettes réelles restant nécessaires. Publication seulement après capacité suffisante et cible privée configurée.

Les lots sont exécutés dans cet ordre selon leurs dépendances. Les migrations additives sont testées sur base existante et base neuve ; aucune migration de production ni purge de données n’est déclenchée dans cette phase.

## Complément : document, assistant et compte personnel

- [x] `mistral-large-4-0` pour les documents ; `zai-glm-5-3-flash` pour le RAG et les propositions du chat. Modèles vérifiés dans les requêtes HTTP simulées ; aucun appel réel fournisseur.
- [x] Inscription OIDC, vérification d’adresse signée et politique MFA ; session d’onboarding sans donnée métier ; organisation test persistante avec six projets fictifs et sans compte administrateur automatique.
- [x] PDF/DOCX/TXT/MD/CSV jusqu’à 5 Mo : original, source, reçu et job persistés atomiquement ; extraction puis propositions non acceptées automatiquement.
- [x] Chat : lecture sourcée ou proposition explicite de propriété/note/action ; confirmation propriétaire liée aux révisions, refus des conflits et écritures idempotentes.
- [x] Parcours navigateur avec vraie API, SQLite, parseur PDF et action Yjs persistante après rechargement ; transports IA simulés. Les contrôles MFA réels sont bloqués au laboratoire par l’interception TLS du poste.
- [x] Candidat OVH app/worker, coffre hors données et Caddy ; rendu Compose vérifié sans démarrer de daemon. Sauvegarde restic, validation Caddy et recette institutionnelle non réalisées.
