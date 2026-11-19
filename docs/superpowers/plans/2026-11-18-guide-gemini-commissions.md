# Guide d’implémentation pour Gemini 3.8 Flash · MayorTech et les commissions

**Mission.** Étends l’application MayorTech existante aux quatre commissions permanentes de Plougastel-Daoulas. Livre d’abord un parcours complet Culture → Finances dans Mairie Test. Ensuite, ajoute les vues Urbanisme et Ports, les campagnes Enfance et Jeunesse, puis les séances. Ce guide s’adresse à l’agent qui modifiera le code.

**Point d’entrée.** Ouvre le dossier `outputs/travaux-mairie/`. Tous les chemins de code ci-dessous partent de ce dossier. Si tu reçois seulement ce Markdown, fais l’inventaire des fichiers nécessaires avec les chemins indiqués et identifie les éléments auxquels tu as réellement accès. Le [plan métier](2026-11-18-deploiement-commissions-plougastel.md), l’[architecture](../../architecture.md) et le [registre de réutilisation](../../REUTILISATION_CODE.md) complètent le contexte.

**Livraison attendue.** Pour chaque lot ou correctif applicatif validé, mène la livraison jusqu’à la production et vérifie la version sur les URLs en service. Enchaîne migration et tests locaux, build, publication et recette HTTPS selon la [procédure de production](#14-publication-en-production). Consigne la release active et les preuves avant de passer au lot suivant. Indique quels parcours ont utilisé un fournisseur simulé.

## 1. Décisions à appliquer

1. **Un espace par organisation.** Ajoute des commissions au tenant existant. Chaque dossier a une commission principale. Une même personne peut éditer en Culture et seulement lire en Finances. Les accès sont calculés côté serveur avec l’identité active et les habilitations existantes.
2. **Un même dossier dans toutes les vues.** Garde les identifiants, documents, notes, sources, historique et actions collaboratives de Travaux. Utilise les modèles de dossier pour adapter les champs et les vues. Le récapitulatif reste dans la fiche du dossier. Mets la liste, le tableau ou l’agenda en avant selon la commission. Le Gantt est réservé aux opérations à dépendances.
3. **Une fiche chiffrée partagée entre commissions.** Transmets une vue figée du budget et des pièces sélectionnées, reliée au dossier d’origine. Finances examine cette version et renvoie ses questions ou son avis. Un avis, une décision officielle renseignée et une action de suivi ont chacun leur propre trace.
4. **Une UX commune.** Fais évoluer le frontend React existant avec ses composants, sa typographie DM Sans et ses repères de navigation. Conserve le chat en popup et l’accès à la messagerie depuis les dossiers. Utilise une action principale par écran et des statuts qui changent l’action à entreprendre.
5. **Un environnement de recette fictif.** Utilise Mairie Test et une seconde organisation fictive pour vérifier l’isolation. L’admission automatique par code est réservée à Mairie Test. Dans un espace réel, la demande d’adhésion doit être traitée par une personne habilitée, puis les accès attribués explicitement. Les essais utilisent des adresses `example.invalid`, des documents générés et des fournisseurs simulés. La publication de l’application conserve le profil des espaces en service. Le raccordement de comptes municipaux suit son propre périmètre d’autorisation.
6. **Les modèles de MayorTech restent ceux du projet.** Le pipeline utilise Mistral Large 4 pour l’extraction documentaire et GLM pour le chat/RAG, selon les adaptateurs et paramètres du serveur. Le corpus du chat respecte les droits actuels. Un changement proposé est sourcé et confirmé par la personne, avec contrôle d’accès au moment de l’application. Les contrats fournisseurs sont déjà vérifiés avec des transports simulés. [Recette de l’espace privé](../../MISE_EN_SERVICE_PRIVEE_2026.md)

Plougastel-Daoulas compte quatre commissions permanentes. Les commissions 2, 3 et 4 chiffrent leurs propositions puis les présentent à la commission 1 pour examen financier. L’avis de faisabilité reste distinct de la suite devant le conseil municipal. [Liste officielle](https://ville-plougastel.bzh/ma-ville/le-conseil-municipal/commissions/), [PV de création et missions, 4 avril 2026](https://ville-plougastel.bzh/wp-content/uploads/2026/05/PV_CM04AVRIL.pdf#page=7)

## 2. Inventaire du code avant toute modification

| Zone | Fichiers à ouvrir | À vérifier avant de modifier |
| --- | --- | --- |
| Persistance | `src/travaux/repository.py`, `src/travaux/project_creation.py`, `src/travaux/project_properties.py` | Schéma des dossiers, tenant dans la clé, migrations existantes, usage de `repo._transaction()`, révisions et valeurs héritées. |
| Identité et droits | `src/travaux/project_access.py`, `src/travaux/identity.py`, `src/travaux/identity_routes.py`, `src/travaux/account_onboarding.py`, `src/travaux/api.py` | Rôle organisation, membre actif, `project_grants`, rôle effectif et contrôle dans les routes. Vérifie le comportement des sources liées à plusieurs dossiers. |
| Tâches | `src/travaux/action_collaboration.py`, `web/api.js`, `frontend-lovable/src/features/workspace/native-actions.ts`, `Actions.tsx`, `ProjectDetail.tsx`, `PlanningActionDialog.tsx` | Action canonique Yjs, projections, identifiants dossier/page/action, version requise pour les écritures, affectation par compte. |
| Navigation et accès | `frontend-lovable/AGENTS.md`, `frontend-lovable/src/features/workspace/Shell.tsx`, `context.tsx`, `data.ts`, `Projects.tsx`, `ProjectAccessManager.tsx`, `MemberAccessManager.tsx`, `OrganizationJoin.tsx`, `OrganizationRequests.tsx` | Entrée active dans `vite.product.ts`, composants réutilisables, clés de cache et état des chargements. Respecte les fichiers générés et les limites Lovable décrites dans `AGENTS.md`. |
| Planning, agenda et terrain | `frontend-lovable/src/features/workspace/Agenda.tsx`, `Planning.tsx`, `GlobalPlanning.tsx`, `PlanningTimeline.tsx`, `Terrain.tsx`, `src/travaux/calendars.py`, `src/travaux/field_reports.py` | Calendrier existant, calendriers importés, filtres, liens vers les dossiers, dates confirmées et suivi terrain. |
| Pièces et partage | `src/travaux/mailbox.py`, `src/travaux/governance.py`, `src/travaux/notifications.py`, `frontend-lovable/src/features/workspace/DocumentsPanel.tsx`, `SourcePreview.tsx` | Accès aux originaux, documents versionnés, liens directs, journal et notifications. |
| Recherche et IA | `src/travaux/retrieval.py`, `src/travaux/calendar_retrieval.py`, `src/travaux/conversations.py`, `src/travaux/assistant_changes.py`, `frontend-lovable/src/features/workspace/AssistantWidget.tsx`, `AssistantChangeCard.tsx` | Filtrage en amont des données, citations, conversation persistée et application d’une proposition. |

Ces fichiers sont les points de départ vérifiés dans le projet. Lorsque ton checkout contient une version plus récente, recherche les points d’entrée actuels avant d’ajouter un service ou une route. Le backend de collaboration existe déjà. Les champs natifs et l’interface doivent converger vers ce backend sans créer une deuxième action.

## 3. Outils à intégrer ou à étudier

Les versions et commits liés servent de repères d’audit. Pour une nouvelle dépendance, vérifie la version sélectionnée, sa licence, le verrou de dépendances, sa compatibilité avec le build et son fonctionnement au navigateur. Inscris dans `docs/REUTILISATION_CODE.md` la provenance exacte des fichiers et notices effectivement intégrés.

| Outil | Décision | Code ou interface à ouvrir | Preuve attendue |
| --- | --- | --- | --- |
| **FullCalendar 6.1.21** | **Réutiliser maintenant.** Garde `core`, `react`, `daygrid`, `timegrid`, `list` déjà installés. Ajoute les filtres lieu, ressource et équipe à partir des données autorisées. | `Agenda.tsx`, `frontend-lovable/package.json`. Utilise une vue liste ou grille et des filtres pour les ressources. Les plugins Scheduler ont une licence distincte. [FullCalendar](https://github.com/fullcalendar/fullcalendar), [Plugins Premium](https://fullcalendar.io/docs/premium) | Un événement autorisé s’ouvre sur le dossier canonique, dans l’agenda et dans sa fiche. Il apparaît une fois, avec une heure cohérente en `Europe/Paris`. |
| **Frappe Gantt 1.2.2** | **Réutiliser dans Travaux.** Garde les dépendances du planning existant. Propose cette vue aux dossiers qui portent un planning à dépendances. | `PlanningTimeline.tsx`, `Planning.tsx`, `GlobalPlanning.tsx` et moteur adapté dans `frontend-lovable/src/vendor/frappe-gantt/`. Teste les dates des actions, les libellés et les avancements non renseignés. [Frappe Gantt](https://github.com/frappe/gantt) | Les dates et dépendances des chantiers existants restent correctes. Les entrées Culture, Finances et Enfance ouvrent sur leur vue métier. |
| **Kanboard**, MIT | **Relire deux fichiers, puis raccorder l’existant.** Vérifie les sous-tâches et la distinction entre échéance fixe et relative à la clôture. | [SubtaskModel.php](https://github.com/kanboard/kanboard/blob/2ddb31bf72d355727d0639fc3423630f3bae1a9c/app/Model/SubtaskModel.php), [TaskRecurrenceModel.php](https://github.com/kanboard/kanboard/blob/2ddb31bf72d355727d0639fc3423630f3bae1a9c/app/Model/TaskRecurrenceModel.php), [Licence](https://github.com/kanboard/kanboard/blob/2ddb31bf72d355727d0639fc3423630f3bae1a9c/LICENSE). Réutilise `action_collaboration.py` pour ces fonctions. | Une affectation, une case cochée ou une occurrence confirmée se retrouve dans toutes les vues, avec le même identifiant d’action. |
| **MRBS 1.13.0**, GPLv2 | **Étudier comme référence de comportement.** Écris les règles de réservation dans FastAPI avec la base actuelle. Garde MRBS hors des dépendances du pilote. | [Recherche de créneau et règles](https://github.com/meeting-room-booking-system/mrbs-code/blob/383c98214deed41ee05ce2cd3e7a57c3f72a0af0/web/mrbs_sql.inc) (`mrbsCheckFree`, `mrbsCheckPolicy`), [RepeatRule.php](https://github.com/meeting-room-booking-system/mrbs-code/blob/383c98214deed41ee05ce2cd3e7a57c3f72a0af0/web/lib/MRBS/RepeatRule.php), [Licence](https://github.com/meeting-room-booking-system/mrbs-code/blob/383c98214deed41ee05ce2cd3e7a57c3f72a0af0/LICENSE). Le `README.sqlapi` décrit son abstraction SQL interne. | Chevauchement refusé, créneaux adjacents acceptés, annulation libérant le créneau, réessai sans doublon. Le contrôle tient aussi pour deux requêtes concurrentes. |
| **MapLibre GL JS**, BSD-3-Clause | **Intégrer directement au lot 3.** Ajoute `maplibre-gl` épinglé au frontend. Charge la vue carte à la demande et garde un mode liste au clavier. Utilise des fixtures locales pour le premier rendu. | `addSource`, `addLayer`, `queryRenderedFeatures`. Affiche du GeoJSON déjà filtré côté serveur. Les fonds de carte et leurs attributions ont leur propre choix de source. [Exemple GeoJSON](https://maplibre.org/maplibre-gl-js/docs/examples/add-a-geojson-polygon/), [Licence et notices du commit audité](https://github.com/maplibre/maplibre-gl-js/blob/861a52a6ba19017697d2532c602934cfd19f4de9/LICENSE.txt) | La sélection ouvre le même dossier depuis la liste et la carte. Les données d’une autre commission restent exclues de la réponse serveur. La liste reste utilisable quand la carte échoue. |
| **Grist Core**, Apache-2.0 | **Raccordement conditionnel.** Livre le tableau chiffré natif au lot 2. Propose un export CSV, puis un import en lecture de lignes versionnées si le service confirme qu’il utilise Grist. | [DocApi.ts au commit audité](https://github.com/gristlabs/grist-core/blob/a10b7227365adfe2555be40ae87bb9741284c0ca/app/server/lib/DocApi.ts), [API REST](https://support.getgrist.com/api/), [Règles d’accès](https://support.getgrist.com/access-rules/), [Licence](https://github.com/gristlabs/grist-core/blob/a10b7227365adfe2555be40ae87bb9741284c0ca/LICENSE.txt). | Une version reçue est datée, dédoublonnée et reliée à son origine. Elle conserve ses propres habilitations et laisse intact l’avis précédent. |
| **FixMyStreet / Open311** | **Raccordement conditionnel après le lot 3.** Garde `Terrain.tsx` pour les constats internes. Relis l’adaptateur si un canal de signalement compatible est identifié. | [Adaptateur Open311](https://github.com/mysociety/fixmystreet/blob/691e1b8cc8476e97ebffb44b1f8eb2aeff63155c/perllib/FixMyStreet/SendReport/Open311.pm), [Licence AGPL-3.0-or-later](https://github.com/mysociety/fixmystreet/blob/691e1b8cc8476e97ebffb44b1f8eb2aeff63155c/LICENSE.txt). | Un identifiant externe stable évite le double import et l’affichage public de constats internes. |
| **Decidim Meetings**, **webdelib**, **Mégalis** | **Revoir au lot 5.** Lis la clôture d’une séance dans Decidim pour les liens et les suites. Commence côté MayorTech par un dossier préparatoire et des références officielles. Identifie l’outil d’actes et son interface avec l’équipe avant d’ajouter un connecteur. | [CloseMeeting de Decidim](https://github.com/decidim/decidim/blob/6b835ff5f460c7fa34e177d5adfea4fb45067ce1/decidim-meetings/app/commands/decidim/meetings/admin/close_meeting.rb), [webdelib](https://www.libriciel.fr/logiciels/webdelib/), [Marchés publics de Plougastel et Mégalis](https://ville-plougastel.bzh/ma-ville/les-marches-publics/). | Une séance peut être relue à la version examinée. Le lien vers l’acte d’origine reste stable et visible pour les personnes habilitées. |

Le périmètre impose les actions et les identités MayorTech. Garde OpenProject, Vikunja, Nextcloud Deck et PLANKA comme références de comparaison. Consulte OpenProject pour le passage d’un courriel à un élément de projet si tu travailles sur le classement, puis vérifie la chaîne EML existante de MayorTech. Les expériences historiques sont dans `../commissions-oss-2026-11-17/` depuis la racine projet, notamment `notes/kanban.md` et `notes/commissions-reunions.md`. [Courriels entrants d’OpenProject](https://www.openproject.org/docs/installation-and-operations/configuration/incoming-emails/)

Pour les révisions de code, les repères audités sont Kanboard `1.2.57`, MapLibre GL JS `6.19.0`, Grist Core `1.7.22`, FixMyStreet `6.0` et Decidim `0.32.2`. Pour webdelib, version, licence du code concerné et contrat d’interface restent à confirmer auprès du service. Le code retenu doit être exécuté depuis un vrai parcours du produit avec un test ciblé.

## 4. Lot 1 · Habilitations par commission et tâches communes

### 4.1 Modèle et migration

- Ajoute un modèle de commission rattaché à `tenant_id`, avec identifiant stable, libellé, ordre et état d’activation. Prépare les quatre commissions de Plougastel-Daoulas comme modèle d’organisation configurable. Place les spécialisations Travaux, Urbanisme et Ports sous la commission 3.
- Associe les membres actifs à une commission et à un rôle de contenu. Utilise des clés uniques tenant/commission/membre et des références tenant/objet. Calcule les droits effectifs au serveur et renvoie les capacités utiles à l’interface, par exemple `can_edit` et `can_submit_for_review`.
- Rattache les dossiers existants au périmètre Travaux par organisation. Conserve les identifiants de dossiers et de pages, les liens de sources, documents, actions, grants explicites et historiques. Limite le backfill à l’organisation concernée. Applique-le deux fois sur une copie et compare volumes, relations et droits avant/après.
- Pour la compatibilité Travaux, conserve les accès historiques validés. Pour les nouveaux périmètres, exige un droit de contenu explicite de commission ou de dossier. Le rôle organisation sert à administrer les accès et n’élève pas un droit de contenu en lecture à l’écriture. Précise dans les tests la politique d’accès du secrétariat avant de créer son rôle.
- Traite le cas des dossiers à visibilité limitée. Une appartenance à la commission ouvre les dossiers ordinaires de son périmètre selon le rôle. Une restriction de dossier exige un grant explicite supplémentaire. Un grant historique sans droit explicite d’écriture suit la politique de compatibilité, jamais un élargissement implicite à une nouvelle commission.
- Utilise les migrations et transactions du dépôt, avec `tenant_id` dans les contraintes d’unicité et les jointures. Dans la transaction, contrôle à nouveau les invariants des opérations concurrentes. Teste restauration sur base copiée avant activation sur des données réelles. [Transactions SQLite](https://sqlite.org/lang_transaction.html)

### 4.2 Autorisation de bout en bout

- Étends `ProjectAccess` et les contrôles appelés par l’API. Applique les mêmes prédicats aux listes, pagination, compteurs, recherche, détails, exports, notifications, agenda, pièces et pages natives. Détermine l’identité et le tenant à partir de la session. Le paramètre commission sélectionne une vue parmi les droits autorisés.
- Garde la règle des sources multi-dossiers. Une pièce liée à un autre dossier inaccessible peut contenir ses informations. Sa présence dans une transmission doit reposer sur la projection validée prévue au lot 2. Vérifie directement, par identifiant, les accès à l’original et à ses aperçus, extraits et citations.
- Dans le RAG, filtre les candidats et extraits avant l’envoi au fournisseur. Attache une conversation et ses propositions au contexte organisation/commission/dossier pertinent. Vérifie les droits sur les objets et citations avant de retourner la réponse ou d’afficher une conversation sauvegardée, puis lors de chaque écriture confirmée. Lorsqu’une révocation intervient pendant une requête, inhibe la réponse et ses effets.
- Au changement de commission, isole les clés de cache et remplace les requêtes précédentes. Vérifie le changement de commission en présence d’une réponse tardive. Identité inactive, lien direct, compteurs, export, historique du chat et page ouverte pendant une révocation font partie de la recette.

### 4.3 Raccordement de l’action native

1. Garde une seule action canonique, identifiée par son dossier, sa page et son identifiant de ligne. Lis les métadonnées de collaboration via `/api/v1/projects/{project_id}/action-collaboration`. Relis les schémas Pydantic de `action_collaboration.py` avant de typer les appels.
2. Raccorde `GET /participants`, `GET` et `PATCH` sur la base, `GET` et `POST /comments`, `PUT /recurrence`, puis les routes de préparation et confirmation d’occurrence selon le lot. Utilise la révision attendue, `client_id` des commentaires et l’identifiant d’opération existant. La confirmation d’occurrence vérifie la ligne créée et la révision de page. Gère la reprise d’une opération préparée dont la réponse a été perdue.
3. Dans « Planifier une action », en ouvrant depuis un dossier, conserve le dossier de départ. Depuis « Mes actions », demande un dossier autorisé s’il manque. Charge ensuite les responsables de ce dossier. Au changement de dossier, vide un responsable devenu invalide et ignore le résultat des requêtes précédentes. Garde les affectations héritées lisibles.
4. Dans la fiche et dans « Mes actions », affiche échéance, responsable et checklist depuis les mêmes données. Sur conflit de révision, montre l’état enregistré et propose de reprendre la modification. Les transitions importantes et la raison d’un échec sont visibles dans le formulaire ou la fiche.

**Recette du lot.** Deux membres dans la même organisation, un membre dans une autre, un membre révoqué. Vérifie au moins lecture/écriture par dossier, droits mixtes Culture/Finances, projet historique accessible, pièces liées à deux dossiers, recherche et notifications, et mutation d’une action simultanée. La perte de réponse d’une occurrence préparée ne crée qu’une ligne canonique.

## 5. Lot 2 · Événements, demandes et arbitrage financier

### 5.1 Culture, sport et vie associative

**Vue initiale.** Agenda semaine/mois ou liste selon la largeur, filtres « Salle », « Équipement », « Équipe », et bouton « Nouvel événement ». L’autre vue « Demandes » montre la prochaine action, les pièces manquantes et l’état du créneau. Dans la fiche, reprends les onglets Actions, Documents, Échanges et Historique.

- Ajoute les modèles « Événement associatif » et « Demande de subvention ». Dans la fiche événement, conserve la période, le lieu, le service, la référence de l’association, la checklist, la convention et les demandes de ressources. Dans la campagne de subventions, filtre par exercice, complétude et instruction. Renseigne la référence de la décision lorsqu’elle existe. L’Espace citoyen est déjà utilisé par la commune pour ces démarches. [Démarches associatives de Plougastel](https://ville-plougastel.bzh/activites-et-loisirs/vie-associative/demarches/)
- Modélise une réservation comme une relation entre un dossier, une ressource et un intervalle, avec état, révision et références de provenance. En pilote, une ressource correspond à une unité réservée. Distingue « Demandé », « Disponibilité à vérifier », « Confirmé » et « Annulé ». Une tâche de vérification peut référencer la demande et son état.
- Pour les ressources dont MayorTech tient le planning de référence, compare l’intervalle semi-ouvert `[début, fin)` aux occupations confirmées. Les créneaux qui se touchent sont compatibles. Vérifie la disponibilité et réalise la confirmation dans la même transaction avec un verrou d’écriture adapté à la base. `Repository._transaction()` utilise déjà `BEGIN IMMEDIATE` hors transaction imbriquée. Refuse un intervalle invalide ou ambigu et vérifie les transitions d’heure de `Europe/Paris`.
- Pour une ressource tenue par un outil externe, affiche la provenance et la date de fraîcheur. En l’absence de disponibilité fiable, garde l’état « Disponibilité à vérifier ». La détection de conflit révèle le blocage du créneau sans exposer le titre privé de l’événement qui l’occupe. Une confirmation répétée avec la même opération retrouve le résultat initial.
- Le socle de la recette est une demande ponctuelle. Les récurrences de ressources, les exceptions et les quantités de matériel partagées ajoutent leurs propres tests avant activation. Relis MRBS pour identifier ces cas, puis implémente les règles retenues dans le domaine MayorTech.

### 5.2 Fonctions supports et transitions

**Vue initiale.** Liste d’arbitrage filtrable par exercice, commission d’origine et étape. Chaque ligne présente l’objet partagé, le reste à charge estimé, le service et la prochaine action. La fiche montre les variantes, les pièces reçues, le fil d’échanges et les avis par version.

1. Ajoute une fiche chiffrée à un dossier. Pour chaque variante, indique l’exercice, le montant estimé en centimes, la base HT ou TTC, les financements et leur état. Calcule le reste à charge par ligne et par scénario sur des montants comparables. Rends visibles l’hypothèse, la devise et la source du montant. Rends CSV exportable depuis les droits du dossier et traite les valeurs susceptibles d’être interprétées comme des formules par un tableur.
2. Ajoute « Transmettre pour avis financier ». Avant confirmation, affiche un aperçu de ce qui sera visible par la commission 1. Garde au serveur une transmission stable avec `tenant_id`, dossier d’origine, commission source, commission destinataire, auteur, date et version. Les variantes, notes et pièces sélectionnées sont figées ou référencées par version. Un réessai idempotent retourne la transmission existante.
3. Construis le panneau Finances depuis cette projection. Accorde à ses lecteurs et éditeurs la consultation ou l’écriture sur la transmission selon leur rôle. La transmission ne crée aucun grant général sur le dossier d’origine. Limite les aperçus et téléchargements aux pièces sélectionnées pour cette version, avec le contrôle de provenance et de droits à chaque accès. Une pièce sensible requiert une sélection et une validation explicites avant partage.
4. États du circuit proposé **En préparation → Transmis → Complément demandé / Avis rendu**. Une demande de complément précise la pièce ou l’hypothèse attendue. La réponse crée une version suivante et garde l’historique. Un avis écrit est associé à l’identifiant de la version examinée, à son auteur et à sa date. Une mutation avec version obsolète retourne un conflit exploitable par l’interface.
5. Affiche l’avis dans le dossier d’origine. Ajoute la référence de décision officielle si la personne habilitée la renseigne, puis lie une action de suivi au même dossier. L’assistant peut proposer des tâches et un résumé sourcé. La confirmation de créneau, la transmission budgétaire et l’avis suivent les actions explicites de leurs interfaces métier.
6. Étends par modèles après le parcours initial. Exemples **subvention d’investissement**, **sobriété d’un bâtiment** et **suivi d’une convention économique**. Réemploie la fiche de financement et les tâches pour suivre les échéances et engagements. Les usages RH, population et sécurité du pilote se limitent au suivi collectif sur données fictives ou agrégées.

**Recette du lot.** Crée une fête avec une demande de salle, une checklist, un devis et deux scénarios de budget. Teste conflit et annulation sur deux sessions et deux connexions à une même base de test. Soumets le budget, demande un complément depuis Finances, renvoie une version, rends l’avis et saisis une référence de décision fictive. Après rechargement, vérifie les deux versions, le dossier d’origine et ses actions. Le membre Finances accède uniquement à la projection reçue et aux pièces de cette version. Une révision, une révocation ou une transmission répétée conserve les mêmes liens et le bon périmètre.

## 6. Lot 3 · Urbanisme, travaux et ports

**Travaux.** Réutilise les chantiers, notes, calendriers, actions et dépendances existants. Depuis l’entrée historique et les liens déjà partagés, ouvre le bon dossier avant et après migration.

**Urbanisme.** Ajoute au dossier une référence externe, une parcelle ou un secteur, le type de demande, la checklist de pièces, l’avis suivi et la prochaine action. Propose la file de dossiers et un lien vers la source réglementaire. La personne saisit une date de suivi et confirme les faits extraits. L’instruction de l’autorisation reste dans l’outil du service. [Géoportail de l’urbanisme](https://www.geoportail-urbanisme.gouv.fr/)

**Ports.** Associe une fiche d’ouvrage à des inspections, constats, réserves et interventions. Réutilise `Terrain.tsx`, `field_reports.py` et la création d’action liée au constat. Les inspections ponctuelles et périodiques utilisent les tâches communes. Une maintenance avec plusieurs phases peut utiliser le Gantt.

**Intégration MapLibre.** Crée une vue carte chargée à la demande. L’API sert seulement les objets autorisés, avec leur `project_id` et les propriétés indispensables à la carte. Normalise les coordonnées et valide les géométries avant affichage. Le clic ouvre la fiche existante. Associe noms, légende et raccourci vers la liste au clavier. Démonstration avec données et style locaux. Pour un fond ou une couche externe, spécifie source, date, attribution, conditions d’usage et requêtes réseau avant installation.

**Recette du lot.** « Réfection du ponton — port Exemple » est visible en liste et carte, lié au même dossier. Crée un constat puis son action, modifie son échéance dans la fiche et vérifie Actions et Planning. Ouvre un dossier de parcelle fictive. Coupe la source de carte et vérifie le mode liste et les liens. Vérifie que l’API GeoJSON écarte les ouvrages hors périmètre avant d’envoyer la réponse.

## 7. Lot 4 · Action sociale, enfance et jeunesse

**Vue initiale.** Liste « Campagnes et actions », groupée par école, site ou service. L’agenda sert aux événements, dates limites et échéances pratiques. Les dossiers portent pièces, conventions et indicateurs agrégés. Le pilote repose sur des activités collectives fictives.

1. Commence par le modèle « Préparation de la rentrée » puis ajoute « Action jeunesse » et « Programme aînés ». Garde l’accès aux conventions, tâches et partenaires depuis la même fiche. Donne la prochaine action à chaque site.
2. Une campagne reconduite présente les dates, sites et responsables proposés avant confirmation. Les anciennes occurrences et leurs pièces restent lisibles. Pour les règles compatibles, utilise la préparation et confirmation du backend `action_collaboration.py` et ses identifiants d’opération. Identifie chaque occurrence par règle, période et site si plusieurs sites portent le même modèle. Une relance retrouve les occurrences existantes.
3. Valide le traitement d’un responsable désactivé, d’une date déplacée et d’une création partielle interrompue. Prévois le cas d’une échéance de fin de mois ou d’une journée sans heure. Rends visible ce qui attend une nouvelle personne habilitée.

**Recette du lot.** Reconduis la rentrée des écoles fictives des Alizés et des Genêts pour 2027. Confirme puis rejoue la préparation après interruption. Change la date d’un site et vérifie que seul ce site change. Examine les actions à venir, les conventions et la conservation de l’année précédente.

## 8. Lot 5 · Séances et instances spécialisées

1. Ajoute un dossier de séance avec date et ordre du jour ordonné. Associe chaque point à un dossier ou à une référence et aux versions des éléments examinés. Le brouillon permet l’ajout, le réordonnancement et la relecture.
2. À la clôture, conserve une version lisible de l’ordre du jour, des pièces examinées, des avis et des tâches issues de la séance. Relis le code `CloseMeeting` de Decidim pour les idées de traçabilité. Garde la décision officielle et sa référence dans un champ distinct saisi par une personne autorisée. Les étapes de signature, publication et transmission officielles sont gérées dans la chaîne d’actes.
3. Ajoute les instances spécialisées seulement avec une visibilité dédiée. Commence par la **CAO** et les références Mégalis, puis la **CCSPL** et les rapports de service, puis la **CCID** et les points de séance. Dans ce pilote, traite références, dates et pièces fictives. Les offres confidentielles et dossiers fiscaux individuels restent dans leurs outils habilités. [CAO](https://ville-plougastel.bzh/wp-content/uploads/2026/04/2026_CAO.pdf), [CCSPL](https://ville-plougastel.bzh/wp-content/uploads/2026/07/01A_PVdu07mai2026.pdf#page=49), [CCID](https://ville-plougastel.bzh/wp-content/uploads/2026/10/PV_CM_25.6.2026.pdf#page=6)

**Recette du lot.** Prépare et clos une séance avec deux dossiers. Modifie ensuite un dossier, son budget et ses pièces. Vérifie la traçabilité des versions examinées et l’accès aux versions actuelles depuis leurs liens autorisés. Un membre d’une commission ordinaire ne découvre aucun titre, compteur ou document de séance réservée via la navigation, un accès direct ou la recherche.

## 9. Flux externes et agenda Outlook

- **Courrier.** Réutilise la connexion déjà développée dans `MailConnectionWizard.tsx` et `src/travaux/mail_oauth.py`. Respecte la sélection de dossiers et le rattachement explicite des messages. Lorsqu’un courriel concerne plusieurs commissions possibles, propose des destinations autorisées ou laisse-le à classer. Un message importé reste une preuve et ses annonces de dates restent à confirmer. Le pilote se teste avec des `.eml` fictifs. [Connecteurs mail](../../CONNECTEURS_MAIL_OAUTH_2026.md)
- **Agenda.** Utilise l’import `.ics` et les intégrations calendrier existantes selon l’environnement. Pour un futur lot Outlook, crée une autorisation calendrier distincte du courrier. Vérifie en premier la permission déléguée `Calendars.ReadBasic` et les champs réellement disponibles. L’utilisateur choisit les calendriers et la fenêtre de lecture. Prévois la pagination, les occurrences et exceptions, la déduplication, la révocation et la provenance. Aucune disponibilité d’Exchange ou d’Outlook n’est supposée dans la recette des lots 1 et 2. [Microsoft Graph calendarView](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0)
- **Imports conditionnels.** Pour Grist, Open311 ou l’outil d’actes, fixe quelle application possède les données éditables. Une liaison stable associe organisation, instance, fournisseur, type et identifiant externe à un objet MayorTech. Vérifie la portée commission, la version reçue et le comportement au réessai. Après un timeout de création externe, rapproche le résultat avant de renvoyer. Garde les secrets côté serveur et journalise les actions utiles avec leurs identifiants de version.

## 10. Écrans et états à vérifier

| Écran | Réemploi et comportement |
| --- | --- |
| Sélecteur et accueil | `Shell.tsx`, composants de navigation et `context.tsx`. Affiche les commissions autorisées et le nom de la commission active. Un accueil sans dossier présente « Créer un dossier » pour un contributeur et une explication courte pour un lecteur. |
| Liste et fiche | `Projects.tsx` et `ProjectDetail.tsx`. Utilise « Dossier » pour les commissions et « Chantier » pour Travaux. Ouvre la bonne vue par modèle en conservant les liens des dossiers existants. |
| Affectation et date | `PlanningActionDialog.tsx` avec recherche de responsables habilités. Les champs « Dossier », « Responsable » et « Échéance » indiquent à quel dossier et à quelle action on travaille. |
| Pièces, échanges et notes | `DocumentsPanel.tsx`, `SourcePreview.tsx` et les panneaux actuels. En cas d’original indisponible, montre l’état de la pièce et les actions autorisées. Les notes restent sauvegardées via l’éditeur natif. |
| Envoi financier | Aperçu de la version et des pièces, confirmation, message d’échec exploitable et conservation du brouillon si l’envoi échoue. Affiche le statut de l’avis dans la fiche. |
| Erreurs et droits | Chargement localisé, liste vide utile, erreur récupérable, révision obsolète avec reprise, lecture seule avec indication utile et retour aux dossiers autorisés après révocation. |

Conserve l’ordre de lecture au clavier, le focus au retour des dialogues et des cibles tactiles confortables. À 390 px, la liste et le calendrier doivent rester accessibles. À 320 px, vérifie les libellés longs des commissions, le sélecteur et l’action principale. Évite les bandeaux de sauvegarde permanents. Place les échecs et actions de reprise auprès du champ ou du formulaire concerné.

## 11. Données de recette à préparer

Utilise `fixtures/` et `fixtures/storylines/` pour le chantier hérité. Pour les nouvelles commissions, génère un corpus déterministe. Les noms ci-dessous sont des exemples fictifs pour les tests. Ajoute un identifiant de fixture stable pour retrouver l’objet après rechargement et réexécution du seed.

| Donnée | Valeur de recette | Vérification |
| --- | --- | --- |
| Comptes | `culture@example.invalid`, `finances@example.invalid`, `mixte@example.invalid`, `autre@example.invalid` | Culture édite son dossier, Finances édite son avis, Mixte édite Culture et lit Finances, Autre appartient au second tenant. Ajoute un compte révoqué pendant une requête. |
| Événement | « Fête des associations · exemple », 12 juin 2027, 15 h à 18 h, salle municipale Exemple | Une réservation existante de 14 h à 16 h bloque le créneau. 16 h à 19 h est adjacent. Une deuxième requête de confirmation simultanée est refusée sur le même créneau. |
| Fiche financière | Variante A 9 600 € TTC et aide de 2 500 €, variante B 11 700 € TTC et même aide | Restes à charge de 7 100 € et 9 200 € sur les hypothèses saisies. Après demande de complément, révision A à 10 700 € TTC, reste à charge de 8 200 €. |
| Pièces | `devis-fete-v1.pdf` partagé, `devis-fete-v2.pdf` transmis après complément, `notes-internes-culture.txt` interne | La demande de complément reste liée à la version 1 et l’avis à la version 2. Finances voit la version de la pièce qu’elle a reçue. La note interne est absente du dossier transmis, de son index et des citations. |
| Urbanisme et ports | « Parcelle Exemple A-12 » et « Réfection du ponton · port Exemple » | Les liens de liste et carte convergent, la date de l’action reste commune à la fiche et au Gantt de l’opération. |
| Enfance et jeunesse | « Préparation de la rentrée 2027 », sites fictifs des Alizés et des Genêts | La campagne regroupe deux checklists. Une réaffectation locale laisse l’autre site et le cycle précédent intacts. |

Pour tester l’adhésion, relis `scripts/prepare_test_organization.py` et `tests/test_test_organization.py`. Utilise la préparation existante sur base neuve ou explicitement fictive. La démonstration publique partagée se prête à la recette visuelle seulement. Vérifie les autorisations sur une instance et une session représentatives du mode privé, ou par des tests HTTP avec identités contrôlées.

## 12. Installation et vérifications locales

Prérequis du projet vérifiés sur disque au 18 novembre 2026. Python ≥ 3.11, `uv` et Node 22. Utilise les versions du checkout et ses verrous. Ouvre [README.md](../../../README.md) et `frontend-lovable/AGENTS.md` en premier. Le runtime produit est FastAPI et React. Les fichiers Lovable historiques et ses réglages de passerelle restent en dehors de cette intégration.

### 12.1 Démarrer une recette d’interface sur une base neuve

Depuis la racine du produit, dans un terminal de test sans configuration de production chargée. Le lanceur `LANCER.ps1` charge `.env` quand il le trouve. Pour cette recette, démarre la CLI avec les variables explicites ci-dessous et un répertoire temporaire. Cette démo locale sert à l’UX. Les permissions OIDC se testent séparément avec les fixtures ou l’instance privée isolée.

```powershell
uv sync --frozen --all-extras
$mayorTechQaDir = Join-Path ([System.IO.Path]::GetTempPath()) ("mayortech-commissions-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $mayorTechQaDir
$env:TRAVAUX_DB = Join-Path $mayorTechQaDir 'commissions.sqlite3'
$env:TRAVAUX_MODE = 'demo'
$env:TRAVAUX_AUTH_MODE = 'password'
$env:TRAVAUX_LLM = 'demo'
$env:TRAVAUX_LLM_EGRESS_APPROVED = 'false'
$env:TRAVAUX_TEST_ORGANIZATION_SELF_JOIN = 'false'
uv run --frozen --all-extras travaux serve --host 127.0.0.1 --port 8766
```

Dans un autre terminal, depuis `frontend-lovable/`.

```powershell
npm ci --ignore-scripts
npm run dev
```

Ouvre `http://127.0.0.1:18766/web/product/`. `vite.product.ts` pointe vers le serveur local sur le port 8766. Pour une recette asynchrone de dépôt et indexation, lance `uv run --frozen --all-extras travaux worker` avec les mêmes variables et la même base temporaire. Le navigateur à lui seul ne valide pas l’indexation.

### 12.2 Tests et compilation

Depuis la racine du produit.

```powershell
uv run --frozen --all-extras ruff check src tests
uv run --frozen --all-extras pytest -q
node --test frontend-lovable/src/features/workspace/*.test.mjs web/tests/*.test.mjs
```

`pytest -q` découvre `tests/`. L’existant `tests/test_gantt_browser.py` lance Chrome via Playwright et requiert ce navigateur. Si tu touches la configuration de déploiement ou l’authentification privée, lance aussi `uv run --frozen --all-extras pytest deploy/hetzner/tests deploy/private-site/tests -q`. Ces vérifications restent locales.

Dans `frontend-lovable/`, utilise `npm run typecheck` et `npm run build`. Pour la recette intégrée du bundle, exécute ensuite `uv run --frozen python scripts/package_frontend.py` à la racine du produit. Ce script reconstitue `web/product/` et les pages servies. Les sources à modifier restent dans `frontend-lovable/`. Vérifie la présence et le chargement de `native-editor/dist/`. En cas de modification de l’éditeur, dans `native-editor/` lance `npm ci --ignore-scripts`, `npm test`, puis `npm run build`.

### 12.3 Tests existants sur lesquels s’appuyer

| Besoin | Suites de départ |
| --- | --- |
| Admission et droits | `tests/test_organization_codes.py`, `tests/test_test_organization.py`, `tests/test_project_access.py`, `tests/test_identity_api.py` |
| Synchronisation des actions | `tests/test_action_collaboration.py`, tests du workspace en `.test.mjs`, `tests/test_gantt_browser.py` |
| Recherche et modifications proposées | `tests/test_document_chat_workflow.py`, `tests/test_assistant_changes_review.py`, `tests/test_calendar_retrieval.py` |
| Agenda et courrier | `tests/test_calendars.py`, `tests/test_calendar_http.py`, `tests/test_calendar_readers.py`, `tests/test_mail_oauth.py` |
| Terrain | `tests/test_field_reports.py`, `tests/test_field_reports_http.py` |

Ajoute les tests de régression propres au lot. Mets les règles dans les tests métier, l’accès et les écritures dans les tests HTTP avec session et base, et le comportement de navigation dans le navigateur. Pour l’autorisation, vérifie le contenu des réponses API et leur rendu à l’écran.

## 13. Parcours de vérification et preuves à rendre

1. **Migration.** Compare une base d’essai avant et après la migration rejouée. Vérifie les identifiants, accès et liens des chantiers existants, ainsi que les actions en cours et leurs révisions.
2. **Accès.** Teste trois niveaux et un autre tenant. Vérifie les droits mixtes, les accès directs à une pièce, l’absence dans les résultats et les compteurs, la révocation en cours de requête et l’application d’une proposition du chat devenue périmée.
3. **Pilote complet.** Avec le compte Culture, ouvre l’événement, affecte une action, joins un devis, vérifie le créneau, puis transmets le budget. Change de compte, demande le complément dans Finances, retourne dans Culture, fournis la version suivante, puis rends l’avis. Relis la fiche depuis les deux périmètres après rechargement.
4. **Échecs.** Provoque une réponse tardive lors du changement de commission, deux confirmations concurrentes, un conflit de version, une erreur réseau et une pièce indisponible. L’interface conserve la saisie modifiable et indique l’action suivante lorsque celle-ci est possible.
5. **Autres lots.** Rejoue carte et liste, inspections, campagne et séances sur les identifiants de fixture. Vérifie la cohérence d’une échéance d’action dans toutes ses vues et la conservation de la version étudiée après clôture.
6. **Captures réelles du navigateur.** Capture en **1920 × 1080** et **390 × 844**, puis effectue un contrôle à **320 × 844**. Pour les lots 1 et 2, fournis le sélecteur et « Mes actions », la demande de salle en conflit, la transmission côté Culture, l’avis côté Finances, et un état de lecture seule ou d’erreur. Pour chaque lot suivant, capture sa vue d’ouverture et l’action métier principale. Nomme les preuves par lot, taille, écran et état. Garde les captures dans le dossier de résultats local utilisé pour la recette.

### Compte rendu attendu pour chaque lot

- **Livré** · parcours et points d’entrée accessibles dans l’application.
- **Modifié** · fichiers, migration, modèle de données et décisions d’accès.
- **Code libre** · dépendance ou extrait réellement employé, version, licence et provenance. Liste aussi les outils étudiés comme références et les connecteurs conditionnels.
- **Vérifié** · commandes, résultats, tests simulés ou réels locaux et liens des captures.
- **Publié** · identifiant de release, date et heure UTC, URLs, reçus opérateur, contrôles HTTPS et capture du parcours sur la version mise en ligne.
- **Restant** · éléments reproductibles à corriger et raccordements qui dépendent d’un service municipal ou d’une autorisation réelle.

## 14. Publication en production

**Consigne de livraison.** À chaque lot fonctionnel ou correctif applicatif dont la recette passe, poursuis jusqu’à la mise en ligne sur la cible autorisée et à sa vérification. Une fois l’accès opérateur et l’autorisation de mise en ligne obtenus pour ce périmètre, utilise-les pour mener la livraison à son terme. Si une étape échoue, corrige ce qui est récupérable, relance les vérifications et reprends la publication. Si un blocage persiste, fournis l’étape précise, le dernier état confirmé et ce qui manque pour reprendre.

La procédure documentée le 18 novembre 2026 publie une image sur **[travaux.kerforge.com](https://travaux.kerforge.com)**, la démo publique fictive, puis met à jour l’app et le worker de **[espace.kerforge.com](https://espace.kerforge.com)**, l’espace privé avec Keycloak et Mairie Test. Le checkout de livraison contrôlé à cette date ne contient pas de dépôt Git. La publication passe par les opérateurs SSH/Docker, avec un reçu de release. Si tu travailles dans un clone Git relié au projet, enregistre et pousse les changements vers la branche autorisée selon ses règles, puis vérifie la mise en ligne par le canal de déploiement réel. [Preuve de production du 18 novembre](../../verification-production-2026-11-18.json), [Opérateur public](../../../deploy/hetzner/README.md), [Espace privé](../../../deploy/private-site/README.md)

### 14.1 Préparer la release et sa réversibilité

1. Vérifie la cible réellement en service et l’accès depuis ton environnement. Les opérateurs historiques utilisent la configuration locale d’exploitation `~/.saas-factory/owner.json`, hors projet, avec clé SSH et vérification stricte de la clé hôte. Utilise les accès déjà provisionnés dans l’environnement autorisé. Garde leurs valeurs hors des sorties, logs, archives, captures et messages.
2. Lance les tests de la section 12, y compris les suites des opérateurs si leurs contrats sont touchés. Fais le build du frontend, le paquet local `web/product/` et les tests et le build de l’éditeur natif. Relis le résultat du parcours métier avec le bundle final. Le `gate` atteste ces validations sur les empreintes du paquet. Attends le gel effectif des fichiers livrés avant de l’exécuter.
3. Identifie la release, l’image active et le profil de chaque cible à partir des reçus ou du statut opérateur. Préserve les checkpoints et images précédents. Si les versions publique et privée divergent déjà, prépare un retour documenté pour chacune. Pour un changement de données, contrôle une sauvegarde cohérente et teste la restauration vers une base isolée.
4. **Traite les migrations du lot 1 avant toute bascule.** L’opérateur public peut refuser une modification avec `schema_review_required_before_update`. L’opérateur privé applicatif refuse les changements des fichiers protégés avec `protected_schema_or_dependency_changed`. Son chemin courant est adapté aux mises à jour compatibles. La revue d’une ancienne paire d’empreintes publiques constitue une preuve historique pour cette seule paire. Pour les commissions, prépare la migration exacte depuis les versions réellement actives, teste le backfill rejoué, compare données et habilitations, puis vérifie le démarrage de la release précédente sur une copie migrée. Fais revoir la procédure publique et privée, les empreintes de départ et d’arrivée, l’intégrité et les conditions de retour. Les contrôles des opérateurs restent applicables. [Exemple historique de revue de migration](../../publication-hetzner/REVUE_MIGRATION_PUBLIQUE_2026-11-17.md)
5. Si la cible a effectivement migré vers OVH, vérifie le runbook activé, l’image par digest, la sauvegarde, le proxy et la cible de retour avant de publier. Le dossier OVH fourni décrit un candidat. [Runbook OVH du projet](../../../deploy/ovh/README.md)

### 14.2 Démo publique · préparer, publier et tester

Depuis `outputs/travaux-mairie/`, avec le Python de l’environnement du projet. Les noms de sortie doivent être neufs et hors du projet. `plan` calcule l’inventaire local. `preflight` vérifie la cible et ses ressources via le transport opérateur. Lis ses résultats avant d’enchaîner.

```powershell
python deploy/hetzner/deploy.py plan
python deploy/hetzner/deploy.py preflight
```

Après les tests verts, la revue de la cible et le gel des fichiers à livrer, crée une archive fermée. Conserve le SHA-256 de l’archive et l’identifiant de release retournés par `package`. Toute modification de l’inventaire impose une nouvelle attestation et un nouveau paquet.

```powershell
$mayorTechReleaseDir = Join-Path (Split-Path (Get-Location).Path -Parent) ("mayortech-release-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $mayorTechReleaseDir
$mayorTechGate = Join-Path $mayorTechReleaseDir 'gate.json'
$mayorTechArchive = Join-Path $mayorTechReleaseDir 'release.tar.gz'
python deploy/hetzner/deploy.py gate --python-passed --frontend-passed --native-passed --out $mayorTechGate
if ($LASTEXITCODE -ne 0) { throw 'Attestation de release refusée' }
python deploy/hetzner/deploy.py package --gate $mayorTechGate --out $mayorTechArchive
if ($LASTEXITCODE -ne 0) { throw 'Paquet de release refusé' }
```

Applique l’archive examinée, conserve la réponse du script, puis ouvre le site dans un navigateur neuf. L’opérateur vérifie l’image, sauvegarde la base précédente, relance l’app et le worker et teste le profil public avant d’activer la route. `deployed: true` déclenche la recette HTTPS externe.

```powershell
python deploy/hetzner/deploy.py apply --archive $mayorTechArchive
```

Vérifie le certificat, `/health/live`, l’ouverture anonyme, les données fictives, l’éditeur et ses sous-assets. Vérifie le refus d’import privé et le parcours livré qui est visible sur la démo. Compare les noms ou empreintes des assets servis à ceux du bundle si une ancienne interface apparaît. Conserve le reçu et les captures.

### 14.3 Espace privé · reprendre l’image publiée

Pour une mise à jour applicative compatible, utilise `app_update.py` sur **la même image déjà active et vérifiée côté public**. Le script contrôle les manifestes et l’image en cours d’exécution. Il sauvegarde SQLite, compare les empreintes du plan et recrée seulement l’app et le worker. La commande `operator.py apply --reviewed` appartient à la première installation de l’espace privé.

Remplace les valeurs d’exemple par le tag exact de l’image publiée et l’identifiant de la revue du candidat. Le tag accepté contient la version applicative et la release UTC retournée par `apply`. Le résultat de `plan` donne `expected_compose_sha256` et `expected_status_sha256`.

```powershell
$mayorTechImage = 'travaux-mairie:0.8.1-RELEASE_PUBLIEE'
$mayorTechReview = 'commissions-lot-1-REVUE_DU_CANDIDAT'
python deploy/private-site/app_update.py plan --image $mayorTechImage --review-id $mayorTechReview
```

Avec les deux empreintes du plan frais et la revue terminée. Si un changement concurrent invalide le plan, relis l’état et refais le plan avant d’appliquer.

```powershell
$mayorTechComposeHash = 'COMPOSE_SHA256_RETOURNE_PAR_PLAN'
$mayorTechStatusHash = 'STATUS_SHA256_RETOURNE_PAR_PLAN'
python deploy/private-site/app_update.py apply --image $mayorTechImage --review-id $mayorTechReview --reviewed --expected-compose-sha256 $mayorTechComposeHash --expected-status-sha256 $mayorTechStatusHash
if ($LASTEXITCODE -ne 0) { throw 'Mise à jour privée en échec' }
python deploy/private-site/operator.py status
```

Attends le résultat `applied: true` ou la confirmation idempotente de la même image, puis vérifie la release et le reçu correspondant. En HTTPS, vérifie le refus de l’accès anonyme, la connexion et le TOTP avec un compte de recette autorisé, l’accès à Mairie Test et le parcours modifié. Teste le cloisonnement en privé si le lot touche les droits. Capture le parcours à la taille demandée, avec des données fictives. Confirme la santé de l’app et du worker et observe les erreurs et le traitement des tâches pertinentes avant d’annoncer la publication.

### 14.4 Échec, retour et preuve finale

- **Échec avant activation.** Lis le code d’erreur et le dernier reçu. Regénère une archive si elle a dérivé du code. Refais le précontrôle si l’état de la cible a changé. Un défaut d’accès opérateur, une validation de migration manquante ou un espace disque insuffisant doit être résolu sur le bon périmètre avant de réessayer.
- **Démo publique dégradée.** Après confirmation du précédent compatible, utilise `python deploy/hetzner/deploy.py rollback`. Vérifie ensuite HTTPS et le profil restauré. Le rollback préserve les volumes et ne restaure pas automatiquement la base. Si une migration rend l’ancienne image incompatible, applique le plan de récupération vérifié sur copie avant de réouvrir les écritures.
- **Espace privé dégradé.** Pendant l’activation, `app_update.py` tente le retour à son Compose et à son image précédents. Confirme le retour via le reçu, le statut et le navigateur. Après une mise à jour déjà réussie, il s’agit d’une opération de retour distincte. Si l’image précédente du privé correspond exactement à l’image publique restaurée et que leurs manifestes et schémas sont compatibles, reprends `plan` puis `apply` avec cette image et de nouvelles empreintes. Dans les autres cas, utilise le plan opérateur revu pour le reçu et la sauvegarde concernés. Le message `application_update_failed_manual_recovery_required` exige une vérification de l’état réel avant toute autre mutation.
- **Compte rendu.** Donne, par cible, la release précédente, la release réellement active, l’heure UTC, l’URL testée, le reçu et les contrôles qui ont réussi. Distingue une archive prête, un déploiement exécuté, un retour arrière et une version vérifiée en ligne. Mets à jour la preuve de production du projet avec les seuls éléments publiables.

**Démarrage.** Reprends les tests d’accès et de création de dossiers, relève les points où l’organisation et le dossier sont résolus, puis implémente la migration et les tests du lot 1. Après recette, suis la procédure de publication. Le pilote Culture → Finances doit être vérifiable avant d’intégrer MapLibre ou de brancher un service externe.
