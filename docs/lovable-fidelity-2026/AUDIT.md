# Écarts avec la base Lovable originale

Audit du 15 novembre 2026 : les huit composants originaux du ZIP ont été lus, puis rendus dans un client local isolé. La version publiée 0.4 a été consultée dans un autre navigateur isolé. **Le décalage ne vient pas principalement du CSS : plusieurs parcours ont été remplacés, et le scénario qui leur donnait du contenu a disparu.**

Archive : `C:/Users/Utilisateur/Downloads/mayor-project-hub.zip`, SHA256 `0df387dfe867b63736ee3f6644bf6e7a65f8aa92459292ffdd88be41c6075e05`.

Les captures `original-*` viennent des composants et du `makeSeed()` originaux, avec seulement un contexte React en mémoire et un routeur local. Elles ne prétendent pas montrer le backend Lovable. Aucun `.env` n'a été lu, aucune requête Supabase ni fournisseur IA n'a été utilisée. Les PDF et la photo viennent du ZIP. L'éditeur BlockSuite original n'a pas été ouvert ; son aperçu de notes est intact. Les captures `published-*` viennent de `https://travaux.kerforge.com/`. Les écritures de la session d'audit ont été bloquées ; les appels de création idempotente de page ont reçu les métadonnées déjà accessibles en GET. Les avertissements de sauvegarde provoqués par ce blocage ne sont pas des régressions produit. [Provenance détaillée](provenance.json).

La police demandée dans le ZIP est DM Sans aux graisses400/500/600/650/700/750. La référence finale la charge localement avec `@fontsource-variable/dm-sans@5.2.8`, sans CDN. La couleur primaire originale `oklch(.55 .17 255)` a été mesurée par canvas à **sRGB(21,112,209), soit #1570d1**, et non le bleu #305fa0 de la première intégration.

## Restaurations à traiter d'abord

1. **Scénario et dossier de référence.** Retrouver le portail de Ker Avel, ses personnes fictives, ses dates, son devis initial et son devis révisé. Sans cela, les mêmes classes donnent une interface beaucoup plus vide et générique.
2. **Assistant distinct du récapitulatif.** Restaurer le bouton, le dialogue, les trois suggestions, la question libre, la réponse et les liens source/devis. Le ZIP indiquait déjà clairement « réponses de démonstration » sans fournisseur IA.
3. **Actions complètes.** Restaurer la vue transversale, les filtres, la fiche action et les champs responsable/date/priorité/description, y compris dans une présentation mobile éditable. Garder la base native comme stockage partagé.
4. **Documents métier.** Restaurer devis v1/v2, montant HT, états Validé/En examen/Remplacé, aperçu PDF et validation explicite. Un lien vers un texte extrait ne couvre pas ce parcours.
5. **Mail dans le dossier.** Retrouver répondre/à tous/transférer, préparer une réponse, créer une action et le contexte du devis, sans sortir du chantier en cliquant un message.
6. **Structure littérale de la page.** Photo dans la colonne de droite, métadonnées complètes, noms Page/Échanges/Assistant, notes en aperçu avec une action Modifier, puis derniers événements lisibles. Restaurer ces éléments avant d'ajuster des marges au hasard.

## Le scénario perdu

| Élément | ZIP original | Publication 0.4 observée |
| --- | --- | --- |
| Corpus principal | 4 chantiers : portail, voirie, gymnase, parc | 6 autres chantiers : parvis, vestiaires, salle, rue, éclairage, chemin |
| Dossier phare | Remplacement du portail de l'école, TRV-2026-042 | Parvis de l'école des Alizés, TRV-2026-014 |
| Localisation et catégorie | École de Ker Avel · Plougastel ; bâtiments scolaires | Localisation/catégorie largement vides ou génériques |
| Suivi | Thomas Le Gall, Marie Kervella, Lucie Prigent ; avatars distincts | Service travaux ou responsable non renseigné ; un accès partagé réel |
| Entreprise | Armor Fermetures | Entreprise Fictive 1 |
| Date confirmée | 18 novembre ; annonce du 25 novembre à examiner | Livraison non renseignée en en-tête ; une annonce du 18 décembre reste à examiner |
| Devis initial | AF-2026-184, v1, 4 850,00 € HT, Validé | Plan de circulation et consignes d'accès ; pas de devis v1 |
| Nouveau mail | Report de thermolaquage + devis v2 + accès vendredi | Mises à jour génériques d'avancement et livraison |
| Devis reçu | v2, 5 120,00 € HT, En examen | Pas de version ni de montant de devis |
| Actions du dossier après réception | Devis terminé ; sécurisation en cours ; accès vendredi à faire | Trois autres actions, toutes initialement à faire, sans les mêmes dates/responsables |
| Histoire racontée | Mail → comparaison → confirmation de date → validation séparée du devis → mémoire actualisée | Chaîne de sources et décisions conservée mais exemple métier différent |

