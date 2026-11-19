# Coordination des chantiers — version 0.6

Rapport historique. La [version 0.7 et sa recette Lovable v2](../lovable-integration-v2/README.md) documentent l’interface actuellement publiée.

Version publiée le 15 novembre 2026 sur [travaux.kerforge.com](https://travaux.kerforge.com), release `20261115T202346Z-1b3715`. Le frontend Lovable est conservé ; le planning ouvre désormais chaque chantier.

## Parcours livrés

| Parcours | Comportement vérifié |
| --- | --- |
| Propriétés du dossier | [Quinze intitulés de la référence Notion](CHAMPS_NOTION.md), quatorze champs éditables et les vrais originaux des pièces jointes. Coût estimé/réel distincts et décimaux, Notes/Observation distinctes, Date demande/Échéance distinctes de la livraison confirmée. Titre et statut canoniques, provenance humaine et double contrôle de version. |
| Reprise des anciens mails | [Workflow Exchange](../REPRISE_ANCIENS_MAILS_2026.md) : dossiers autorisés et période inclusive, aperçu, création puis lecture par lots de cinq changements. Pause/reprise/annulation durables, transactions avant curseur, déduplication dans les deux sens avec le flux courant. Aucune annonce historique acceptée automatiquement. |
| Planning | Frappe Gantt réellement embarqué et adapté ; dates et progression modifiables, formulaire mobile/clavier. Même document Yjs et mêmes lignes que les Actions. Les dates de planning ne changent pas les faits confirmés. |
| Agendas | Plusieurs agendas Exchange EWS ou CalDAV sélectionnés avant synchronisation, import/export ICS, affectation explicite à un chantier. Annulations et versions périmées contrôlées, liens canoniques retrouvant un rendez-vous hors du mois courant. |
| Conversations | Historique privé de 30 jours, recherche SQLite FTS5/BM25 et sources exactes, contexte de dossier et rendez-vous typés. Même fil entre l’Assistant général et le chantier. Le mode local restitue des passages ; le sélecteur Mistral nécessite une configuration autorisée. |
| Notifications et Telegram | Centre de notifications, appairage privé, file chiffrée, révocation relue à l’envoi. Alertes et liens par défaut ; texte complet uniquement après autorisation de l’organisation et activation de la personne. Worker réseau distinct du worker d’import isolé. |
| Première connexion | Messagerie, choix des agendas, notifications et accès à l’espace. Parcours ignorable et reprenable ; terminer ne déclare aucun compte réellement raccordé. |

Accès directs : [Planning du portail](https://travaux.kerforge.com/#/chantiers/98d50277-8cda-49c8-8db4-3cd571fdb79b?view=planning), [Propriétés](https://travaux.kerforge.com/#/chantiers/98d50277-8cda-49c8-8db4-3cd571fdb79b?view=properties), [Agendas](https://travaux.kerforge.com/#/agenda), [Assistant](https://travaux.kerforge.com/#/assistant), [Connexions](https://travaux.kerforge.com/#/connexions).

## Vérifications

- 372 tests Python applicatifs et de déploiement passent ; 61 tests Node frontend/métier et 22 tests du module natif passent. TypeScript, builds frontend et natif, Ruff et verrou de dépendances vérifiés.
- [20 contrôles des propriétés](qa-properties/REVALIDATION.md) : montants, persistance, dates distinctes, conflit entre deux contextes et relecture obligatoire avant navigation. Six onglets et Assistant accessibles à 1920, 390 et 320 px.
- [15 contrôles du workflow historique](qa-backfill/checks.json) : vrai serveur applicatif privé en processus, lecteur Exchange fictif. Aperçu sans réseau, reprise après rechargement, compteurs observés, rejouement sans doublon et annulation après déconnexion. Ce test ne prétend pas établir une connexion EWS ou TLS réelle.
- [13 contrôles de revalidation](qa-local/REVALIDATION.md) pour le composeur mobile, la reprise de première connexion et les liens agenda hors période. Les rapports antérieurs gardent les échecs initiaux ; ces revalidations portent les résultats corrigés.
- [22 contrôles du contrat public HTTPS](public/contract.json) : version, empreintes des assets, propriétés, refus d’import privé/reprise réelle, cookie visiteur sécurisé, absence de connexion réelle et séparation avec l’ancienne base privée.
- Revue indépendante des connecteurs, du backfill, des conversations, notifications et propriétés : les P2 reproduits ont été corrigés puis revérifiés. La relecture des propriétés après conflit est imposée avant toute sauvegarde à la navigation.
- Audit des 63 dépendances Python du runtime et audit npm des dépendances de production du nouveau client : aucune vulnérabilité connue signalée à la date du contrôle. Le SDK natif conserve son [backport Zod 3 documenté](../../native-editor/patches/README.md), sans revendiquer un audit npm global à zéro alerte.

Les deux rendez-vous et six actions planifiées du corpus public sont des choix opérateur fictifs. [Preuve calendrier](public/operator-calendar.json), [preuve planning et faits préservés](public/operator-native.json). Ils ne proviennent pas des photos privées.

## Limites opérationnelles

La démonstration ne raccorde aucun compte municipal, bot Telegram, transport d’envoi de mail, identité individuelle ou modèle Mistral réel. Exchange et CalDAV disposent d’adaptateurs exécutables ; leur serveur, authentification, périmètre et droits doivent encore être qualifiés dans un espace privé. Les raccordements OAuth Google Agenda et Microsoft 365 ne sont pas implémentés dans cette version et sont indiqués comme tels dans l’interface.

La reprise Exchange inventorie les métadonnées des dossiers pour filtrer les dates ; le corps MIME n’est lu que pour les messages de la période et sous les limites configurées. La page ouverte demande les lots suivants ; revenir après fermeture permet de reprendre le dernier curseur enregistré. Le collecteur CLI historique séparé n’a pas été modifié.

Les propriétés humaines conservent leur provenance sans remplacer les faits confirmés issus des courriels. Après une actualisation conservant un brouillon concurrent, la navigation reste bloquée jusqu’au clic explicite sur Enregistrer. L’écran affiche encore plusieurs rappels de relecture dans ce cas exceptionnel ; ce point visuel mineur n’empêche ni la sauvegarde ni la conservation des données.

Le mode public permet l’édition des seules données fictives avec les permissions existantes de l’espace. La configuration de comptes et les imports réels restent interdits. Les conversations sont propres à chaque visiteur ; les dossiers fictifs, eux, restent partagés. Aucun nom, montant, demandeur ou contenu réel des huit photographies n’a été transféré dans ce corpus ou l’archive.

La recette utilise Chrome headless réel et les largeurs indiquées. Elle ne constitue ni un essai sur téléphone physique ni une certification RGAA/RGPD. Les [provenances des connecteurs](../CONNECTEURS_AGENDAS_2026.md), du [planning](../planning-2026/REUTILISATION.md) et des [conversations](../conversation-integration-2026/README.md) décrivent les SDK, versions, sources officielles et code libre effectivement réutilisés.
