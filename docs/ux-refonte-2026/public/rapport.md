# Recette de la version publiée — validée

Le 14 novembre 2026, **28 contrôles passent sur le site HTTPS publié** [travaux.kerforge.com](https://travaux.kerforge.com). Version déployée : 0.3.0, release `20261114T185316Z-4bb73e`. Les captures de ce dossier proviennent du site public après authentification, dans un Chrome headless isolé. Aucun accès privé n'est reproduit dans les preuves.

Un nouveau chantier entièrement fictif a été créé pour cette recette, avec un EML, une consigne TXT, un PDF et une action explicite. Aucun courrier municipal réel ni appel LLM payant n'a été utilisé. Le statut LLM de démonstration a été vérifié avant l'import.

## Accès directs

- [Page du chantier de recette](https://travaux.kerforge.com/#/project/d6f5b38c-9bd7-4f7f-bbb5-50252af2ef5a?view=page).
- [Kanban](https://travaux.kerforge.com/#/project/d6f5b38c-9bd7-4f7f-bbb5-50252af2ef5a?view=kanban).
- [Documents et originaux](https://travaux.kerforge.com/#/project/d6f5b38c-9bd7-4f7f-bbb5-50252af2ef5a?view=documents).
- [Échanges filtrés sur ce chantier](https://travaux.kerforge.com/#/project/d6f5b38c-9bd7-4f7f-bbb5-50252af2ef5a?view=exchanges).

Ces liens nécessitent la connexion privée habituelle ; ils ne contiennent aucun jeton d'accès.

## Résultats constatés

| Parcours | Preuve obtenue |
|---|---|
| Accès privé | Liste des chantiers et téléchargement original refusés sans session ; cookie Secure, HttpOnly, SameSite Strict ; après déconnexion, le téléchargement est à nouveau refusé. |
| Courriel → action | Action confirmée via la revue, importée une seule fois dans la base native. Ajout d'une action manuelle : deux lignes distinctes. |
| Page en blocs | Sous-titre, liste à puces et case à cocher créés et saisis par l'interface, puis enregistrés par la vraie API. |
| Tableau / Kanban | Vrai mode Kanban, quatre colonnes lisibles ; mêmes IDs de lignes entre les modes et après rechargement ; aucun doublon de l'action issue du mail. |
| Documents liés | EML, TXT et PDF téléchargés **octet par octet identiques** aux originaux importés. Réponse attachment/octet-stream avec CSP sandbox. PDF également téléchargé depuis l'interface et comparé ; extrait ouvert depuis sa propre source. |
| Échanges dans le chantier | Filtre chantier appliqué, ouverture du message dans le même dossier ; retours mobiles préservant le filtre. |
| Mobile 390 et 320 px | Cinq modes visibles sans défilement horizontal, document dans le premier écran ; fiches Kanban de mêmes IDs que les lignes de bureau ; Documents et Échanges parcourus ; fermeture du menu avec retour du focus. |
| Note → contexte durable | Saisie d'une nouvelle note, navigation immédiate, retour et rechargement : texte conservé. Le récapitulatif courant contient cette note et cite sa source humaine actuelle. |

**Aucune erreur JavaScript, erreur console ou requête externe observée pendant cette recette.** Les contrôles, IDs et empreintes complètes sont conservés dans [resultats-publics.json](resultats-publics.json).

La zone native commence à **388 px à 390 px de large** et **383 px à 320 px**, contre respectivement 919 et 1 055 px dans les écrans AVANT. Les dossiers et leurs titres diffèrent ; cette mesure documente l'ordre de l'interface, pas une étude chronométrée d'utilisateurs.

Lignes natives contrôlées : `6E_xZ-KNEq` et `VSQp2UjDD4`. Récapitulatif vérifié : `c14f09f1-ec64-494b-a009-3246410546f3`. Sa couverture reste partielle tant que la proposition d'avancement attend une validation ; la recette n'a pas artificiellement confirmé toutes les informations.

## Captures réelles

- [Kanban publié sur ordinateur](1440-kanban-viewport.png) et [Tableau](1440-tableau-viewport.png).
- [Page à 390 px](390-page-viewport.png), [page à 320 px](320-page-viewport.png), [menu des blocs à 320 px](320-menu-blocs-viewport.png).
- [Documents à 320 px](320-documents-viewport.png) et [documents sur ordinateur](1440-documents-viewport.png).
- [Échange dans le dossier](1440-echange-viewport.png), [Kanban mobile](390-kanban-viewport.png).
- [Comparaison AVANT / APRÈS publié](../comparaison.html).

## Portée du résultat

Cette réussite valide une démonstration privée avec données fictives, sur un seul hôte. Les cellules de bases restent en lecture sur mobile, ce qui est annoncé ; les notes sont éditables. Le test utilise des fenêtres mobiles de navigateur et ne remplace pas un essai sur téléphone physique avec son clavier virtuel. Les récapitulatifs gardent leur éditeur de texte Markdown ; les relations/formules avancées et la collaboration simultanée ne sont pas déclarées livrées.

Les contrôles locaux complémentaires de [chargement et clavier](../apres/polish-final.json) restent distincts des 28 contrôles publics. Aucun audit RGAA complet, test d'intrusion complet, homologation municipale ou conformité RGPD n'est déduit de cette recette. Aucune messagerie institutionnelle réelle n'est déclarée connectée.

**Verdict : version publiée fonctionnelle sur le parcours fictif testé.**
