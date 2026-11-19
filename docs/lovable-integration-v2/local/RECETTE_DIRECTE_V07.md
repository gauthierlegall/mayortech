# Recette directe du client v0.7

Contrôle du 15 novembre 2026 sur `http://127.0.0.1:8766`, **sans substitution des assets, des réponses API ou de la configuration**. Données fictives uniquement. Les captures de ce dossier proviennent du bundle réellement servi ; celles du dossier `mail-implementation` étaient une compilation isolée et restent distinctes.

## Messagerie : validée

- [1920 px](1920-mail.png) : trois colonnes réelles de 170 px / 310 px / espace restant ; une seule arborescence interne de dossiers, aucun doublon dans le Shell.
- [390 px](390-mail.png) et [320 px](320-mail.png) : dossiers défilants, filtre chantier accessible et document sans débordement horizontal.
- Le filtre chantier appelle `project_id` sur l'API et affiche exactement les six courriels effectivement rattachés au dossier contrôlé, sans rechercher son nom dans leur texte.
- Lecture du même courriel sur [ordinateur](1920-mail-reader.png), [390 px](390-mail-reader.png) et [320 px](320-mail-reader.png) ; la liste s'efface au profit du lecteur sur mobile.
- [Brouillon réouvert](1920-mail-draft-reopened.png) après rédaction, navigation réelle vers Chantiers, retour dans Messagerie puis Brouillons : objet et corps intégralement conservés. Le brouillon de recette a ensuite été supprimé dans ce navigateur isolé.
- L'instance expose `server_drafts=false` et `can_send=false`. Cette recette valide donc la conservation sur l'appareil. Aucun appel de création de brouillon serveur ni d'envoi ; les tests privés du service et du moteur sont des preuves séparées.

## Autres écrans

[Chantiers](1920-projects.png) affiche un compteur chargé, sans zéro artificiel avant les données. [Page du dossier](1920-project-page.png) : six onglets Page/Actions/Planning/Terrain/Documents/Échanges, propriétés accessibles dans Page, mise en page cohérente avec la référence v2. Les captures 390 et 320 px conservent une largeur de document égale au viewport.

## Observation Actions et retest ciblé

Le premier passage a révélé une course entre l'ouverture native de `<details>` et les rendus asynchrones des actions : le filtre pouvait se refermer avant la livraison de l'événement `toggle`. Signalé **P2**, correctif pris par le parent. La validation après reconstruction est enregistrée séparément ; aucune modification applicative effectuée par cet auditeur dans cette passe.

Le JSON brut du premier passage est conservé dans [qa-v07-direct-first-pass.json](qa-v07-direct-first-pass.json). Ses attentes « fermé » à 320 px et pour les propriétés après changement de largeur étaient trop strictes : naviguer vers le même hash conserve légitimement l'état déjà ouvert. Ces attentes de harnais ne constituent pas des défauts du produit. Le retest utilise un rechargement réel pour tester l'état initial, puis les clics et le clavier.

Le passage complet a produit 21 captures, sans erreur JavaScript ni HTTP. Les appels `POST /projects/{id}/page` enregistrés correspondent à l'obtention idempotente des pages natives par le client ; aucune sauvegarde Yjs ni modification du contenu des dossiers n'a été demandée.

## Retest après correction : 20/20 validés

Le correctif a été revérifié directement sur le bundle servi `index-C7hSDCby.js`, sans substitution. À **390 et 320 px**, le clic a été effectué pendant que le chargement natif était encore actif : les filtres s'ouvrent et restent ouverts après sa fin. Entrée ferme, Espace ouvre, le filtre Haute réduit réellement les lignes, puis le clic referme. Aucun débordement horizontal ni erreur JavaScript/HTTP. Les propriétés sont initialement repliées après rechargement réel, puis accessibles dans Page aux deux largeurs.

[Résultats du retest](qa-v07-filters-retest.json) · [390 px](390-actions-filters-retest.png) · [320 px](320-actions-filters-retest.png).

**Aucun P1/P2 ouvert dans le périmètre contrôlé.** Le JSON du premier passage reste brut pour traçabilité ; ses observations sont résolues par ce retest ciblé, sans relancer les autres parcours.
