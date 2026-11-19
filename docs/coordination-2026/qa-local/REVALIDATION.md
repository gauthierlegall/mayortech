# Revalidation des trois régressions

Les **13 contrôles de `regression-final.json` passent** sur les derniers fichiers compilés, sans erreur JavaScript ni HTTP.

- À 390 × 844 et 320 × 760, le composeur reste dans la grille et ses deux contrôles, textarea et Envoyer, sont réellement atteints par `elementFromPoint`, au-dessus de la navigation fixe. L’historique et l’en-tête ne sont plus découpés par le défilement d’un parent masqué.
- Le lien de l’étape Agendas reste dans une page de 320 px. La fixture utilise réellement `public_demo` et n’affiche aucun champ de mot de passe. Aucun POST n’a été tenté.
- Avec l’horloge du navigateur fixée au 15 janvier 2027, un lien `#/agenda?event=…` sans paramètre de date retrouve le rendez-vous du 20 novembre 2026, affiche novembre et ouvre son dialogue. Un changement de hash ouvre ensuite le second rendez-vous dans le même composant.

[Rapport et géométries](regression-final.json), [composeur 390 px](390-chat-composer-fixed.png), [composeur 320 px](320-chat-composer-fixed.png), [lien Agendas 320 px](320-onboarding-agenda-link-fixed.png), [lien canonique](1920-agenda-canonical-link-fixed.png), [changement de hash](1920-agenda-hashchange-fixed.png).

Script de recette : `work/qa_coordination_regressions06.py` dans le workspace. Les précédents rapports conservent les échecs observés avant correction ; cette revalidation les remplace pour ces trois points uniquement. La fixture publique sur 8768 était un serveur HTTP en boucle locale, utilisé pour GET et progression du navigateur : elle ne constitue pas une preuve TLS ni une recette de mutations publiques. Les tests fonctionnels de conversation ont été réalisés sur 8766 avec un historique propre au navigateur de recette, sans message externe. Aucun champ de projet, planning ou rendez-vous n’a été modifié par cette dernière passe.
