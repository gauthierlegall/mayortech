# Éditeur natif AFFiNE intégré à Travaux

Ce module embarque réellement le moteur de pages, blocs et bases AFFiNE/BlockSuite dans la même application et la même session que Travaux. Il n’ouvre ni un second SaaS ni une iframe. Le navigateur utilise les paquets publics `@blocksuite/*` **0.22.4**, verrouillés par `package-lock.json`. Le backend AFFiNE et ses parties Enterprise ne sont pas incorporés.

## Installation et compilation

Utiliser **Node 22** : la dépendance `@blocksuite/icons@2.2.17` annonce `>=18.19.0 <23.0.0`. Le runtime Windows22.23.5 téléchargé dans `.tools/` est isolé ; sa provenance et son SHA256 sont dans `node-runtime.lock.json`. Il ne modifie pas Node global. Linux/CI peut utiliser Node 22 sans télécharger ce ZIP Windows.

```powershell
npm ci --ignore-scripts
npm test
npm run build
```

Les scripts d’installation des packages restent désactivés. `build` applique d’abord le backport Zod vérifié par hash, compile avec Vite, puis génère les notices et les sources du thème. Le plugin officiel `@vanilla-extract/vite-plugin` est nécessaire : les paquets BlockSuite exposent des fichiers TypeScript et des styles `.css.ts`. React 18 est un peer du paquet d’icônes, sans migration de notre application vanilla vers React.

Le dossier **`dist/` complet** doit être servi sous `/native/` : `editor.js`, `style.css` et les fichiers `assets/`. Le chunk principal fait environ 8,3 Mo brut, 2,03 Mo gzip lors de cette compilation ; son chargement doit rester à la demande. Les sources de développement, `node_modules/` et `.tools/` ne font pas partie du déploiement web.

## Contrat d’intégration

```javascript
import {mount} from '/native/editor.js';
const editor = await mount(container, {
  pageId, title,
  onDirty: dirty => { /* état d’enregistrement dans l’interface hôte */ },
  onSave: acknowledgement => { /* révision enregistrée */ },
});
await editor.save();
editor.unmount();
```

Charger aussi `/native/style.css`. Le handle fournit `getState()`, `getText()`, `getDatabases()`, `getMetadata()`, `addBlock(kind,text)`, `addParagraph()`, `addDatabase()`, `ensureDatabase()`, `setDatabaseView('table'|'kanban')`, `addAction()`, `importActions()`, `save()` et `unmount()`, ainsi que `dirty` et `revisionHash`. La création normale d'une base commence sans ligne. `seedRows:true` est un modèle fictif explicite, seul chemin exécutant l'initialiseur upstream à trois lignes.

`importActions()` relie chaque proposition confirmée à un identifiant de ligne natif dans la map Yjs `travaux:action-bindings`. Réouvrir la page conserve les titres/statuts corrigés et ne recrée pas une ligne supprimée. Cette déduplication concerne la même proposition identifiée ; elle ne prétend pas rapprocher automatiquement toutes les actions différentes de plusieurs courriels. Le statut d'exécution reste distinct de la proposition source. Les quatre statuts proposés sont À faire, En cours, En attente et Terminé.

Le chargement appelle `GET /api/v1/pages/{id}/state`. L’enregistrement appelle `PUT` sur la même route avec `state_base64`, `expected_revision_hash`, `text`, `editor_version:'blocksuite-0.22.4'`, cookies de session de même origine et `X-Requested-With: Travaux`. Un conflit 409 conserve le document local et ses modifications. L’hôte doit prévenir avant navigation lorsqu’il reste des modifications ou un enregistrement en échec. Aucun client ne doit forcer l’écrasement d’une révision distante.

La sauvegarde contient un véritable état Yjs, limité à2 000 000 octets, et un texte matérialisé par le **`PlainTextAdapter` natif**, limité à200 000 caractères. Le texte inclut les valeurs des bases. Une normalisation du snapshot d’export corrige le titre de colonne virtuel omis par l’adaptateur 0.22.4 ; l’état natif n’est pas modifié pour cette opération. Les modèles de permission, les pages et leurs versions restent gérés par le backend Travaux. `NativeWorkspace` implémente les interfaces publiques ; aucune classe `TestWorkspace`/`TestDoc` n’est utilisée.

