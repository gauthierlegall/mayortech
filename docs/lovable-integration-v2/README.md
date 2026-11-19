# Interface Lovable v2 — version 0.7.0

[Ouvrir l’application](https://travaux.kerforge.com).

La navigation, les pages de chantier, la messagerie et les nouveaux écrans Planning/Terrain suivent la seconde proposition Lovable fournie par l’utilisateur. Les fonctions existantes restent reliées aux données réelles de l’application : les actions sont toujours les mêmes lignes Yjs, les constats ont leur propre source et les conversations gardent leur historique.

**Publication finale vérifiée :** release `20261115T212740Z-53de17`, version 0.7.0, le 15 novembre 2026. Application et worker sains ; contrat HTTPS et finition Notes revérifiés après déploiement. Les recettes Planning, popup et transversale portent sur la release initiale `20261115T211012Z-707e4a` ; la correction finale conserve ces capacités et son contrôle complémentaire vérifie les notes, la frise et Frappe sur le site publié.

## Parcours livrés

| Surface | Résultat |
| --- | --- |
| Navigation | Messagerie, Chantiers, Actions, Planning et Suivi terrain en premier. Agenda et À vérifier restent accessibles. Sur mobile, cinq raccourcis et un menu complètent la navigation. |
| Chantier | Six onglets : Page, Actions, Planning, Terrain, Documents, Échanges. Le dossier ouvre Planning ; Page conserve situation, preuves, notes et prochaine action. Le bouton Propriétés ouvre la section repliable dans Page ; les anciens liens restent valides. |
| Propriétés | Les quinze intitulés de la référence Notion sont conservés, avec quatorze champs éditables et les pièces effectivement rattachées. Coûts, dates, notes et observations sont distincts ; une modification humaine ne valide pas une proposition extraite d’un courriel. [Détail des champs](../coordination-2026/CHAMPS_NOTION.md). |
| Planning | Frise mensuelle globale et par chantier, filtre réel, navigation entre les mois, jalons confirmés distincts des propositions. Le mode Déplacer utilise Frappe ; le formulaire partage les dates, le responsable, le statut et l’avancement des Actions. Une date de début ou un pourcentage absent reste absent. La liste est le défaut sur mobile. |
| Suivi terrain | Visites, anomalies et réserves datées, auteur, statut, filtre chantier et création explicite d’une action native. Réessayer après une erreur de liaison réutilise la même action ; aucun second stockage d’actions. |
| Messagerie | Trois colonnes internes sur ordinateur : dossiers, messages, lecteur. Sur mobile : dossiers défilants, filtre chantier puis passage liste/lecture. Le filtre s’appuie sur les rattachements de sources avant pagination. Brouillons et contrôles de version sont conservés. |
| Assistant | Une seule bulle en bas à droite ouvre un popup non modal. Réduire conserve le fil, la saisie et la réponse en cours ; navigation et rechargement n’effacent pas l’historique. Sources et historique restent accessibles. Un nouveau contexte de chantier est proposé explicitement. |
| Aperçu des notes | La projection exclut uniquement la base Actions gérée identifiée par son rattachement exact. Les paragraphes humains restent visibles et les actions restent dans leur onglet ; aucun document natif ni export complet n’est réécrit. |
| Actions et chargement | Filtres secondaires repliables sur mobile, utilisables à la souris et au clavier. Le chargement natif affiche un état d’attente au lieu d’un faux zéro. |

Les agendas, la première connexion, les notifications et la reprise des anciens courriels restent disponibles. Le [rapport de coordination v0.6](../coordination-2026/README.md) et le [workflow historique Exchange](../REPRISE_ANCIENS_MAILS_2026.md) décrivent ces capacités et leurs limites.

## Réemploi et correction du Gantt

La référence est `mayor-project-hub (1).zip`, 563 587 octets, SHA-256 `5667d2a6d1d03259a3067863c2478243dc5ed582cd7ebd5bcd3812119fe46680`. L’[inventaire et les différences](provenance.json), l’[audit par écran](AUDIT_UX.md), les [extraits de code](source-excerpts/) et les [captures de référence](reference/captures.json) documentent le réemploi. Les fichiers d’instructions contenus dans l’archive ont été traités comme des documents de référence ; aucun script de l’archive ni fichier d’environnement n’a été exécuté ou importé.

La frise mensuelle reprend le JSX et la grille CSS du Planning Lovable : colonne de noms fixe, groupes de chantiers, lignes de 65 px, barres de 25 px, jours et week-ends. Les mois fixes, dates déduites et stockage JSON de la maquette sont remplacés par les dates et commandes existantes. Le mode Déplacer conserve Frappe Gantt 1.2.2 et ses véritables changements de dates.

La panne Frappe provenait d’un appel `classList.add` recevant plusieurs classes dans un seul jeton, notamment pour une action sans avancement. Le correctif sépare les classes avant leur ajout. Les barres dont le pourcentage est inconnu s’affichent ; la politique CSP reste active. La [provenance du moteur](../planning-2026/REUTILISATION.md) décrit cette adaptation.

Le popup Assistant est une adaptation demandée par l’utilisateur : cette seconde archive contient un dialogue centré, pas de widget flottant. Il réutilise le moteur de [conversation sourcée existant](../conversation-integration-2026/README.md), avec ses droits et sa persistance.

## Vérifications et preuves

Les comptages concernent des suites distinctes ; ils ne constituent pas un total de scénarios utilisateurs uniques. Les totaux Node du correctif final comprennent six nouveaux tests frontend de rattachement exact et trois tests natifs de projection sans mutation.

| Vérification | Résultat | Preuve |
| --- | --- | --- |
| Application et déploiement | 396 tests Python passent | [Rapport de vérification courant](../verification-native.json) |
| Frontend et domaine | 80 tests Node passent ; TypeScript, build frontend et Ruff passent | [Rapport de vérification courant](../verification-native.json) |
| Module natif | 27 tests Node passent ; build natif passe | [Rapport de vérification courant](../verification-native.json) |
| Planning local | 31 contrôles passent : sauvegarde, rechargement, déplacement réel, un seul PUT, mobile et faits préservés | [Recette locale](local-planning/RECETTE.md) |
| Propriétés | 20 contrôles passent, dont conflit et conservation de saisie | [Revalidation](../coordination-2026/qa-properties/REVALIDATION.md) |
| Popup local | 20 contrôles passent, dont réponse retardée pendant réduction/navigation et changement d’identité | [Résultats](../coordination-2026/qa-popup-independent/checks.json) |
| Terrain local | 12 contrôles passent, dont panne de liaison simulée après sauvegarde native puis reprise sans doublon | [Résultats](qa-terrain/checks.json) |
| Reprise historique | 15 contrôles passent sur le vrai serveur applicatif privé en processus, avec lecteur Exchange fictif | [Résultats](../coordination-2026/qa-backfill/checks.json) |
| Planning HTTPS — release initiale | 65 contrôles passent, 18 captures, aucune mutation | [Recette publiée](public/planning/RECETTE-HTTPS.md) |
| Popup HTTPS — release initiale | 19 contrôles passent ; seuls les fils fictifs de la recette ont été créés puis supprimés | [Résultats](../coordination-2026/public-popup/checks.json) |
| Contrat HTTPS — release finale | 27 contrôles passent : version, empreintes du client et du module natif, droits publics, séparation de la base et refus des imports privés | [Résultats](public/contract.json) |
| Parcours HTTPS transversaux — release initiale | 34 contrôles fonctionnels passent ; le P2 Notes signalé dans ce rapport est levé par la recette finale ci-dessous | [Recette publique](public/QA_PUBLIQUE_V07.md) |
| Projection Notes sur le vrai SDK | Export `getText` strictement identique et état Yjs identique octet par octet ; deux paragraphes humains conservés, trois titres de la seule base gérée exclus, aucun PUT/PATCH ni sauvegarde | [Preuve du navigateur](local/notes-projection-purity.json) |
| Finition Notes locale | 15 contrôles passent : notes lisibles aux trois largeurs, édition accessible, frise et trois barres Frappe intactes, faits et notes stockées inchangés | [Résultats locaux](local/notes-final/checks.json) |
| Finition Notes HTTPS — release finale | 15 contrôles passent aux trois largeurs ; notes humaines et édition accessibles, trois barres de frise et trois barres Frappe affichées, faits et notes stockées inchangés, aucun PUT/PATCH | [Résultats publiés](public/notes-final/checks.json) |

Les captures et mesures couvrent 1920×1080, 390×844 et 320×760 dans Chrome headless réel. Les captures finales de la Page avec ses notes sont disponibles en [1920 px](public/notes-final/1920-notes.png), [390 px](public/notes-final/390-notes.png) et [320 px](public/notes-final/320-notes.png). La validation TLS normale est conservée ; aucun asset ou résultat d’API n’est remplacé dans la recette publique. L’indicateur de lecture du seul courriel ouvert a été restauré avec contrôle de révision ; le hash du corps est inchangé. Les contrôles du planning n’ont modifié ni les pages natives ni les faits confirmés.

Une revue indépendante a aussi reproduit puis levé la fuite possible d’un brouillon Terrain lors d’un changement d’acteur. Le garde de sauvegarde natif est relu immédiatement avant le PUT : un changement d’identité pendant l’export empêche l’écriture et la liaison.

Deux rendez-vous, six actions planifiées et deux constats Terrain ont été préparés explicitement comme exemples fictifs : [calendrier](../coordination-2026/public/operator-calendar.json), [actions](../coordination-2026/public/operator-native.json), [constats](public/operator-terrain.json). Les essais d’édition locaux utilisent un dossier QA séparé ; les exemples principaux restent préservés.

## Limites opérationnelles

Aucun compte municipal Exchange/CalDAV, modèle Mistral, bot Telegram, transport d’envoi de courriel ou fournisseur d’identité individuel réel n’est connecté. Les raccordements OAuth Google Agenda et Microsoft 365 ne sont pas implémentés et sont indiqués comme tels. Les adaptateurs et formulaires ne valent pas qualification d’un serveur institutionnel ; le workflow historique utilise un lecteur Exchange fictif pendant la recette.

Aucune donnée réelle des photographies privées n’a été copiée dans la démonstration ou l’archive ; seuls les intitulés et types de propriétés ont servi à vérifier le périmètre. La recette ne porte pas sur un téléphone physique et ne constitue pas une certification RGAA/RGPD. Les audits des dépendances de production du nouveau client et des 63 dépendances Python du runtime ne signalent aucune vulnérabilité connue à la date du contrôle ; le SDK natif conserve un [backport Zod 3 documenté](../../native-editor/patches/README.md), avec l’avis amont toujours signalé par npm.
