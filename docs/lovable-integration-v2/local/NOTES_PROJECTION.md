# Correction de l'aperçu Notes — preuve de non-mutation

## Cause

`getText()` exporte intentionnellement toute la page AFFiNE via `PlainTextAdapter`, y compris la base Actions. Le backend conserve cet export complet comme note `manual_affine`. L'aperçu du dossier affichait ce texte comme un paragraphe, donc rendait le tableau Markdown des actions en brut.

## Règle appliquée

La nouvelle méthode de lecture `getNotesText()` travaille sur un **clone du snapshot SDK**. Elle retire seulement le bloc `affine:database` dont l'identifiant correspond exactement au marqueur Yjs `actionDatabaseId`. Aucun rapprochement par titre, texte, colonnes ou syntaxe Markdown. Les paragraphes autour du bloc et les bases humaines, y compris une base nommée « Actions », restent présents.

`getText()` et la sauvegarde gardent l'export complet. L'aperçu frontend remplace une matérialisation uniquement si son lien `remote_id` désigne la même page et si son texte enregistré correspond à l'export complet lu. Une projection périmée ne remplace rien. Le chargement affiche un état explicite, sans faire clignoter le tableau brut ; en cas d'échec, le texte enregistré reste disponible et l'indisponibilité est signalée.

## Vérifications

- Trois tests natifs après échec initial : seul bloc marqué retiré, contenu humain et table homonyme conservés, snapshot original inchangé même après normalisation de présentation.
- Six tests frontend après échec initial : lien de page/texte exact, notes humaines intactes, projection périmée refusée, chargement explicite, échec sans perte et cas contenant uniquement des actions.
- Typecheck produit vert ; contre-revue indépendante sans P1/P2, incluant la révocation de l'identité pendant le nouvel `await` : pas de publication du cache ni de notification après révocation.
- [Preuve Chromium du moteur réel](notes-projection-purity.json) : export complet avant/après identique, état Yjs avant/après identique octet pour octet, deux paragraphes humains préservés et trois titres de lignes gérées exclus de l'aperçu. Texte complet : 2 097 caractères ; aperçu : 407 caractères.
- Aucun `PUT`, `PATCH` ou appel de sauvegarde durant cette preuve. Seul un appel idempotent d'obtention de la page native a été nécessaire.

Aucune modification de stockage, de schéma ou de contenu enregistré. Le parent réalise les compilations, la recette visuelle et la publication ; ce document ne prétend pas valider une publication distante avant son contrôle.