Ce sont des différences de données **et** de modèle d'interface. La projection actuelle `documentFromApi()` force notamment `version:null` et `amount:''` ; changer seulement le seed ne restaurera pas l'affichage des versions et montants.

## Inventaire des huit composants

### 1. Shell

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Marque MayorTech, sidebar, fil d'Ariane, réduction de navigation | Présents ; structure globale proche |
| Organisation « Ville de Plougastel », initiale P, chevron | Remplacée par l'organisation serveur générique, initiale C ; intitulé et aspect changés |
| Navigation Messagerie / Chantiers / Actions et compteurs | Présente ; ajout À vérifier et Récapitulatifs déplace les repères |
| Deux chantiers favoris, noms et points colorés | Remplacés par d'autres favoris ou une liste de quatre dossiers ; catégorie visuelle simplifiée |
| Profil bas de rail avec avatar, nom, rôle, chevron | Retiré ; pas d'équivalent visuel du bloc profil |
| Avatar et état d'enregistrement en haut à droite | Retirés ; le suivi natif reste local à l'éditeur |
| Navigation mobile à quatre entrées | Conservée, avec ajout d'un menu latéral mobile utile |
| Recherche globale dans le header | **Pas une fonction originale** : icône importée mais aucune recherche rendue. Ne pas inventer cette régression |

### 2. Projects

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Titre, introduction, Nouveau chantier, liste/fiches | Conservés ; recherche étendue à référence/localisation |
| Compteurs chantiers en cours / actions cette semaine / dernier échange | Remplacés par chantiers / actions confirmées / courriels disponibles ; sens métier différent |
| Bandeau ciblé sur le mail du portail et Recevoir le mail | Remplacé par un nombre générique d'informations à vérifier ; déclencheur narratif absent |
| Ligne chantier : symbole coloré, référence, lieu, responsable/initiales, prochaine échéance | Nom/statut présents ; référence retirée de la ligne, valeurs responsables/dates souvent vides ; icônes/avatars moins différenciés |
| Formulaire nom + localisation + entreprise + date + description, référence générée | Nom + référence obligatoire + description seulement. Localisation/entreprise/date ont disparu |
| Bloc À suivre de près avec photo et texte du portail | Surface présente, mais autre dossier et contenu générique ; photo du dossier absent côté détail |
| Prochaines actions issues du même ensemble opérationnel | Liste actuelle fondée sur les faits d'actions confirmés, pas sur toutes les lignes éditables de la base native |
| Pied de page données fictives et mémoire partagée | Copie supprimée/déplacée dans le rail |

### 3. ProjectDetail

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Retour, favoris, nom, référence/catégorie au-dessus, localisation en dessous | Retour/favoris/nom conservés ; catégorie et ligne de localisation absentes quand le modèle n'a pas de fait ; référence déplacée |
| Statut + avatar responsable + nom + livraison + entreprise | Responsable/avatar retirés visuellement ou non renseignés ; livraison souvent vide ; en-tête plus court |
| Onglets **Page / Actions / Documents / Échanges** + **Assistant** | **Notes / Actions / Documents / Courriels** + **Récapitulatif**. Fonction et vocabulaire changés |
| Recevoir le nouveau mail avant l'annonce | Absent du dossier ; le backend a `nextMail` mais pas ce parcours narratif dans le composant courant |
| Carte précise Report de la livraison, 18→25 novembre, cause, source | Carte générique à sélecteur de quatre propositions d'avancement ; plus haute et moins immédiatement lisible |
| Confirmer le report / Corriger date / Rejeter, puis bannière Livraison confirmée | Décisions réelles conservées/améliorées mais libellés génériques ; bannière métier de confirmation disparue |
| Situation actuelle rédigée, quelques sources nommées, Actualiser le récapitulatif | Remplacée par concaténation de quatre faits ; textes et puces métier moins riches. Versions réelles et validation ajoutées |
| Notes : aperçu lisible, texte/checklist initiale, bouton Modifier les notes | Éditeur toujours ouvert. Perte de l'état aperçu et du bouton explicite, prise de place différente |
| Dernières évolutions : titre, détail, auteur, date, message source | Timeline conservée mais détails souvent réduits à champ/motif et acteur technique ; moins narrative |
| Photo du portail en tête de colonne droite | **Absente** du composant intégré ; photo d'accueil ne remplace pas cette surface |
| Prochaine action avec date et responsable, Ouvrir l'action | Date/responsable dépendants de lignes souvent vides ; bouton mène à l'ensemble des actions, pas à la fiche précise |
| Documents importants avec version, statut et montant | Liste de fichiers conservés, sans version/statut de validation/montant |
| Points à vérifier formulés en actions compréhensibles | Valeurs de propositions génériques à la place des consignes du scénario |
| Assistant : trois questions, saisie libre, réponse, liens source/devis | **Absent**. Récapitulatif n'est pas un substitut fonctionnel |
| Historique des récapitulatifs, reprise, modification, export texte | Conservé sous forme plus robuste mais changé : sélecteur de version, validation, export Markdown/HTML ; export TXT original et Reprendre ce texte explicite absents |

