# Le dossier de chantier vivant — cadrage avant reprise du code

**Historique du cadrage.** Une instruction ultérieure a autorisé l'audit des écrans et l'implémentation de la refonte0.3, maintenant [publiée et vérifiée](ux-refonte-2026/public/rapport.md). Les mentions de pause ci-dessous décrivent le moment de cette réflexion. Le workflow cible complet reste plus large que les fonctions démontrées par cette version.

14 novembre 2026. **Proposition de workflow, pas fonctionnalités déjà livrées.** Les modifications applicatives et les déploiements sont en pause à la demande de l'utilisateur. Ce document fixe le comportement attendu avant une nouvelle interface.

## 1. Résumé

Un responsable travaux continue à recevoir ses courriels dans Outlook. L'outil rassemble les échanges autorisés, leurs pièces et les notes de terrain dans un dossier de chantier durable. L'IA propose ce qui change ; les décisions, documents applicables, actions et récapitulatifs restent reliés à leurs sources.

La valeur recherchée est de retrouver immédiatement où en est un chantier, pourquoi sa situation a changé, quel document utiliser et quelle action accomplir. AFFiNE apporte l'écriture en blocs ; le produit doit apporter les relations et l'évolution du dossier.

## 2. Contexte et diagnostic de l'existant

Le circuit actuel du père passe d'Outlook à Gmail, ChatGPT et Notion. La messagerie est annoncée comme un Exchange local ou géré par un prestataire. Le périmètre initial est son suivi des travaux, avec une lecture mobile confortable.

Le pilote publié contient un vrai éditeur AFFiNE, une mémoire sourcée, des imports et des récapitulatifs. Cependant, la lecture du code montre trois écarts :

- Les lignes créées dans une base AFFiNE et les actions métier extraites des mails ne constituent pas encore le même ensemble d'objets. Leur présence simultanée ne donne donc pas un Kanban alimenté par les courriels.
- Le traitement des pièces conserve empreintes, métadonnées et texte extrait. Il ne fournit pas encore une gestion complète des fichiers originaux, de leur aperçu et des versions applicables.
- Le serveur Exchange réel n'est pas raccordé. Le fonctionnement sur données fictives ne prouve pas la collecte institutionnelle.

Ces écarts imposent de concevoir le parcours et les relations avant de modifier les couleurs ou d'ajouter des boutons.

## 3. Objectif et critères de réussite proposés

Un jeu d'acceptation fictif comportera un chantier, cinq mails, deux versions d'un devis, un report et une note terrain. Les critères proposés sont :

1. Les cinq mails rejoignent le même dossier sans créer cinq projets ou cinq actions identiques ; tout rattachement ambigu reste à confirmer.
2. Le report affiche ancienne et nouvelle dates avec leur preuve ; la validation met à jour la même échéance dans chaque vue et garde son historique.
3. Une action est retrouvée dans la page, le tableau et le Kanban avec le même identifiant, les mêmes documents et le même état.
4. Le fichier original, son mail d'origine et la version déclarée applicable sont ouvrables depuis le chantier et depuis l'action concernée.
5. Un récapitulatif nouveau reprend les dernières décisions, distingue les annonces non confirmées et cite les sources. Les notes personnelles et anciennes versions approuvées restent conservées.

Ce sont des critères à démontrer dans la prochaine version, pas des résultats acquis.

## 4. Utilisateur et situation d'usage

Le premier utilisateur est le responsable des travaux qui traite les mails au bureau et consulte le dossier sur téléphone pendant une visite. Il veut comprendre les changements et retrouver une pièce sans refaire son classement. La manipulation d'un tableur large est une friction connue.

Le futur usage par plusieurs services ou plusieurs collectivités reste une extension. Il ne doit pas élargir le premier parcours à l'état civil, la comptabilité ou un ERP municipal complet.

## 5. Proposition de valeur

- **Qui :** responsable travaux qui suit plusieurs dossiers et entreprises.
- **Pourquoi :** chaque nouvel échange peut changer une date, un montant, une action ou une version de document.
- **Avant :** classement et résumés entre plusieurs outils, contexte à reconstituer et pièces dispersées.
- **Comment :** un dossier durable relie sources originales, informations proposées et confirmées, documents, décisions, actions et notes.
- **Après :** l'agent voit le changement utile, décide si nécessaire, puis retrouve le même état dans toutes les vues.
- **Alternatives :** espace Notion organisé manuellement, logiciel projet avec messagerie, GED ou combinaison de ces outils.