## Périmètre réel et mobile

Pages, paragraphes, formats natifs, listes, blocs, bases à propriétés typées, vues tableau et Kanban sont disponibles dans le moteur. Les bases ne constituent pas une reproduction complète de Notion : relations globales entre bases, formules et calendrier ne sont pas livrés par cette intégration0.22.4. Les lignes de base sont des blocs natifs, pas automatiquement des sous-pages indépendantes. Les noms de certains menus natifs restent en anglais.

Sur téléphone, les bases utilisent une adaptation de lecture en fiches : mêmes `DatabaseBlockDataSource`, IDs de lignes et valeurs Yjs, conversion native des types et actualisation lors des modifications. Chaque fiche donne accès à tous ses champs. La grille native est conservée sur ordinateur. Le SDK 0.22.4 impose la lecture seule des bases sur appareil mobile ; nous ne contournons pas cette restriction. Les paragraphes restent éditables avec le moteur natif.

Les pièces jointes, images, signets et embeds externes sont désactivés dans cette version. `BlobEngine` refuse explicitement les écritures ; aucun stockage mémoire trompeur ni téléversement fournisseur n’est proposé. La synchronisation collaborative en temps réel et le mode hors ligne durable ne sont pas implémentés : les versions reposent sur l’API Travaux.

CSP vérifiée : `script-src 'self' 'wasm-unsafe-eval'` (Oniguruma/Shiki), styles de même origine avec styles inline nécessaires au moteur, `worker-src 'self' blob:`, images locales/data/blob. Aucun `unsafe-eval` général, CDN, police distante ni télémétrie envoyée n’est nécessaire. Le test navigateur vérifie l’absence de requête externe pour le parcours qualifié ; cela n’est pas une preuve de tous les parcours futurs.

## Vérifications et dépendances

`npm test` exécute les tests du codec, du backport de sécurité et de la fonction upstream copiée. `tests/browser-proof.py` utilise Chromium pour vérifier le bundle de production : saisie clavier, vraie base, export de ses valeurs, sauvegarde/rechargement Yjs, conservation du brouillon après409, fiches mobiles 390 px sans débordement, IDs natifs et démontage. Son API est une **fixture synthétique**, pas une mairie connectée. Les captures et `test-results/native-proof.json` en constituent les preuves ; la recette du backend réel relève de l’application hôte.

`test-results/npm-audit.json` résulte d’un véritable `npm audit`. Après overrides versionnés Vitest 4.1.12, minimatch 11.0.1 et KaTeX 0.18.2, il reste **70 nœuds high par propagation d’un unique avis racine Zod** et zéro critical/moderate/low. Le backport local de l’avis [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) est tracé et testé dans `patches/`, sans prétendre à une nouvelle version upstream ni à un audit sans avis. Les collections non bornées restent à limiter dans l’application. Ne pas présenter le prototype comme une qualification de production pour des données réelles.

Les paquets BlockSuite utilisés annoncent MIT. Les dépendances incluent notamment le thème **MPL-2.0**, du code Apache/BSD/ISC/BlueOak, et les données caniuse-lite CC-BY 4. Les textes sont dans `THIRD_PARTY_LICENSES.txt`, les versions et preuves dans `third-party-licenses.json`. Les cinq sources TypeScript non modifiées du thème réellement embarqué sont extraites de ses sourcemaps npm versionnées, avec provenance et hashes, dans `vendor-source/theme-1.1.23/` et publiées sous `/native/vendor-source/theme-1.1.23/`. Leurs URL exactes sont listées par `provenance.json`. Les polices du package ne sont pas utilisées ni recopiées dans ce build.

Sources primaires : [paquet0.22.4](https://registry.npmjs.org/@blocksuite%2Faffine/0.22.4), [source AFFiNE épinglée](https://github.com/toeverything/AFFiNE/tree/9c615502796516da5d0ff91bed1597b1476c7978/blocksuite), [licence MIT](https://github.com/toeverything/AFFiNE/blob/9c615502796516da5d0ff91bed1597b1476c7978/LICENSE-MIT), [thème1.1.23](https://registry.npmjs.org/@toeverything%2Ftheme/1.1.23). `REUSE.md` détaille les modules exécutés et l’extrait copié littéralement.

