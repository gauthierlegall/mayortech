# Intégrations et qualification des instances

> **Architecture documentaire mise à jour le 14 novembre 2026.** Le moteur courant est AFFiNE/BlockSuite embarqué dans Travaux, avec notre API de pages, la même session et la même navigation : voir le [guide natif](../native-editor/README.md), le [design actuel](design.md) et le [registre de réutilisation](REUTILISATION_CODE.md). Les sections AppFlowy ci-dessous sont **historiques et remplacées pour le pilote actuel** ; leurs adaptateurs conservés ne sont pas le moteur actuel ni une installation requise. Les sections EML et Exchange décrivent toujours des composants du projet, sans prouver une connexion à un serveur institutionnel réel.

Le logiciel utilise ses données fictives sans compte externe. Les adaptateurs réels sont explicites : une instance accessible, un compte autorisé et une capacité prouvée sont nécessaires. Les tests locaux ne prouvent aucune connexion à la mairie.

## AppFlowy natif : preuves disponibles

Le [guide OpenAPI officiel](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial/blob/e39869a2bae964e951832e577407e35a548b48c8/docs/OPENAPI.md) établit `/api/docs/openapi.json`, l’authentification par jeton utilisateur GoTrue, l’enveloppe `code:0` et la création de page par `POST /api/workspace/{workspace_id}/page-view`. Son exemple ne prouve pas un corps Markdown sur cette route. L’adaptateur REST n’invente donc ni champ Markdown, ni append, ni `If-Match`.

