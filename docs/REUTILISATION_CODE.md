# Code réellement repris et exécuté

Le produit utilise un moteur documentaire AFFiNE intégré. Ce document distingue le code exécuté, les fichiers copiés, les adaptations et les sources étudiées sans les faire passer pour des modules installés.

## Dans le chemin d'exécution actuel

| Origine | Code repris | Utilisation réelle | Adaptation et preuve |
|---|---|---|---|
| AFFiNE / BlockSuite 0.22.4 | Store, BlockStdScope, extensions de blocs, DatabaseBlockDataSource, propriétés typées, gestionnaires tableau/cartes, PlainTextAdapter | `native-editor/src/editor.ts` : pages et bases dans le produit, sans ouvrir une autre application | Liaison à notre API, contexte métier, sauvegarde versionnée et lecture mobile ; tests clavier → base → sauvegarde → rechargement |
| AFFiNE, commit `9c615502…` épinglé dans le manifeste vendor | `databaseViewInitTemplate`, corps copié depuis le vrai module database | `native-editor/vendor/affine/database-view-init.ts`, appelé par le modèle fictif explicite ; la création métier démarre sans ligne | Corps upstream conservé ; wrapper métier séparé. Voir [REUSE.md](../native-editor/REUSE.md), provenance/hash et licence |
| Grist Core, commit `a3c557ac1bc4bd55b9b9d4333842bec255586ff4` | `tryParseUrl` et `sanitizeHttpUrl` | Petit extrait conservé dans `web/upstream-grist.js`, importé par `web/model.js` ; la recherche statique du 16 novembre n'a pas établi d'appel courant au wrapper `safeUrl()` | Annotations TypeScript retirées, corps des fonctions inchangés ; Apache-2.0 + NOTICE conservés. Aucun moteur Grist installé |
| La Suite Docs, commit `f0e1b79a406b11c8c2b120cf211c26819c7aa74d` | Feuille d'export `export-html-styles.txt`, copiée intégralement | `src/travaux/vendor/docs_export.css`, lue par `exporting.py` et utilisée dans chaque export HTML validé | Fichier original inchangé et empreinte identique. Nos ajustements sont ajoutés séparément ; MIT conservée |
| OpenGateLLM, commit `223551e18857d38a8eb69081d3f04eae56753f2b`, et Docs | Construction en étapes, `UV_COMPILE_BYTECODE`, `UV_LINK_MODE`, `UV_PYTHON_DOWNLOADS`, copie de l'environnement vers une étape runtime non privilégiée | `Dockerfile` de l'application déployée | Instructions reprises et adaptées au package FastAPI/à Python 3.11, images épinglées ; aucun serveur Django ou gateway entier ajouté |
| Yjs 13.6.33 | Document CRDT et encode/apply update natifs | État des pages, enregistré et rechargé par l'éditeur | Persisté côté serveur avec empreinte, historique et contrôle de concurrence ; pas de reconstruction de l'éditeur à partir d'un textarea |
| Bibliothèques EWS et documents | exchangelib, pypdf, python-docx, markdown-it-py | Connecteur Exchange, extraction documentaire et rendu de récapitulatif | Dépendances verrouillées, tests des frontières et limites de ressources |

Les chemins exacts et empreintes Docs/Grist sont dans `src/travaux/vendor/UPSTREAM.json`. Les notices Grist sont aussi servies dans `web/GRIST-LICENSE.txt` et `GRIST-NOTICE.txt`. Les notices du moteur et les sources exactes des fichiers de thème MPL sont fournies dans `native-editor/dist/`.

L'essai de build réel Hetzner a révélé l'absence de Buildx/BuildKit sur cet hôte. Le montage de cache `RUN --mount` a été retiré de notre adaptation ; `uv sync --frozen --no-cache` garde le lock et la construction en étapes, tout en fonctionnant avec son moteur existant.

## Pourquoi certains fichiers lus n'ont pas été copiés

- Le starter AFFiNE complet crée plusieurs bases et beaucoup de lignes fictives, puis remet son historique à zéro. La fonction de production isolée convient à notre bouton ; le starter entier altérerait les dossiers.
- Le `LogSanitizer` Grist lu traite spécifiquement des journaux Redis `rpush` et modifie leur payload. Notre pilote n'utilise pas cette structure de journal ; l'ajouter n'aurait pas protégé les sources.
- L'adaptateur Mistral OpenGateLLM est une classe vide qui hérite d'une infrastructure de gateway. Copier ce fichier seul n'apporterait pas cette infrastructure. Notre port d'extraction reste explicite et sans outils d'action ; une gateway complète est un choix de déploiement ultérieur.
- Le streaming OpenGateLLM lu traite les codes HTTP en début de flux et dépend d'une version Python plus récente. Le parcours courant valide un objet JSON complet avant de proposer des changements ; il n'utilise pas ce flux. Ce fichier n'est pas présenté comme un module intégré.
- Frappe, Odoo et Grist ont chacun un modèle d'identité et de données complet. Les juxtaposer ne crée pas un cœur métier cohérent. Leurs modules applicatifs seront repris quand le domaine choisi en a besoin, avec une décision et une recette propres.

## Processus appliqué aux prochains modules

