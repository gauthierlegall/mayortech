# Calendriers, planning et conversations — Implementation Plan

> **For agentic workers:** use the scoped agent tasks and verify each deliverable before integration. The referenced `superpowers:subagent-driven-development` skill is not installed; native collaboration tools provide the scoped execution here.

**Goal:** Retrouver les rendez-vous, planifier les actions du chantier et poser des questions avec un historique sourcé, dans la continuité du frontend Lovable.

**Architecture:** Modules FastAPI additionnels et tables SQLite tenant/acteur, documents d’actions Yjs existants conservés. Connexions réelles uniquement dans les modes protégés, secrets chiffrés côté serveur ; démo publique sans secrets ni communication externe. Recherche SQLite FTS5/BM25 sur les sources et données structurées autorisées, puis assistant déjà existant ; aucun SQL rédigé par un modèle.

**Tech Stack:** Frappe Gantt1.2.2 MIT, BlockSuite0.22.4, exchangelib, python-caldav3.7.0, icalendar7.3.0, cryptography50.0.2, SQLite FTS5, API Telegram optionnelle.

**Spec:** Demandes utilisateur du 15 novembre 2026, frontend Lovable v0.5 puis seconde archive `mayor-project-hub (1).zip`. Référence et recette courantes : `docs/lovable-integration-v2/README.md`.

## Global Constraints

- Préserver le style Lovable DM Sans/bleu et les parcours existants.
- Les dates de planification restent distinctes des dates annoncées/confirmées dans les courriels.
- Aucune durée ni progression déduite silencieusement : champs vides = à planifier/indéterminé.
- Un seul stockage éditable des actions : le document Yjs ; sauvegardes avec contrôle de version.
- Aucun secret dans les réponses API, logs, navigateur ou archive ; aucun import privé en public_demo.
- Notifications Telegram minimales par défaut, conversation externe seulement sur activation explicite et autorisation institutionnelle.
- La première connexion peut être ignorée et reprise depuis les paramètres ; aucun faux état « connecté ».

## Review Focus

- Fuseaux horaires, journées entières et récurrences ne doivent pas dériver lors des synchronisations.
- Annulation, reprise et rejouement de synchronisation ne doivent pas dupliquer les rendez-vous.
- Le Gantt ne doit pas écraser des modifications concurrentes, récréer des actions supprimées ou modifier une date confirmée du dossier.
- Les conversations ne doivent pas révéler les données d’un autre acteur/visiteur/tenant, même avec un identifiant deviné.
- Le contenu d’un mail ou d’un document ne doit jamais devenir une instruction d’outil, un SQL ou un ordre d’envoi.

## Lots

- [x] Lire les sources officielles, vérifier les licences/versions, conserver la provenance et les parties réutilisées.
- [x] Tester puis ajouter début/fin/progression optionnels dans la commande native d’action et sa projection frontend.
- [x] Implémenter coffre de secrets, état des fournisseurs, test réel de connexion, sélection et synchronisation Exchange/CalDAV, import/export ICS et rattachement explicite au chantier.
- [x] Ajouter planning éditable avec Frappe Gantt, formulaire clavier/mobile, jalons sourcés et rendez-vous rattachés.
- [x] Implémenter conversations persistantes, recherche FTS5/BM25 et réponses avec citations exactes du périmètre courant.
- [x] Implémenter appairage Telegram, déduplication webhook/outbox, activation explicite et notifications minimales ; aucun envoi réel pendant la recette.
- [x] Ajouter première connexion et paramètres Connexions : choix fournisseur, périmètre, test, calendriers, notifications et récapitulatif ; démo locale au navigateur.
- [x] Ajouter Agenda et accès au planning dans le chantier ; la conversation est accessible depuis le popup flottant, avec route historique compatible.
- [x] Vérifier parcours réels FHD/390/320, erreurs réseau, conflit de sauvegarde, reprise de connexion et isolation des visiteurs.
- [x] Finaliser l’archive portable après la mise à jour du rapport de vérification. Revue indépendante, tests, audits, publication finale `20261115T212740Z-53de17` et recette HTTPS avec captures exécutés. Archive source et manifeste de livraison générés ; intégrité ZIP, empreinte, release embarquée et exclusions des données/secrets vérifiées.

Les identifiants et droits institutionnels restent à fournir puis à qualifier dans un espace privé. Exchange et CalDAV disposent d’adaptateurs ; Google Agenda et Microsoft 365 OAuth ne sont pas implémentés et sont affichés comme indisponibles. Aucun compte réel ni envoi Telegram/courriel n’a été utilisé pendant la recette.

## Extension métier — propriétés Notion et reprise des anciens mails

Les photos privées servent exclusivement à vérifier les intitulés et les types de propriétés. Aucun nom, dossier, montant ou texte réel photographié ne doit rejoindre les fixtures, captures de démonstration ou archives livrées.

