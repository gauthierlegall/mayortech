# Commissions Plougastel et simplification UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Proposer des outils et vues adaptés aux tâches réelles des quatre commissions de Plougastel-Daoulas, récupérer les briques libres utiles et retirer les indicateurs de fonctionnement décoratifs du produit.

**Architecture:** Recherche sur les sources officielles de la ville et le PV du 4 avril 2026 ; séparation entre responsabilités documentées et propositions de produit. Références tierces isolées avec licences/empreintes, essais fictifs locaux. Le frontend Lovable et les garanties de sauvegarde restent dans le produit actuel. GLM servi par Mistral est le choix IA signalé par l'utilisateur ; aucune nouvelle connexion ou clé n'est utilisée pour cette étude.

**Tech Stack:** React/TypeScript, FastAPI, BlockSuite/Yjs existants ; références Vikunja, Kanboard et outils de réunions collectives. Aucun Docker ou service distant de benchmark.

**Spec:** demandes de la conversation : recherche des tâches commission par commission, Gantt seulement pertinent selon besoin, prise en compte de Registrar IA/GLM/Mistral, suppression des pastilles inutiles comme « Tout est enregistré », explication honnête des connecteurs mail indisponibles.

## Global Constraints

- Commune confirmée : Plougastel-Daoulas, quatre commissions permanentes et CAO distincte ; ne pas inventer de nouvelles commissions administratives.
- Pas de données individuelles municipales dans les essais ; aucun mail, appel IA, réservation ou publication officielle envoyé.
- Pas de copie de code Fair Use comme s'il était libre ; garder les licences et sources exactes des références.
- Les statuts métier, erreurs, modifications non enregistrées et progrès actifs utiles ne sont pas des pastilles décoratives.
- Outlook/Microsoft365 et Google OAuth restent non implémentés : ne pas lever les restrictions de la démo ni présenter un raccord réel comme livré.

## Review Focus

- Distinguer instruction/avis/arbitrage de commission, décision du conseil et services métier déjà en place.
- Distinguer travail général d'une commission des dossiers individuels sensibles du CCAS/RH ; aucun partage implicite ou index IA global.
- Vérifier la récurrence réelle (report ou création d'occurrence), les échéances et les accès entre deux commissions.
- Après suppression des indicateurs, sauvegarde, rechargement et gestion d'erreur restent vérifiables ; aucun polling inutile ne reste attaché au seul badge.
- Ne pas déployer un paquet qui contiendrait les binaires/env/données privés des essais.

### Task 1: Fonctions et écrans par commission

- [x] Vérifier les quatre commissions et leur circuit dans les sources municipales datées.
- [x] Rattacher aux pages des services les tâches concrètes, les rythmes et les outils déjà utilisés.
- [x] Proposer liste, calendrier, dossier, carte, tableau d'arbitrage ou Gantt selon le travail réel.

### Task 2: Code libre et essais

- [x] Épingler sources/licences de Vikunja et Kanboard ; séparer Planka Fair Use.
- [x] Tester des fonctions originales et tenter le workflow local : 5 cas parseur Vikunja, 3 utilitaires Nextcloud, 6 cas helper PLANKA. Démarrage Vikunja observé, recette HTTP/UI bloquée par disparition/refus de réécriture du binaire ; pas de contournement ni de succès complet revendiqué.
- [x] Conserver les preuves, les limites et l'arrêt des seules ressources locales créées.

### Task 3: Suppression des indicateurs décoratifs

- [x] Inventorier les lieux d'affichage du statut global et des succès persistants inutiles.
- [x] Modifier les composants et retirer les styles/listeners/polling devenus inutiles.
- [x] Tester sauvegardes/navigation et build ; vérifier le vrai navigateur FullHD/mobile : 396 Python, 56 frontend, 27 éditeur, 26 web ; 18 + 15 contrôles navigateur, 12 captures, relecture indépendante sans finding.
- [x] Préparer une livraison isolée, vérifier le contexte de déploiement et le retour arrière avant toute mise en ligne du correctif. Archive fermée préparée, release 20261117T095037Z-1cded0 ; publication non tentée car précontrôle disque insuffisant (disk_headroom=false). Aucun service voisin nettoyé.

### Task 4: Remise et vérification

- [x] Rédiger une proposition concise pour les quatre commissions et la CAO avec sources proches des faits.
- [x] Vérifier liens, empreintes, licences et distinction testé/documenté/proposé. Références et licences vérifiées, archive produit sur liste fermée, aucune base/clé/binaire d'essai inclus.
- [x] Livrer les modifications UI et le dossier de références, en précisant leur état de publication : préparé localement, pas encore en ligne.
