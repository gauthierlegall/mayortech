# Travaux — espace municipal de suivi des chantiers

La [comparaison de code et de briques libres](../travaux-oss-comparison-2026-11-16/README.md) conserve les sources utiles OpenProject/Zammad avec licences et empreintes, teste leurs fonctions portables et compare Haystack à notre recherche. Zammad a aussi une recette réelle de tickets et droits HTTP ; ERPNext est distingué de ses parcours restant à valider. Un correctif local limite les suggestions de responsable au chantier choisi, avec recette Full HD et sauvegarde Yjs ; il n'est pas déployé par cette étude.

L'[essai réel OpenProject Community](../travaux-openproject-evaluation/README.md) vérifie tâches, dépendances, dates, pièces et permissions sur des données fictives. Sa [galerie Full HD](../travaux-openproject-evaluation/index.html) montre les écrans natifs. Cette évaluation n'a pas migré le produit ni connecté une messagerie municipale.

L'[audit des solutions libres et de l'existant](docs/audit-solutions-libres-2026-11-16.md) distingue les moteurs réellement utilisés, le code métier spécifique et les alternatives OpenProject/ERPNext/Zammad/Nextcloud/RAG. Les comparaisons portent sur les éditions effectives ; aucune migration n'est engagée.

Le [dossier Exchange, OVH et Mistral du 16 novembre 2026](docs/cible-ovh-exchange-mistral-2026-11-16.md) explique le raccordement des mails, compare les briques libres et modèles rapides, et priorise les écarts de sécurité avant données municipales. Il prépare une cible privée ; il ne constitue pas un raccordement ou une migration réalisés.

Le **correctif 0.8.1** conserve les dossiers cochés lors des retours dans le parcours mail, permet de rejouer l’exemple et actualise les compteurs après import puis lecture. La [recette en Full HD et ses 24 captures](docs/mail-workflow-fullhd-2026/README.md) distingue la démonstration publique du parcours privé testé avec un lecteur Exchange fictif. Le site public ne permet pas de relier une vraie boîte.

La **version 0.8** ajoute un parcours guidé pour relier sa messagerie : fournisseur, compte et test, dossiers autorisés, puis première lecture explicite. Il est essayable en démonstration sans identifiants réels. Le formulaire **Planifier une action** demande désormais un chantier explicite et conserve le responsable enregistré ; les responsables peuvent aussi être saisis librement. [Parcours et recette 0.8](docs/mail-connection-2026/README.md).

La **version 0.7** rapproche l’ensemble de l’interface du nouveau **mayor-project-hub (1).zip** : navigation et six onglets de dossier, planning mensuel global et par chantier, suivi terrain et messagerie à trois colonnes. L’Assistant devient une **bulle en bas à droite ouvrant un popup non modal**, avec historique et requête conservés pendant la navigation. Le Gantt est corrigé pour les actions dont l’avancement reste inconnu. [Livraison et recette Lovable v2](docs/lovable-integration-v2/README.md), [référence et provenance](docs/lovable-integration-v2/AUDIT_UX.md).

Les quinze propriétés de la référence Notion, agendas, reprise des anciens courriels, preuves et documents Yjs AFFiNE restent raccordés au même backend. [Propriétés et référence Notion](docs/coordination-2026/CHAMPS_NOTION.md), [connexions agendas](docs/CONNECTEURS_AGENDAS_2026.md), [conversations, recherche et Telegram](docs/conversation-integration-2026/README.md). Les [versions0.6](docs/coordination-2026/README.md) et [0.5](docs/lovable-fidelity-2026/comparatif-0.5.html) restent documentées.

Les actions confirmées d'un mail sont matérialisées une fois dans la base native à l'ouverture du dossier, puis partagent les mêmes lignes entre Tableau/Kanban et fiches mobiles. Les nouveaux imports conservent aussi les octets originaux EML et pièces, téléchargeables depuis Documents ; les anciens fichiers absents ne sont pas reconstitués artificiellement depuis leur extrait.

