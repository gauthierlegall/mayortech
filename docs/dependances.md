# Dépendances : audit versionné du 14 novembre 2026

Pour la composition applicative **0.8.1**, voir l'[inventaire vérifié du 16 novembre](audit-solutions-libres-2026-11-16.md). Les contrôles de dépendances ci-dessous restent datés de leur exécution ; leurs paragraphes historiques sur les anciens fronts ne décrivent pas le frontend React actuel. Aucun nouveau balayage de vulnérabilités n'est revendiqué par cet inventaire.

La refonte0.3 conserve les mêmes versions de dépendances. Le contrôle PyPI a été rejoué après publication :63distributions interrogées, aucun avis connu trouvé dans [le résultat](audit/pip-audit-native-release.json). Le contrôle npm et son avis Zod avec mitigation locale restent documentés ci-dessous. Les nouvelles commandes natives et le parcours public possèdent leurs [preuves0.3](ux-refonte-2026/public/rapport.md).

## Mise à jour : éditeur AFFiNE intégré, version 0.2.0

Le nouvel audit PyPI de l'environnement installé, après ajout de `markdown-it-py 4.3.0` et `mdurl 0.1.2`, est dans [pip-audit-native-release.json](audit/pip-audit-native-release.json). Il ne trouve aucun avis connu aux versions interrogées. Le projet éditable est exclu explicitement. Le détail ci-dessous décrit l'état antérieur et n'est plus un inventaire exhaustif de la version 0.2.0.

Le front embarque désormais réellement les packages AFFiNE/BlockSuite 0.22.4 et Yjs ; il possède un manifeste npm et un lock. Les notices et sources MPL du thème sont distribuées dans `native-editor/dist/`. Voir [réutilisation effective](REUTILISATION_CODE.md), [licences natives](../native-editor/REUSE.md) et [correctif local Zod](../native-editor/patches/README.md).

L'audit npm conserve un avis racine sur Zod 3, propagé aux packages qui en dépendent. Un backport borné et vérifié par empreinte évite de parcourir les collections trop grandes avant leur rejet ; npm continue de signaler la version. Aucun résultat « zéro vulnérabilité » n'est revendiqué pour le moteur natif. Les [preuves npm](audit/native-editor/npm-audit.json) et la [recette client avec transport contrôlé](audit/native-editor/native-client-proof.json) sont conservées ; la recette intégrée utilise ensuite le vrai backend.

La roue 0.2.0 a été construite et l'export HTML exécuté depuis son contenu. L'archive de déploiement conserve les ressources Docs/Grist et les fichiers de thème MPL ; un test protège ce point. Docker Desktop est installé localement mais son moteur WSL n'est pas disponible. L'exécution conteneur de cette livraison est vérifiée séparément sur Hetzner et consignée dans le rapport de publication.

## État historique avant l'intégration native

Deux contrôles réels ont été exécutés, sans modification de `pyproject.toml` ni `uv.lock` :

