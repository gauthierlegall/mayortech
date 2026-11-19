# Revue de migration publique — 17 novembre 2026

**Verdict : exception additive admissible uniquement pour la transition exacte ci-dessous.** Aucun blocage de schéma ou de conservation des données n’a été trouvé dans ce périmètre. Cette revue ne constitue ni un déploiement, ni une autorisation de convertir une base privée/test, ni une approbation générale des migrations futures.

## Baseline et empreintes contrôlées

Archive examinée en lecture seule : `work/travaux-workflow09-release.tar.gz`, release **`20261116T102001Z-234aeb`**, version `0.8.1`. SHA256 de l’archive :

```text
c667dec6b80dd6c896f7a4d017ff8e785d9c0a8d9414b38e178f10d7e79c040e
```

Les **437 fichiers** référencés par le manifest concordent avec leurs empreintes ; aucun membre dupliqué ou hors inventaire n’a été trouvé. Son gate d’archive porte le source digest `43f9ab4614714f86b89b91c68fd3de7297fb9c32784854293fb2b40a7bf7f3b5`. Le dépôt courant n’étant pas un checkout Git, l’archive vérifiée est la référence de comparaison, sans affirmation de diff Git.

Empreintes pour l’exception proposée : SHA256 du JSON trié et compact des couples chemin→SHA256, selon `common.inventory_digest`, en incluant **tous les chemins `src/travaux/` autorisés dans la release**, plus `Dockerfile`, `pyproject.toml` et `uv.lock` :

| Ensemble | Digest |
| --- | --- |
| Baseline | `63c42120f748d29602aaffdc931190d3ea4da79a9deba894297531c2a220305c` |
| Candidat audité | `503b33f8d37f60fd97c41587a8785e9703b356efdd1a7f71d39b02e2d195f378` |

Ces deux valeurs ont été recalculées indépendamment depuis l’archive et les sources actuelles. Une modification du backend, du Dockerfile ou des dépendances sort de cette revue. Les fichiers d’interface restent soumis au gate de release existant ; leur évolution ne vaut pas une nouvelle approbation de schéma.

## Fichiers protégés

| Fichier | Baseline → candidat | Conséquence |
| --- | --- | --- |
| `repository.py` | Identique : `af7c56e2109616a05fcae5d52894d9ad390874556cfb7475660ff467eb642a07` | Schéma et migrations conditionnelles historiques inchangés |
| `workspace.py` | Identique : `d5717ba8c26efe3370c865683e27eebce7ff486f1fa03b4da4803600902cc73e` | Tables et stockage des pages/versions inchangés |
| `jobs.py` | Identique : `7f7f46df6731da3f97975f9c6050bfa70c29a5df5572f439cd34e63d50be36b0` | Schéma de file durable inchangé |
| `auth.py` | `bf874b153f2bee65e2649cfde61d64bd00b56e398f98b3cf6556417e2574aa1b` → `4123a8bf56cacf1d6d0690e932316190c733c003cc27986b7d51d206c1ec4643` | Seul ajout : `revoke_actor`, suppression ciblée de sessions à l’usage ; aucune DDL ou mutation nouvelle au démarrage |
| `governance.py` | `a16fd8633d7f5eed607a42824902f9fb1809aa6ea4be5e740de3dc902fc0805e` → `9e5a5160e62eaad5ccdf236b97240017b8339b913fb1ff283cafb50fe8486dc0` | SCHEMA inchangé ; identité OIDC conditionnelle et filtrage des lectures/audit |

Dans `governance.py`, le rôle visiteur public et sa limite de permissions sont conservés. Les branches d’identité active ne s’appliquent qu’au mode OIDC, incompatible avec `public_demo` dans Settings. Les nouveaux scopes restent compatibles avec le mode public historique. Aucun rôle venant du navigateur ne remplace l’autorité serveur.

## Migrations des nouveaux services

