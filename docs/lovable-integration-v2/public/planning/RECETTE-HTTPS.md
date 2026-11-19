# Planning public 0.7 — recette HTTPS

Site vérifié : https://travaux.kerforge.com, version API **0.7.0**, après le GO de publication de la release `20261115T211012Z-707e4a`.

**65 contrôles passent**, sans erreur JavaScript ni réponse HTTP inattendue. Les 18 captures de viewport ont été relues en FHD 1920×1080, mobile 390×844 et 320×760. Les résultats détaillés et les géométries sont dans `checks.json`.

## Comportements observés

- La grille mensuelle globale présente les six actions réellement planifiées et les jalons confirmés. Les lignes d’action mesurent 65 px.
- Le filtre sélectionne le vrai chantier portail et ses trois actions ; mois précédent puis suivant changent la plage réelle et restituent le mois initial.
- Ouvrir le chantier sélectionne Planning. Sa frise mensuelle reprend les mêmes lignes.
- Le mode Déplacer rend réellement les **trois barres dont l’avancement n’est pas renseigné**. Le fallback d’erreur n’apparaît plus et aucun curseur de pourcentage n’est visible sur ces barres. Le rendu source corrigé a donc été vérifié sur le client publié, avec les politiques de production.
- Sur mobile, les vues globale et projet ouvrent une liste lisible. La grille reste disponible ; son défilement est interne et les noms restent fixes à gauche.
- Le bouton Assistant reste accessible en bas à droite au-dessus de la navigation. Le popup reprend le contexte du chantier portail dans trois contextes navigateur neufs. Le champ de question et le bouton Envoyer activé sont atteignables par hit-test aux trois tailles.
- Aucun débordement horizontal de page n’est constaté sur les écrans capturés.

## Périmètre de lecture et HTTPS

Chrome a utilisé sa validation système normale des certificats. `ignore_https_errors` n’est jamais activé. Les requêtes API Playwright ont utilisé `NODE_OPTIONS=--use-system-ca`.

Le harnais bloque tout PUT/PATCH et tout POST, sauf l’appel idempotent de lecture d’une page native **déjà présente** avant navigation. Aucune mutation bloquée ou soumission de chat n’a été tentée. Une question fictive a seulement été saisie pour activer le bouton Envoyer et mesurer sa cible, puis effacée sans envoi.

L’ensemble des pages natives et le dossier portail sont strictement identiques avant/après chaque contexte navigateur. Les six actions de l’opérateur et les faits confirmés restent préservés. Aucun service externe, police distante ou traceur n’a reçu de requête de l’application.

Cette passe contrôle le popup et son contexte initial ; elle ne prétend pas rejouer la persistance ou les citations d’une conversation envoyée, vérifiées séparément par la recette du popup.

## Reprise

Depuis le répertoire du produit :

```powershell
$env:NODE_OPTIONS='--use-system-ca'
../../.venv/Scripts/python -X utf8 ../../work/qa_public_planning_v07.py
```

Le harnais n’édite aucun fichier de runtime et écrit seulement ses preuves dans ce répertoire.