La proposition est : « Tes courriels et documents alimentent le suivi du chantier ; tu retrouves son état, ses preuves et la prochaine action dans la même page. »

## 6. Parcours cible et écrans

### Un cas concret, entièrement fictif

L'entreprise envoie : « La livraison du portail passe du 18 au 25 novembre ; devis révisé joint. Merci de confirmer l'accès vendredi. »

| Étape | Travail du système | Ce que voit ou fait le responsable |
|---|---|---|
| Réception | Collecter le mail et ses pièces dans le périmètre Exchange autorisé ; identifier les doublons | Il continue à utiliser Outlook ; aucun transfert manuel vers une boîte personnelle |
| Rattachement | Retrouver le chantier avec référence, fil connu et indices ; demander une décision si nécessaire | « Ce message concerne-t-il le chantier Portail ? » seulement en cas d'ambiguïté |
| Classement documentaire | Conserver le fichier original, son empreinte, son origine et son lien au chantier ; proposer sa famille et sa version | Le devis apparaît dans Documents, avec le mail d'origine ; « reçu » et « applicable » restent distincts |
| Comparaison | Comparer les informations reçues au contexte courant, identifier contradiction et action | « Livraison annoncée : 18 → 25 novembre », « Nouveau devis », « Accès vendredi à confirmer » |
| Décision | Enregistrer les validations/corrections et leurs motifs | Confirmer le report, garder le devis en examen, créer ou mettre à jour l'action d'accès |
| Mise à jour | Mettre à jour les objets communs et la synthèse de travail | La même échéance change dans la page et le suivi ; le Kanban montre l'action liée au mail et au devis |
| Consultation | Réunir état courant, chronologie et sources autorisées | Sur téléphone : situation, prochaine action, accès direct au devis ; question possible « pourquoi la livraison a changé ? » |
| Récapitulatif | Construire une nouvelle version à partir du contexte courant et des points en attente | Relire et exporter ; l'ancien récapitulatif approuvé garde sa version et son contexte |

Le moment de valeur est la première fois qu'un second mail enrichit le dossier existant et que l'utilisateur retrouve immédiatement l'ancienne annonce, la nouvelle et la pièce associée. La friction à supprimer est le re-classement manuel à chaque mail. Le point de confiance est la possibilité de vérifier et corriger une proposition sans perdre la source.

### Organisation de l'espace

La navigation garde les chantiers accessibles. L'accueil présente les évolutions à traiter et les dossiers concernés, sans imposer une liste brute de tous les mails.

Chaque chantier possède quatre entrées :

1. **Page du chantier** : situation courante, dernières évolutions, notes libres en blocs et documents importants. Les sections synchronisées sont distinctes du carnet personnel ; une synthèse automatique ne réécrit pas librement les notes.
2. **Actions** : Tableau, Kanban et fiches mobiles sont des vues des mêmes actions. Une carte ouvre responsable, échéance, état, échanges et pièces liés. Le statut global du chantier reste distinct du statut de ses actions.
3. **Documents** : originaux ouvrables, aperçu lorsque possible, versions, type, état et liens vers chantier/actions/décisions. Un document peut être inséré dans une page par son lien durable, sans copie divergente.
4. **Échanges** : conversations rassemblées dans le contexte du chantier, pièces et changements proposés. Le mail complet est accessible depuis un fait, une action ou un document.

La chronologie montre les évolutions métier : annonce reçue, date confirmée, document déclaré applicable, action terminée, note terrain. Un résumé de mail isolé ne remplace pas cette histoire.

### Règles d'automatisation

L'ingestion, la détection de doublons, le classement à forte certitude et la préparation d'une proposition peuvent être automatiques. Une annonce de fournisseur ne devient pas une décision de la mairie. Les changements de montant, d'échéance applicable ou de document validé passent par une décision explicite. La notion de certitude et les seuils devront être évalués, pas affichés comme une précision scientifique inventée.

L'IA utilise le contexte autorisé du chantier et retrouve les passages pertinents ; elle ne se contente pas du dernier résumé généré. Les dates de réception et les dates auxquelles les faits s'appliquent restent distinctes. Un mail tardif ne remplace pas mécaniquement une décision plus récente. Un mail multi-chantiers conserve un original et des rattachements explicitement localisés.