Les constructeurs nouveaux emploient `CREATE TABLE/INDEX IF NOT EXISTS`. La revue n’a relevé ni `DROP`, ni renommage, ni réécriture d’une table ancienne, ni trigger nouveau attaché aux anciennes données. Les anciens `ALTER TABLE ... ADD COLUMN` conditionnels de Repository/ConnectionHub sont inchangés par rapport à l’archive.

Le démarrage public du candidat ajoute seulement ces **14 tables** :

```text
account_join_requests
action_collaboration
action_comments
action_occurrences
action_recurrence_rules
assistant_change_proposals
document_uploads
identity_audit
identity_flows
identity_members
mail_oauth_flows
mail_oauth_refresh_leases
project_acl_versions
project_grants
```

Les index de collaboration portent sur ces nouvelles tables. `cloud_mail_checkpoints` est également défini dans le nouveau lecteur cloud, mais n’est pas créé par le démarrage public testé : ce lecteur exige une connexion externe, désactivée dans ce profil. Le marqueur `test_organization_metadata` est réservé à l’organisation test explicite et n’est pas créé ici. Les suppressions/updates des nouveaux services concernent leurs opérations explicites, non une migration générale exécutée au boot.

## Preuves exécutées

Une revue indépendante a extrait uniquement les sources, ressources vendor et fixtures nécessaires vers un `TemporaryDirectory`, avec refus des chemins indirects/non réguliers. Trois processus d’application distincts ont utilisé la **même base publique jetable** :

1. Initialisation par l’application de l’archive ; capture des schémas et de toutes les colonnes de toutes les lignes.
2. Initialisation et lectures par l’application courante.
3. Redémarrage et lectures par l’application de l’archive sur cette base désormais étendue.

Résultat : **44 tables anciennes présentes, schémas identiques, aucune ancienne ligne modifiée**, après le candidat comme après le retour arrière ; 14 tables nouvelles seulement. Session, bootstrap, projets, organisation et audit retournent HTTP 200 dans les trois phases. Les temporaires ont été nettoyés. Aucun serveur distant ni donnée réelle n’a été lu ou modifié.

Vérifications supplémentaires : **8 tests** jobs/workspace/importing-backup verts ; **71 tests** public_demo, exemples publics, gouvernance et ACL verts. La première exécution de ce dernier ensemble avait 70 réussites et un refus attendu du garde de diagnostic TLS ambiant devant un MockTransport ; la relance a retiré uniquement `SSLKEYLOGFILE`/`QUICLOGDIR` dans le processus de pytest, puis obtenu 71 réussites. Aucune protection runtime n’a été modifiée. La suite globale finale et les preuves de frontend/natif restent celles du gate tenu par la racine ; elles ne sont pas remplacées par cette revue ciblée.

## Conditions de l’exception et retour arrière

L’exception à `schema_review_required_before_update` doit exiger simultanément :

- Ancienne release exactement `20261116T102001Z-234aeb`, ancienne et nouvelle empreintes backend/build exactement égales à la paire ci-dessus.
- Ancien et nouveau runtime **strictement identiques** au contrat public : `mode=public_demo`, `db_path=/data/public-demo.sqlite3`, `tenant_id=public-demo-travaux`.
- Aucun élargissement aux profils staging/pilot/OIDC, aux autres bases, tenants ou anciennes releases ; aucun drapeau général de contournement.
- Archive et gate vérifiés, sauvegarde SQLite cohérente de la base précédente avant construction/activation, puis healthchecks et probe public conservés.
- Ancienne image/release et route conservées pour redémarrage ; aucun retrait automatique des nouvelles tables, aucune restauration destructive de la DB pour un simple retour de binaire.

Le retour arrière vérifié concerne le démarrage, la conservation des données anciennes et les lectures indiquées. L’ancien backend ignore les nouvelles métadonnées de collaboration/upload/propositions et ne les efface pas. Ce test ne qualifie pas chaque nouveau parcours d’écriture après usage prolongé ni chaque état Yjs possible. La base réelle distante n’a pas été inspectée par ce lot ; son runtime, sa sauvegarde et ses probes doivent encore satisfaire la procédure de publication. Le code d’exception et son test d’ordre sauvegarde→construction sont intégrés séparément par la racine.
