# Connexion mail et cohérence de la planification — Implementation Plan

> **For agentic workers:** native collaboration is already active. The parent owns mail UX and publication; a scoped agent owns the planning dialog; independent review and browser checks follow. No Git checkout is configured.

**Goal:** Guider le raccordement d’une messagerie sans états de connexion inventés, et corriger les incohérences du formulaire de planification signalées par l’utilisateur.

**Architecture:** Le nouveau parcours utilise les contrats Exchange existants : création, test, sélection puis collecte explicite, avec leurs révisions. Une démonstration signalée fonctionne uniquement en mémoire et n’appelle aucun endpoint de mutation. Les actions restent dans leur document Yjs canonique ; les dates de planning ne deviennent pas des faits confirmés.

**Tech Stack:** React/TypeScript, composants et tokens Lovable existants, FastAPI/Exchange EWS existants, tests Node et Python Playwright.

**Spec:** Demandes utilisateur du 16 novembre 2026, DESIGN.md et contrats de `connection_hub.py`. Quatre étapes mail : Messagerie, Compte, Accès, Terminer. Le test est intégré à Compte ; le premier import est explicite dans Terminer. La reprise historique reste facultative.

## Global Constraints

- Conserver DM Sans, les couleurs et les composants Lovable. Mise en page utilisable à 1920, 390 et 320 px, sans nouveau dialogue plein écran imposé.
- Exchange EWS est la seule messagerie raccordable actuellement. Ne pas annoncer Gmail, IMAP ou OAuth Microsoft 365 comme disponibles.
- Aucun identifiant réel demandé en public ; aucun mot de passe dans URL, stockage navigateur, journal ou rapport.
- Création n’est pas vérification ; vérification n’est pas import. Ne jamais déduire un état depuis une étape parcourue.
- Préserver les calendriers déjà sélectionnés et employer la révision effectivement retournée par chaque mutation.
- Pas de rejeu automatique d’une création ou collecte après une réponse ambiguë. Échec de test : reprendre le profil créé, sans nouveau compte silencieux.
- Planification : champs vides conservés, responsables humains conservés, statut et pourcentage indépendants, contrôle de concurrence existant maintenu.

## Review Focus

1. Démonstration publique et acteur sans droits : aucune saisie de secret ni mutation réelle ; fin de parcours explicitement fictive.
2. Test réseau ou conflit : sélection/saisie conservée ; aucun succès prématuré ni création répétée au simple réessai.
3. Changement d’identité ou démontage pendant une requête : pas de seconde opération ni réponse appliquée au nouvel acteur.
4. Sélections mail modifiées : impossibilité d’importer l’ancienne sélection sans avertissement ; calendriers inchangés.
5. Planification sans dates, responsables hors membres et retrait de frise : pas de valeurs inventées ni champs ignorés.

## Lots

- [x] Auditer le contrat réel, les capacités des fournisseurs, le formulaire et la référence visuelle ; reproduire les problèmes de planification.
- [x] Écrire les tests de régression du modèle de raccordement avant son implémentation : ordre création/test/sélection, calendrier conservé, reprise, mode démo, conflit et import partiel.
- [x] Ajouter `mail-connection-model.mjs` et `MailConnectionWizard.tsx` : quatre étapes, aide serveur progressive, état de test réel, permissions, sélection et récapitulatif. Raccorder Connexions, première connexion et Messagerie ; conserver le gestionnaire d’agendas et la reprise historique.
- [x] Corriger `PlanningActionDialog.tsx` et ses raccordements : choix initial explicite, chantier identifiable, responsable libre suggéré, dates facultatives, retrait préparé puis une sauvegarde explicite de tous les champs.
- [x] Vérifier les parcours privés avec vraie API et lecteur Exchange fictif, et la démonstration publique sans mutation ; souris/clavier, erreurs et trois largeurs. Revue indépendante puis suites complètes, TypeScript, builds et contrôles adaptés.
- [x] Publier la mise à jour du produit existant, revérifier HTTPS et les empreintes servies, documenter preuves/limites. Release `20261116T094932Z-306a53` vérifiée : mail26, planning28, contrat27.
- [x] Régénérer et vérifier l’archive portable des sources et preuves : intégrité ZIP, empreinte, release embarquée et exclusions des données/secrets vérifiées.
