# Design de l’espace Travaux intégré

**Document historique de la version0.2.** La refonte0.3 est définie dans [DESIGN.md](../DESIGN.md), à partir de la [galerie des parcours concurrents réels](ux-refonte-2026/concurrents/index.html) et de la [comparaison AVANT/APRÈS](ux-refonte-2026/comparaison.html). Les descriptions visuelles et le statut de publication ci-dessous correspondent à l'étape précédente.

Document mis à jour le **14 novembre 2026**. Il remplace la conception initiale d’un complément pilotant un espace AppFlowy séparé. Le produit actuel embarque le moteur documentaire **AFFiNE/BlockSuite 0.22.4** : pages, blocs et bases sont ouverts dans Travaux, avec la même session et la même navigation. L’utilisateur n’a pas à comprendre ni à ouvrir une autre application.

## Travail principal et structure

Le responsable travaux revient sur un chantier, écrit une note, prend connaissance des nouveaux échanges et prépare un compte rendu qu’il peut justifier. La page native est son document de travail. La mémoire confirmée, les propositions, les messages et leurs extraits ajoutent du contexte à ce même dossier ; ils ne forment pas un second produit.

L’accueil met d’abord en évidence les changements à relire et les chantiers concernés. La référence, le nom, l’état, l’avancement confirmé et le nombre de points à vérifier permettent d’identifier un dossier avant de l’ouvrir. Un chiffre ne doit pas être décoratif : une donnée absente ou non confirmée garde un libellé explicite.

Les espaces disponibles sont la vue d’ensemble, les chantiers et leur page native, les courriels, la revue, les imports, les récapitulatifs et les connexions. La configuration affiche les capacités réellement renvoyées par le serveur. Elle ne demande pas au père les secrets Exchange et ne permet pas au navigateur de choisir un endpoint LLM arbitraire.

## Page native et bases

La page est un **vrai document Yjs manipulé par les extensions natives** : paragraphes, listes, mise en forme et bases ne sont pas une imitation dans un textarea. Le backend Travaux gère les pages, leurs versions, la session et la persistance. Le serveur standalone AFFiNE et ses fonctions Enterprise ne sont pas incorporés. Voir le [contrat du moteur](../native-editor/README.md) et [le registre de code réutilisé](REUTILISATION_CODE.md).

Sur ordinateur, la base utilise ses propres modèles, propriétés typées et gestionnaires de vues tableau/Kanban. Les valeurs sont également lues par le `PlainTextAdapter` natif pour entrer dans le contexte textuel enregistré. Une ligne de cette base reste un bloc natif ; elle n’est pas automatiquement une sous-page de chantier. Formules, relations globales complètes et calendrier ne sont pas des capacités livrées par cette intégration.

La commande « Ajouter une base » appelle l’initialisation native réellement reprise d’AFFiNE. Elle ne fabrique pas une grille HTML destinée à remplacer le moteur. Les écrans et sources du module précisent les fonctionnalités désactivées : images, pièces, signets et embeds externes sans stockage pris en charge. L’absence de blob store n’est pas masquée par un faux téléversement réussi.

## Sauvegarde, notes humaines et mémoire

L’interface distingue **modifications en cours**, **enregistrement**, **page enregistrée** et **modifications non enregistrées**. Le bouton Enregistrer reste disponible. Une navigation attend les différentes générations de saisie encore en vol ; un premier acquittement ne signifie pas qu’une deuxième modification a déjà été sauvegardée.

L’état natif et son texte matérialisé sont enregistrés avec la révision attendue. En cas de conflit ou d’échec, la saisie reste locale et une erreur explique la reprise. Aucun écrasement forcé d’une version distante n’est présenté comme une résolution normale. La fermeture de page et les sorties du dossier sont protégées lorsque des changements restent non enregistrés.

Le contexte durable utilise les versions effectivement enregistrées : notes humaines, texte de la page et valeurs de ses bases conservent une provenance et une empreinte. Un nouveau mail crée des propositions ; il ne donne pas à l’analyse le droit de réécrire librement les notes de l’agent. Une génération intervenue avant l’acquittement d’une note ne contient pas magiquement cette note ; le changement durable ultérieur doit rendre le brouillon à actualiser. Les preuves de recette distinguent ce cas de l’inclusion d’un contenu déjà enregistré.

Ce modèle n’est pas une collaboration multi-utilisateurs en temps réel. Yjs sert ici à représenter et recharger le document natif ; sa présence ne prouve ni synchronisation en direct, ni résolution métier automatique de toutes les modifications concurrentes, ni mode hors ligne durable.

## Courriels dans le contexte du chantier

La consultation de courrier est **en lecture seule**. La recherche et les filtres par chantier/rattachement portent sur les messages disponibles dans le périmètre de l’espace. La source reste en texte brut : aucun HTML actif, image de suivi ou lien distant ne se charge à partir du corps du mail. L’application ne propose ni composition, envoi, suppression ou marquage comme lu.

Sur grand écran, la liste, le message et le contexte de chantier restent voisins. Un extrait de pièce s’ouvre sans imposer une navigation vers un outil tiers. Le lien chantier mène à sa page dans le même produit. Un message sans correspondance peut être rattaché explicitement ; ce rattachement ne valide pas le contenu qu’il annonce.

