# Travaux — référence Lovable v2

Mode : Operate. La demande utilisateur du 15 novembre 2026 impose de rapprocher toute l’UX de `mayor-project-hub (1).zip`, après le premier réemploi de `mayor-project-hub.zip`. Le [registre de provenance et les captures](docs/lovable-integration-v2/AUDIT_UX.md) sont la référence visuelle ; les données et API réellement raccordées restent canoniques.

Conserver DM Sans auto-hébergé, fond blanc, rail gris très clair et accent bleu de la référence. Les tokens de `frontend-lovable/src/styles.css` et l’apparence choisie par la personne règlent les variantes. Ne pas réintroduire le vert de la refonte0.3 comme nouvelle direction implicite.

La navigation principale commence par Messagerie, Chantiers, Actions, Planning, Suivi terrain. Agenda et À vérifier conservent leurs fonctions réelles. Sur téléphone : Messages, Chantiers, Actions, Planning, Terrain ; les autres rubriques restent dans le menu accessible.

Un dossier conserve titre, référence, état, responsable et livraison. Les six vues sont Page, Actions, Planning, Terrain, Documents, Échanges. Le Planning reste la vue d’ouverture demandée. Les quinze propriétés du dossier se trouvent dans une section dépliable de Page, accessible par Propriétés et par le lien historique `?view=properties`.

La Page reprend la hiérarchie Lovable : proposition compacte, situation en prose, preuves courtes, propriétés repliables, notes et historique. Les documents et prochaine action restent dans la colonne de droite sur ordinateur. L’éditeur natif s’ouvre explicitement pour modifier les notes. Ne pas transformer chaque information en carte décorative.

La frise mensuelle reprend la colonne fixe Chantier/Action, les groupes bleu pâle, les lignes65px, les barres25px et la navigation mensuelle. Seules les vraies dates de début/fin créent une barre. Les livraisons confirmées ont des losanges, les propositions restent distinctes. Le mode Déplacer utilise Frappe pour les gestes de dates/progression ; les mêmes actions Yjs sont éditées par les formulaires. Mobile : liste initiale, frise défilante interne disponible.

La Messagerie reprend trois colonnes internes : dossiers, messages, lecture. Les filtres chantier doivent être réels et se combiner avec les dossiers, la recherche et la pagination. Ne pas afficher une seconde arborescence de dossiers dans le rail principal. Le suivi Terrain reprend les listes et formulaires du ZIP, avec persistance, source humaine et action native liée.

L’Assistant est une bulle fixe en bas à droite ouvrant un popup non modal. Le popup conserve conversation, brouillon et requête pendant la réduction ou la navigation. Le contexte courant est visible ; changer de chantier ne change pas silencieusement le fil existant. Historique et sources restent accessibles. Sur mobile, popup et composeur restent au-dessus de la navigation et du clavier ; Escape respecte les dialogues sources avant de réduire le chat.

Ne pas réintroduire stockage JSON de démonstration, réponses mockées, dates implicites, faux comptes raccordés ou envoi simulé comme succès. Les anciens rapports et captures restent archivés ; seules les recettes du dernier bundle prouvent la livraison. Toutes les illustrations/données de démonstration sont fictives et signalées. Cibles utiles44px, clavier, gestion des conflits et saisie préservée à320px restent requis.

Le raccordement mail suit les étapes de choix du fournisseur, autorisation du compte, sélection des dossiers et première lecture. Outlook (Microsoft 365) est proposé en premier. Après autorisation, le serveur renvoie vers le compte correspondant et laisse à l’utilisateur le choix des dossiers et le lancement de l’import. Microsoft 365 et Gmail nécessitent une configuration serveur dans un espace autorisé. L’exemple Exchange utilise une boîte fictive.

Dans Planifier une action, le contexte global commence par un chantier explicitement choisi. Dans un dossier, le nom du chantier ouvert est visible et verrouillé. Une suggestion de responsable n’est jamais une attribution ; les noms déjà saisis restent conservés même sans membre correspondant.