1. Lire l'implémentation et ses tests, pas seulement le README.
2. Épingler la source et vérifier le périmètre de licence.
3. Choisir une dépendance maintenue pour un moteur complet, ou copier le module autonome utile avec son origine.
4. Isoler nos adaptations et tester le composant dans le vrai parcours de l'outil.
5. Garder visibles les limites et les correctifs locaux. L'avis Zod reste déclaré malgré son backport tracé ; aucune affirmation artificielle « zéro vulnérabilité » ne le masque.

Ce registre décrit un réemploi effectif. Les études publiques et ERP dans `ux-benchmark-2026/` ne sont pas comptées comme des composants installés.

## Ajouts vérifiés le 15 novembre 2026

| Composant | Copie effective | Origine et statut |
|---|---|---|
| PyCasbin 2.8.0, Apache-2.0 | `src/travaux/vendor/casbin_domains/rbac_with_domains_model.conf` : 14 lignes copiées littéralement, avec `LICENSE` et `UPSTREAM.json`. Moteur `pycasbin==2.8.0` installé et verrouillé ; import Python `casbin`. | Tag `v2.8.0`, commit `f858158e85eb9abdf308fd356d0246b89922b11b`. Wheel/sdist et licence vérifiés. Test du modèle en mémoire : accès autorisé dans son organisation, refus hors organisation et d’une action absente. La recette des routes de gouvernance reste distincte. |
| Nodemailer 10.5.0, MIT-0 | `web/vendor/nodemailer-addressparser.js` : module ESM officiel de 1398 lignes, copié sans changement de logique ; licence, notice et provenance conservées. | Tag/npm `gitHead` `f4bacd5dca6ddc47b8b865acee4084d54a7aa797`. Intégrité de l’archive npm et hash du fichier vérifiés. Trois tests de destinataires réussis. Aucun transport SMTP ou paquet Nodemailer complet ajouté ; le branchement au composeur est une étape séparée. |

La [lecture de code messagerie et IAM](LECTURE_CODE_MAIL_IAM.md) cite les implémentations et les limites. Nextcloud Mail (AGPL-3.0-or-later) et Casdoor (Apache-2.0) ont été étudiés mais leurs applications ou composants UI ne sont pas présentés comme intégrés. La copie MIT-0 du parseur et le modèle Apache-2.0 n’entraînent aucune réétiquette silencieuse du frontend sous AGPL.

## Comparaison du 16 novembre 2026

Le [nouveau dossier de comparaison](../../travaux-oss-comparison-2026-11-16/README.md) conserve sept sources OpenProject et quatre Zammad avec leurs avis, commits et empreintes, dans des répertoires de référence isolés. Le parseur de durée OpenProject et le filtre d'en-têtes non fiables Zammad ont été exécutés tels quels ; les classes Rails couplées ne sont pas présentées comme des bibliothèques embarquées dans Travaux.

Haystack et son intégration Mistral ont été installés dans un environnement d'essai séparé : le pipeline de recherche a réellement tourné, sans inférence externe. Aucun ajout aux dépendances du produit n'est justifié par les résultats de classement obtenus. Après une première installation interrompue pour réserve disque, Zammad a une recette réelle de tickets, sources, affectations et droits HTTP en seconde instance. ERPNext conserve un rapport distinct de ses phases ; l'installation n'est pas présentée comme une preuve de tous ses workflows.

Le correctif des suggestions de responsable, limité au chantier choisi, est du code original dans notre formulaire ; il ne copie aucun module GPL/AGPL et ne crée pas un IAM individuel. Le registre distingue ainsi références acquises, tests locaux, installations temporaires et code effectivement incorporé au produit.

## Ajouts et Études du 18 novembre 2026 · Commissions Plougastel-Daoulas

| Composant | Statut et Intégration | Origine et Licence | Utilisation dans MayorTech |
|---|---|---|---|
| **MapLibre GL JS 6.19.0** | Module frontend intégré | BSD-3-Clause, commit `861a52a` | Composant `GeoMap.tsx` : affichage vectoriel des parcelles d'urbanisme et ouvrages portuaires de Plougastel (Tinduff, Passage, Auberlac'h). Mode liste et accessibilité clavier conservés en repli. |
| **MRBS 1.13.0** | Étude de référence comportementale (aucun code copié) | GPLv2, commit `383c982` | Règles d'anti-collision dans `culture_finances.py` : contrôle d'intervalle semi-ouvert `max(s1, s2) < min(e1, e2)` avec verrou `BEGIN IMMEDIATE` et gestion du fuseau `Europe/Paris`. |
| **Kanboard 1.2.57** | Étude de référence comportementale | MIT, commit `2ddb31b` | Modèles de sous-tâches et récurrence relative raccordés à l'action collaborative native Yjs dans `action_collaboration.py`. |
| **Decidim 0.32.2** | Étude de référence comportementale (`CloseMeeting`) | AGPL-3.0-or-later, commit `6b835ff` | Cycle de vie des séances dans `seances_instances.py` : clôture formelle, contrôle du quorum légal CGCT L2121-17 et calcul de l'empreinte canonique SHA-256 (`pv_hash`) verrouillant le procès-verbal. |
| **FullCalendar 6.1.21 & Frappe Gantt 1.2.2** | Dépendances réutilisées | MIT | `Agenda.tsx` partagé entre commissions et planning à dépendances dans Travaux. |

