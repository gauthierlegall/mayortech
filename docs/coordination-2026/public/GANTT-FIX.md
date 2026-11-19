# Frise : diagnostic et correction ciblée

Le 15 novembre 2026, la recette HTTPS de `0.6.0` a confirmé que la grille et les actions étaient chargées, mais qu’aucune barre n’était rendue. Le constructeur était intercepté par le fallback React.

L’exception exacte est conservée dans `gantt-probe.json` et l’écran dans `1920-gantt-render-failure.png` : `InvalidCharacterError`, car Frappe Gantt 1.2.2 appelait `DOMTokenList.add` avec `planning-task progress-unknown` comme argument unique. Une valeur d’avancement absente déclenche les deux classes ; un statut terminé le fait également. La CSP n’est pas en cause et n’a pas été modifiée.

Correction dans le fichier amont vendorizé `bar.js` : séparer les classes par les espaces avant l’appel à `classList.add`. L’empreinte originale reste conservée dans `UPSTREAM.json`, à côté de l’empreinte du fichier adapté ; la licence MIT est inchangée.

Validation exécutée avant et après la correction :

- `python -m pytest tests/test_gantt_browser.py -q` : rouge avant correction avec l’exception exacte, puis **1 test passé** sur Chrome réel. La frise initialise trois barres : avancement absent, zéro explicite et terminé. Le curseur d’avancement absent reste masqué, le titre échappé ne crée aucun élément SVG image.
- `node --test src/features/workspace/planning-model.test.mjs src/features/workspace/gantt-lifecycle.test.mjs` : **8 tests passés**.
- `npm run typecheck` : succès.

Ces résultats valident la correction source. La vérification du client compilé et publié doit être rejouée après publication du correctif avec la nouvelle interface de conversation.
