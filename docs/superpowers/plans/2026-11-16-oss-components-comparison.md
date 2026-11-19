# OSS components comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Récupérer un corpus utile de code OpenProject traçable et tester des alternatives sur leurs fonctions réellement plus complètes que Travaux 0.8.1.

**Architecture:** Références tierces isolées du runtime ; essais fictifs locaux ou conteneurs privés successifs, ressources bornées. Aucune connexion mail/IA réelle, migration ou publication. Les agents de collaboration disponibles exécutent les tâches indépendantes.

**Tech Stack:** OpenProject 17.9.7, Zammad, ERPNext/Frappe, Haystack, Python, Docker et Playwright. Les versions des nouveaux candidats sont vérifiées puis épinglées dans leurs preuves.

## Fichiers et responsabilités

- `outputs/travaux-oss-comparison-2026-11-16/vendor-reference/openproject/` : code original, licences et manifeste d'empreintes, sans import dans Travaux.
- `outputs/travaux-oss-comparison-2026-11-16/notes/openproject-code.md` : portée, dépendances et choix de réemploi.
- `outputs/travaux-oss-comparison-2026-11-16/{zammad,erpnext,haystack}/` : scripts, corpus fictif, versions et résultats propres au candidat.
- `outputs/travaux-oss-comparison-2026-11-16/README.md` : comparaison par capacité et recommandation fondée sur les essais.
- `work/*{zammad,erpnext,haystack}*` : état temporaire privé, jamais inclus dans les livrables publics.

## Review Focus

- Ne pas confondre bibliothèque embarquable, application complète et simple inspiration ; conserver chaque licence et les obligations de distribution.
- Ne pas déclarer testés Exchange, génération Mistral, transport mail ou droits non exercés.
- Comparer recherche sur les mêmes questions et sources, filtrer les droits avant recherche et signaler les erreurs.
- Les nouvelles piles serveur doivent être successives ; vérifier noms/labels, mémoire, disque et release Travaux avant/après ; arrêt propre à l'essai.
- Les captures sont issues des vrais parcours ; données et comptes fictifs exclusivement.

### Task 1: Code OpenProject

- [x] Sélectionner 3–5 mécanismes utiles et lire leur code exact sur le tag évalué.
- [x] Acquérir les fichiers avec licences, URLs et SHA-256 ; exécuter au moins une fonction originale portable si possible.
- [x] Comparer au code actuel et distinguer intégration API, reprise de code et mécanisme à développer.

### Task 2: Recherche Haystack

- [x] Installer une version épinglée dans un environnement local distinct.
- [x] Exécuter les mêmes documents/questions français avec Haystack et Travaux ; conserver classements, citations et refus d'accès.
- [x] Mesurer honnêtement gain, régression, coût d'intégration et limites sans appel LLM.

### Task 3: Applications projet et demandes

- [x] Vérifier sources/versions/licences, préflight ressources et revue des configurations Zammad et ERPNext.
- [x] Exécuter Zammad isolément : onze contrôles natifs et huit HTTP authentifiés sur mails locaux, affectations, pièces, historique et droits.
- [x] Installer ERPNext r1 ; conserver le refus du seed et les trois refus r2 pour réserve disque, avec zéro ressource r2 créée.
- [ ] Exécuter le workflow métier ERPNext et les captures d'UI Zammad sur une infrastructure disposant d'une réserve stable. Ces parcours restent non validés ; aucune réussite n'est revendiquée.
- [x] Capturer le correctif local Full HD, conserver les résultats et signaler les parcours d'interface incomplets des candidats.
- [x] Arrêter les seules ressources d'essai et vérifier que Travaux reste inchangé.

### Task 4: Remise

- [x] Rédiger matrice des capacités réellement testées et les meilleurs ajouts à notre application.
- [x] Relecture indépendante des affirmations, licences et preuves ; vérification des liens, captures et absence de secrets.
- [x] Livrer le corpus de code traçable, les recettes et le rapport, sans bascule du produit.

### Task 5: Correctif local issu de la comparaison

- [x] Observer la régression des suggestions Ajoncs/Chênes avant correction.
- [x] Limiter les suggestions au chantier, conserver les noms libres et les protections fingerprint/CAS.
- [x] Vérifier tests/build puis vrai navigateur/API/SDK Yjs dans une base locale fictive ; conserver captures et fermeture de l'environnement.

**État intermédiaire :** premières installations ERPNext et Zammad terminées, essais métier non lancés faute de réserve disque ; nettoyages bornés conservés. Un nouveau préflight après nettoyage/GC montre environ 24 Gio libres et 4,4 Gio mémoire disponible. Reprises r2 autorisées successivement, avec seuils de disque plus hauts (avant pull 16 Gio, avant init 10 Gio, arrêt 8 Gio), preuves séparées. Ne pas confondre les premières installations avec leurs recettes métier ultérieures.

**Clôture documentée :** Zammad r2 a terminé onze contrôles natifs et huit HTTP authentifiés ; le watchdog l'a arrêté avant une capture d'UI métier valide. ERPNext r2 n'a franchi aucun des trois préflights, donc zéro mutation et zéro ressource créée. Tous les conteneurs ERPNext/Zammad r1/r2 et leurs états privés ont été retirés ; les deux anciens volumes OpenProject restent conservés. Site public vérifié à HTTP200 en version0.8.1. Archive `outputs/travaux-oss-code-2026-11-16.zip` créée avec CRC et SHA-256 ; les parcours non validés ci-dessus restent explicitement ouverts pour un environnement stable.