Le texte du mail et le texte extrait d’une pièce restent distingués. Les formats non extraits, erreurs, permissions insuffisantes et champs absents ne prennent pas l’apparence d’une source intégralement lue. La preuve textuelle ne remplace pas l’original pour une vérification exhaustive.

## Revue et récapitulatif

La revue présente le fait proposé, les valeurs précédentes comparables et l’extrait source ouvrable. Les effets sont explicites : accepter une nouvelle information, remplacer une valeur contradictoire, corriger avec un motif ou écarter. Une correction humaine est attribuée comme telle. Dates de réception/livraison et montants HT/TTC restent distingués.

Le brouillon de récapitulatif dépend d’un snapshot du contexte. Son contenu est éditable avant approbation ; les citations, avertissements de couverture partielle et éléments en attente restent accessibles pendant la relecture. Une nouvelle source ou un contexte modifié peut le rendre obsolète. L’approbation compare la version du contenu, du snapshot et du chantier ; elle ne se transfère pas silencieusement à un texte modifié. L’export correspond à la version approuvée.

## Mobile : lire le dossier et prendre une note

Le téléphone est un parcours principal, particulièrement pour un utilisateur qui peine avec les tableurs. Jusqu’à 640 px, les listes métier du shell deviennent des fiches étiquetées : référence, nom, état, évolution et points à vérifier, puis ouverture en un appui. Les valeurs complètes restent accessibles ; une colonne cachée ne tient pas lieu de parcours mobile.

Les bases de la page native ont une adaptation spécifique en fiches : mêmes `DatabaseBlockDataSource`, identifiants de lignes et valeurs Yjs que sur ordinateur. Chaque fiche donne accès à tous ses champs. **Cette surface est en lecture seule sur mobile, conformément à la restriction du SDK utilisé. L’édition des cellules mobiles n’est pas livrée.** Les paragraphes du document restent éditables par le moteur natif. La grille de bureau n’est pas simplement réduite à la largeur du téléphone.

Le courrier suit une séquence **liste → message → pièce**, avec retours visibles, conservation des filtres et retour de focus. Les preuves occupent l’espace utile sur téléphone ; la liste, le document et un panneau latéral ne sont pas comprimés côte à côte. Les contrôles du shell atteignent 44 px et la navigation rapide demeure accessible. Le clavier virtuel et les gestes d’un téléphone physique nécessitent encore une recette sur appareil réel.

## Direction visuelle et accessibilité

Le shell conserve un bureau municipal sobre : ivoire clair `#f5f4ef`, blanc `#ffffff`, encre `#18312c`, vert de travail `#234f43`, gris chaud et corail `#a83f35` réservé aux alertes. La typographie du shell est locale, Segoe UI/Aptos ; Georgia est limitée à l’accueil. Les blocs gardent leur comportement natif et s’inscrivent dans ce cadre commun. Certains menus natifs restent en anglais : la livraison ne prétend pas à une traduction exhaustive du moteur.

Les statuts sont textuels, la couleur les accompagne. Le focus clavier est visible ; la fermeture d’un panneau ou d’un dialogue retourne au déclencheur. La navigation mobile masquée est retirée de l’interaction. Les attentes, vides, erreurs, accès refusés et conflits ont des états distincts. Une erreur ne doit pas supprimer un brouillon pour donner l’impression d’un rechargement propre.

L’absence d’un audit RGAA complet demeure une limite. Les vérifications clavier et responsive obtenues ne permettent pas d’attribuer un niveau de conformité globale à tous les composants natifs et à tous les contenus futurs.

## Réutilisation, preuves et statut de livraison

Le [registre de réutilisation](REUTILISATION_CODE.md) donne les extraits réellement utilisés de Docs, Grist et OpenGateLLM, leurs origines, licences et adaptations. Ils complètent le moteur AFFiNE/BlockSuite ; les applications entières Docs/Grist/OpenGateLLM ne sont pas ajoutées au parcours. La [recherche publique française](ux-benchmark-2026/briques-publiques-france.md) et [l’étude ERP](ux-benchmark-2026/erp-et-agents.md) restent des études, pas des modules installés.

Les [preuves intégrées](ux-benchmark-2026/integration/) contiennent notamment la [base native relue après sauvegarde](ux-benchmark-2026/integration/database-result.json), les [courriels et pièces à 1440/390/320 px](ux-benchmark-2026/integration/mail-result.json), les [saisies pendant une requête en vol](ux-benchmark-2026/integration/inflight-result.json) et le [cas de récapitulatif devenu obsolète](ux-benchmark-2026/integration/summary-result.json). Les [captures du premier pilote](screens/index.md) restent historiques. La [galerie concurrentielle](ux-benchmark-2026/index-competiteurs.html) identifie ses images comme publications des éditeurs ; elles ne prouvent pas le fonctionnement de Travaux.

**Staging Hetzner : préparation réalisée, publication et recette publique en cours de validation.** Aucun succès HTTPS n’est déduit de la seule préparation. Le staging utilise des données fictives et une authentification ; il ne constitue pas une autorisation de traiter les mails municipaux ni une certification RGPD. Aucun serveur Exchange institutionnel ou modèle Mistral réel n’est déclaré connecté. Le [guide staging](../deploy/hetzner/README.md), [l’exploitation](exploitation.md) et [la protection des données](protection-donnees.md) précisent les étapes distinctes.
