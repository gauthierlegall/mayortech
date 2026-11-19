# Préparation du déploiement Hetzner 0.4.0

Ce dossier gère désormais la démo publique fictive sur `https://demo-travaux.kerforge.com`. Le domaine `travaux.kerforge.com` appartient à l’espace protégé et à un autre opérateur. Les preuves 0.4.0 et les publications protégées 0.2/0.3 restent historiques : aucun `apply`, SSH ou démarrage Docker n'est effectué par les tests locaux.

Depuis la séparation des origines, cet opérateur possède uniquement `/opt/caddy/conf.d/travaux-mairie-demo-origin.caddy`. Son rendu canonique conserve le backend public existant : `Host` et `Origin` amont restent `travaux.kerforge.com`, avec contrôle puis réécriture de l’Origin exact de la démo. Seul le cookie anonyme `travaux_chat_session` est transmis au backend public. `DOMAIN` désigne l’alias public ; `RUNTIME_DOMAIN` désigne le domaine attendu par le backend et ses probes loopback. Le Compose et sa base ne changent pas.

La migration opérateur de `current.json.route_hash` doit vérifier le contenu exact de l’alias actif et se faire atomiquement. L’ancien fichier `travaux-mairie.caddy` est un garde sous forme de commentaire, laissé à l’opérateur de l’espace protégé ; cet outil ne le modifie plus. Les anciens opérateurs doivent refuser ce garde grâce à leur contrôle d’empreinte. Les historiques de rollback qui contiennent encore le vhost protégé sont refusés avant toute modification de service ; ils exigent une migration explicite, jamais une réinjection automatique de l’ancienne route.

Le profil courant `public_demo` permet de consulter des données fictives sans mot de passe. Le serveur AFFiNE complet, Exchange institutionnel et Mistral ne sont pas activés. Le moteur de documents embarqué et le service Python sont livrés ensemble. Cette démo ne constitue ni un déploiement municipal autorisé ni une certification RGPD.

## Contrat de données et d'accès

| Profil | Base dans le volume | Tenant | Contrôle vérifié |
| --- | --- | --- | --- |
| Nouvelle démo 0.4.0 | `/data/public-demo.sqlite3` | `public-demo-travaux` | Session et projets accessibles sans cookie ni mot de passe ; import EML refusé par HTTP403 |
| Anciennes releases 0.2/0.3 | `/data/travaux.sqlite3` | `staging-travaux-fictif` | Authentification privée avec cookie Secure/HttpOnly/SameSite |

La nouvelle démo utilise un autre fichier SQLite dans le volume existant. Elle ne rebaptise, ne réinitialise et ne copie pas la base privée. Le marqueur applicatif public refuse une base préexistante non marquée. Le manifeste d'archive contient mode, base et tenant exacts ; un contrat hybride est refusé.

Le hash de mot de passe est vide dans le Compose public. Les anciens fichiers d'accès serveur restent conservés pour un retour arrière privé ; le probe public ne les lit pas. La commande `credentials` reste réservée à l'exploitation d'une release privée, sans utilité pour la démo publique. Ne pas afficher ni partager les anciens fichiers d'accès.

## Périmètre réservé

| Ressource | Comportement |
| --- | --- |
| Répertoire | `/opt/apps/travaux-mairie`, création si absent ou marqueur de propriété exigé |
| Image | `travaux-mairie:0.4.0-<release-id>`, tag unique sans écrasement |
| Compose | Projet `travaux-mairie`, app et worker du même release, environnement et volume partagés |
| Volume | `travaux-mairie-data`, marqué pour cette app ; collision étrangère refusée |
| Réseau | App sur `caddy_net`, alias `travaux-mairie-app` ; worker sans réseau ni alias |
| Ports | 8765 interne ; aucun port publié sur l'hôte |
| Limites | App 768 MiB/0,75 CPU ; worker 256 MiB/0,25 CPU ; UID 10001, racine en lecture seule, capacités retirées |
| Caddy | Notre seul fichier `/opt/caddy/conf.d/travaux-mairie-demo-origin.caddy`, validation complète avant reload ; les routes protégée et historique sont incluses dans le contrôle d’intégrité des autres fichiers |
| SSH | Utilisateur `deploy`, clé de `owner.json`, BatchMode et StrictHostKeyChecking activés |

Aucune commande `down`, prune, suppression de volume ou intervention sur un service voisin n'est automatisée. Les erreurs SSH/Docker ne sont pas reproduites dans stdout. Les fichiers serveur d'accès restent sous répertoire 0700 et fichiers 0600 ; ils ne sont ni empaquetés ni transmis par arguments de processus.

## Archive fermée

La liste autorisée comprend Dockerfile, pyproject/lock, modules Python, fichiers statiques racine de `web`, assets construits de `native-editor/dist` et scripts d'exécution de ce dossier. Sept ressources imbriquées sont nommément autorisées et obligatoires : parseur Nodemailer et ses trois fichiers de licence/provenance dans `web/vendor`, puis modèle PyCasbin, licence et provenance dans `src/travaux/vendor/casbin_domains`. Il n'existe pas d'autorisation générique pour `web/vendor`.

Les ressources Docs/Grist/OpenGate et sources de thème natif déjà autorisées restent incluses. `.env*`, `owner.json`, secrets, clés, SQLite, logs, sourcemaps, tests web, `.venv`, caches, `.git` et `node_modules` sont exclus. Liens, traversals, doublons et membres hors manifeste sont refusés ; hashes vérifiés avant extraction. Un `.dockerignore` est généré. Archives, attestations et accès privés doivent rester hors du projet applicatif.

