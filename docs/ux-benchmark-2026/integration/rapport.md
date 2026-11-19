# Recette intégrée — page AFFiNE, mémoire et courriels

14 novembre 2026. Résultat : **parcours fictif local validé après correction de deux courses de sauvegarde**. Aucun défaut bloquant encore observé dans les parcours décrits ci-dessous. Ce résultat concerne la démonstration locale ; il ne vaut ni homologation municipale, ni contrôle complet du futur hébergement ou de sa conformité.

## Conditions et méthode

- Serveur réel `http://127.0.0.1:8765`, vraie API FastAPI, SQLite persistante, bundle AFFiNE BlockSuite 0.22.4 embarqué sur la même origine.
- Chrome headless isolé piloté par Python Playwright ; aucun accès au navigateur ou aux applications de l'utilisateur.
- Fenêtre ordinateur 1440 × 1000 ; fenêtres mobiles 390 × 844 et 320 × 844. Ce sont des dimensions de navigateur, pas des appareils physiques.
- Création du seul chantier fictif `TEST-UX-INTEGRE`, projet `f658a522-8a10-4499-a47e-bd259803a4fc`, page `04250459-f311-4c1a-970d-ce83c602a4cc`.
- Import d'un EML entièrement fictif et d'une pièce TXT. Aucune messagerie réelle, aucun courrier municipal, aucun secret et aucun appel LLM payant.
- Saisie réelle au clavier dans les paragraphes et cellules AFFiNE. Les vérifications du store natif sont en lecture seule ; elles ne remplacent pas les interactions utilisateur.
- Pour les courses, seul le départ réseau d'un PUT a été retenu puis libéré vers le vrai serveur. Aucun faux ACK, faux état sauvegardé ou faux résumé. Pour le cas d'erreur mail uniquement, un GET a reçu un 503 simulé puis la relance a utilisé le vrai backend.

Les contrôles combinent rendu, interactions, rechargement, lectures API et identifiants de sources. Les captures ont été inspectées. Les scripts de recette sont dans `work/integration_*.py` du dossier de travail ; les résultats JSON et captures conservés ici constituent les preuves de cette exécution.

## Résultats

| Parcours | Vérification effective | Résultat et preuve |
|---|---|---|
| Écrire une note | Paragraphe AFFiNE édité au clavier, autosauvegarde réelle, texte relu par GET page | Conforme — [probe.json](probe.json) |
| Quitter pendant une sauvegarde | A envoyé, B tapé pendant le PUT de A, clic Mémoire, puis ACK de A | A et B conservés après correctif — [inflight-result.json](inflight-result.json) |
| Modifier une base native | Titre, description et nombre saisis dans les vraies cellules ; sauvegarde, rechargement | Valeurs conservées et même row ID — [database-result.json](database-result.json) |
| Lire cette base sur mobile | Fiches dépliables à 390 et 320, même ID des trois lignes que le tableau natif | Conforme — [final-state-result.json](final-state-result.json) |
| Préparer un récap avec dernière note en vol | Dernière note saisie, PUT retenu, génération demandée avant ACK | La génération attend la note ; contenu courant et cellule native présents — [summary-result.json](summary-result.json) |
| Vérifier la provenance du récap | Lecture de la source citée et vérification exacte de la citation dans son corps | Conforme — [final-state-result.json](final-state-result.json) |
| Vérifier l'historique humain | Une seule note humaine courante `manual_affine`, texte égal à la page ; 13 versions natives conservées | Conforme — [final-state-result.json](final-state-result.json) |
| Retrouver un courrier | Recherche + filtre chantier + filtre Rattachés, un seul message attendu ; 3 tailles | Conforme — [mail-result.json](mail-result.json) |
| Lire courrier, pièce puis revenir | Vrai texte TXT lié à sa source, retours et filtres conservés, lien chantier dans la même application | Conforme — [mail-result.json](mail-result.json) |
| Texte hostile dans un courrier | Chaîne `<img ... onerror=...>` affichée littéralement, aucune image créée, aucun code exécuté | Conforme sur ce cas précis — [mail-result.json](mail-result.json) |
| Clavier et menu mobile | Focus titre du message puis de la pièce, retour focus bouton, sidebar fermée inert, Échap ferme et rend le focus au bouton | Conforme à 320 et 390 — [mail-result.json](mail-result.json) |
| Recherches et erreurs | Ancienne recherche retardée ne remplace pas la suivante ; Entrée soumet ; 503 lisible puis Réessayer récupère le vrai résultat | Conforme — [mail-resilience-result.json](mail-resilience-result.json) |

Le parcours mail compte **28 contrôles passés**, sans erreur JavaScript, erreur console ou requête externe observée. Le document natif et les courriels ne provoquent pas de débordement horizontal du document aux tailles vérifiées. Ce contrôle géométrique est complété par les mesures et captures de la sidebar ci-dessous.