- **pip-audit 2.10.1**, service PyPI : 61 distributions installées analysées, aucun avis connu trouvé ; le projet local editable est explicitement exclu. [Résultat JSON](audit/pip-audit-installed.json)
- **Collecteur supply-chain** du skill [Trail of Bits](https://github.com/trailofbits/skills/tree/e4dd0bb5b15535f7c5a0834187dffba6ac37e4ff/plugins/supply-chain-risk-auditor) : 12 dépendances directes et 50 transitives du lock vérifiées au registre, aucun avis connu aux versions résolues ; 43 requêtes sources, 12 réponses de cache, 0 erreur. [Rapport complet](audit/supply-chain-report.md), [mesures JSON](audit/supply-chain-findings.json)

Le lock comporte 63 entrées, projet compris. L’environnement contient le projet et 61 distributions ; toutes leurs versions correspondent au lock. `httpx2-jsfetch==1.0`, variante de plateforme non installée ici, est couverte par le balayage du lock. Les empreintes exactes des deux fichiers et du collecteur figurent dans [audit-snapshot.json](audit/audit-snapshot.json). Aucun correctif de version n’a été nécessaire selon ces bases au moment du contrôle.

Ce résultat couvre les avis connus interrogés, sans établir l’absence de défaut dans le code du pilote. Les images, bibliothèques natives, navigateurs téléchargés et poids de modèles ne sont pas couverts par l’audit PyPI.

## Versions directes et licences observées

Les métadonnées et notices des distributions réellement installées ont été lues ; les notices directes sont conservées dans `docs/audit/licenses/`. [Inventaire direct avec fichiers source de licence](audit/direct-licenses.json)

| Dépendance | Version verrouillée | Licence observée | Périmètre |
|---|---|---|---|
| FastAPI | 0.133.1 | MIT | Base |
| Uvicorn | 0.41.0 | BSD-3-Clause | Base |
| Pydantic | 2.13.4 | MIT | Base |
| HTTPX | 0.28.1 | BSD-3-Clause | Base |
| jsonschema | 4.26.0 | MIT | Base |
| exchangelib | 5.6.0 | BSD-2-Clause | Extra Exchange |
| pypdf | 6.21.4 | BSD-3-Clause | Extra documents |
| python-docx | 1.2.0 | MIT | Extra documents |
| MCP SDK | 2.3.0 | MIT | Extra AppFlowy |
| pytest | 9.1.1 | MIT | Développement |
| Ruff | 0.17.5 | MIT | Développement |
| Playwright Python | 1.65.2 | Apache-2.0 | Développement |

Le package `mcp` correspond au dépôt officiel `modelcontextprotocol/python-sdk`, vérifié par ses métadonnées et par son [projet au tag v2.3.0](https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/pyproject.toml) ; sa [licence MIT versionnée](https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/LICENSE) est conservée. Le SDK constitue le transport protocolaire ; il ne transforme pas automatiquement tous les outils du serveur en capacités du LLM. Notre client restreint les appels applicatifs et vérifie les schémas attendus.

L’[inventaire transitif des métadonnées de licence](audit/all-installed-license-metadata.json) relève notamment `certifi` sous MPL-2.0 et `cryptography` sous `Apache-2.0 OR BSD-3-Clause`. Conserver leurs notices et examiner les obligations lors d’une modification ou redistribution. Les métadonnées parfois incomplètes, les composants natifs inclus dans les wheels et les licences de modèles exigent une revue de distribution séparée ; ce fichier ne les classe pas arbitrairement comme permissifs.

Le collecteur a évalué les 12 dépôts directs comme non archivés et leurs versions comme non retirées. Il ne peut pas établir les ACL de publication PyPI, la provenance de publication ni l’exécution à l’installation, chacune non évaluable pour 12/12. Les scores CI ne couvrent pas tous les dépôts. Ces lacunes restent visibles dans le rapport ; elles ne deviennent pas un verdict « sûr ». GitHub authentifié n’était pas disponible ; aucune réauthentification n’a été tentée.

## AppFlowy : distribution séparée et droits distincts

Le [client AppFlowy](https://github.com/AppFlowy-IO/AppFlowy/blob/main/LICENSE) est AGPL-3.0 ; cela ne rend pas libre le serveur commercial actuel. Le serveur retenu est la distribution officielle épinglée au commit `e39869a2bae964e951832e577407e35a548b48c8`. Son [accord](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial/blob/e39869a2bae964e951832e577407e35a548b48c8/SELF_HOST_LICENSE_AGREEMENT.md) réserve l’usage interne et interdit notamment revente et client personnalisé sous la licence standard. Un futur SaaS/OEM nécessite un accord distinct. Aucun fork du serveur ni client modifié n’est livré.

Le catalogue MCP officiel est référencé au commit `318a8c81cab86418fa3e71cc8e03b7cb874378a6` ; le projet [appflowy-ai-plugins](https://github.com/AppFlowy-IO/appflowy-ai-plugins/blob/318a8c81cab86418fa3e71cc8e03b7cb874378a6/README.md) annonce AGPL-3.0 et une licence One/Team/Enterprise pour MCP self-host. Le pilote n’embarque ni les plugins, ni leur code : les noms/champs de protocole et empreintes de schémas servent de contrat d’interopérabilité. Les templates de workspace sont originaux. Le code des dépendances reste dans l’environnement installé ; aucun arbre upstream ou skill Claude/Codex n’a été copié dans les sources applicatives.

La revue des sources du front a trouvé des imports relatifs et les modules de test Node natifs ; aucun manifeste npm, import CDN ni bibliothèque JavaScript externe n’est livré dans ce front. Les instructions de skills sont des aides de développement inspectées, pas des dépendances exécutables du produit ni une autorisation d’exécuter du contenu provenant d’un courrier.

## Actions CI : SHA officiels et Node24

Les sources `action.yml` et README ont été consultées aux commits suivants. Le workflow est épinglé et le checkout ne conserve pas les identifiants Git. [Mesures](audit/github-actions-pins.json)

| Action | Version | SHA |
|---|---|---|
| [actions/checkout](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1) | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| [actions/setup-node](https://github.com/actions/setup-node/tree/949feb2413d6458794dcd2491c4babbbce0c15c1) | v7.1.0 | `949feb2413d6458794dcd2491c4babbbce0c15c1` |
| [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv/tree/68559e99cc807c1eb7e9238fd43a15bba460eec2) | v10.3.3 | `68559e99cc807c1eb7e9238fd43a15bba460eec2` |

Ces trois actions utilisent Node24. Checkout et setup-node documentent un runner minimal 2.327.1 ; les commandes Git authentifiées depuis une action conteneur checkout exigent 2.329.0. Le workflow fourni n’a pas été exécuté sur GitHub pendant cette livraison.

## Images : métadonnées vérifiées, pas de build

Les registres publics officiels ont été interrogés sur leurs **manifestes uniquement**. Pour chaque réponse, le SHA-256 des octets reçus correspond exactement au header `Docker-Content-Digest`. Les index bruts et la liste des plateformes sont conservés dans [les preuves OCI](audit/image-manifests/image-digests.json).

| Référence | Digest d’index vérifié |
|---|---|
| `ghcr.io/astral-sh/uv:0.11.27` | `sha256:4d01caf3b22dfd11003455e2e68153da08c4ee1fa54fdbd166c6282d22693419` |
| `python:3.11.15-slim-bookworm` | `sha256:d29f48a31a8b408ed19272ca1e7b10ebae13b240a27e862d3d4217c528e2e0c3` |

Docker est absent : aucune couche n’a été tirée, aucune image construite/exécutée, aucun scan OS d’image réalisé. Les images AppFlowy restent à relever et qualifier selon le jeu de services upstream. Les poids Mistral/OCR doivent aussi être choisis et inventoriés avec leurs versions/licences avant une exploitation réelle.

## Reproduire le contrôle PyPI

```powershell
uv tool run --system-certs --isolated --from pip-audit==2.10.1 --with truststore python docs/audit/run_pip_audit.py --path .venv/Lib/site-packages --skip-editable --progress-spinner off --format json --output audit-pypi-nouveau.json
```

L’outil est isolé du projet. Le lanceur utilise le magasin de certificats système ; TLS reste vérifié. Aucune option `--fix` n’est employée. Le [comportement de pip-audit](https://github.com/pypa/pip-audit) a été vérifié : son mode `--locked` lit actuellement `pylock.*.toml`, pas directement `uv.lock`. Le balayage complet de ce lock a donc été réalisé par le collecteur dédié, en complément de l’audit de l’environnement installé.