## 7. Références vérifiées et conséquences

Ces produits prouvent l'existence de morceaux du parcours. Leurs fonctionnalités ne sont pas toutes libres, incluses dans toutes les éditions ou compatibles avec un Exchange local.

| Produit | Comportement documenté | Ce que nous reprenons comme logique |
|---|---|---|
| **OpenProject** | Création/mise à jour d'éléments de travail par mail ; pièces rattachées. Les fichiers Nextcloud peuvent être liés aux éléments, avec retour vers les éléments depuis le fichier | Le lien durable mail → action → document, dans les deux sens. [Courriels entrants](https://www.openproject.org/docs/installation-and-operations/configuration/incoming-emails/), [fichiers liés](https://www.openproject.org/docs/user-guide/file-management/nextcloud-integration/) |
| **Odoo** | Fil d'échanges et de changements associé à un enregistrement ; notes, fichiers, activités. Les projets peuvent recevoir des tâches par mail | Le dossier comme centre des échanges et des prochaines actions. L'IA standard documentée ne modifie pas librement la base ; les fonctions Documents/IA demandent une vérification d'édition séparée. [Chatter](https://www.odoo.com/documentation/19.0/applications/productivity/discuss/chatter.html), [tâches](https://www.odoo.com/documentation/19.0/applications/services/project/tasks/task_creation.html), [IA](https://www.odoo.com/documentation/19.0/applications/productivity/ai.html) |
| **Frappe Helpdesk** | Plusieurs échanges d'un même ticket réunis et compte mail synchronisé ; correctif de threading utilisant References documenté en avril2026 | Une conversation persistante, plusieurs messages, pas un nouvel objet à chaque réponse. [Communication mail](https://docs.frappe.io/helpdesk/email-communication), [retour de maintenance](https://frappe.io/blog/product-updates/product-updates-for-april-2026) |
| **Notion** | Connecteur Outlook de NotionAI pour Microsoft365, offres Business/Enterprise ; la documentation indique que les pièces jointes ne sont pas lues par ce connecteur | L'espace documentaire et la recherche contextualisée sont de bons repères ; les pièces et Exchange local doivent avoir leur propre traitement. [Connecteur Outlook](https://www.notion.com/help/microsoft-outlook-ai-connector) |
| **Shortwave** | Assistant adapté aux mails visibles, recherche dans les échanges et suggestions de suivi | L'assistant doit arriver dans le contexte de l'écran et du dossier. Cela ne prouve pas une gestion de chantier ou de documents applicables. [Guide officiel](https://www.shortwave.com/docs/guides/ai-assistant/) |

L'assemblage proposé est une **inférence produit** à partir de ces parcours, pas une fonctionnalité déjà observée dans une solution unique. Installer tous ces serveurs en parallèle n'est pas une décision prise.

## 8. Périmètre avant reprise

La première tranche devra prouver le parcours du cas concret, d'abord avec les cinq mails fictifs, puis avec une messagerie de test autorisée. Il faut relier les actions et vues au même objet, conserver et ouvrir les fichiers originaux, gérer leurs versions, alimenter le dossier depuis la collecte et exposer les changements à décider. L'éditeur AFFiNE garde son rôle dans cette expérience.

Le protocole réellement disponible sur Exchange, le dossier à lire, les règles documentaires de la commune et la distinction entre décisions que le père peut valider seul ou avec un tiers restent à préciser avant les essais institutionnels. Aucun identifiant municipal n'est nécessaire pour continuer la conception sur données fictives.

Le modèle de stockage canonique des actions et l'adaptation des bases AFFiNE doivent être décidés à partir de ces critères. Ajouter un deuxième ensemble de cartes non reliées au métier ne satisfait pas le besoin. La génération autonome de réponses envoyées, l'ERP municipal global, le SaaS multi-collectivités et la facturation sont des tranches ultérieures.

**Ordre de travail recommandé :** objets et relations communs → scénario email/documents complet → écrans de ce scénario → vraie recette de messagerie → extension des fonctions. La pause de code reste en vigueur à l'issue de ce cadrage ; ce document n'autorise ni ne déclenche une reprise automatique.