Dernier récapitulatif contrôlé : `b40a99b4-bae7-479a-b7eb-205832312d0e`. Au dernier contrôle, il est courant, avec la note source `e34a49ae-97f2-40f0-9cb9-4b6534f88833`. La citation correspond exactement au texte de cette source immuable. Sa couverture reste explicitement **partielle**, car deux propositions attendent une confirmation humaine ; le test ne les a pas validées artificiellement.

## Défauts trouvés et corrections vérifiées

| Priorité | Déclencheur et constat avant correction | Correction et résultat après |
|---|---|---|
| P1 — perte de saisie | PUT A retenu, saisie B, changement d'onglet. La navigation attendait seulement A puis détruisait l'éditeur : B absent du backend. | `web/native.js:26` draine les générations tant que l'éditeur reste sale avant de rendre la main. Rejeu indépendant : A et B présents, sans temporisation masquant la navigation. |
| P1 — brouillon déjà périmé | Génération demandée pendant le PUT de la dernière note. Le POST résumé revenait avant l'ACK page : note absente du résumé, puis résumé immédiatement périmé. | `web/app.js:435` attend `preserveNativePage()` avant `api.generate`. Rejeu : aucun résumé avant ACK, dernière note présente et `stale=false`. |
| P3 — titre répété | Deux H1 « Courriels » et « Courriers » dans la vue mail ; espace vertical consommé sur mobile. | Titre du module devenu H2. Nouvelle lecture DOM aux trois tailles : un seul H1 « Courriels ». Captures mail actualisées. |

Les corrections applicatives ont été réalisées par l'agent principal. Cette recette n'a pas modifié le code de l'interface.

## Sidebar et captures longues

Les premières captures longues prises après un redimensionnement et avec un défilement non nul montraient une bande de sidebar et un lien d'évitement à mi-page. Ce constat visuel a été réexaminé au lieu d'être écarté sur le seul critère `scrollWidth`.

Après 350 ms de repos, au sommet puis à `scrollY=1100`, avant et après chaque capture, aux deux largeurs mobiles : sidebar `position:fixed`, `transform:matrix(1,0,0,1,-255,0)`, rectangle horizontal de −255 à 0, `inert=true`, `aria-hidden=true`. Le lien d'évitement est non focalisé, à `y=-100`, son bas à −52,75 px. Les captures viewport montrent le menu fermé hors écran. Les mesures sont inchangées après la capture longue et la révision de page reste 13.

Les captures de référence sont donc les nouvelles séries `native-*-top-*` et `native-*-scrolled-*`, accompagnées de [native-capture-metrics.json](native-capture-metrics.json). Les anciens `native-*-cards.png` restent une trace intermédiaire et ne doivent pas servir à juger la visibilité du menu.

## Captures de référence

- [Page et base natives sur ordinateur](native-desktop-final.png).
- [Fiche native dépliée à 390 px](native-390-record-detail.png) et [à 320 px](native-320-record-detail.png).
- [Viewport natif à 390 px après défilement](native-390-scrolled-viewport.png) et [capture longue depuis le sommet](native-390-top-full.png).
- [Liste mail à 320 px](mail-320-list.png), [message à 320 px](mail-320-message.png), [pièce à 320 px](mail-320-attachment.png).
- [Mail et contexte sur ordinateur](mail-1440-message.png).
- [Erreur de lecture simulée et récupérable](mail-390-error.png).
- [Récapitulatif alimenté par la dernière note](summary-context.png).

## Limites à conserver dans la présentation

- La base est modifiable sur ordinateur et présentée en fiches de lecture sur mobile. La recette n'a pas prouvé l'édition des cellules sur téléphone ; l'interface l'annonce.
- La saisie clavier a couvert le titre, un champ texte et un nombre. Elle n'établit pas le bon fonctionnement de toutes les propriétés, formules, relations ou vues avancées d'AFFiNE.
- Le récapitulatif est encore relu dans un éditeur texte Markdown. Cette recette vérifie la conservation du contexte et des citations, pas une expérience complète de traitement de texte.
- Le parcours n'a utilisé aucun Exchange réel. Connexion institutionnelle, droits, pièces réelles, volumétrie et règles de conservation demandent un pilote autorisé séparé.
- La protection publique HTTPS, l'authentification du staging, la sauvegarde serveur et la restauration relèvent de la recette du déploiement. Elles ne sont pas déduites de ces tests locaux.
- Il ne s'agit pas d'un audit WCAG complet, d'un test sur appareils physiques ou d'une certification RGPD. Les régressions clavier et mobiles explicitement décrites ont été vérifiées.

**Décision pour cette étape :** cette recette autorise la poursuite vers le staging protégé avec données fictives, sous réserve des vérifications propres au déploiement. Elle ne conclut pas à l'autorisation d'importer des courriers municipaux réels.
