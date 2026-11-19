# APRÈS — le chantier devient l'espace de travail

**Recette locale validée le 14 novembre 2026.** Les trois problèmes ciblés dans [l'audit AVANT](../avant/constats.md) ont une réponse visible et fonctionnelle : document en premier écran, ajout explicite de blocs, modes Page / Tableau / Kanban / Documents / Échanges. Les vues Tableau et Kanban manipulent les mêmes lignes natives enregistrées ; les documents téléchargés sont les vrais originaux conservés.

L'AVANT a été capturé sur le staging publié. L'APRÈS de ce dossier a été capturé sur **la nouvelle version locale `127.0.0.1:8765`**, avec le bundle natif final rechargé. Une [recette publique distincte de 28 contrôles a ensuite validé la version publiée](../public/rapport.md) ; la galerie de comparaison utilise désormais ses vraies captures HTTPS.

## Les trois priorités, avant et après

| Priorité | Avant, constat public | Après, résultat local vérifié |
|---|---|---|
| Document central sur mobile | Zone native à y=919 px en 390 px, et y=1 055 px en 320 px, viewport 844 px. Repères et onglets précèdent toute écriture. | Zone native à **y=388 px en 390 px** et **y=407 px en 320 px**. Informations et preuves sont repliées ; le document et l'ajout de bloc sont visibles au premier écran. |
| Blocs découvrables | Paragraphe/base/enregistrement ; aide `/` sous le document, hors premier écran. | Menu visible **+ Ajouter un bloc** : titre, sous-titre, texte, liste, case, citation, séparateur. H2, liste, case à cocher, citation et séparateur ont été ajoutés par l'interface et conservés par la vraie API. |
| Modes de travail explicites | « Liste / Cartes » dans une base, sans modes de chantier Tableau/Kanban. | Les **cinq modes sont visibles sans défilement horizontal à 320 et 390 px**. Tableau/Kanban sont de vraies vues natives, de même base et mêmes IDs. Documents et Échanges sont reliés au chantier. |

Les données et titres de chantier diffèrent entre les deux environnements ; les mesures documentent l'ordre et la place de l'éditeur, pas une comparaison chronométrée d'utilisateurs.

## Parcours réellement testés

**29 contrôles intégrés passent**, puis **6 contrôles du bundle final** et **16 contrôles de finition** ont été rejoués. Aucune erreur JavaScript ou console ni requête externe n'a été observée pendant le parcours intégré.

- Courriel fictif contenant une action, un TXT et un PDF créés pour cette recette. Action confirmée via la revue ; import dans la base native une seule fois.
- Saisie de blocs au clavier ; texte matérialisé dans la page sauvegardée. Changement de vue et rechargement conservent les IDs des blocs.
- Kanban réellement actif, passage au Tableau, ajout d'une action manuelle puis rechargement : deux lignes, mêmes IDs, aucun doublon du fait confirmé. Base `SRLEvue7GX` ; lignes `TK5HHPYtyT` et `l3EFmnzjvK`.
- PDF : extrait ouvert depuis la bonne source, téléchargement par l'interface, SHA-256 du fichier identique aux octets attendus. Les trois originaux EML/TXT/PDF ont aussi été comparés octet par octet à l'import ; en-têtes `attachment` et CSP `sandbox` vérifiés.
- Échanges du chantier filtrés automatiquement, message ouvert dans la route du même dossier, retour mobile conservant le filtre. Preuve source ouvrable depuis les informations repliées.
- Mobile 390/320 : Page, menu de blocs, Kanban groupé, Tableau en fiches, Documents et Échanges. IDs des fiches égaux aux lignes natives de bureau ; pas de débordement horizontal du document ; Échap ferme le menu et restaure le focus.
- Émulation mobile avec toucher : saisie d'une **nouvelle note native**, sortie immédiate vers Documents sans attendre l'autosauvegarde, retour et rechargement. Même bloc et texte conservés. Génération par l'interface : note présente dans le récapitulatif courant, avec citation de sa source humaine actuelle. La couverture demeure partielle car une proposition attend encore une validation.
- Finition clavier : Échap ferme le menu des blocs et rend le focus à son déclencheur ; clic extérieur le ferme. Les vues ont un seul arrêt Tab, acceptent les flèches, Home/End et une activation avec Entrée. L'éditeur reste inerte et Enregistrer désactivé pendant le chargement retenu de son état, puis deviennent utilisables une fois le montage terminé.
- Finition Kanban : quatre colonnes natives de 240 px, toutes visibles à 1440 px ; aucune colonne sans statut vide ni champ vide parasite. La carte ne montre plus l'URL brute. Le Tableau conserve le lien, nommé « Voir le courriel source » pour l'accessibilité et affiché « Voir l'échange ».

Le nouveau parcours d'arrivée `#/workspace` a également été observé : il ouvre directement un chantier dans son document. L'ouverture peut initialiser automatiquement la page d'un dossier jamais ouvert ; aucune saisie humaine n'a été faite dans les chantiers de référence hors du chantier de recette.

## Preuves compactes

- [Comparaison visuelle](../comparaison.html).
- [Résultats des 29 contrôles et métriques](resultats.json), [contrôles du bundle final](bundle-final.json), [16 contrôles de finition](polish-final.json), [note mobile et récapitulatif sourcé](note-mobile-resultat.json).
- Page : [390 px](390-page-viewport.png), [320 px](320-page-viewport.png), [menu de blocs 320](320-menu-blocs-viewport.png).
- [Kanban bureau avec les deux lignes finales](1440-kanban-viewport.png), [Tableau bureau](1440-tableau-viewport.png), [Kanban mobile 390](390-kanban-viewport.png).
- [Documents à 320 px](320-documents-viewport.png), [documents bureau](1440-documents-viewport.png), [échange dans le dossier](1440-echange-viewport.png).
- [Nouvelle arrivée bureau](1440-arrivee-viewport.png), [nouvelle arrivée mobile](390-arrivee-viewport.png).

## Limites et suites

Le bureau utilise les cellules natives éditables. Sur téléphone, les bases restent en **lecture par fiches** et l'interface l'annonce ; les notes en blocs sont éditables. Cette recette en émulation ne remplace pas un essai sur téléphone physique avec clavier virtuel.

Certains menus secondaires du SDK ne sont pas intégralement traduits. La colonne vide « Ungroups » et les URL brutes des cartes ont été corrigées et revérifiées. Les relations/formules avancées, pièces intégrées comme blocs et collaboration simultanée ne sont pas présentées comme livrées. Le récapitulatif conserve son éditeur de texte Markdown.

La couverture de cette passe porte sur le parcours réel, le responsive, les blocs, la persistance, les liens et les contrôles clavier décrits. Un audit complet lecteur d'écran, RGAA, contraste de toutes les surfaces, langues et appareils n'a pas été réalisé. La réussite locale n'établit pas une qualification de production ou une conformité RGPD.

**Verdict local : Approve pour ce parcours fictif et sa refonte fonctionnelle.** La [recette publique ultérieure](../public/rapport.md) complète ce résultat sans confondre les deux environnements.
