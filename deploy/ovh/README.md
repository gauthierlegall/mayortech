# Candidat OVH privé, mono-hôte

Ce dossier câble l’application et le worker avec leur profil OIDC et leurs modèles séparés, derrière un Caddy installé sur l’hôte. **Configuration validée statiquement seulement : aucune image construite ou récupérée, aucun daemon démarré, aucun déploiement effectué.** Le domaine, le digest et les chemins des exemples sont à remplacer. Les comptes, le certificat, les secrets, la sauvegarde chiffrée et les autorisations DSI ne sont pas provisionnés par ces fichiers.

## Fichiers et frontières

- `compose.yaml` : deux processus UID/GID `10001:10001`, racine en lecture seule, aucune capability, interdiction d’élévation de privilèges, temporaires bornés, limites mémoire/CPU/PID, redémarrage et arrêt avec délai.
- `compose.env.example` : paramètres de contrôle Compose, sans secret ; image approuvée avec digest et chemins absolus hors dépôt.
- Le profil privé de l’application est un autre fichier : copier [ovh-prive.env.example](../../docs/env/ovh-prive.env.example) vers un emplacement protégé hors dépôt, puis le compléter. Son `env_file` est partagé par app/worker avec `format: raw`, sans interpolation des valeurs, y compris `$` et les quotes, selon la [spécification Docker](https://docs.docker.com/reference/compose-file/services/#format). Ne pas ajouter de quotes autour des valeurs dans ce format.
- Le répertoire de données est monté sur `/data`. La clé du coffre est un fichier séparé monté en lecture seule sur `/run/secrets/connector-vault.keys`. Ces deux chemins internes et `auth_mode=oidc` sont imposés par Compose ; les chemins hôte écrits dans l’exemple applicatif sont remplacés pour ces conteneurs. Les deux anciennes sources de clé et le mot de passe partagé sont désactivés.
- `Caddyfile` : configuration pour le Caddy **de l’hôte**, qui termine HTTPS et relaie vers `127.0.0.1:8765` en conservant le Host. Aucune publication du worker ni du port applicatif sur une interface publique. Aucun access log n’est activé. Le journal runtime retire les objets `request`/`resp_headers` et les champs URI/URL pour limiter la présence de codes/cookies dans les erreurs de callback, avec le [filtre officiel Caddy](https://caddyserver.com/docs/caddyfile/directives/log#filter) appliqué au [journal global](https://caddyserver.com/docs/caddyfile/options#log). L’absence de contenu sensible doit encore être vérifiée en recette sur les logs réellement collectés.

Les secrets OIDC, IA et OAuth sont lus depuis l’environnement du processus, donc visibles aux administrateurs Docker autorisés. Le fichier d’environnement n’est pas une enclave de secrets. Il n’est ni monté dans `/data`, ni copié dans l’image. La clé de coffre est indispensable en plus de ce fichier ; ne pas stocker l’un ou l’autre dans le volume DB, le contexte de build ou un dépôt de sources.

## Prérequis persistants de l’hôte

1. Hôte Linux OVH et offre/région validés avec la DSI ; Docker Engine et Compose prenant en charge `env_file.format: raw` et les bind mounts longs. Le rendu a été vérifié avec Compose 5.7.0. Le réseau, le disque et les sauvegardes doivent être dimensionnés : ces limites de conteneur ne constituent pas une preuve de capacité.
2. Image applicative approuvée, construite depuis le [Dockerfile](../../Dockerfile), analysée et disponible localement avec une référence `@sha256:...`. `pull_policy: never` empêche une récupération implicite au démarrage. Avant sa construction, compiler le frontend, exécuter `scripts/package_frontend.py` et construire `native-editor/dist`, avec les tests du paquet final. Les outils de build et le code applicatif ne sont pas exécutés par ce candidat de validation.
3. Préparer un **nouveau** répertoire de données local, sans lien symbolique, possédé par UID/GID `10001:10001`, mode `0700`. Exemple de chemin : `/srv/travaux/private-data`. Ne pas réutiliser la DB publique/test, un partage réseau ou un autre déploiement. Le bind refuse de créer ce chemin implicitement.
4. Préparer `/etc/travaux/private.env` avec les seuls paramètres nécessaires, accès `0600` et répertoire restreint à l’exploitant. Remplir OIDC/inscription/MFA et les deux modèles ; les approbations de sortie restent fausses jusqu’à validation institutionnelle. Compose ne remplit ni secrets, ni issuer, ni contrat fournisseur.
5. Provisionner indépendamment une ou plusieurs clés Fernet valides dans `/etc/travaux/secrets/connector-vault.keys`, fichier régulier sans lien, mode `0600`, lisible par UID `10001`. Elles sont séparées du répertoire DB et absentes de la source. Prévoir conservation indépendante et rotation ; ne jamais remplacer une clé dont des données chiffrées dépendent sans procédure de ré-encryptage.
6. Compléter le fichier de contrôle `/etc/travaux/compose.env` à partir de `compose.env.example`. L’opérateur doit vérifier que DB, clé et profil restent à des chemins distincts, et que les fichiers sont présents. Le test synthétique ne vérifie pas les permissions d’un futur serveur.
7. Installer et superviser Caddy sur l’hôte ; configurer `TRAVAUX_PUBLIC_HOST` dans **l’environnement de son propre service**, égal au hostname de `TRAVAUX_PUBLIC_ORIGIN` et inclus dans `TRAVAUX_ALLOWED_HOSTS`. `compose.env` n’est pas chargé par Caddy. Fournir DNS public exact, chaîne de confiance HTTPS et accès ACME adaptés ; réserver `80/443` au proxy. Le fichier fourni désactive son API d’administration ; le mode de rechargement doit en tenir compte. Aucun HTTPS local ou fournisseur réel n’a été recetté ici.
8. Filtrer administration et sorties au niveau de l’hôte/réseau. Le bridge Compose autorise les sorties nécessaires à OIDC/IA/mail ; il ne les limite pas par nom de domaine. Les allowlists applicatives sont complémentaires. Contrôler aussi les logs d’erreur du proxy et de la supervision, et l’absence de diagnostics TLS.

## Validation avant lancement

Les commandes suivantes sont des instructions opérateur ; elles n’ont pas été exécutées avec une configuration réelle :

```sh
docker compose --project-name travaux-prive --env-file /etc/travaux/compose.env -f deploy/ovh/compose.yaml config --quiet
```

Ne pas publier `docker compose config` sans `--quiet` avec les vrais fichiers : son rendu contient les secrets injectés par `env_file`. Les paramètres de contrôle doivent venir du fichier explicite, sans variables shell `TRAVAUX_*` concurrentes. Vérifier aussi le profil `Settings`, la clé, les chemins, les permissions et la configuration Caddy avec l’outil de validation de sa version installée avant tout démarrage.

Après validation DSI et configuration complète seulement, l’opérateur peut lancer le candidat avec les mêmes arguments et `up -d`. Choisir un nom de projet Compose distinct pour chaque instance ; conserver une seule app et un seul worker sur cette base. Le port hôte `8765` est fixe : deux instances sur le même serveur exigent un override de port et une route Caddy distincts, non fournis ici. Le candidat ne lance pas Caddy, l’IdP, le SMTP ou un collecteur EWS séparé.

Le contrôle app appelle uniquement `/health/live` sur loopback avec le Host autorisé. Le contrôle worker vérifie le processus et la lecture de la table de jobs ; **il ne prouve ni progression de la file ni fonctionnement d’un fournisseur**. Prévoir supervision des tâches en erreur, ancienneté de la file, disque, redémarrages et alertes. Compose ne redémarre pas automatiquement un processus devenu seulement `unhealthy` ; la politique `restart` concerne sa sortie.

Avant mise à jour, conserver image/digest précédents et sauvegarde SQLite cohérente vérifiée avec les clés nécessaires ; arrêter les écritures et tester la restauration vers une nouvelle cible pour revenir en arrière. Ne pas utiliser `down -v` comme procédure de reprise. Le [module restic](../../docs/SAUVEGARDE_PRO_RESTIC_2026.md) reste prévu, non implémenté.

## Preuve du candidat

`python deploy/ovh/test_candidate.py -q` effectue deux tests : présence des fichiers/proxy et rendu Compose JSON dans un répertoire temporaire, avec des fichiers synthétiques sans secrets. Le test vérifie le passage de **toutes** les variables du profil privé aux deux services, l’absence d’interpolation du secret fictif, les limites, les montages, la clé en lecture seule, les ports et les healthchecks. Le rendu `config` ré-échappe lui-même les dollars en `$$` ; le test tient compte de cette représentation, confirmée dans le [code de Compose](https://github.com/docker/compose/blob/main/cmd/compose/config.go). Il ne construit aucune image, ne lance aucun conteneur et ne contacte aucun daemon. En l’absence de CLI Docker, le test de rendu est déclaré ignoré, jamais présenté comme réussi.

La CLI Caddy n’est pas disponible sur ce poste : son adaptation/validation n’a pas été exécutée ; le test vérifie seulement les frontières et filtres présents dans son fichier. Les validations réseau/TLS, permissions de l’hôte, migrations sur données sauvegardées, OIDC/MFA, boîte pilote et restauration restent à exécuter sur la cible autorisée. La [notice de mise en service](../../docs/MISE_EN_SERVICE_PRIVEE_2026.md) décrit les décisions et recettes restantes sans certification RGPD ou cybersécurité.
