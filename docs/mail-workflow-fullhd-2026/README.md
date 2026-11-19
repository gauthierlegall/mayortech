# Test du workflow mail en Full HD

Test du 16 novembre 2026, version **0.8.1**, release `20261116T102001Z-234aeb`.

**Le site publié est une démonstration : ses connexions réelles sont désactivées. Aucun compte institutionnel n’a été relié pendant ces essais.** Les tests précédents du parcours public ne prouvaient donc pas un raccordement à une vraie boîte.

Le test a reproduit puis corrigé la perte des dossiers cochés après retour à Compte, l’état « exemple terminé » conservé au second passage, et les compteurs périmés après import puis lecture. Les compteurs privés correspondent désormais à l’API : **9 après import, 8 après ouverture d’un message**.

Les essais privés utilisent la vraie application et ses contrôles d’accès, ses révisions et son ingestion ; le lecteur Exchange est fictif. Aucun serveur institutionnel ni transport d’envoi n’est contacté. Ce n’est pas une qualification de connexion Exchange ou de TLS institutionnel.

| Recette | Résultat | Preuve |
| --- | --- | --- |
| Démo publique HTTPS, workflow complet et second passage | 18/18 | [Résultats](public-after/checks-after.json) |
| Retours Compte et fin d’exemple, deux scénarios | 10/10 | [Régression publiée](public-regression-after/checks.json) |
| Parcours privé avec lecteur fictif, y compris les dimensions des captures | 38/38 | [Rapport privé](private/RECETTE.md) |
| Contrat HTTPS : version, assets et permissions | 27/27 | [Contrat](public-after/contract.json) |

**24 captures originales de 1920 × 1080**, sans redimensionnement. [Ouvrir la galerie](GALERIE.html). Les empreintes et dimensions sont conservées dans [screenshots.json](screenshots.json).

## Démo publique publiée

- [Point de départ : Relier ma messagerie dans la Messagerie publiée.](public-after/01-messagerie.png)
- [Le site propose un parcours de démonstration avec un compte fictif.](public-after/02-fournisseur.png)
- [Microsoft 365 est sélectionnable pour information ; la connexion reste indisponible.](public-after/03-microsoft-indisponible.png)
- [Étape Compte : adresse fictive, aucun test réseau ni identifiant réel.](public-after/04-compte-fictif.png)
- [Sans dossier coché, la progression est bloquée avec le bouton désactivé.](public-after/05-dossiers-avant-choix.png)
- [La réception fictive est sélectionnée ; le parcours peut continuer.](public-after/06-dossier-selectionne.png)
- [Récapitulatif des accès de l’exemple avant sa fin.](public-after/07-recapitulatif.png)
- [Fin explicite : aucun compte relié, aucun mail importé.](public-after/08-fin-exemple.png)
- [Retour dans Compte après un exemple terminé : vérifier titre et données présentées.](public-after/09-reprise-compte.png)
- [Second passage dans Terminer : vérifier que l’exemple est à nouveau terminable.](public-after/10-reprise-recapitulatif.png)
- [Le second passage se termine à nouveau, sans perdre le choix du dossier.](public-after/11-second-exemple-termine.png)

## Parcours privé avec lecteur Exchange fictif

- [Choix du fournisseur dans l’espace privé de recette.](private/01-1920-provider.png)
- [Formulaire de connexion réel, avant saisie.](private/02-1920-account-empty.png)
- [Informations fictives renseignées ; mot de passe masqué.](private/03-1920-account-filled.png)
- [Formulaire avant le premier test.](private/04-1920-account-before-test.png)
- [Échec temporaire du lecteur fictif : erreur visible, compte conservé.](private/05-1920-test-failure.png)
- [Compte vérifié et dossiers découverts par le lecteur fictif.](private/06-1920-folders-verified.png)
- [Retour à Compte puis nouveau test : dossier coché conservé.](private/06b-1920-folders-after-backtrack.png)
- [Conflit réel de révision : choix conservés et actualisation proposée.](private/07-1920-scope-conflict.png)
- [Récapitulatif avant la première lecture explicite.](private/08-1920-review-before-import.png)
- [Premier lot conservé ; continuation disponible.](private/09-1920-import-partial.png)
- [Deuxième lecture terminée, compteur actualisé.](private/10-1920-import-complete.png)
- [Deux originaux fictifs ingérés, présents dans la Messagerie.](private/11-1920-mailbox-imported.png)
- [Courriel ouvert ; compteur non lu actualisé de 9 à 8.](private/12-1920-imported-message.png)

