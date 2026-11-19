# OpenProject evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Évaluer réellement OpenProject Community sur un chantier fictif sans remplacer Travaux.

**Architecture:** Instance isolée, version et image épinglées, accès par boucle locale/tunnel et ressources bornées. Corpus fictif et comptes distincts ; aucune messagerie ou IA externe activée. L'exécution utilise les outils de collaboration disponibles dans cette session.

**Tech Stack:** OpenProject Community 17.9.7, Docker, API HAL v3, Playwright.

**Spec:** [audit des solutions](../../audit-solutions-libres-2026-11-16.md).

## Global Constraints

- Aucune migration ni modification des données ou du déploiement Travaux existant.
- Aucun compte, mail ou document institutionnel ; adresses réservées `.invalid` ou `.test` uniquement.
- Aucun SMTP, IMAP, OAuth institutionnel, modèle payant ni service IA externe activé.
- Instance non publiée sur Internet ; secrets hors rapport et sorties d'outils.
- Distinguer observation réelle, test simulé et capacité documentée.

## Review Focus

- Un autre acteur ne doit pas retrouver projet privé, documents ou PJ.
- Dates et dépendances doivent rester cohérentes après sauvegarde et relecture.
- Une révision ancienne doit être refusée, sans écraser une modification concurrente.
- Un responsable proposé doit correspondre à une identité autorisée, pas à un nom libre inventé.
- Un texte de mail ou une proposition IA ne doit pas confirmer automatiquement une action.

### Task 1: Instance isolée et corpus

- [x] Contrôler moteur Docker et ressources, sans mutation.
- [x] Relire Compose/bootstrap et épingler le digest officiel.
- [x] Démarrer uniquement les ressources propres à l'essai, sur boucle locale.
- [x] Créer le chantier, actions, dépendances, comptes et documents fictifs.
- [x] Vérifier santé, limites et absence de publication Internet/connexion externe.

### Task 2: Parcours et frontières API

- [x] Tester lecture et modification du planning, rechargement et historique.
- [x] Tester acteur autorisé/refusé, identifiants directs, recherche et PJ.
- [x] Tester conflit de révision et validation du responsable.
- [x] Examiner le parcours mail avec EML fictif, sans transport externe.
- [x] Capturer les écrans utiles en 1920 × 1080 et conserver les réponses API expurgées.

### Task 3: Décision et remise

- [x] Confronter le mapping des données aux capacités réellement observées.
- [x] Revoir les preuves avec un agent indépendant.
- [x] Rédiger verdict, fonctions manquantes et coût de raccord qualitatif.
- [x] Arrêter les conteneurs d'essai si leur fonctionnement n'est plus nécessaire ; conserver les preuves et la procédure de relance.

**Clôture du 16 novembre 2026 :** instance et tunnel arrêtés, deux jetons du corpus révoqués, deux volumes conservés. Recette partielle documentée : le scénario mail direct échoue au besoin de déduplication ; des erreurs UI restent ouvertes. Les cases cochées signifient que les travaux d'évaluation sont réalisés, pas que tous les scénarios métier réussissent. Rapport : `outputs/travaux-openproject-evaluation/README.md`.
