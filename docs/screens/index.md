# Captures et preuves de recette

Captures du service local `http://127.0.0.1:8765`, sur données entièrement fictives, pendant la recette du 14 novembre 2026. Navigateur Chrome headless via Playwright ; français, fuseau Europe/Paris. Les images montrent le complément réellement exécuté, pas une maquette et pas une application AppFlowy distante.

- `desktop-overview.png` : vue d’ensemble réelle à 1440 px.
- `mobile-390-projects.png` et `mobile-320-projects.png` : fiches des chantiers, recherche `TRV` appliquée et visible ; aucune colonne cachée.
- `mobile-390-project.png` et `mobile-320-project.png` : mémoire du chantier de démonstration Parvis de l’école des Alizés.
- `mobile-390-review.png`, `mobile-320-review.png`, `mobile-source-proof.png` : revue et accès à la preuve originale.
- `mobile-390-summary.png`, `mobile-320-summary.png` : ancienne version approuvée, avec avertissements explicites de couverture et d’obsolescence.
- `flow-mobile-source.png`, `flow-mobile-human-note.png`, `flow-mobile-summary-proofs.png`, `flow-mobile-summary-approved.png` : étapes du parcours mutable exécuté sur le chantier dédié `TEST-UX-001`.
- `mobile-network-error.png` : panne réseau injectée uniquement dans le navigateur de test, puis reprise réellement vérifiée.
- `flow-export-fictif.md` : fichier réellement téléchargé depuis la version approuvée du chantier de recette.

`browser-check.json` contient les 24 rendus et les contrôles de débordement/console. `browser-flow.json` énumère les 11 opérations fonctionnelles réussies. `browser-failure-states.json` distingue la panne injectée des appels réels et consigne la reprise, le retour depuis un dossier absent et la fermeture de preuve au clavier avec restitution du focus.

Les scripts reproductibles sont `web/tests/browser_check.py`, `browser_flow.py`, `browser_failure_states.py`. Le parcours mutable nécessite le mode démo et ajoute exclusivement des sources, notes et versions fictives au chantier de test ; il ne réinitialise pas les données.

Limites : accès Exchange réel et publication dans AppFlowy réel non exercés. Le bouton de publication n’est proposé que sur une version approuvée, à jour et avec une capacité serveur configurée ; aucune publication distante n’est prétendue par ces captures.
