# Recette indépendante des propriétés — 15 novembre 2026

Serveur local `http://127.0.0.1:8766`, Chrome headless réel via Python Playwright. Les captures de viewport sont prises en 1920×1080, 390×844 et 320×760 ; les fichiers `*-full.png` sont explicitement des captures de page entière.

Seul le dossier fictif `QA-PROP-F25014BA7A` (`749e7ac0-d3ba-4e61-86bc-652e204dc0b3`) a été modifié. Aucun dossier principal, donnée photographique réelle ou message externe. Ce dossier reste local pour permettre une reprise reproductible.

## Résultat final

20 contrôles passent, aucun échec, aucune erreur JavaScript et aucune réponse HTTP inattendue. Le 409 du scénario concurrent est attendu et consigné séparément dans `checks.json`.

- Les 14 champs éditables et la propriété Pièces jointes sont présents. Notes et Observation restent indépendantes.
- Les coûts français `1 234,56` et `0,01` sont conservés exactement sous les valeurs `1234.56` et `0.01`, y compris après rechargement.
- Date demande et Échéance n'altèrent ni l'identifiant ni la valeur du fait Livraison confirmé au 15 décembre 2026.
- Une modification ordinaire est sauvegardée à la navigation.
- Deux contextes isolés provoquent bien un 409 sur révision périmée ; le formulaire conserve le brouillon A.
- « Actualiser en gardant ma saisie » conserve A et affiche la valeur B du serveur. Cliquer Documents reste dans Propriétés, conserve B sur le serveur et émet **zéro PATCH**.
- Un clic explicite sur Enregistrer confirme ensuite A ; Documents devient accessible.
- Les six onglets et Assistant sont tous accessibles par hit-test, sans débordement horizontal, sur les trois largeurs. Assistant fait désormais 44 px de haut en FHD et 44×44 px sur mobile.

## Preuves

`checks.json` contient les valeurs vérifiées, la géométrie des sept boutons et le compteur de requêtes pendant la navigation bloquée. `1920-properties-after-review-navigation.png` montre le formulaire retenu après le conflit. `1920-properties-after-explicit-save.png` montre Documents accessible après confirmation explicite.

Rejouer depuis le répertoire du produit :

```powershell
../../.venv/Scripts/python -X utf8 ../../work/qa_properties06.py 749e7ac0-d3ba-4e61-86bc-652e204dc0b3
```

Le script vérifie le préfixe `QA-PROP-` avant de réutiliser un dossier. Ne pas lui passer un dossier métier.

## Observation visuelle mineure

Après une tentative de navigation pendant la relecture, quatre blocs répètent l'instruction de relire/enregistrer (bandeau global, alerte rouge, statut d'actualisation et aide de relecture), auxquels s'ajoute le détail utile des valeurs concurrentes. Le mécanisme est sûr et passe la recette ; regrouper l'instruction dans une seule alerte accompagnée du détail du conflit allégerait ce cas exceptionnel.