Une voie d’écriture Markdown native est effectivement documentée : le [catalogue MCP exporté par AppFlowy](https://github.com/AppFlowy-IO/appflowy-ai-plugins/blob/318a8c81cab86418fa3e71cc8e03b7cb874378a6/catalog/tools.json). `create-pages` accepte un document avec `content` Markdown ; `fetch` peut retourner `body_format:markdown`. Le [README officiel](https://github.com/AppFlowy-IO/appflowy-ai-plugins/blob/318a8c81cab86418fa3e71cc8e03b7cb874378a6/README.md) indique une licence self-host One, Team ou Enterprise et une connexion OAuth limitée au workspace. Cela ne fait pas partie de l’offre gratuite. Le serveur MCP reste dans le périmètre choisi ; aucun accès Claude/ChatGPT n’est requis par notre application. Le client applicatif doit exposer uniquement les opérations nécessaires au service, jamais au LLM.

`replace-document-content` propose un `expected_version` mais sa propre description précise que ce jeton ne détecte pas toutes les modifications intermédiaires. Nous conservons donc la publication en nouvelle page/version et ne revendiquons pas une mutation conditionnelle atomique des notes humaines.

## Préflight REST exécutable, en lecture seule

Depuis la racine du projet, avec l’environnement installé :

```powershell
.venv/Scripts/python.exe scripts/appflowy-preflight.py --help
.venv/Scripts/python.exe scripts/appflowy-preflight.py --base-url http://localhost:18080 --tenant-id IDENTIFIANT_TENANT --workspace-id IDENTIFIANT_WORKSPACE --output-dir data/preflight-001
```

L’URL vient de l’opérateur ; HTTPS est obligatoire hors boucle locale. Si une authentification est requise pour la documentation, injecter le jeton dans `APPFLOWY_ACCESS_TOKEN` par le gestionnaire de secrets local ; il n’est jamais un argument. `--ca-file` ajoute une CA de confiance en conservant la validation TLS. `--openapi-file chemin.json` analyse une copie sans réseau.

Résultats : OpenAPI de l’installation, SHA-256 de son JSON canonique UTF-8, version API, opérations pertinentes avec schémas/références et `appflowy-manifest.unapproved.json`. Ce dernier garde `read_object:null`, `create_version:null`, `content_roundtrip_verified:false`. Aucun POST n’est envoyé. Choisir un nouveau dossier à chaque qualification ; les preuves existantes ne sont pas écrasées.

Pour qualifier REST : relever les routes/méthodes/operationId exacts dans ce document, associer champs natifs et chemins de réponse, prouver création et relecture sur données fictives, conserver captures/résultats et compléter un manifeste approuvé séparé. Son `openapi_sha256` et son `api_version` doivent correspondre au schéma fourni. Les fichiers `tests/test_integrations.py` utilisent exclusivement des routes nommées `synthetic-pages` : ce sont des fixtures, pas des endpoints AppFlowy.

`AppFlowyHTTPAdapter` rejette un contrat absent/incohérent, une route non déclarée, une référence de schéma externe, un payload invalide, un autre tenant, une redirection ou un ID contenant une traversée de chemin. Il valide l’enveloppe métier et le schéma de réponse. Le support actuel de création REST exige un champ Markdown chaîne prouvé et une relecture identique ; aucun codec richtext interne n’est prétendu.

## Publication et résultat ambigu

`PublicationRequest` contient tenant, ID de publication, parent, titre, contenu et son hash. `SQLitePublicationLedger` réserve cet ID durablement **avant** l’appel réseau. Le succès est `published` seulement après création et relecture. Timeout, panne après envoi, réponse invalide ou échec de relecture donnent `uncertain` ; une nouvelle invocation avec le même ID ne crée pas une seconde page, même après redémarrage. Un même ID avec un contenu différent est refusé.

Le ledger ne se débloque pas automatiquement. Rechercher la page distante, comparer contenu/ID et consigner une réconciliation explicite avant de décider d’une nouvelle publication. Ne pas effacer le ledger pour « réparer » un timeout. Les notes humaines ne sont jamais écrasées par cet adaptateur. Le fake est en mémoire, porte `mode:fake` et ne simule ni les droits natifs ni un serveur persistant.

## EML et pièces jointes

`parse_eml(raw)` extrait sujet, adresses, date déclarée, corps texte, pièces et empreintes. `thread_id` reprend le premier Message-ID de References, sinon In-Reply-To, sinon celui du message courant. Une référence malformée reste inconnue avec avertissement et demande une revue ; cet indice de fil n’authentifie ni expéditeur ni droit de rattachement. Le HTML est converti en texte sans navigateur ni téléchargement distant. Une pièce/EML transféré ne devient pas le corps du parent. Les noms de fichiers sont nettoyés mais ne servent jamais de chemins d’écriture. Limites : MIME 10 Mo, 100 parties, profondeur 20, pièce 5 Mo, corps 250 000 caractères par défaut. Le parseur n’ouvre ni archive, ni PDF, ni macro ; extraction/antivirus relèvent des composants dédiés. Une date sans fuseau reste inconnue ; le champ `received_at` représente le header Date, pas une preuve d’acheminement Exchange.

## Exchange local/prestataire : flux incrémental durable

Le [SDK exchangelib](https://ecederstrand.github.io/exchangelib/) documente un endpoint explicite, `autodiscover=False`, `DELEGATE`, lecture MIME et synchronisation EWS. Les constructeurs et services ont aussi été inspectés dans le SDK **5.6.0 installé**. `EWSSettings.enabled` vaut faux par défaut ; HTTPS et dossiers explicites sont requis. Le code ne fournit aucune opération d’envoi, suppression ou marquage lu. Cela ne réduit pas les droits réels du compte : la DSI doit les borner au serveur. NTLM/GSSAPI/SSPI sont configurables selon prérequis SDK ; OAuth ADFS local n’est pas implémenté ni présumé compatible.

```python
reader = EWSReadOnlyCollector.connect(settings, username=operator_username, password=operator_secret)
source = ExchangelibChangeSource(reader)
collector = EWSIncrementalCollector(
    tenant_id=tenant_id, connection_id=connection_id, settings=settings,
    source=source, checkpoints=SQLiteSyncCheckpointStore("data/ews-checkpoints.sqlite"),
)
report = collector.collect_once(folder_id, sink=persist_source_and_outbox)
```

Le callback reçoit `MailSyncEvent`, persiste source/alias/déduplication et outbox d’extraction dans la même transaction métier, puis retourne `DurableReceipt(event.idempotency_key, True)`. Le curseur n’avance qu’après tous ces ACK. Un crash avant checkpoint rejoue les mêmes clés ; le sink doit accepter un événement déjà durable sans réémettre son effet. Le stockage des checkpoints applique un contrôle de révision contre les collecteurs concurrents et lie le curseur au tenant, connexion, endpoint, boîte et dossier.

Une page EWS lit au plus cinq changements avec `SyncFolderItems.call(shape="IdOnly", sync_scope="NormalItems")`, puis récupère les MIME nécessaires. `read_flag_change` est ignoré avec progression du curseur. Suppression ou accès retiré produisent une métadonnée `review_required`, jamais une purge des archives. Un curseur invalide demande une réconciliation, il n’est pas remis silencieusement à zéro. `read_folder_snapshot` reste disponible pour diagnostic ; il ne remplace pas cette synchronisation incrémentale. [Services et types du SDK](https://ecederstrand.github.io/exchangelib/exchangelib/services/sync_folder_items.html)

Le serveur Exchange n’est pas ouvert sur Internet pour ce code : exécuter le collecteur dans son réseau autorisé et transporter ses événements vers le service. L’authentification, l’état de support Exchange, le TLS interne, les droits dossier et les limites serveur demandent une recette avec la DSI. Aucun test de connexion réelle n’a été exécuté ici.

## Espace AppFlowy à préparer

Voir `deploy/appflowy/README.md` : dépôt upstream épinglé, lancement local à qualifier, modèles Markdown et cinq bases natives avec CSV fictifs. Ce sont des supports d’installation/configuration du vrai clone, pas une imitation de son interface dans notre application.
