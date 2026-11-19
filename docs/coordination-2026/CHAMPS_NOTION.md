# Couverture des propriétés de la référence Notion

Les huit photographies fournies le 15 novembre 2026 servent uniquement à relever les noms et les types des colonnes. Aucun dossier, nom de personne, montant ou contenu réel photographié n’a été repris dans le code, les jeux de démonstration ou cette documentation.

| Libellé observé | Clé API | Présence et comportement |
| --- | --- | --- |
| Dossier | `name` | Titre du projet canonique, modifiable ; pas de second titre parallèle. |
| Catégorie | `category` | Texte modifiable ; valeur vide permise, aucune catégorie supposée. |
| Coût estimé | `estimated_cost` | Montant en euros distinct du réel ; chaîne décimale exacte, deux décimales au maximum. |
| Coût réel | `actual_cost` | Montant en euros distinct de l’estimation ; zéro et absence de valeur sont différents. |
| Date demande | `request_date` | Date civile valide au format `AAAA-MM-JJ`, distincte de l’échéance. |
| Demandeur | `requester` | Texte modifiable, distinct de l’entreprise et du responsable. |
| Entreprise | `contractor` | Texte modifiable ; éventuel fait confirmé initial signalé comme tel. |
| Lieu | `location` | Texte modifiable ; une suppression explicite masque aussi une valeur initiale issue des faits. |
| Notes | `notes` | Texte multiligne modifiable, jusqu’à 40 000 caractères. |
| Observation | `observation` | Texte multiligne distinct des notes, jusqu’à 40 000 caractères. |
| Pièces jointes | `documents` | Originaux réellement conservés et rattachés au projet, disponibilités, téléchargement et accès à Documents. Aucun faux fichier créé à partir d’un libellé. |
| Priorité | `priority` | Choix modifiable : Urgente, Haute, Normale, Basse, ou non renseignée. Seuls Urgente et Haute sont confirmés par les photographies. |
| Service / Responsable | `service_owner` | Texte modifiable, distinct du demandeur. Le fait initial `owner` peut fournir une valeur, avec sa provenance. |
| Statut | `status` | Projet canonique ; À traiter, En cours et En attente sont les valeurs observées. Terminé, Bloqué et Annulé complètent les besoins du suivi. |
| Échéance | `deadline` | Date civile distincte ; une date de livraison ne la remplit pas automatiquement. |

L’onglet **Propriétés** expose les quatorze champs éditables et la liste des pièces jointes. Les pièces proviennent du circuit d’import et de rattachement de courriels existant ; leur message source et leur original restent accessibles dans Documents. L’ajout de données de comptes réels reste interdit en démonstration publique et nécessite un espace protégé. Aucune importation automatique depuis Notion n’est annoncée.

## Écriture et provenance

`GET /api/v1/projects/{id}/properties` renvoie les valeurs, leur origine, les documents, la révision propre aux propriétés et celle du projet. Les origines sont `unset`, `project`, `confirmed_fact` et `human_property`. Un budget générique n’est pas présenté comme un coût estimé ; aucun coût réel ni aucune date de demande n’est déduit d’un courrier.

`PATCH /api/v1/projects/{id}/properties` exige `expected_revision`, `expected_project_revision` et un objet `changes`. Les deux versions doivent correspondre. Les valeurs monétaires arrivent sous forme de chaînes ; les nombres flottants sont refusés. Les espaces français et la virgule sont acceptés à la saisie puis normalisés, par exemple une saisie fictive `1 234,50` est conservée comme `1234.50`.

La transaction conserve une note source humaine immuable, la provenance par champ, un événement et un audit. Elle ne crée ni n’accepte de candidat extrait. Le nom et le statut écrivent le projet canonique ; les autres propriétés restent une couche humaine explicite et ne modifient pas les faits confirmés. Les récapitulatifs antérieurs deviennent obsolètes par la révision du projet. Les anciennes notes et sources restent des archives consultables.

Les autorisations sont vérifiées dans le service et sur les routes HTTP : tenant identique et accès `workspace.read` ou `workspace.write`. Les téléchargements gardent l’autorisation du circuit documentaire existant. Le schéma s’ajoute aux tables existantes, sans modifier leur stockage ni les modules protégés de dépôt.

## Saisie et concurrence

Le panneau conserve le formulaire lors d’une erreur ou d’un conflit. Le bouton d’actualisation conserve uniquement les champs que la personne avait modifiés et signale les valeurs ayant aussi changé à distance. Une nouvelle sauvegarde explicite reste nécessaire. Le contrôleur `registerPreserver` enregistre avant navigation ; un refus de sauvegarde bloque cette navigation. Aucune donnée du formulaire n’est placée dans le stockage local du navigateur.

Validation ciblée : 17 tests Python couvrent les quinze libellés, les limites et types, les coûts distincts, les textes longs, les dates, la provenance, l’absence d’acceptation de faits, les deux versions, l’isolation tenant, les accès, les originaux et les routes HTTP. Le composant et ses styles sont compilés par le build du frontend produit. La recette visuelle de l’intégration relève du rapport général de coordination.
