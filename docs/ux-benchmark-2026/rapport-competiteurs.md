# Un espace chantier natif, preuves à portée de main

Benchmark documentaire vérifié le **14 novembre 2026**. Huit images d’interfaces publiées par quatre éditeurs sont jointes. La [galerie illustrée](index-competiteurs.html) permet de les consulter et la [provenance JSON](provenance.json) donne les URL des pages et des fichiers, les dates connues, les dimensions, les empreintes et les limites.

**Nature des preuves : captures éditeur publiées.** Ce lot ne contient aucune capture live effectuée par nous dans un compte concurrent. Aucun pilotage UI n’a repris après l’arrêt du contrôle du navigateur par l’utilisateur. Les images ont été lues sur leurs URL publiques officielles, puis inspectées. Elles ne démontrent ni la rapidité d’un parcours ni le bon fonctionnement d’une version installée. Les dimensions des fichiers ne sont pas assimilées à un viewport CSS. Aucune image mobile native indépendante n’a été obtenue ; les règles mobiles ci-dessous distinguent documentation et propositions.

## Ce que montrent réellement les quatre références

| Référence | Preuve visible et source primaire | Principe utile au projet | Limite à conserver |
|---|---|---|---|
| Notion | **N01** : navigation de workspace, projets et tâches dans un même espace ; cartes avec propriétés utiles. **N02** : constructeur de disposition d’une page avec propriétés et panneau. **N03** : plusieurs vues sous le titre d’une même base. [Guide projets](https://www.notion.com/help/guides/getting-started-with-projects-and-tasks), [dispositions](https://www.notion.com/help/layouts), [vues](https://www.notion.com/help/views-filters-and-sorts). | Une fiche est une vraie page de la base. Les notes et les propriétés appartiennent au même objet. Des vues servent des intentions différentes sans dupliquer les données. | N02 montre un écran de configuration de disposition, pas un panneau de preuves métier déjà disponible. Les styles ou dates visibles dans les images ne garantissent pas leur actualité au jour de consultation. |
| AppFlowy | **A01** : aperçu des projets avec totaux, tâches terminées, reste et pourcentage. **A02** : tâches avec case, propriétaire, priorité et relation au projet. [Article officiel du 14 octobre 2026](https://appflowy.com/blog/project-task-expense-tracker). | Relier les actions au chantier plutôt que recopier des listes. Les agrégats peuvent rester explicables par leurs enregistrements source. | Ces deux images sont des extraits de bases publiés ; la navigation et l’éditeur de blocs complets n’y sont pas visibles. Une recette du client choisi reste nécessaire. Le pourcentage du modèle compte des tâches de même poids, pas l’avancement physique d’un chantier. |
| AFFiNE | **F01** : navigation du workspace, document « Launch tracker » et base incluse. **F02** : mêmes tâches en Kanban, avec état, propriétaire, date et priorité. L’éditeur date ces exemples du 5 novembre 2026. [Article et images officiels](https://affine.pro/blog/free-online-table-maker-tools). | Le document reste le contenant principal ; une base s’insère dans le travail écrit. Une autre vue change la lecture du même contenu. | Ce sont les exemples choisis par AFFiNE. Leur présence ne prouve pas la parité relationnelle avec AppFlowy ou Notion, ni l’ergonomie sur téléphone. Le Kanban présenté est large : ce n’est pas un modèle mobile à reproduire tel quel. |
| LaPetiteMarianne / Polaria Tech | **P01** : quatre zones visibles : filtres, liste, conversation, contexte du contact. L’image est publiée sur le [site Polaria actuel](https://tech.polaria.ai/differenciateurs), mais affiche des dates de février 2025. Le site annonce le regroupement des anciennes marques dans Polaria Tech. [Annonce](https://tech.polaria.ai/). | Conserver l’objet courant au centre et ses informations utiles à côté ; un passage à l’élément suivant ne doit pas faire perdre le contexte. | L’ancien [site LaPetiteMarianne](https://lapetitemarianne.com/) présente un chatbot citoyen. Ce n’est pas la preuve d’un workspace interne de travaux. La vidéo historique précédemment trouvée est privée ; aucune démo authentifiée n’a été examinée. |

Les images montrent une structure, pas une autorisation de réutiliser le code ou les visuels. Les décisions de licence, d’hébergement et de conformité sont traitées dans les audits dédiés ; ce benchmark ne leur attribue aucun label.

## Le changement nécessaire par rapport au premier pilote

Le premier pilote dispose de listes de chantiers, de sources, de revue et de récapitulatifs. Ces fonctions sont utiles, mais sa fiche chantier demeure une surface créée autour d’un outil de notes distinct. L’exigence exprimée demande une autre structure : **le moteur natif de pages, blocs et bases doit être le cœur du même produit**.

| Situation | Premier pilote à dépasser | Cible de conception — pas encore un résultat implémenté |
|---|---|---|
| Ouvrir un chantier | Une fiche spécifique puis un lien vers l’outil de notes. | Ouvrir directement la page native du chantier dans la même navigation, avec sa base d’origine et son historique de retour. |
| Écrire en réunion ou sur site | Une note additionnelle dans un formulaire métier. | Cliquer dans le corps de page et écrire de vrais blocs natifs : paragraphes, titres, listes et tâches, selon les capacités vérifiées du client retenu. |
| Lire un nouveau mail | Passer de la liste des sources à un écran de revue puis revenir au chantier. | Le mail est affecté au chantier ; sa page native reste ouverte. Un panneau « À vérifier » montre les changements proposés et leurs extraits. |
| Retrouver un chantier sur téléphone | Une adaptation de composants web conçus séparément du clone. | Une liste native lisible, puis une page native en colonne unique. Les mêmes objets et notes s’affichent sur bureau et téléphone. |
| Relire les preuves | Ouvrir un autre ensemble d’écrans. | Depuis le fait concerné, ouvrir le mail ou la pièce dans un panneau contextuel. Sur téléphone, ce panneau occupe l’écran et revient au même emplacement du document. |

Changer uniquement les couleurs, les marges ou les cartes ne suffit donc pas. Une intégration réussie se reconnaît au fait qu’un utilisateur peut naviguer, écrire, rechercher et vérifier dans un seul espace sans devoir comprendre l’existence d’AppFlowy derrière le produit.

## Structure recommandée de l’espace de travail

**Navigation commune : « Chantiers », « À traiter », « Récapitulatifs », puis les réglages accessibles selon le rôle.** Une recherche du workspace, une identité et une session. Le nom du logiciel sous-jacent appartient aux informations techniques, pas au trajet quotidien du père.

La base native « Chantiers » porte un identifiant immuable, la référence, le nom, l’état opérationnel, la dernière évolution validée, la prochaine échéance connue et le nombre de points à vérifier. Commencer par quatre vues enregistrées : « En cours », « À vérifier », « Échéances », « Tous ». Ce sont des vues des mêmes enregistrements. Leur faisabilité dans la version retenue doit être prouvée ; une liste statique qui ressemble à une base ne valide pas ce point.

Chaque enregistrement ouvre une **page native de chantier**, structurée avec un modèle prérempli :

1. **Repères courts** : référence, nom, état et dernière évolution validée. Les autres propriétés restent accessibles dans « Détails ».
2. **Situation à date** : mémoire validée et date de dernière mise à jour ; un avis clair signale les nouveaux éléments encore en attente.
3. **Notes de terrain** : espace de vrais blocs éditables par l’agent, sans formulaire obligatoire pour chaque phrase.
4. **Actions et décisions** : enregistrements natifs liés ou listes natives selon les capacités effectivement éprouvées. Une échéance inconnue reste inconnue.
5. **Historique et pièces** : liens vers les messages et versions, accessibles depuis le texte concerné et depuis un accès récapitulatif.

Le panneau contextuel « À vérifier » affiche une proposition à la fois : ancien fait, nouveau fait, date des messages et extrait exact ouvrable. Les commandes disent l’effet : « Ajouter cette information », « Remplacer la valeur précédente », « Corriger », « Écarter ». Un changement d’unité, de base HT/TTC ou de date ne peut pas disparaître dans une comparaison résumée. Les détails restent lisibles avant décision.

Les notes et changements de propriétés saisis directement dans la page native sont des **contributions humaines de première classe**. Le service les relit avec l’identité de la page/bloc, sa version et sa provenance. L’arrivée d’un mail crée des propositions, puis une version validée ; elle ne réécrit pas librement les notes. Une contradiction entre une note humaine et un mail est montrée à la personne, pas résolue silencieusement. Ce comportement est une exigence de notre outil, pas une fonction attribuée aux concurrents par les images.

## Parcours complet à reproduire dans le produit intégré

Un nouveau mail de chantier arrive dans le périmètre Exchange autorisé. « À traiter » indique les éléments nouveaux, sans demander au père de configurer le serveur. La correspondance à un chantier est explicite ; en cas de doute, il choisit le chantier avant toute mise à jour. L’ouverture mène à la même page native avec le panneau des propositions.

L’agent compare une date annoncée avec la date déjà validée, ouvre le passage du mail, corrige éventuellement la proposition puis la valide. Le panneau confirme le changement, la mémoire du chantier passe à une nouvelle version et ses notes de réunion restent présentes. Revenir à « En cours » rétablit recherche, filtre et position de défilement.

Depuis cette page, il prépare un récapitulatif à partir d’un état identifié du chantier. Le brouillon est éditable, ses preuves restent accessibles et la couverture partielle est affichée. Une nouvelle source reçue après sa création le marque à actualiser. L’approbation porte sur la version revue ; une ancienne approbation ne s’applique pas automatiquement à un nouveau contenu. L’export doit correspondre exactement à la version approuvée.

## Mobile : tâche principale, pas tableau rétréci

La documentation Notion décrit une navigation mobile persistante et une commande d’ajout de blocs au-dessus du clavier. Elle précise aussi que les mises en colonnes se replient et que les commandes de survol deviennent des commandes visibles. Ces comportements sont **documentés**, pas mesurés dans ce lot. [Navigation mobile officielle](https://www.notion.com/help/workspaces-on-mobile), [différences mobile/bureau](https://www.notion.com/help/notion-for-mobile).

Pour le père, la liste d’entrée doit permettre d’identifier un chantier sans déplacement horizontal : référence, nom, état, dernière évolution et badge de vérification. Une pression ouvre sa page native. Une recherche visible et les quatre vues suffisent au premier niveau ; les réglages de colonnes et de base restent secondaires.

Dans la page, le texte et les notes occupent une seule colonne. Une commande « À vérifier · 2 » ouvre un écran de revue avec un retour explicite au chantier. Le justificatif s’ouvre au passage utile ; revenir conserve la proposition courante. Il n’y a pas de conversation, tableau, propriétés et source comprimés côte à côte sur 390 px. Les grandes cibles tactiles et le comportement du clavier sont à tester sur le vrai moteur natif, pas simulés par une capture du bureau réduite.

## Critères de validation de la refonte

| ID | Preuve attendue dans la version intégrée |
|---|---|
| UX-B01 | Depuis la liste, ouverture d’un chantier, création d’un titre et d’une checklist natifs, rechargement puis retrouvailles du même document. Aucun lancement d’une autre application. |
| UX-B02 | Les vues « En cours » et « À vérifier » présentent le même enregistrement avec le même identifiant ; un changement validé se retrouve dans les deux. |
| UX-B03 | Une note créée dans les blocs et une propriété modifiée par l’agent sont relues dans la mémoire avec provenance ; un nouveau mail ne les écrase pas. |
| UX-B04 | Un mail sans correspondance peut être affecté au bon chantier sur mobile ; une affectation erronée est corrigeable sans dupliquer le document. |
| UX-B05 | Une contradiction affiche ancien/nouveau/extraits, puis une décision humaine crée une version et une trace ; aucune correction silencieuse. |
| UX-B06 | À 320 et 390 px, référence, nom, état, dernière évolution et compteur sont lisibles ; aucune table à faire défiler pour l’action principale. Tous les détails restent accessibles. |
| UX-B07 | Le clavier permet recherche, ouverture, édition native, accès aux preuves et fermeture des panneaux ; focus visible et retour au déclencheur. |
| UX-B08 | Clavier virtuel ouvert, l’agent peut finir une note et atteindre sa confirmation ; le texte ne disparaît pas derrière une barre fixe. Vérification sur un appareil réel requise. |
| UX-B09 | Un récapitulatif brouillon peut être corrigé, puis approuvé et exporté ; un nouveau mail le marque à actualiser avant réapprobation. |
| UX-B10 | Sans réseau, avec droits insuffisants ou lors d’un conflit de versions, le statut réel s’affiche, le contenu saisi n’est pas présenté comme sauvegardé à tort et une reprise claire existe. |

Ces critères sont une recette à exécuter après intégration. Les captures de concurrents n’en valent pas validation.

## Méthode de conception et périmètre de cette passe

Les références `shape` et `critique` d’Impeccable ont servi à cadrer cette recherche autour du travail réel, de la hiérarchie, de la continuité du contexte et de la charge cognitive. Le besoin, le public, la contrainte mobile et la direction native ont déjà été explicités par l’utilisateur ; cette passe n’ajoute pas de questionnaire. Elle produit un benchmark documentaire et un brief d’interaction. **Elle ne prétend pas être une exécution complète de la commande Impeccable critique**, qui impose des évaluations séparées et un détecteur sur l’application cible ; cette revue appartient au chantier de recette de l’application.

Le risque prioritaire est structurel : une double navigation et une double expérience d’écriture annuleraient la demande même avec une présentation soignée. Viennent ensuite la lecture mobile et le maintien des notes humaines. Les variations de style passent après la preuve que ces trois trajets fonctionnent dans le moteur retenu.
