# Réemploi fidèle de Lovable v2 — audit du 15 novembre 2026

Le ZIP apporte deux nouveaux écrans : **Planning** et **Suivi terrain**. Chantiers, Actions, Messagerie, Documents et Paramètres sont identiques à la première archive. L'écart principal vient donc de notre intégration et de ses ajouts, pas d'une refonte de ces écrans dans la référence.

## Provenance et périmètre

- Archive utilisateur : `C:/Users/Utilisateur/Downloads/mayor-project-hub (1).zip`, 563 587 octets ; SHA-256 `5667d2a6d1d03259a3067863c2478243dc5ed582cd7ebd5bcd3812119fe46680`.
- Archive précédente : SHA-256 `0df387dfe867b63736ee3f6644bf6e7a65f8aa92459292ffdd88be41c6075e05`.
- Extraction vérifiée : `work/lovable-reference-v2`. Traversées, chemins absolus et liens symboliques refusés ; fichiers `.env*` exclus. Aucun script du ZIP exécuté.
- Inventaire et hashes : [provenance.json](provenance.json). Extraits des différences : [source-excerpts](source-excerpts/).
- Six fichiers ajoutés : `Planning.tsx`, `Terrain.tsx`, `planning-model.ts`, son test et les routes Planning/Terrain. Sept modifiés : `AGENTS.md`, `roadmap.md`, `ProjectDetail.tsx`, `Shell.tsx`, `model.ts`, `routeTree.gen.ts`, `styles.css`. Aucun supprimé.
- Les recommandations ci-dessous concernent le rendu ; les API FastAPI, droits, versions, preuves et actions Yjs existants sont conservés. Les modifications concurrentes de production ne font pas partie de cette revue.

## Captures réellement vérifiées

[Référence FHD Planning](reference/1920-planning.png) · [Référence mobile Planning](reference/390-planning.png) · [Dossier FHD](reference/1920-project.png) · [Dossier mobile](reference/390-project.png).

Seize captures de référence couvrent Planning, son dialogue, Chantiers, Dossier, Actions, Messagerie, Paramètres et Terrain, en 1920×1080 et 390×844. Leurs métadonnées sont dans [reference/captures.json](reference/captures.json). Aucun événement d'erreur JavaScript, aucune connexion externe tentée ; largeur du document égale au viewport. Le débordement Planning reste dans sa zone défilante.

Le rendu isolé utilise le code des composants et le CSS du ZIP sans réécriture. Seul le contexte est remplacé par un état React fictif en mémoire, sans Supabase ni compte. Les dépendances déjà présentes sont réutilisées en lecture ; `date-fns` 4.4.0 est employé, et non une réinstallation du lock de l'archive. Les adaptations exactes figurent dans [reference-runtime.json](reference-runtime.json).

La [baseline locale v0.6](baseline-v06/captures.json), dix captures sans interaction d'écriture, porte sur le bundle servi par `127.0.0.1:8766` avant reconstruction. Il ne contient pas encore les nouvelles routes Planning/Terrain : son `Not Found` ne diagnostique pas les fichiers en cours de développement. Les captures permettent surtout de comparer Chantiers, Actions, Messagerie et Paramètres.

## Directives concrètes par écran

