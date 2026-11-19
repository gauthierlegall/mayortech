# AppFlowy natif : installation et espace de démonstration

> **Historique — remplacé le 14 novembre 2026.** Ce plan AppFlowy n’est plus le parcours d’installation du pilote actuel. Travaux embarque désormais le moteur AFFiNE/BlockSuite dans la même application et la même session, sans second service documentaire à ouvrir. Voir le [README actuel](../../README.md), le [guide du moteur natif](../../native-editor/README.md) et le [registre de réutilisation](../../docs/REUTILISATION_CODE.md). Les commandes et modèles ci-dessous sont conservés comme étude antérieure ; ils ne décrivent pas un service AppFlowy installé ni une étape requise du staging.

Le serveur AppFlowy n’a pas été installé : Docker est absent de l’environnement utilisé. Les sources officielles ont été vérifiées et épinglées dans `upstream.lock.json`. Aucun compte mairie ni licence commerciale n’a été accepté par cette préparation.

## Déployer la distribution officielle en environnement fictif

Prérequis : Git, Docker et **Compose 2.30 ou supérieur**, capacité machine suivant le [dimensionnement officiel](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial/blob/e39869a2bae964e951832e577407e35a548b48c8/docs/HARDWARE_SIZING.md). La [procédure upstream](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial/blob/e39869a2bae964e951832e577407e35a548b48c8/docs/docker-compose.md) utilise le `deploy.env` du même commit et `docker compose up -d`. Conserver le jeu de services compatible du dépôt ; ne pas choisir des versions indépendantes.

Depuis la racine du projet, dans PowerShell :

```powershell
$TravauxRoot = (Get-Location).Path
$AppFlowyUpstream = Join-Path $TravauxRoot '.local/appflowy-upstream'
if (Test-Path -LiteralPath $AppFlowyUpstream) { throw 'Choisir un dossier neuf ; ne pas écraser une installation.' }
git init $AppFlowyUpstream
git -C $AppFlowyUpstream remote add origin https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial.git
git -C $AppFlowyUpstream fetch --depth 1 origin e39869a2bae964e951832e577407e35a548b48c8
git -C $AppFlowyUpstream checkout --detach FETCH_HEAD
git -C $AppFlowyUpstream rev-parse HEAD
Copy-Item -LiteralPath (Join-Path $AppFlowyUpstream 'deploy.env') -Destination (Join-Path $AppFlowyUpstream '.env')
```

Lire l’accord livré par upstream avant utilisation. Configurer **localement**, hors chat et Git, les secrets de `deploy.env` : remplacer tous les exemples de mots de passe, secrets JWT et compte administrateur. Régler les variables de domaine/schéma pour `http://localhost:18080` selon les commentaires du même template ; désactiver les fournisseurs IA et OAuth externes non utilisés. Ne pas conserver une valeur exemple pour ouvrir le service. Le certificat de développement upstream n’est pas un certificat de production.