## Procédure opérateur

Depuis `outputs/travaux-mairie`, exécuter les recettes Python, frontend et éditeur natif réelles. `gate` enregistre ensuite une attestation opérateur liée aux hashes ; cette commande ne lance pas les tests. Toute modification livrée invalide l'attestation. Tant que des agents modifient l'application, ne pas attester son gel global.

```powershell
.\.venv\Scripts\python.exe deploy\hetzner\deploy.py plan
.\.venv\Scripts\python.exe deploy\hetzner\deploy.py preflight
```

`plan` reste local. `preflight` consulte le serveur et n'affiche que des booléens. Le DNS existe déjà pour les publications historiques : `dns-plan` est un outil de création seulement et refuse tout enregistrement au nom exact. Ne pas recréer cet enregistrement pour une mise à jour.

Après les trois recettes vertes et le gel effectif des sources :

```powershell
.\.venv\Scripts\python.exe deploy\hetzner\deploy.py gate --python-passed --frontend-passed --native-passed --out ..\..\work\travaux-gate.json
.\.venv\Scripts\python.exe deploy\hetzner\deploy.py package --gate ..\..\work\travaux-gate.json --out ..\..\work\travaux-release.tar.gz
```

Les sorties existantes sont refusées. L'archive reçoit un identifiant UTC unique, un manifeste, les empreintes de fichiers et le contrat public. Les valeurs de `owner.json` ne sont pas copiées ni affichées.

La publication relève d'une action opérateur distincte, explicitement autorisée :

```powershell
.\.venv\Scripts\python.exe deploy\hetzner\deploy.py apply --archive ..\..\work\travaux-release.tar.gz
```

`apply` revalide sources, attestation et archive, réserve un upload unique et acquiert un verrou exclusif. Il sauvegarde la base précédente en lecture seule, construit une image sans build Node serveur, contrôle Compose, démarre app+worker et attend leur santé. Le worker est contrôlé par la présence du processus exact `python -m travaux worker` ; cela ne prouve pas l'avancement de chaque tâche.

Avant activation de la route, le probe public dans l'app vérifie environnement fictif, nouvelle base/tenant, absence de cookie à l'ouverture, session anonyme, projets accessibles et capacité d'import désactivée. Il tente un import EML fictif avec les en-têtes requis et exige HTTP403. Il ne lit ni mot de passe ni fichier d'accès. Le probe privé reste utilisé lors d'un rollback vers une ancienne release protégée.

La route n'est activée qu'après ces contrôles. Caddy valide toute sa configuration et refuse un changement concurrent des autres fichiers. La recette HTTPS externe reste obligatoire après publication : certificat, proxy, consultation anonyme, refus d'import, éditeur natif et sous-assets, parcours desktop/mobile. Ne pas importer de contenu institutionnel.

## Retour arrière et schéma

```powershell
.\.venv\Scripts\python.exe deploy\hetzner\deploy.py rollback
```

Le rollback reprend l'image et le Compose précédents, puis leur probe. Les manifestes historiques 0.2/0.3 sans champ `runtime` sont reconnus comme staging privé : le retour utilise `/data/travaux.sqlite3` et son accès privé. La base publique distincte reste conservée. Aucune base n'est automatiquement restaurée ou effacée.

La sauvegarde cohérente pré-mise à jour utilise la base de la release précédente et SQLite `mode=ro` ; un fichier absent ne doit pas être créé silencieusement. Les modifications de `repository.py`, `workspace.py`, `auth.py`, `jobs.py` ou `governance.py` bloquent les mises à jour sur une même base en attendant une procédure de migration. La seule exception encodée est la transition exacte de la base staging privée vers le nouveau fichier public séparé.

Le 17 novembre, une [revue additive bornée](../../docs/publication-hetzner/REVUE_MIGRATION_PUBLIQUE_2026-11-17.md) autorise également une seule paire d’empreintes backend depuis `20261116T102001Z-234aeb`, exclusivement sur le contrat public inchangé. Les 44 tables existantes et leurs données ont été vérifiées identiques au démarrage et au retour à l’ancien backend ; 14 tables sont ajoutées. `reviewed_public_schema_upgrade` fige tous les fichiers backend, Dockerfile et dépendances. Un autre baseline, un contrat privé ou la moindre autre modification backend restent refusés. La sauvegarde avant construction et les probes avant bascule restent obligatoires ; aucun argument de forçage n’est ajouté.

Après échec, les compensations de route et services sont tentées séparément ; leur résultat sans secret est conservé dans `last-failure.json`. Releases, images, volumes et DNS ne sont jamais purgés automatiquement.

## Vérifications locales

```powershell
.\.venv\Scripts\python.exe -m pytest deploy\hetzner\tests -q
.\.venv\Scripts\python.exe -m py_compile deploy\hetzner\common.py deploy\hetzner\deploy.py deploy\hetzner\remote.py
uv --system-certs lock --check
```

Les tests couvrent archive fermée, ressources de licence/provenance, runtime public, refus d'une archive rebaptisant la base privée, probe public réel via FastAPI TestClient, sélection du probe privé/public, sauvegarde de la bonne base et maintien du garde de schéma. Ils ne remplacent ni Docker/Linux, ni scan d'image, ni recette HTTPS. Les quotas déclarés devront être inspectés après le démarrage réel.