- [x] Ajouter `project_properties.py`, table additive tenant/projet et édition avec révision attendue. Exposer le titre canonique existant et les 14 autres propriétés : Catégorie, Coût estimé, Coût réel, Date demande, Demandeur, Entreprise, Lieu, Notes, Observation, Pièces jointes, Priorité, Service / Responsable, Statut, Échéance. Les valeurs humaines restent distinctes des propositions extraites et des faits sourcés acceptés.
- [x] Ajouter `ProjectProperties.tsx` et son accès dans le chantier ; vérifier montants décimaux, dates, texte long, pièces réellement rattachées, lecture seule et conflit préservant la saisie.
- [x] Ajouter un service de reprise historique des courriels Exchange utilisant les dossiers déjà autorisés et une période explicite. Curseur durable distinct du flux courant, lots bornés, pause/reprise/annulation, dédoublonnage et originaux conservés avant avancement. Aucun ancien message ne confirme automatiquement un état du chantier.
- [x] Ajouter le parcours de préparation, démarrage et suivi des lots dans Connexions. Afficher le nombre réellement traité et la fenêtre parcourue ; ne pas inventer de pourcentage lorsque le serveur ne donne pas de total fiable.
- [x] Tester les interruptions, rejouements, changements de périmètre, ACL, autre tenant et absence de secrets en public. Vérifier les 15 propriétés et le parcours historique à 1920, 390 et 320 px avant publication.

Les modules de stockage protégés par le contrat de déploiement restent inchangés ; ces deux fonctionnalités utilisent des migrations additives à leurs propres tables.

## Ajustement demandé — chatbot flottant et nouvelle référence Lovable

- [x] Comparer le nouveau `mayor-project-hub (1).zip` à la première archive, conserver empreinte/provenance et reprendre ses choix d’UX sans importer ses données fictives comme un deuxième stockage.
- [x] Ajouter une seule bulle Assistant en bas à droite et un popup non modal disponible sur toutes les pages. Réutiliser conversations, sources et Telegram existants ; préserver fil, saisie et requête en cours après réduction. Changement de contexte explicite, historique et sources accessibles, clavier et mobile au-dessus de la navigation.
- [x] Brancher les accès Assistant du chantier et de la navigation sur ce même popup ; la route historique reste un accès compatible et les réglages de notifications.
- [x] Corriger puis reproduire le cas Gantt des actions à avancement absent : plusieurs classes CSS ne doivent pas être passées comme un seul jeton DOM. Reprendre l’UX Planning de la nouvelle archive selon les éléments réellement présents.
- [x] Tester l’affichage/publication du popup et de la frise réelle à 1920, 390 et 320 px, sans perte de données ni duplication des conversations.


## UX globale de la seconde référence — intégration vérifiée

- [x] Reprendre la navigation Messagerie / Chantiers / Actions / Planning / Suivi terrain, avec Agenda et À vérifier ; cinq raccourcis sur mobile et menu complémentaire.
- [x] Reprendre les six onglets du chantier : Page, Actions, Planning, Terrain, Documents, Échanges. Déplacer Propriétés dans une section repliable de Page avec accès depuis les métadonnées et lien historique compatible.
- [x] Réemployer la grille mensuelle CSS de Lovable dans Planning global et projet. Garder Frappe pour Déplacer et la liste mobile ; relier les trois vues aux mêmes lignes Yjs.
- [x] Ajouter les constats Terrain avec source humaine, auteur/date/statut, révisions et filtres. Créer explicitement une action native ; une reprise après erreur de liaison réutilise la même ligne.
- [x] Reprendre la messagerie à trois colonnes internes et le filtre chantier réel avant pagination ; préserver brouillons, contrôle de version et affichage mobile liste/lecture.
- [x] Grouper les filtres Actions sur mobile et vérifier souris, Entrée et Espace pendant le chargement natif. Remplacer les zéros non connus par l’état de chargement.
- [x] Préserver l’isolation d’acteur sur popup et Terrain, y compris une réponse ou un export natif tardif ; empêcher le PUT après changement d’identité.
- [x] Corriger l’aperçu Notes par projection de la seule base Actions gérée, sans modifier le document, l’export complet ou les paragraphes humains. Six tests frontend, trois tests natifs, preuve de pureté dans le vrai SDK et 15 contrôles locaux passent.
- [x] Vérifier les 15 contrôles Notes sur la publication finale et conserver les captures aux trois largeurs : aucun PUT/PATCH, notes et faits inchangés, frise et Frappe affichent chacun les trois barres.

État final : v0.7.0 publiée, release `20261115T212740Z-53de17`. Application et worker sains ; contrat HTTPS 27/27 et finition Notes HTTPS 15/15 validés après publication. Les 65 contrôles Planning, 19 du popup et 34 transversaux ont été exécutés sur la release initiale `20261115T211012Z-707e4a`. Les preuves et limites de qualification sont regroupées dans `docs/lovable-integration-v2/README.md`.