Travaux réunit **une vraie page native AFFiNE/BlockSuite, ses blocs et ses bases**, les courriels, les preuves et la mémoire du chantier dans la même application et la même session. L’éditeur est embarqué dans le produit ; il n’ouvre ni une seconde application ni une iframe.

Le pilote vise d’abord le quotidien d’un responsable travaux : retrouver un dossier, écrire une note, lire ce qui a changé, confirmer une information et préparer un récapitulatif sourcé. **Toutes les données de démonstration sont inventées. Aucun compte mairie, serveur Exchange institutionnel ou endpoint Mistral réel n’est connecté.** L’analyse de démonstration est déterministe et ne fait aucun appel LLM payant.

La livraison embarque le moteur documentaire et le backend Travaux. **Elle n’installe pas le serveur standalone AFFiNE complet** et ne revendique pas toutes les fonctions de Notion ou d’AFFiNE. L’ancienne architecture avec AppFlowy séparé est remplacée ; ses documents et adaptateurs conservés sont historiques.

**Démonstration HTTPS : [travaux.kerforge.com](https://travaux.kerforge.com)**. Le mode public **sans mot de passe** utilise une base séparée de données inventées. Les imports de fichiers privés et les connexions institutionnelles y sont interdits côté serveur. Les conversations sont isolées par un cookie visiteur privé ; les brouillons de courriels restent dans le navigateur de leur auteur.

## Ouvrir la démonstration locale

Sur ce poste, depuis ce dossier :

```powershell
.\LANCER.ps1
```

Puis ouvrir **http://127.0.0.1:8765**. Si le serveur est déjà démarré, ouvrir directement cette adresse. Arrêt : `Ctrl+C` dans le terminal du serveur.

Sur un autre poste avec Python 3.11+ et `uv` :

```powershell
uv sync --frozen --extra documents --extra exchange --extra calendars
uv run --frozen travaux serve
```

Le bundle natif compilé dans `native-editor/dist/` est fourni et servi sous `/native/`. Le répertoire complet, avec ses sous-assets, est nécessaire. Pour le recompiler, utiliser **Node 22** et suivre le [guide de l’éditeur natif](native-editor/README.md) ; l’éditeur se charge à la demande.

Le mode démo reste sur la boucle locale et ne demande pas de mot de passe. Une adresse `127.0.0.1` ouverte sur un téléphone désigne ce téléphone, pas ce PC. La démo publique HTTPS permet de consulter les données inventées sur un téléphone. Un espace contenant des données réelles conserve son authentification.

Les variables viennent de l’environnement du processus. Pour charger explicitement un `.env` local : `uv run --frozen --env-file .env travaux serve`. Le lanceur PowerShell le fait si ce fichier existe. Ne pas commettre de secrets.

## Parcours dans le même espace

1. Dans **Chantiers**, ouvrir un dossier : le **Planning** permet de renseigner début, fin, responsable, statut et avancement des actions. Le bouton **Propriétés** ouvre la section dépliable de Page : Dossier, Catégorie, Coût estimé, Coût réel, Date demande, Demandeur, Entreprise, Lieu, Notes, Observation, Pièces jointes, Priorité, Service / Responsable, Statut et Échéance. Ces saisies humaines ne valident aucune annonce extraite des courriels.
2. Écrire directement dans les blocs de la page. Ajouter une base et modifier ses lignes/propriétés sur ordinateur. L’état d’enregistrement distingue modifications, requête en cours, sauvegarde confirmée et erreur.
3. Dans **Messagerie**, parcourir réception, brouillons, envoyés, archives et corbeille, rechercher, lire, classer et marquer les messages. Répondre ou transférer prépare un brouillon ; l’envoi reste désactivé tant qu’aucun transport institutionnel n’est connecté. Le classement est réversible et ne supprime jamais la preuve du dossier.
4. Dans **À vérifier**, comparer ancien et nouveau fait et ouvrir l’extrait source. Accepter, remplacer explicitement une valeur contradictoire, corriger avec un motif ou écarter. Une correction humaine garde sa propre provenance.
5. Préparer un récapitulatif à partir du **contexte enregistré et versionné** : mémoire, notes, texte des pages et valeurs des bases matérialisées. Les propositions non arbitrées et la couverture partielle restent visibles.
6. Corriger le brouillon, enregistrer une nouvelle version, relire ses preuves, puis approuver le contenu exact. Exporter la version approuvée en Markdown ou HTML. Un changement de contexte rend un ancien brouillon à actualiser ; il n’est pas silencieusement réapprouvé.
7. Dans un espace privé ou local, importer un EML fictif pour poursuivre la recette. La démo publique partagée refuse cet import. Les fils et références peuvent proposer un rattachement ; une ambiguïté demande une décision. Les pièces traitées suivent le courrier.
8. Dans **Connexions**, vérifier un compte Exchange ou CalDAV, puis enregistrer les dossiers et agendas autorisés. La reprise historique Exchange prépare une période et des dossiers avant lecture par lots ; pause, reprise, annulation et compteurs restent conservés. Les anciens messages et les pièces passent par le même circuit de rattachement et de validation.
9. Dans **Agenda**, consulter les rendez-vous importés et les rattacher explicitement à un chantier. Les dates du calendrier restent distinctes des faits confirmés du dossier. Les fichiers ICS conservent leur original et peuvent être exportés.
10. Ouvrir la bulle **Assistant** en bas à droite pour retrouver ses conversations et leurs sources. La recherche SQLite FTS5/BM25 consulte le contexte autorisé ; changer de chantier ne change pas silencieusement le fil courant. Telegram utilise le même historique après appairage ; la conversation complète exige l’autorisation de l’organisation et l’activation explicite de l’utilisateur. Le worker Telegram est séparé du worker d’import.
11. Dans **Planning**, filtrer les vrais chantiers et consulter la frise mensuelle ; **Déplacer** permet de glisser les dates. Dans **Suivi terrain**, enregistrer une visite, anomalie ou réserve, la lever ou la rouvrir, puis créer une action native liée. Rejouer une création après interruption réutilise la même ligne ; une action supprimée n’est pas recréée silencieusement.

Les mails d’essai de `fixtures/` sont entièrement fictifs, y compris les cas de contradiction, ambiguïté, instruction hostile et pièce jointe. Ce ne sont pas des mails municipaux anonymisés.

## Ce qui est réellement intégré

| Élément | Périmètre livré et limites |
|---|---|
| Pages et blocs natifs | Paquets AFFiNE/BlockSuite **0.22.4** réellement exécutés dans Travaux ; état Yjs enregistré et rechargé par notre API. Certains menus natifs restent en anglais. |
| Bases sur ordinateur | Modèles et propriétés typées natifs, vues tableau et Kanban. Les lignes sont des blocs natifs ; elles ne deviennent pas automatiquement des pages de chantier indépendantes. |
| Bases sur téléphone | **Lecture en fiches des mêmes lignes et identifiants natifs**, avec accès à tous les champs. L’édition des bases mobiles n’est pas livrée ; les paragraphes restent éditables avec le moteur natif. |
| Sauvegarde et contexte | Historique, empreintes et contrôle de révision côté serveur. Le texte matérialisé par l’adaptateur natif inclut les bases. Un conflit conserve la saisie locale ; la navigation attend les générations d’enregistrement en cours. |
| Mémoire, propositions et récapitulatifs | Persistance SQLite transactionnelle, sources identifiées, décisions humaines, versions de contexte et de contenu, couverture et obsolescence. Une saisie encore non acquittée par le serveur ne fait pas partie d’un snapshot durable. |
| Courriels et pièces | Consultation en texte brut, recherche, filtres et rattachement. Import EML ; extraction des formats pris en charge. PDF/DOCX en sous-processus borné ; un scan sans texte peut demander de l’OCR. Aucun contenu HTML actif ou traceur distant du mail n’est chargé. |
| Propriétés de dossier | Quinze intitulés vérifiés sur la référence photographiée, coûts décimaux distincts, textes longs, dates et provenance. Titre et statut restent canoniques. Les pièces jointes réutilisent les vrais originaux. Aucune donnée personnelle photographiée n’est copiée dans la démonstration. |
| Planning | Frappe Gantt 1.2.2 réellement réutilisé ; glisser les dates et la progression sur ordinateur, formulaire clavier/mobile. Mêmes lignes Yjs que les Actions, contrôles de concurrence et champs vides préservés. |
| Frise Lovable et Terrain | Grille mensuelle, listes et formulaires repris de la nouvelle archive utilisateur. Placement des seules dates enregistrées, jalons confirmés distincts des propositions. Constats persistants tenant/projet, source humaine, audit, contrôle de révision et lien vers l’action Yjs existante. |
| Agendas | Exchange EWS et CalDAV en lecture seule, plusieurs collections choisies, import/export ICS, rattachement local. Google Agenda et Microsoft 365 OAuth sont non implémentés ; leurs fiches indiquent cette limite. |
| Conversations et notifications | Historique privé de 30 jours, citations exactes et rendez-vous typés ; rappels dans l’app et relais Telegram optionnel avec appairage, double accord pour le texte complet, files chiffrées et statut des livraisons. Aucun bot réel raccordé en démonstration. |
| Mistral | Client et garde-fous d’extraction structurée fournis ; endpoint, modèle et sortie autorisée à qualifier. Aucune inférence Mistral réelle validée dans cette démonstration. |
| Exchange local ou prestataire | Collecteur EWS incrémental, stockage avant checkpoint et périmètre explicite. Pas de connexion institutionnelle réelle testée ; la DSI doit vérifier serveur, authentification et droits de lecture. |
| Hébergement | **Staging Hetzner fictif publié et testé en HTTPS**, session, éditeur natif, worker, sauvegarde et restauration contrôlés. Aucun déploiement municipal ou OVH de production n’est annoncé comme réalisé ici. |

Ne sont pas livrés : collaboration native en temps réel, stockage de blobs/images/pièces dans l’éditeur, mode hors ligne durable, formules de bases, relations globales complètes entre bases ou calendrier natif. Les blocs de médias et d’embed externes concernés sont désactivés, plutôt que présentés comme fonctionnels sans stockage.

Les sources, versions et licences du moteur et les dépendances sont documentées dans [native-editor/README.md](native-editor/README.md), [REUSE.md](native-editor/REUSE.md) et [les dépendances](docs/dependances.md). Le backport local de l’avis Zod reste tracé ; la livraison n’est pas présentée comme un audit sans vulnérabilité ni une qualification de production.

## Code réellement réutilisé

Le [registre de réutilisation](docs/REUTILISATION_CODE.md) distingue les dépendances exécutées, fichiers copiés et adaptations : moteur AFFiNE/BlockSuite, fonction native d’initialisation de base, fonctions d’URL de Grist Core, feuille d’export de La Suite Docs et instructions de construction adaptées depuis OpenGateLLM/Docs. Les sources, commits, notices et empreintes y sont reliés.

Cela **n’installe pas les applications Docs, Grist ou OpenGateLLM complètes**. Les recherches ERP et publiques ne sont pas comptées comme du code intégré. Les adaptateurs AppFlowy conservés ne sont pas le moteur documentaire du produit actuel.

## Vérifier et consulter les preuves

Pour les tests Python, documents et connecteurs, y compris les adaptateurs historiques :

```powershell
uv sync --frozen --extra dev --extra documents --extra exchange --extra appflowy
uv run --frozen ruff check src tests
uv run --frozen pytest -q
node --test web/tests/model.test.mjs web/tests/mail.test.mjs web/tests/workspace.test.mjs
uv build
```

L’extra `appflowy` sert aux tests des adaptateurs historiques ; il n’est pas requis pour ouvrir la page native AFFiNE. Les commandes de compilation et de tests propres au moteur sont dans le [guide natif](native-editor/README.md).

Les [preuves de recette intégrée](docs/ux-benchmark-2026/integration/) distinguent la vraie API locale des fixtures du module : [base native sauvegardée et relue, cartes 320/390 px](docs/ux-benchmark-2026/integration/database-result.json), [courriels, pièces, filtres et retours de focus](docs/ux-benchmark-2026/integration/mail-result.json), [deux saisies pendant un enregistrement](docs/ux-benchmark-2026/integration/inflight-result.json), [génération avant acquittement et brouillon signalé obsolète](docs/ux-benchmark-2026/integration/summary-result.json). Les captures de ce dossier sont issues de données fictives. Les anciens [rapports de l’interface initiale](docs/screens/index.md) ne prouvent pas à eux seuls la recette du moteur natif ajouté ensuite.

Les tests responsive en navigateur ne remplacent ni un essai sur téléphone physique, ni un audit RGAA complet. Les captures de concurrents sont des références documentaires, pas des preuves que nos écrans fonctionnent. La CI distante et le staging doivent chacun produire leurs propres résultats ; leur préparation n’est pas une exécution réussie.

## Publication et usage municipal

Le [dossier staging Hetzner](deploy/hetzner/README.md) décrit la publication isolée, protégée par authentification et limitée aux données fictives. La [recette publique0.3](docs/ux-refonte-2026/public/rapport.md) vérifie HTTPS, session, documents et vues natives. La [première publication0.2](docs/publication-hetzner/rapport.md) reste archivée. Les accès et secrets sont remis séparément, hors du dépôt et de l'archive de sources.

Le pilote vise une collectivité, un compte opérateur et un hôte persistant. Un futur SaaS demande une décision propre sur identité/SSO, autorisations, séparation des collectivités, stockage, exploitation et contrats. **Ni le code libre, ni le fournisseur d’hébergement, ni les tests ne constituent une certification RGPD.** Lire [protection des données](docs/protection-donnees.md), [exploitation](docs/exploitation.md) et [architecture du domaine](docs/architecture.md) avant toute donnée municipale réelle. Le choix final d’hébergement, notamment OVH, reste distinct du staging fictif.

Pour le raisonnement UX et les briques étudiées : [design actuel](docs/design.md), [galerie des interfaces publiées](docs/ux-benchmark-2026/index-competiteurs.html), [benchmark et critères de recette](docs/ux-benchmark-2026/rapport-competiteurs.md), [briques publiques françaises](docs/ux-benchmark-2026/briques-publiques-france.md), [usages de l’IA au travail](docs/ux-benchmark-2026/usages-ia-au-travail.md), [ERP et agents](docs/ux-benchmark-2026/erp-et-agents.md).


## Recompiler le frontend fourni

Le client fonctionne sans Supabase ni passerelle Lovable. Les migrations et fichiers générés de l’archive d’origine sont conservés comme source, sans être utilisés au runtime. Le fichier `.env` de l’archive n’a pas été copié.

Depuis `frontend-lovable/`, avec Node 22 : `npm ci --ignore-scripts`, puis `npm run build`. Depuis la racine : `python scripts/package_frontend.py`. Le build place le client, les polices DM Sans locales et les notices sous `web/product/`. Le backend sert cet ensemble et l’éditeur natif sur le même domaine. Le mode de développement Vite utilise seulement un proxy sur la boucle locale ; il ne modifie pas la protection CSRF du serveur.

Les préférences offrent six accents et deux espacements. L’administration présente le profil de l’organisation, l’accès réellement utilisé, les droits appliqués par Casbin et le journal réel. L’espace privé utilise les comptes individuels Keycloak avec email vérifié et second facteur. Le [parcours d’adhésion](docs/adhesion-organisation.md) demande le code de l’organisation puis son accord ; **Mairie test / MAIRIE-TEST** accepte automatiquement les nouveaux membres sur ses seuls dossiers fictifs.
