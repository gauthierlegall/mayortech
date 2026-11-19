# Scénario Lovable persistant — contrat et recette opérateur

**Objectif :** retrouver le récit du prototype fourni, dans les vraies sources, faits, documents et récapitulatifs du serveur.

**Architecture :** ajout atomique et idempotent par un opérateur ; quatre nouveaux dossiers, dix courriels fictifs reconstitués, deux PDF fournis inchangés. Aucun raccordement à une messagerie réelle et aucun appel LLM. Le module ne s’exécute depuis aucune route HTTP.

**Pile :** Python 3.11, SQLite, services d’import et de provenance existants. Contrat : `travaux.storyline.seed_storyline(repo, queue, tenant, fixture_dir)`.

## Provenance et limites

Le ZIP utilisateur `mayor-project-hub.zip` contient le scénario dans `src/features/workspace/model.ts` et les deux PDF dans `public/documents/`. Les EML de cette fixture sont **reconstitués pour la démonstration** à partir de ce scénario ; ils ne sont pas des originaux municipaux reçus. Chaque corps le dit explicitement. Les domaines `.example` et `.invalid` sont réservés aux exemples. Les personnages du récit sont des propriétaires métier et des auteurs de courriels fictifs ; aucun compte, membre, droit ou identité vérifiée n’est créé à leur nom.

Les mentions « Validé » et « En examen » décrivent les décisions fictives dans le scénario. Elles ne constituent aucune validation juridique ou comptable réelle.

| Élément | SHA-256 |
| --- | --- |
| ZIP fourni | `0df387dfe867b63736ee3f6644bf6e7a65f8aa92459292ffdd88be41c6075e05` |
| Manifeste `storyline.json` | `bbeb8eb65fba682e7bc239bbb70c71dd656da99eff7039332ad77751f04351e9` |
| PDF version 1, octets du ZIP | `15b64a163d12d207d3e25f6bc0d02c9c427fcc2792421c7e4154bf38c926d39c` |
| PDF version 2, octets du ZIP | `e823e0577376872b9894529875f852c8b1154c0a3645649d9828fca4bd359fce` |

Les empreintes des dix EML et des deux PDF figurent dans `storyline.json`. Le module vérifie l’empreinte épinglée du manifeste et toutes celles des fichiers avant la première écriture.

## Dossiers et récit

| Priorité de présentation | Référence | État | Livraison confirmée dans la fixture |
| --- | --- | --- | --- |
| Portail de l’école de Ker Avel | TRV-2026-042 | En cours | 18 novembre 2026 |
| Rue de la Fontaine | TRV-2026-038 | En cours | 4 décembre 2026 |
| Éclairage du gymnase | TRV-2026-045 | À préparer | 16 décembre 2026 |
| Parc de Ty Glas | TRV-2026-031 | Terminé | 6 novembre 2026 |

Les six dossiers historiques restent présents. L’ordre de présentation ci-dessus est un choix d’interface ; l’opérateur ne modifie pas leurs données.

Pour le portail : devis initial reçu le 3 novembre, validation le 5, dimensions confirmées le 7, sécurisation préparée le 10, fabrication suivie le 12, puis report annoncé le 15. Le devis version 1 reste validé à **4 850,00 EUR HT**. La version 2 est explicitement **en examen**, à **5 120,00 EUR HT**. Le report du 18 au 25 novembre et le nouveau budget restent des propositions en conflit, sans remplacement automatique. La tâche « Confirmer l’accès vendredi » est enregistrée ; son existence ne signifie pas que l’accès est accordé.

Six tâches disposent de leur source, échéance, responsable fictif et état de suivi. Quatre notes préparées sont conservées comme notes de démonstration. Le premier récapitulatif du portail reste validé mais est signalé dépassé après le nouveau courrier ; un second brouillon distingue les faits confirmés des annonces à vérifier.

## Contrat documentaire