| Surface | Référence v2 et écart observé | Réemploi attendu |
|---|---|---|
| Navigation | Cinq rubriques principales : Messagerie, Chantiers, Actions, Planning, Suivi terrain. La baseline garde Agenda et Assistant à la place de Planning/Terrain. | Reprendre ordre, icônes et espacement de `Shell.tsx`. Ajouter Agenda et À vérifier comme fonctions réelles demandées ; Assistant devient le bouton flottant. Ne dupliquer aucune entrée Assistant dans la barre mobile. |
| Navigation mobile | Le ZIP affiche six liens, dont Réglages. Les 390 px restent lisibles mais serrés. | Adaptation validée : cinq liens Messages/Chantiers/Actions/Planning/Terrain ; Agenda et Réglages dans le menu. Garder les intitulés courts et une seule barre fixe. |
| Dossier | Exactement six onglets : Page, Actions, Planning, Terrain, Documents, Échanges. Métadonnées sous le titre, deux colonnes sur ordinateur, une sur mobile. | Réutiliser `detail-heading`, `detail-meta`, `detail-tabs`, `detail-columns`. Propriétés dans une section dépliable de Page avec accès depuis le titre ; conserver les liens historiques. Ne pas rouvrir toutes les propriétés en permanence. |
| Page du dossier | Bandeau jaune compact, situation en prose, preuves en boutons courts, aperçu de notes et « Modifier les notes », photo et prochaine action à droite. | Conserver cette hiérarchie et l'édition native explicite. Les propositions secondaires restent repliées. Ne pas remplacer la prose par une liste de champs techniques. La photo du ZIP reste une illustration signalée, pas une preuve terrain. |
| Chantiers | La baseline reproduit déjà `page-heading`, `overview-band`, `attention-strip`, `filterbar`, `project-row`. Dans le ZIP, pictogrammes et avatars ont des couleurs distinctes ; notre liste est uniformément verte. | Garder la structure existante. Restaurer des variantes visuelles stables par chantier/initiales, sans déduire un statut. Conserver les vrais nombres. La première visite locale montre « 0 actions » avant le chargement natif puis neuf dans Actions : afficher un état de chargement au lieu d'un zéro non connu. |
| Actions | Structure déjà proche ; nous ajoutons filtre Chantier et bouton Actualiser. En mobile, ces contrôles repoussent la première carte d'environ 48 px dans la baseline. | Garder recherche, statut, responsable, priorité et bascule Liste/Kanban. Grouper les filtres secondaires sur mobile ou permettre leur repli. Le filtre chantier est utile dans la vue globale ; absent dans un dossier. Préserver les vraies lignes Yjs et l'édition avec contrôle de concurrence. |
| Messagerie | Écart le plus net parmi les écrans inchangés : le ZIP a trois colonnes internes (dossiers, liste, lecture). Notre baseline déplace les dossiers dans le Shell et affiche un composeur de liste plus technique avec bouton Chercher/Actualiser. | Reprendre `mail-layout`, `mail-folders`, `mail-list`, `mail-item`, `mail-reader`, `reader-empty`. Restaurer la colonne interne avec dossiers de messagerie et filtres réels par chantier. Garder la recherche dans la liste ; remplacer les commandes secondaires par une action discrète. Ne pas afficher deux arborescences de dossiers simultanément. |
| Paramètres | Le ZIP possède quatre onglets ; notre application ajoute Rôles et droits et Journal, qui sont réels. Palette et formulaires conservent déjà les classes Lovable. | Conserver ces capacités. Reprendre le petit surtitre « VOTRE ESPACE DE TRAVAIL », l'alignement des onglets et les sections aérées. Ranger les réglages avancés dans leurs onglets plutôt qu'ajouter des cartes au premier écran. Ne pas rétablir le faux bouton de remise à zéro du JSON démo. |
| Assistant | Aucun `ChatWidget`, aucune popup bas droite et aucune page Conversation dans le ZIP. Le bouton du dossier ouvre toujours un `Dialog` centré avec trois suggestions et question libre. | Le widget flottant est une adaptation demandée par l'utilisateur, pas un module prétendument copié. Réemployer boutons, typographie, bordures et suggestions du dialogue ; conserver réponses sourcées, historique et moteur configuré réels. |

## Planning : morceaux exacts à reprendre

Source : `src/features/workspace/Planning.tsx`, lignes 16–45 ; modèle `planning-model.ts`. Le Gantt du ZIP est une **grille CSS**, sans Frappe ni glisser-déposer. Notre moteur Frappe peut conserver son vrai déplacement et les actions Yjs tout en reprenant l'enveloppe visuelle :

- Une seule barre d'outils : mois précédent/suivant, filtre chantier, petite légende Action/Livraison confirmée, bouton « Planifier une action » dans le titre.
- Colonne fixe « CHANTIER / ACTION » de 260 px ; groupes chantier sur fond bleu pâle ; référence sous le nom. Lignes de 65 px, en-tête de 53 px, barres de 25 px.
- Noms et responsables à gauche, jours et week-ends différenciés à droite ; jalon en losange pour la **date confirmée**. L'annonce non validée reste un avertissement séparé relié à sa preuve.
- En mobile : colonne de 180 px, défilement horizontal de la grille seule, mêmes filtres et formulaire vertical.

Extrait CSS exact prêt à réemployer : [lovable-v2-planning-terrain.css](source-excerpts/lovable-v2-planning-terrain.css), SHA-256 `41bf704fc39566930e8540b62604a85ee53657f9b5577a0c4e6a9e06a4882e91`. Il correspond aux lignes 15–17 de `src/styles.css` ; ne pas copier ses règles globales `.detail-tabs` et `.mobile-nav>a` hors coordination.

