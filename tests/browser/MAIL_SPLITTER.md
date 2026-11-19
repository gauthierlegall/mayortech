# Recette des séparateurs de messagerie

Depuis la racine du projet, avec `.venv`, Chrome et Playwright déjà installés :

```powershell
.venv/Scripts/python tests/browser/mail_splitter.py
```

Construire préalablement le frontend courant avec `npm --prefix frontend-lovable run build`. Aucun paquet supplémentaire n’est installé par la recette.

Le script refuse de démarrer si le port **19806** est occupé. Il lance son propre serveur sur **127.0.0.1**, attend son API, exécute Chrome sans interface, puis termine uniquement ce processus dans `finally` et vérifie la libération du port. Le navigateur et son contexte sont aussi fermés. `--serve` est un mode interne utilisé par le processus enfant ; l’exécution normale gère tout le cycle de vie.

Le serveur emploie les vraies routes de l’application et une base SQLite fictive neuve sous `.local/mail-splitter-browser-qa/<run>/workspace.sqlite3`. Les variables `TRAVAUX_*` héritées sont écartées. Aucun compte, fournisseur ou secret réel n’est utilisé. Le navigateur bloque les requêtes vers toute autre origine.

Les preuves sont écrites dans `test-results/mail-splitter` : `fixture.json`, `checks.json`, journaux du serveur et captures. `--output <répertoire>` permet de choisir un autre répertoire de résultats. La base fictive et les preuves restent conservées après la fermeture du serveur ; le script ne procède à aucun nettoyage récursif.

Le passage du 17 novembre a réussi **41 contrôles** et produit six captures en 1920×1080, 1280×900 et 390×844. Il vérifie souris, bornes, clavier, double-clic, préférence numérique seulement, rechargement, brouillons, perte de capture et navigation pendant un glissement, changement de format, et retour liste/lecture sur mobile. Le cas « Fin avant la première sélection, puis ouverture d’un message court » vérifie le maintien d’un lecteur d’au moins 320 px lorsque le contexte apparaît.

Cette recette qualifie les contrôleurs et l’interface avec une API de démonstration locale. Elle ne qualifie ni la messagerie réelle, ni une identité ou une MFA, ni l’envoi de courriels. Les clés de largeur ne contiennent aucune donnée de courrier ; le stockage de brouillon fictif existant est testé séparément et n’est pas confondu avec cette préférence.