### 4. Actions

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Toutes les actions de tous les chantiers | `/actions` demande de choisir un chantier et montre sa base ; vue globale transversale perdue |
| Recherche titre ; filtres statut, responsable, priorité | Absents de la barre d'actions actuelle. Les réglages internes d'une base ne rendent pas ces contrôles équivalents |
| Bascule tableau/Kanban | Présente, sur base native ; meilleure source unique mais présentation et colonnes différentes |
| Création avec titre, chantier, responsable, date, priorité, description | Création rapide titre seul ; les autres champs ne sont plus proposés au même endroit |
| Tableau : statut select et échéance date modifiables directement | Remplacé par édition de cellules native desktop ; mobile en fiches de lecture seule |
| Carte : titre, chantier, priorité, date, select de statut | Carte native plus nue ; informations/champs et select mobile manquent |
| Drag and drop entre quatre colonnes | Présent côté base native desktop ; non offert dans la lecture mobile |
| Fiche d'action avec description, statut, responsable, échéance, message source et suivi | Plus de dialogue métier équivalent ; manipulation native des propriétés différente |
| Même action dans tableau, Kanban, accueil et détail | Base native cohérente entre ses vues, mais accueil/prochaines actions lisent une projection différente (`state.actions` issue des faits) |
| Statuts, priorité, responsables fictifs déjà renseignés | Seed opérationnel absent ; beaucoup de cellules deviennent vides |

Le fichier original `Actions.tsx` reste dans le checkout, mais le routeur importe `AllActions` de `ServicePages.tsx`. Il ne prouve donc pas que ces contrôles sont accessibles.

### 5. Documents

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Liste des versions d'un même devis, dates et montants | Liste de fichiers originaux ; aucune relation de versions de devis |
| Badges Validé / En examen / Remplacé | Remplacés par Original conservé/disponible ; disponibilité technique et décision métier sont deux choses différentes |
| Valider v2 après confirmation, conserver v1 comme remplacé | **Absent** ; aucune commande de validation documentaire équivalente |
| Clic nom → aperçu PDF dans dialogue | Nom non cliquable ou Lire l'extrait ; dialogue texte, pas aperçu PDF |
| Ouvrir PDF dans un onglet + Télécharger + Message source | Téléchargement original et source conservés ; ouverture/aperçu PDF retirés |
| Traçabilité de la validation dans l'historique | Décisions sur propositions conservées, mais pas l'événement de validation du devis |
| Originaux réellement conservés et hashes | Amélioration actuelle réelle à conserver lors de la restauration de l'UX |

`Documents.tsx` original reste également sur disque ; le détail rend `DocumentsPanel` de `ProjectPanels.tsx`, plus réduit.

### 6. Mail

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Dossiers réception/envoyés/brouillons/archives/corbeille | Présents globalement et déplacés dans le rail commun, avec Tous les messages ajouté |
| Raccourcis de trois chantiers dans la messagerie | Perdus en tant que filtres mail : liens de dossiers globaux à la place |
| Recherche sujet/expéditeur/corps | Conservée ; dans le global, ajout d'un bouton Chercher et d'un Actualiser |
| Recevoir le nouveau mail depuis la liste | Absent ; scénario d'entrée perdu |
| Liste : nom humain, extrait, date, trombone, référence chantier | Références/nom lisibles réduits dans la messagerie globale ; adresses brutes et présentation différente |
| Actions d'icône archivage/corbeille/non-lu + rattachement select | Actions globales cachées dans menu « … » ; rattachement absent de la messagerie globale et non disponible pour le visiteur public |
| Nom/initiales d'expéditeur, À : Thomas, lien chantier près de l'en-tête | Enveloppe simplifiée en adresses/texte et lien chantier plus bas |
| Répondre / À tous / Transférer dans le dossier | Le dossier utilise un module de lecture sans ces commandes ; global conserve Répondre/Transférer, **À tous absent** |
| Préparer une réponse suggérée, explicitement simulée | **Absent** |
| Créer une action reliée au message | **Absent** |
| Pièce jointe : nom + version + statut + Ouvrir/Télécharger | Texte extrait et original récupérables, mais relation version/statut métier absente |
| Encadré annonce 18→25 et lien Voir le changement dans le dossier | **Absent** |
| Composer dans un dialogue ; sauver brouillon ; simuler envoi vers Envoyés | Composer intégré dans la colonne, brouillon navigateur plus robuste ; pas de simulation Envoyés |
| Modifier brouillon dans le même dialogue | Présent mais surface différente et persistance locale/privée distincte |
| Choisir un message sans quitter l'onglet Échanges du chantier | Régression de navigation : le module contextuel utilise `#/mail/id` ; il ouvre la messagerie globale. À rétablir en URL dossier + `mail=id` |
| Retour mobile liste/message | Conservé ; gestion du focus améliorée à garder |

