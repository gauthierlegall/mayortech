# Code upstream réellement exécuté

| Module repris | Source exacte | Usage vérifié dans Travaux |
|---|---|---|
| `databaseViewInitTemplate` — copie littérale | `vendor/affine/database-view-init.ts`, extrait de [data-source.ts](https://github.com/toeverything/AFFiNE/blob/9c615502796516da5d0ff91bed1597b1476c7978/blocksuite/affine/blocks/database/src/data-source.ts), commit9c615502796516da5d0ff91bed1597b1476c7978, MIT | Appelé uniquement par le modèle fictif explicite `seedRows:true` ; la création métier commence sans ligne. Type import et attribution ajoutés, corps inchangé, hash dans `vendor/affine/provenance.json`. Fonction également identique au package0.22.4 installé. Tests hash/comportement et vrai rendu Chromium. |
| `StoreExtensionManager`, `ViewExtensionManager` | `@blocksuite/affine-ext-loader@0.22.4`, lock npm et intégrité | Enregistrement des vrais schémas, vues et services ; aucun éditeur de substitution. |
| `BlockStdScope`, `EditorHost` | `@blocksuite/std@0.22.4`, MIT | Rendu des blocs, clavier, sélection, formats et widgets natifs ; saisie réelle testée dans Chromium. |
| `StoreContainer`, `AwarenessStore`, `Text` | `@blocksuite/store@0.22.4`, MIT | Modèles publics et état partagé Yjs dans notre hôte mono-page ; `NativeWorkspace` adapte navigation/auth au backend Travaux. |
| `DatabaseBlockDataSource`, vues et propriétés natives | `@blocksuite/affine-block-database@0.22.4`, `@blocksuite/data-view@0.22.4`, MIT | Vrai tableau et Kanban, cellules texte/nombre/select ; les fiches mobiles lisent cette même source, sans deuxième copie éditable. |
| `PlainTextAdapter`, snapshot/transformer natifs | `@blocksuite/affine-shared@0.22.4`, `@blocksuite/store@0.22.4`, MIT | Texte des paragraphes et cellules exporté puis sauvegardé dans l’API mémoire. Ajout de l’en-tête synthétique Intitulé dans le snapshot exporté pour corriger un décalage constaté, sans modifier l’état Yjs. |
| `BlobEngine` | `@blocksuite/sync@0.22.4`, MIT | Contrat de blobs natif raccordé à une source explicite en lecture seule ; écritures refusées tant que le stockage réel n’est pas intégré. |
| Yjs | `yjs@13.6.33`, MIT | `encodeStateAsUpdate`/`applyUpdate` ; vrai état binaire préservé après sauvegarde et remontage, avec contrôle de révision serveur. |
| Styles et thème natifs | CSS des modules BlockSuite ; `@toeverything/theme@1.1.23` MPL-2.0 | Styles natifs compilés avec le plugin officiel vanilla-extract ; variables adaptées par notre feuille CSS séparée. Sources exactes non modifiées du thème fournies avec le build. |
| Backport Zod borné | `scripts/security-patch.mjs` et `patches/`, basé sur [correctif upstream a0ebf970](https://github.com/colinhacks/zod/commit/a0ebf970f2d752e5f58527cd2942ff48be4f46bd) | Hash avant/après obligatoire, ESM/CJS/TypeScript ; tests démontrent le refus des collections bornées trop grandes avant parsing des éléments. Aucune migration forcée vers Zod 4 incompatible. |

Le starter complet `blocksuite/playground/apps/starter/data/database.ts` a été lu. Il initialise dix bases de démonstration, ajoute des lignes fictives et efface l’historique ; nous ne l’exécutons pas dans une page métier. Le modèle fictif explicite utilise la fonction isolée ci-dessus. Le chemin métier emploie les opérations du SDK sans ligne préremplie, puis les actions explicitement saisies ou confirmées depuis les courriels.

Les textes et licences ne sont pas copiés dans nos sources métier ; ils restent attribués sous `vendor/`, `licenses/`, `vendor-source/` et `THIRD_PARTY_LICENSES.txt`. Aucune partie Enterprise du backend AFFiNE n’est nécessaire à ces modules. Les classes de test Workspace/Doc du SDK ne sont pas utilisées.

