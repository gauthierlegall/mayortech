# Développer MayorTech pour les commissions de Plougastel-Daoulas

**Objectif.** Étendre l’espace Travaux aux quatre commissions permanentes avec des dossiers, des tâches et des documents communs, puis adapter la première vue au travail de chaque équipe.

**Architecture.** Une organisation contient plusieurs commissions. Un dossier et ses actions ont une commission principale. Une transmission à une autre commission donne accès aux éléments sélectionnés et à leur version, avec un lien vers le dossier d’origine pour les personnes habilitées.

**Socle technique.** React et TypeScript, FastAPI et SQLite, Keycloak pour les comptes, contrôle d’accès côté serveur, actions collaboratives Yjs. FullCalendar pour les agendas et Frappe Gantt pour les opérations à dépendances.

**Périmètre.** Ce document fixe le parcours et les critères de recette. Il s’appuie sur le [recensement précédent](2026-11-17-commissions-plougastel.md) et l’état du code au 18 novembre 2026.

## Le premier parcours à livrer

Dans **Mairie Test**, une personne rejoint l’organisation, ouvre **Culture, sport et vie associative**, prépare une fête associative et assigne les tâches. Elle demande un créneau, joint un devis fictif et transmet un budget à **Fonctions supports et transitions**. Cette commission demande un complément ou rend un avis sur la version examinée. L’équipe d’origine voit la réponse dans son dossier et peut ensuite y rattacher une référence de décision officielle et les tâches de suivi.