### 7. Settings

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Quatre onglets Apparence / Organisation / Membres / Connexions | Six onglets : Rôles et droits/Journal ajoutés ; plus de défilement horizontal mobile |
| Couleurs Bleu / Vert / Violet / Ardoise | Six couleurs et densité locale ajoutées ; visuel de sélection et vocabulaire changés |
| Réinitialiser toute la démonstration, après confirmation | **Retiré**. Peut être proposé pour un espace de démonstration isolé, pas comme reset global silencieux |
| Nom de collectivité modifiable | Présent en API, mais visiteur public en lecture seule |
| Services Travaux / Voirie / Espaces verts / Direction générale et effectifs | **Absents** |
| Quatre membres fictifs avec avatar, service, rôle et Suspendre/Réactiver | Remplacés par le seul acteur serveur courant ; absence des quatre fiches et de leurs contrôles |
| Note claire « rôles de démonstration uniquement » et habilitations prévues | Remplacée par matrice exécutée côté serveur. Ne pas appeler rétablissement des boutons une vraie invitation/identité tant que l'IdP reste absent |
| Détails Exchange : serveur local/prestataire, protocoles, habilitations | Copie réduite à état/capacité serveur et courte note ; informations de préparation moins détaillées |
| Assistant IA non connecté + hébergement OVH à préparer | Deux rubriques retirées ou absorbées ; statut réel de connexions ajouté |

### 8. BlockEditor

| Fonction/surface originale | État actuel et écart |
| --- | --- |
| Éditeur chargé uniquement en cliquant Modifier les notes | Chargé directement dans Notes ; état aperçu fermé perdu |
| Texte initial et checklist lisibles en mode aperçu | Perdus avec le scénario et la page native vierge/générique |
| Notes sauvées comme état Yjs, séparées du récapitulatif | Conservées et renforcées : versions serveur, détection de conflit, sauvegarde attendue avant navigation |
| Un document de notes par chantier | Conservé ; base d'actions native intégrée en plus |
| Barre d'ajout de blocs et bases | Plus explicite actuellement, à garder sans déplacer toute la hiérarchie originale |
| Structure mobile | Fiches lisibles ajoutées, mais édition des actions sur mobile perdue par rapport aux contrôles React originaux |

## Critères pour la prochaine passe

- Vérifier sur **le même scénario Ker Avel** avant/après réception, avec les mêmes états, acteurs fictifs, montants et dates. Comparer deux projets différents ne suffit pas à juger la fidélité.
- Reprendre les classes et la structure originales au lieu de remplacer des composants complets par les anciens panneaux vanilla. Les adaptateurs doivent changer la source des données, pas supprimer les contrôles.
- Conserver séparément Assistant et Récapitulatif, et retrouver les libellés Page/Échanges là où ils figuraient.
- Rendre le parcours mail→action, mail→devis v2→validation et question→preuve réalisable en quelques gestes sur ordinateur **et** mobile.
- Restaurer la vue globale Actions sans créer une seconde vérité : toutes les surfaces doivent lire/écrire les mêmes lignes natives.
- Maintenir les acquis techniques actuels : vraie conservation des originaux, preuves et versions, permissions serveur, absence d'envoi institutionnel/LLM réels tant qu'ils ne sont pas raccordés. Les fonctions de simulation du ZIP doivent être clairement désignées comme telles.
- Ne pas réintroduire les défauts du ZIP constatés par lecture : « À tous » n'ajoutait pas réellement tous les destinataires, l'aperçu de notes était figé, le compteur d'onglet excluait les actions terminées alors que la table les montrait, et les réponses de l'assistant étaient des textes préparés. Restaurer la surface attendue avec un comportement cohérent.

## Preuves consultables

[Comparateur visuel](index.html) · [Provenance des 25 captures](provenance.json) · client de référence local : `http://127.0.0.1:18768/`.

Les fichiers de référence intacts et leurs empreintes sont décrits dans `work/lovable-reference-client/SOURCE.json`. Les captures de production sont une observation ponctuelle de 0.4 ; ce rapport ne présume pas des restaurations lancées après l'audit.