Le résultat opérateur expose `document_catalog` et une source documentaire du chantier conserve exactement le même tableau dans `source.metadata.document_catalog`.

Chaque entrée contient `document_id`, `source_id` de la pièce jointe, `mail_source_id`, `filename`, `sha256`, `family`, `version`, `status`, `status_label`, `amount: {amount, currency, basis}` et `evidence: {version, status, amount}`. Chaque preuve contient son véritable `source_id` et une citation exacte. La validation de la version 1 cite le courriel du 5 novembre ; les versions et montants citent les PDF ; l’examen de la version 2 cite sa mention explicite. Rien n’est déduit du nom du fichier ou du dernier montant reçu.

La source de catalogue porte `source_kind=demo_document_catalog`, `origin=demo_fixture_catalog` et un marqueur de note documentaire. Elle est exclue de la boîte de courriels et de l’inventaire des originaux. Elle ne se présente pas comme une note humaine vérifiée.

## Exécution autorisée par un opérateur

Dans l’environnement serveur déjà configuré en `public_demo`, après sauvegarde et publication du module :

```sh
python -m travaux.storyline --fixture-dir /chemin/vers/fixtures/storylines/lovable-v1
```

Le module prend le chemin de base et le périmètre depuis la configuration serveur existante. En `public_demo`, il exige son marqueur `public_demo_metadata`, sans modifier ce marqueur ni permettre l’emploi d’une ancienne base privée. Un opérateur peut aussi préparer sa démo locale : fournir les véritables `Settings(mode="demo", ...)` via `seed_storyline(..., settings=settings)`, ou utiliser la CLI dans cet environnement local configuré. Ce cas exige la même base et le même périmètre, le moteur fictif, aucune autorisation de sortie ni paramètres LLM/AppFlowy ; une base marquée publique y est refusée. `staging` et `pilot` sont toujours refusés. Sans paramètres explicites, l’appel Python continue d’exiger le marqueur public.

La file de traitements doit utiliser la même base. Les références sont refusées si elles existent sans appartenir au scénario. Le résultat JSON contient les identifiants réels, le catalogue, les tâches, les propositions et les versions de récapitulatifs.

Une transaction englobe tous les ajouts. Les traitements de ces fixtures sont préparés de manière déterministe et clos dans cette même transaction, sans prendre ni modifier les travaux d’autres courriels. Une interruption annule toute la création. Le registre `demo_storylines` rend une nouvelle exécution sans effet : aucune note humaine, décision ultérieure ou version de récapitulatif n’est réinitialisée.

**Raccordement natif restant à l’opérateur :** le résultat `native_seed` fournit les paragraphes et tâches associés à chaque véritable projet. Ils doivent être insérés et sauvegardés par les API de l’éditeur natif, puis relus depuis son état persistant. Cette étape ne fait pas partie de l’initialisation SQLite. Ne jamais réappliquer ce contenu sur une page déjà modifiée : ouvrir sa révision, refuser un état déjà rempli et conserver la trace d’initialisation native. Les tâches natives restent ensuite éditables dans leur document, pas dans une seconde liste simulée.

## Vérifications effectuées

```sh
python -m pytest tests/test_storyline.py tests/test_import_review.py tests/test_importing_backup.py tests/test_documents.py tests/test_public_demo_auth.py -q
```

**61 tests passent** : octets originaux exacts, preuves documentaires, quatre dossiers additifs, dates et budgets contradictoires conservés, reprise sans doublon ni écrasement, refus d’une référence occupée, refus d’un fichier altéré, refus de la base privée ou d’un autre périmètre et annulation atomique sur panne d’import. Le mode local exige sa configuration explicite sans connexion externe et ne contourne pas le marqueur public. Ruff vérifie les deux nouveaux fichiers Python.

Aucune base publique existante n’a été modifiée pour produire cette fixture. La recette publique et le contrôle de la sauvegarde native doivent être effectués après son exécution opérateur.
