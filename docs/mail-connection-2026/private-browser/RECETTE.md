# Raccordement de messagerie — recette privée indépendante

Le 16 novembre 2026, **20 contrôles sur 20 passent** sur le produit compilé servi à `http://127.0.0.1:8766`, entrée `index-BnmrdBgI.js`. Le passage préalable sur Vite est conservé séparément dans [checks-vite.json](checks-vite.json) ; les [résultats courants](checks.json) et les cinq captures viennent du bundle servi.

Le navigateur charge les véritables assets du produit. Les requêtes API sont acheminées vers une vraie application FastAPI privée en processus, avec sa session authentifiée, ses permissions, sa protection CSRF, sa base temporaire, son coffre et ses contrôles de révision. Seul le lecteur Exchange est fictif. Tous les comptes, serveurs et courriels sont inventés en `.invalid`. Cette recette ne valide ni un serveur institutionnel ni une connexion TLS Exchange réelle.

## Parcours et erreurs reproduits

- **Compte et vérification** : création puis premier test volontairement interrompu par le lecteur fictif. Le bouton de vérification réessaie sur le même profil ; un seul POST de création pour l’ensemble du parcours. Le mot de passe n’apparaît pas dans le stockage persistant du navigateur. [Capture de l’échec](1920-private-probe-failure.png).
- **Conflit réel de sélection** : une autre requête à la vraie API sélectionne le calendrier `cal-a` avant la sauvegarde des dossiers du wizard. La première sauvegarde reçoit donc un vrai HTTP409. Le dossier coché localement reste choisi après « Actualiser le compte ». La seconde sauvegarde utilise la nouvelle révision et conserve le calendrier sélectionné par l’autre requête. [Capture du conflit](1920-private-selection-conflict.png).
- **Premier import explicite** : avant le clic de lecture, l’état mail est `ready` et aucun appel de collecte n’a eu lieu. Le [récapitulatif](1920-private-summary.png) précède l’import. Le premier passage renvoie `more_available=true` ; l’interface indique qu’il reste des éléments et propose [Continuer la lecture](1920-private-import-more.png), sans annoncer une importation complète.
- **Suite de lecture et preuves** : le clic suivant utilise la révision rendue par le passage précédent. Les deux courriels fictifs passent par la véritable fonction `import_mail`, avec deux sources et deux originaux enregistrés. L’état devient `read_only`, avec `can_send=false`.
- **Adresse longue sur mobile** : une adresse fictive proche de 200 caractères se replie dans le compte enregistré et dans l’encart de compte vérifié. À 320 px, aucune largeur de document excessive ni adresse hors écran. [Capture inspectée](320-private-long-mailbox.png).

Aucune erreur JavaScript, aucune requête de navigateur vers un service externe et aucun compte institutionnel utilisé. Le rapport des appels API conserve seulement méthode, route, statut, révision et sélection ; il ne recopie pas les mots de passe ou les paramètres du compte.

Le harnais indépendant est `work/qa_mail_connect08.py` dans le workspace opérateur. Aucun fichier applicatif n’a été modifié par cette recette.