Ce passage reprend le circuit décrit par la commune. Les commissions 2, 3 et 4 évaluent leurs propositions chiffrées, puis la commission 1 examine leur faisabilité financière et organise, selon le dossier, la suite du processus. [Commissions officielles](https://ville-plougastel.bzh/ma-ville/le-conseil-municipal/commissions/), [PV du 4 avril 2026, p. 7 à 11](https://ville-plougastel.bzh/wp-content/uploads/2026/05/PV_CM04AVRIL.pdf#page=7)

## Fonctions et vues par commission

| Commission | Vue d’ouverture | Fonctions métier | Premier cas à tester |
| --- | --- | --- | --- |
| **1. Fonctions supports et transitions** | File d’arbitrage et tableau chiffré par exercice | Comparer variantes, estimation, financements et reste à charge. Attribuer une demande, demander une pièce, rendre un avis motivé sur une version. Suivre les dates des campagnes budgétaires, demandes de subvention et actions de transition. | Comparer deux scénarios de coût pour une manifestation et renvoyer une question à la commission d’origine. |
| **2. Action sociale, enfance et jeunesse** | Actions par service et calendrier des campagnes | Modèles rentrée scolaire, action jeunesse et programme aînés. Checklist par site ou partenaire, reconduction d’une campagne avec responsables et dates, suivi des conventions et indicateurs agrégés. Démarches et dossiers individuels dans les outils métier habilités. | Préparer la rentrée de deux écoles, assigner les vérifications et générer les échéances de l’année suivante. |
| **3. Urbanisme, travaux et ports** | Travaux existants, file Urbanisme, carte des ouvrages et interventions | Urbanisme avec référence externe, parcelle, pièces à recueillir, avis et prochaine action. Ports avec fiche d’ouvrage, constats, photos, visites périodiques et interventions. Gantt disponible dans les opérations dont les phases dépendent les unes des autres. | Ouvrir un dossier depuis la carte et planifier la prochaine visite d’un ouvrage. |
| **4. Culture, sport et vie associative** | Calendrier des événements et liste des demandes | Fiche événement, demandes de salle et de matériel, disponibilités connues, pièces et conventions. Campagne de subventions avec pièces manquantes, instruction et décision renseignée. | Préparer une fête avec l’association, détecter un créneau occupé et transmettre le budget. |

La mairie propose déjà des démarches associatives pour les salles, le matériel et les subventions. Retenir les références de ces demandes et confirmer avec les services quelle source fait foi pour les créneaux avant de proposer une confirmation dans MayorTech. Pour l’urbanisme, fournir un accès à la parcelle et à la source réglementaire de référence. [Démarches associatives](https://ville-plougastel.bzh/activites-et-loisirs/vie-associative/demarches/), [Géoportail de l’urbanisme](https://www.geoportail-urbanisme.gouv.fr/)

Pour les autres sujets de la commission 1, partir du même suivi de dossiers. Une action de sobriété peut suivre des sites, des relevés agrégés et une échéance. Une action économie locale peut suivre une convention et ses engagements. Les services population, RH et sécurité peuvent suivre leurs projets collectifs par jalons et tâches. [Missions de la commission 1, PV du 4 avril 2026](https://ville-plougastel.bzh/wp-content/uploads/2026/05/PV_CM04AVRIL.pdf#page=7)

## Socle à reprendre et travail à prévoir

- **Dossiers et tâches.** Garder la fiche Travaux, ses documents, notes, courriels rattachés, récapitulatif et historique. Dans chaque commission, **Dossiers**, **Mes actions** et la vue métier utilisent les mêmes actions. La liste, le tableau et l’agenda changent la présentation. Le backend de checklists, commentaires, affectations et récurrences existe dans `src/travaux/action_collaboration.py`. Raccorder `Actions.tsx` et `ProjectDetail.tsx` à ces fonctions et proposer les responsables habilités sur le dossier choisi.
- **Admission et accès.** Distinguer l’adhésion à l’organisation de l’accès à une commission. L’admission automatique concerne Mairie Test. Pour une organisation réelle, une personne habilitée traite la demande puis attribue les accès. Ajouter le rôle effectif par commission ou dossier au rôle d’organisation existant. Tester les droits de lecture et d’écriture séparément avant d’ouvrir un périmètre additionnel.
- **Transmission chiffrée.** Une transmission conserve l’identifiant du dossier et la version du budget et des pièces partagées. La commission destinataire voit la référence, le résumé, les montants et les pièces sélectionnées. Toute pièce ajoutée au dossier après envoi exige une nouvelle transmission pour devenir visible. Un avis comporte un auteur, une date et la version examinée. La décision officielle a sa propre référence.
- **Agenda et messagerie.** FullCalendar et l’import `.ics` sont disponibles. Le raccordement Outlook développé pour le courrier et la lecture d’événements sont deux connexions distinctes. Prévoir pour Outlook un consentement délégué séparé, une sélection de calendriers, une plage d’import et le minimum de champs nécessaires. Tester `Calendars.ReadBasic` pour une lecture de calendrier simple, ses séries et exceptions, après autorisation sur le compte. Le pilote interne utilise l’agenda et des événements fictifs. [Microsoft Graph, lecture de calendarView](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0)
- **Recherche et assistant.** Appliquer les habilitations aux listes, compteurs, résultats, pièces, événements, notifications et exports, puis au contexte transmis à GLM. L’extraction documentaire Mistral Large 4 alimente des champs proposés et sourcés selon les accès du dossier. Une personne autorisée confirme les écritures et les transmissions. Revérifier son accès lors de l’application de la proposition.

## Réemploi de logiciels libres

| Brique | Code ou interface repérés | Choix pour MayorTech |
| --- | --- | --- |
| **FullCalendar et Frappe Gantt** | FullCalendar est déjà dans `Agenda.tsx`. Frappe Gantt est déjà une dépendance du frontend. | Partager l’agenda entre les modules. Ajouter un filtre par lieu, ressource ou équipe. Garder le Gantt dans les dossiers qui ont des dépendances. [FullCalendar](https://github.com/fullcalendar/fullcalendar), [Frappe Gantt](https://github.com/frappe/gantt) |
| **Kanboard**, MIT | `SubtaskModel.php`, `TaskRecurrenceModel.php` et le déclenchement sur événements. | Reprendre les cas d’usage de sous-tâches, date de référence et distinction entre échéance fixe et récurrence après clôture. Les actions natives et leur API restent la base. [Licence](https://github.com/kanboard/kanboard/blob/2ddb31bf72d355727d0639fc3423630f3bae1a9c/LICENSE), [Sous-tâches](https://github.com/kanboard/kanboard/blob/2ddb31bf72d355727d0639fc3423630f3bae1a9c/app/Model/SubtaskModel.php), [Récurrence](https://github.com/kanboard/kanboard/blob/2ddb31bf72d355727d0639fc3423630f3bae1a9c/app/Model/TaskRecurrenceModel.php) |
| **MapLibre GL JS**, BSD-3-Clause | `addSource`, `addLayer` et `queryRenderedFeatures` affichent et sélectionnent les objets géographiques. | Intégrer directement la bibliothèque côté React. Afficher les marqueurs des dossiers autorisés avec un fond de carte identifié et attribué. Prévoir la même navigation en liste. [Licence et notices](https://github.com/maplibre/maplibre-gl-js/blob/861a52a6ba19017697d2532c602934cfd19f4de9/LICENSE.txt), [Exemple GeoJSON](https://maplibre.org/maplibre-gl-js/docs/examples/add-a-geojson-polygon/) |
| **MRBS**, GPLv2 | `mrbsCheckFree`, `mrbsCheckPolicy` et `RepeatRule.php` isolent les cas de chevauchement, de politique de salle et de répétition. | Prendre ces comportements comme référence pour les tests et écrire les règles en FastAPI. Le code PHP inspecté utilise le stockage MRBS. L’intégration à un outil de réservation existant dépend de son interface d’échange vérifiée. [Licence](https://github.com/meeting-room-booking-system/mrbs-code/blob/383c98214deed41ee05ce2cd3e7a57c3f72a0af0/LICENSE), [Contrôles](https://github.com/meeting-room-booking-system/mrbs-code/blob/383c98214deed41ee05ce2cd3e7a57c3f72a0af0/web/mrbs_sql.inc), [Récurrence](https://github.com/meeting-room-booking-system/mrbs-code/blob/383c98214deed41ee05ce2cd3e7a57c3f72a0af0/web/lib/MRBS/RepeatRule.php) |
| **Grist Core**, Apache-2.0 | L’API des tables permet de lire et de modifier des lignes. | Commencer par un tableau MayorTech et un export CSV. Si un service utilise déjà Grist, étudier une lecture cadrée par document et importer une version identifiable. Le service fixe la source de référence des chiffres. [Licence](https://github.com/gristlabs/grist-core/blob/a10b7227365adfe2555be40ae87bb9741284c0ca/LICENSE.txt), [API](https://support.getgrist.com/api/) |
| **FixMyStreet / Open311**, AGPL-3.0-or-later pour FixMyStreet | L’adaptateur Open311 conserve la référence d’un signalement dans le système destinataire. | Prévoir un connecteur si un service compatible existe et que le service terrain a besoin de ce flux. [Licence](https://github.com/mysociety/fixmystreet/blob/691e1b8cc8476e97ebffb44b1f8eb2aeff63155c/LICENSE.txt), [Adaptateur Open311](https://github.com/mysociety/fixmystreet/blob/691e1b8cc8476e97ebffb44b1f8eb2aeff63155c/perllib/FixMyStreet/SendReport/Open311.pm) |
| **webdelib** | Libriciel documente la préparation, le traitement et la transmission d’actes. | Commencer l’échange avec l’outil d’actes par un dossier et une référence de séance. Chiffrer un connecteur après confirmation de l’outil, du contrat d’interface et de la licence de la version. [Documentation webdelib](https://www.libriciel.fr/logiciels/webdelib/) |

Les dépendances ou extraits retenus à l’implémentation seront identifiés par version et accompagnés de leurs notices dans le [registre de réutilisation](../../REUTILISATION_CODE.md). Cette étude vérifie des sources et interfaces. Les essais d’intégration font partie des lots ci-dessous.

## Ordre de réalisation

### Lot 1 · Accès par commission et tâches communes

- [ ] Créer les quatre commissions dans Mairie Test. Rattacher les chantiers existants à la commission 3 en gardant leurs identifiants, historiques et accès actuels. Vérifier la migration sur une copie et la rejouer pour confirmer son idempotence.
- [ ] Étendre `src/travaux/project_access.py` et le parcours d’adhésion. Appliquer le périmètre au serveur avant calcul des compteurs, accès aux pièces et recherche. Garder les exceptions d’accès explicites et traçables.
- [ ] Ajouter le sélecteur de commission et « Mes actions ». Raccorder la collaboration aux écrans existants, avec choix de responsable filtré selon le dossier. Invalider le cache et les réponses en vol au changement de commission.
- [ ] **Recette.** Une personne éditrice en Culture et lectrice en Finances peut modifier ses actions en Culture et consulter ses dossiers autorisés en Finances. Toute écriture hors périmètre est refusée. La révocation masque immédiatement titres, pièces, agenda, citations et notifications, y compris via un ancien lien ou une réponse déjà en préparation. Les écrans Travaux existants passent leur recette.

### Lot 2 · Culture et arbitrage financier

- [ ] Ajouter les modèles « Événement associatif » et « Demande de financement », avec checklist et dates. Rendre visible la différence entre créneau demandé et confirmé. Pour les ressources gérées dans le pilote, vérifier le chevauchement dans la transaction de confirmation. Une disponibilité externe inconnue laisse la demande en attente de vérification.
- [ ] Ajouter la transmission de la version chiffrée et une file d’arbitrage. Prévoir le retour pour complément, le dépôt d’une nouvelle version et l’avis motivé. Rattacher ensuite une référence de décision et une action au dossier d’origine.
- [ ] **Recette.** Jouer le parcours de la fête jusqu’à la suite de l’avis. Deux confirmations concurrentes sur un même créneau aboutissent à une seule réservation. La commission 1 voit seulement les éléments transmis. Une correction du budget après examen conserve la version sur laquelle l’avis a été rendu. Vérifier sur navigateur en 1920 × 1080 et sur mobile, sans compte mail réel.

### Lot 3 · Urbanisme et ports

- [ ] Ajouter les modèles « Dossier d’urbanisme » et « Entretien d’ouvrage ». Mener un essai MapLibre avec parcelles et ouvrages fictifs, puis choisir les fonds, les données et la gestion des mises à jour avec le service.
- [ ] **Recette.** Ouvrir le même dossier depuis la carte ou la file, consulter sa référence externe et planifier un contrôle périodique. Quand le fond de carte est indisponible, la liste conserve les liens et toutes les actions. Les localisations suivent les droits des dossiers.

### Lot 4 · Actions sociales collectives, enfance et jeunesse

- [ ] Créer les modèles de campagne et réutiliser les checklists par site. Choisir un calcul de récurrence, permettre la validation des nouvelles dates et gérer les exceptions. Les démonstrations utilisent seulement des indicateurs agrégés et des données fictives.
- [ ] **Recette.** Reconduire une rentrée tout en gardant l’historique. Un second lancement sur la même période retrouve les occurrences existantes. L’équipe voit les actions à venir et peut corriger une date ou un responsable pour un site.

### Lot 5 · Séances et instances spécialisées

- [ ] Ajouter un ordre du jour, des dossiers et des pièces associés, puis une version figée des éléments examinés, un avis relu et des actions issues de la séance. Pour les actes, conserver la référence et le lien du système officiel.
- [ ] Envisager la **CAO** en premier avec références Mégalis et préparation de séance, puis la **CCSPL** avec rapports de service et suites à donner, et la **CCID** avec échéances et points de séance sans données fiscales individuelles dans ce lot. Prévoir des accès distincts avant de traiter des dossiers réservés.
- [ ] **Recette.** Modifier un dossier après clôture et vérifier que la version examinée reste consultable par les personnes habilitées. Une commission ordinaire ne découvre aucun élément réservé à une instance spécialisée. [Marchés publics et Mégalis](https://ville-plougastel.bzh/ma-ville/les-marches-publics/), [CCSPL, PV du 7 mai 2026](https://ville-plougastel.bzh/wp-content/uploads/2026/07/01A_PVdu07mai2026.pdf#page=49), [CCID, PV du 25 juin 2026](https://ville-plougastel.bzh/wp-content/uploads/2026/10/PV_CM_25.6.2026.pdf#page=6)

## Points d’entrée pour l’implémentation

| Zone | Fichiers existants à reprendre | Tests de départ |
| --- | --- | --- |
| Adhésion et droits | `src/travaux/account_onboarding.py`, `src/travaux/identity_routes.py`, `src/travaux/project_access.py` | `tests/test_organization_codes.py`, `tests/test_project_access.py` |
| Collaboration et interface | `src/travaux/action_collaboration.py`, `frontend-lovable/src/features/workspace/Actions.tsx`, `ProjectDetail.tsx`, `context.tsx`, `data.ts` et `native-actions.ts` dans le même dossier frontend | `tests/test_action_collaboration.py` et recette navigateur |
| Agenda, recherche et assistant | `src/travaux/calendars.py`, `src/travaux/mailbox.py`, `src/travaux/retrieval.py`, `src/travaux/conversations.py`, `src/travaux/assistant_changes.py`, `frontend-lovable/src/features/workspace/Agenda.tsx` | `tests/test_calendars.py`, `tests/test_calendar_retrieval.py`, `tests/test_assistant_changes_review.py` |

Après les lots 1 et 2, le pilote doit démontrer le parcours complet et les accès avant de généraliser les autres vues. Les informations RH individuelles, les dossiers des familles et les offres confidentielles restent dans leurs outils métier pendant ce pilote.