Sélecteurs principaux : `.planning-toolbar`, `.month-navigation`, `.gantt-legend`, `.gantt-scroll`, `.gantt-board`, `.gantt-line`, `.gantt-heading`, `.gantt-label`, `.project-line`, `.gantt-track`, `.gantt-day`, `.weekend`, `.gantt-action-name`, `.gantt-bar`, `.gantt-milestone`, `.planning-pending`.

Limites fonctionnelles à adapter explicitement : le ZIP fixe novembre 2026, déduit parfois le début depuis la fin, écrit l'agrégat JSON par `state.update` et contient un avertissement portail codé en dur. Aucun de ces comportements n'est une vérité métier à réintroduire. Une date de début absente reste inconnue ; les propositions ne déplacent aucun jalon sans confirmation.

## Terrain : nouvel écran réutilisable

`Terrain.tsx` apporte réellement le titre « Suivi terrain », filtres chantier/statut, état vide sobre, liste de constats, formulaire et boutons Lever/Rouvrir/Créer une action. Réutiliser son JSX et les classes `.terrain-empty`, `.terrain-row`, `.terrain-copy`, `.terrain-controls`, `.form-pair`, `.terrain-section`.

Le modèle source garde le constat séparé des notes du dossier et un `actionId` lié. L'intégration réelle doit garder cette séparation et une création d'action idempotente, avec auteur/date/révision provenant du serveur. Les valeurs fixes du ZIP, sa liste de personnes fictives et son stockage JSON ne remplacent pas les API. Aucune photo terrain ou pièce jointe réelle n'est fournie par ce module.

## Ce que cette archive ne contient pas

Pas de nouveau système d'agenda, d'onboarding, d'édition des quinze propriétés, de popup conversationnelle ni de backend. Ces fonctions demandées restent des adaptations de nos capacités réelles au même langage visuel. Aucun achat, service externe, envoi de courriel ou installation de fournisseur n'a été réalisé pour cet audit.

## Recette après intégration

Comparer les mêmes cinq écrans et le dossier aux captures 1920/390, avec données fictives. Vérifier : une navigation unique, six onglets de dossier, Planning visible, grille confinée sur mobile, listes lisibles sans contrôles doublés, absence de faux zéro avant chargement, même action après changement de vue/rechargement et aucune perte d'édition à la navigation. Les captures présentes sont la référence et la baseline ; elles ne prétendent pas valider le prochain bundle.

## Lot Messagerie intégré après l'audit

`Mail.tsx` reprend la colonne interne de dossiers et de chantiers du JSX Lovable, avec les icônes Lucide et des compteurs réels. Le moteur existant `web/mailbox.js` conserve ses brouillons, sauvegardes avec révision, lecture et actions ; un emplacement de portail React ajoute l'aside. `mail-layout.css` adapte uniquement cette messagerie : trois colonnes 170/310/reste sur ordinateur, dossiers défilants et filtre chantier sur mobile, puis passage liste/lecture. Aucun style global ni Shell n'est modifié par ce lot.

Le lien `#/messagerie?folder=inbox&project=<id>` devient un vrai `project_id` API, filtré sur `source_links` avant calcul du total et pagination. Il ne recherche pas le nom du chantier dans le texte. Les compteurs de dossiers restent globaux. Les brouillons restent privés et globaux ; choisir Brouillons retire le filtre de sources. Un lien profond vers un courriel d'un autre chantier sélectionné n'affiche pas ce courriel.

Vérifications exécutées : 19 tests Python de messagerie, 12 tests Node de routes/sauvegarde/adresses, six parcours Chromium synthétiques sans requête externe, `ruff` et typecheck produit. La nouvelle recette couvre notamment le maintien du filtre chantier à la deuxième page de 51 courriels. Les captures de référence ne sont pas rebaptisées en captures de production ; la validation visuelle du prochain bundle est distincte.

Contrôle visuel du lot : [Messagerie intégrée FHD](mail-implementation/1920-mail.png) et [mobile](mail-implementation/390-mail.png). Un build Vite isolé dans `work/mail-layout-preview-dist` a fourni uniquement le HTML et les assets du frontend au navigateur sur l'origine locale 8766 ; API, cookies, CSRF et ressources natives restent inchangés. Ce contrôle ne modifie ni le bundle servi sur disque ni le serveur. [Métadonnées](mail-implementation/captures.json) : trois colonnes 170/310/reste en FHD, filtre mobile visible, largeurs 1920/390 exactes, aucune écriture et aucune erreur JavaScript. Il valide cette compilation, pas encore une publication distante.