Le complément `compose.local.yaml` remplace les ports Nginx par des publications sur boucle locale ; il ne change aucun code commercial. Docker documente [la fusion `!override`](https://docs.docker.com/reference/compose-file/merge/) depuis Compose 2.24.4. Vérifier la configuration effective sans imprimer le contenu des secrets :

```powershell
Set-Location -LiteralPath $AppFlowyUpstream
$LocalOverride = Join-Path $TravauxRoot 'deploy/appflowy/compose.local.yaml'
docker compose -f docker-compose.yml -f $LocalOverride config --quiet
docker compose -f docker-compose.yml -f $LocalOverride config --services
docker compose -f docker-compose.yml -f $LocalOverride pull
docker compose -f docker-compose.yml -f $LocalOverride up -d
docker compose -f docker-compose.yml -f $LocalOverride ps
```

Ces commandes de mise en route ne sont pas déclarées exécutées ou validées ici. Ne pas employer `down -v` sur une installation existante. Relever ensuite les digests effectivement tirés et compléter la preuve d’installation. En local, ouvrir `http://localhost:18080`, créer un workspace fictif et vérifier les pages/blocs/bases natives. La qualification OVH et les sauvegardes sont un déploiement distinct.

Pour MCP Markdown, vérifier la licence One/Team/Enterprise, l’activation et le service MCP officiel : le Compose de base ne prouve pas sa présence. Suivre les [instructions upstream de la version](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial/blob/e39869a2bae964e951832e577407e35a548b48c8/README.md) et l’URL affichée dans Settings → MCP. Un compte gratuit n’autorise pas cette connexion.

## Configurer cinq bases natives

Créer un espace privé « Travaux — Val-des-Ajoncs (fictif) ». Importer les cinq CSV de `templates/` par l’interface native de la version, ou créer leurs colonnes manuellement. Les CSV sont des **échafaudages de données fictives**, pas un schéma d’API ni un export Notion. Leur import ne crée pas automatiquement les relations, utilisateurs, règles d’accès ou vues ; qualifier ces étapes dans l’instance.

| Base / fichier | Propriétés à configurer dans l’UI native | Vues de travail proposées |
|---|---|---|
| Chantiers / `chantiers.csv` | Chantier (titre), Référence (texte unique par convention), Statut (choix), Adresse (texte), Échéance (date), Responsable (personne), Entreprise (texte), Actions (relation), Sources (relation) | **Liste/cartes** par responsable sur mobile ; Kanban par statut si utile ; tableau secondaire |
| Sources / `sources.csv` | Source (titre), Référence (texte), Nature (choix), Date déclarée (date), Chantier (relation), État accès (choix), Empreinte (texte), Référence preuve (texte) | **Liste** « Sources du chantier » et « Accès à revoir », ouverture en fiche |
| Évolutions à vérifier / `evolutions.csv` | Évolution (titre), Référence (texte), Chantier (relation), Champ (texte), Valeur avant/après (texte), Source (relation), Version source (texte), Révision chantier (nombre), État proposition (choix), Action revue (lien vers le service) | **Cartes/liste « À vérifier »** : avant/après, extrait source, incertitude et action de revue ; tableau de diagnostic secondaire |
| Actions / `actions.csv` | Action (titre), Référence (texte), Chantier (relation), Échéance (date), Pilote (personne), Statut (choix), Validation (choix), Sources (relation) | **Liste « Cette semaine »**, « À valider » ; Kanban facultatif sur grand écran |
| Récapitulatifs / `recapitulatifs.csv` | Récapitulatif (titre), Référence (texte), Chantier (relation), Version (nombre), Statut (choix), Arrêté au (date), Empreinte (texte), Page précédente (relation) | **Cartes/liste** des brouillons, versions validées et versions périmées |

Remplacer les colonnes de liaison textuelles des CSV par les relations natives vers les lignes créées. L’entreprise reste une propriété texte du chantier, sans sixième base. Les cinq bases canoniques sont Chantiers, Sources, Évolutions à vérifier, Actions et Récapitulatifs. Choisir les vues liste/cartes disponibles dans la version pour les usages quotidiens et mobiles ; ne pas imposer un grand tableur comme accueil.

Une propriété « Validation » ou « État proposition » modifiable n’est pas une décision authentifiée. La carte d’évolution montre le champ, les valeurs avant/après, la preuve et sa version, la révision chantier attendue, puis le lien vers la revue humaine du service. Seule cette commande authentifiée et auditée peut accepter/rejeter/corriger la proposition et contrôler sa révision ; une modification libre dans AppFlowy ne l’approuve pas. Un filtre de vue n’est pas une permission.

Importer/copier `accueil.md`, `chantier.md` et `recapitulatif.md` en pages natives ; remplacer les liens indiqués par de vraies pages/vues AppFlowy. Préserver « Notes de l’agent » comme contenu humain. Chaque récapitulatif généré est une nouvelle page reliée ; il ne remplace pas les notes ou une version déjà validée.

Recette : ouvrir la ligne chantier comme page, modifier une note native, relier deux actions, ouvrir les preuves, vérifier l’accès par un second compte de test, puis créer et relire une version publiée par le connecteur qualifié. Capturer l’interface réellement exécutée ; les templates ne prouvent pas que cette recette a réussi.
