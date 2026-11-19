# Planifier une action — chantier et responsable explicites

La demande du 16 novembre 2026 concernait en priorité le chantier et le responsable proposés dans « Planifier une action ». La [capture et les valeurs initiales](before/dialog.json) montraient un choix automatique de la première action non planifiée, sans nom de chantier dans le dialogue global. Les responsables proposés étaient limités aux membres et au propriétaire de la seule action sélectionnée ; une action vide pouvait donc ne proposer que « Visiteur ».

## Comportement livré

- Dans le planning global, le dialogue commence par **Choisir un chantier**, puis **Choisir une action**. Aucun premier chantier, action ou responsable n’est imposé. Le sélecteur d’action reste désactivé avant le choix du chantier et ses options ne comprennent ensuite que les actions de ce chantier.
- Dans un dossier, le chantier ouvert est nommé et verrouillé. Les actions d’un autre chantier ne peuvent pas apparaître dans ce sélecteur. Le lien de création conduit aux Actions du chantier choisi, au lieu de retomber sur le premier dossier d’un formulaire global.
- Le responsable enregistré sur l’action est repris tel quel, y compris lorsqu’il ne correspond pas à un membre. Le champ accepte un nom ou un service et suggère les valeurs réellement présentes dans les actions et les membres. Un responsable vide reste à attribuer.
- Une saisie non enregistrée n’est plus effacée silencieusement lors d’un changement de chantier ou d’action : le formulaire permet de la conserver ou de confirmer le changement.
- **Enregistrer les modifications** sauvegarde ensemble les dates, le responsable, le statut et l’avancement. Début et échéance sont facultatifs ; seules deux dates complètes et valides produisent une barre dans la frise. Aucune date ni progression n’est inventée.
- **Retirer de la frise** prépare l’effacement de la date de début dans le formulaire. L’échéance et les autres champs saisis sont conservés ; aucune écriture n’a lieu avant l’enregistrement explicite. Annuler conserve l’état enregistré.
- Statut et pourcentage restent indépendants. Une contradiction connue est expliquée sans changer automatiquement l’un des deux champs. Le statut personnalisé et l’avancement absent restent préservés.
- Lire le message lié garde le formulaire et sa saisie ouverts sous l’aperçu de la source.

Les écritures restent les commandes existantes du document Yjs, avec leur contrôle de révision. Aucun module backend, SDK natif, rôle ou stockage d’action supplémentaire n’a été modifié.

## Vérification du bundle de production

La [recette finale](local/checks.json) passe **27 contrôles** sur `http://127.0.0.1:8766`, avec le bundle `index-BnmrdBgI.js` réellement servi. Aucun asset ni résultat d’API n’est remplacé. Les contrôles concernent les tailles 1920×1080, 390×844 et 320×760, avec Chrome réel sans interface visible.

Le parcours global vérifie le contexte vide initial, la restriction des actions au chantier choisi, la conservation du responsable et de la saisie, les avertissements, le retrait préparé et l’ouverture des sources. Le parcours dans le dossier vérifie le chantier verrouillé et ses seuls identifiants d’actions. Les noms de responsables enregistrés restent disponibles sans forcer l’acteur courant.

Une seule action du dossier fictif préexistant `QA-PROP-…` a été enregistrée : dates et progression vides, responsable saisi, **un seul PUT**. Le rechargement du vrai SDK retrouve les mêmes identifiants et le même nombre de lignes, sans modification des faits confirmés. Les champs initiaux de cette action ont ensuite été restaurés avec un second PUT. Les dossiers principaux n’ont reçu aucune écriture pendant les essais de formulaire.

Les **17 tests du modèle** passent, dont sept ajouts couvrant dates partielles, retrait consolidé, actions homonymes dans deux chantiers, responsables non membres, contradictions statut/avancement et détection d’une saisie non enregistrée. Six de ces ajouts échouaient avant correction ; le cas des dates impossibles préserve une validation déjà existante. TypeScript et la suite Node globale courante passent également (97 tests au gel).

Les [captures finales](local/) montrent le choix vide et le formulaire aux trois largeurs. Le fichier `dev-navigation-timeout.json` conserve un passage partiel du serveur de développement : ses 17 contrôles étaient verts avant l’expiration d’une attente de navigation sous HMR. La recette complète du bundle de production ci-dessus résout cette incertitude ; elle ne contient aucune erreur JavaScript ou HTTP.

## Vérification HTTPS publiée

La version 0.8.0, release `20261116T094932Z-306a53`, est également vérifiée sur [travaux.kerforge.com](https://travaux.kerforge.com). La [recette publique](public/checks.json) passe **28 contrôles**, avec Chrome et une validation TLS normale, sans substitution d’assets ou de résultats d’API.

Le choix vide initial, les actions et propriétaires de deux chantiers réels de la démonstration, la saisie d’un responsable non membre, le changement de contexte explicite, le maintien du brouillon pendant la lecture de sa source et le chantier verrouillé dans le dossier sont vérifiés. Les [cinq captures](public/) couvrent 1920, 390 et 320 px et conservent DM Sans sans débordement horizontal.

Aucun enregistrement, import ou effacement n’est demandé : **zéro PUT, PATCH ou DELETE**. Les faits, notes et états natifs complets — révisions comprises — des deux dossiers sont strictement identiques avant et après ; leurs empreintes sont conservées dans le rapport. Les seuls POST de page obtiennent des pages préexistantes de façon idempotente, sans les sauvegarder. Aucun test d’édition ni dossier QA n’est créé dans la démonstration publique.

Toutes les données utilisées sont fictives. Ces contrôles ne constituent pas un essai sur un téléphone physique.
