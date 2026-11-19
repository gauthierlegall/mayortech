# Avant refonte : trois priorités visibles

Site publié observé le 14 novembre 2026 avec Chrome headless isolé, à 1440 × 1000, 390 × 844 et 320 × 844. Parcours : connexion, arrivée, chantier natif existant et courriels. Les accès sont lus en mémoire et ne figurent pas dans ce dossier. Aucun contenu n'a été saisi ; les révisions natives préexistantes sont inchangées. Zéro erreur JavaScript observée.

L'examen applique `better-interface` et ses six domaines, avec un périmètre ciblé sur la structure du parcours et la découvrabilité. La convention consultée est `docs/design.md` : la page native doit être le document de travail central. Le rendu public montre un écart entre cette intention et la place réelle du document. Il ne s'agit pas d'une demande de changer seulement les couleurs.

| Priorité | Écran et preuve | Constat observé | Changement attendu |
|---|---|---|---|
| 1 — MEDIUM, layout | Chantier mobile : [390 px](390-chantier-viewport.png), [320 px](320-chantier-viewport.png), [mesures](metrics.json). Cause actuelle : `web/native.css:11` place l'aside en première ligne ; `web/app.js:180` empile les onglets. | La zone native commence à **y=919 px à 390 px** et **y=1 055 px à 320 px**, pour un viewport de 844 px. Titre, deux actions, onglets et repères prennent le premier écran. Le document est accessible en défilant, mais son rôle principal n'est pas visible à l'arrivée. | Mettre le document et son action d'écriture avant les métadonnées ; rendre les repères secondaires repliables. À vérifier ensuite au même scroll initial, sans masquer les faits importants. |
| 2 — MEDIUM, layout/writing | Chantier ordinateur : [capture](1440-chantier-viewport.png), [éditeur mobile](390-chantier-editeur-viewport.png). Cause : `web/native.js:5`. | La barre expose « Ajouter un paragraphe », « Ajouter une base », « Enregistrer ». L'explication « Tapez / pour les blocs disponibles » vient **après le document**, à y=1 019 sur ordinateur et y=1 582 sur mobile 390. Les blocs riches ne sont donc pas annoncés au moment où l'on commence à écrire. | Montrer une commande « Ajouter un bloc » et un choix compréhensible près du curseur ou dans la barre du document. Garder le clavier `/` comme raccourci, pas comme unique découverte. |
| 3 — MEDIUM, writing/structure | Même [chantier ordinateur](1440-chantier-viewport.png) ; [vue mobile après défilement](390-chantier-editeur-viewport.png). Cause : `web/app.js:180` propose Page/Mémoire/Actions/Sources/Notes ; la vue native est à l'intérieur d'une base. | Le Kanban n'est pas absent du moteur : la base préexistante propose « Liste / Cartes ». Mais ces petits libellés sont à l'intérieur du document, sans mode « Tableau / Kanban » au niveau du chantier. Un utilisateur qui ne sait pas d'abord créer une base ne rencontre pas ces vues. Sur téléphone, la base devient une lecture en fiches. | Donner des modes de travail explicites Page / Tableau / Kanban, reliés aux mêmes données natives. Expliquer ce qui est disponible sur mobile. Ne pas promettre une édition mobile que le moteur ne fournit pas. |

Ces trois constats sont classés MEDIUM : la saisie est accessible en défilant et les capacités existent. Les captures ne prouvent ni une absence technique de blocs, ni un Kanban inexistant. Elles établissent un problème d'ordre, de vocabulaire et de visibilité du travail attendu.

## Couverture et limites

| Domaine | Contrôle effectué | Portée |
|---|---|---|
| Accessibilité | Inspection des libellés visibles et contrôles, tailles 320/390 | Pas de nouveau parcours complet lecteur d'écran ou clavier ; pas d'avis WCAG global. |
| Layout | Rendu réel, ordre visuel, hauteur de la zone native, contenu avant le premier écran | Deux constats prioritaires ci-dessus. |
| Writing | Vocabulaire Page/Mémoire/Sources, « Liste / Cartes », aide `/` | Découvrabilité des blocs et du Kanban à corriger. |
| Typographie | Lecture visuelle des écrans capturés | Pas de mesure exhaustive de contraste/agrandissement ou de changement de police proposé. |
| Couleurs | Observation des états et de leur texte | Contrastes non remesurés pour cette passe ; aucun avis de conformité. |
| UI | Cohérence des surfaces observée | Pas de défaut de décoration retenu face aux problèmes de parcours. |

Les courriels restent lisibles dans le même produit : [liste ordinateur](1440-courriels-viewport.png), [message ordinateur](1440-courriel-viewport.png), [message 390](390-courriel-viewport.png). Cela ne suffit pas à rendre visible le cycle courriel → évolution du chantier → document lié : la refonte doit relier ces actions dans le dossier plutôt qu'ajouter une nouvelle couche d'onglets.

Les [mesures brutes](metrics.json) enregistrent les rectangles, contrôles, textes et révisions. Les captures `*-viewport.png` montrent ce qui est vu à l'arrivée ; `*-full.png` documentent la page entière. L'étape APRÈS devra rejouer ces mêmes tailles et vérifier les actions réelles, la sauvegarde et les liens de documents.

**Verdict ciblé :** aucune nouvelle barrière bloquant le rendu n'a été observée ; la structure actuelle doit évoluer avant de présenter la page comme le centre visible du travail. L'évaluation APRÈS reste à faire.
