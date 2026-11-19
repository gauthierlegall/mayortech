# Recette publique HTTPS — v0.7

Recette directe sur [travaux.kerforge.com](https://travaux.kerforge.com), après autorisation de publication de la release `20261115T211012Z-707e4a`. Le serveur annonce `0.7.0`. Chrome utilise sa validation TLS standard : aucun certificat ignoré, aucun asset ni réponse API substitué.

## Parcours contrôlés

- [Messagerie FHD](1920-mail.png) : trois colonnes 170/310/reste, dossiers internes uniques, aucune arborescence dupliquée dans le Shell.
- [Messagerie mobile](390-mail.png) : dossiers défilants et filtre chantier ; vérification également à 320 px, sans débordement. Le filtre affiche les identifiants effectivement rattachés au projet par l'API.
- [Lecture mobile](390-mail-reader.png) : lecteur vérifié à 1920/390/320 px et liste masquée sur mobile.
- [Actions chargées](390-actions-filters-loaded.png) : filtres ouverts au clic, fermés par Entrée et ouverts par Espace, sans réapparition de la course corrigée. Les contrôles 320 px avaient aussi été validés directement sur le bundle local identique avant publication.
- [Dossier](1920-project-page.png) : six onglets, accès aux propriétés dans Page ; aucun champ enregistré pendant la recette.
- [Suivi terrain](390-terrain.png) : deux constats réellement créés par l'opérateur, explicitement fictifs, rattachés aux dossiers portail et voirie. Aucune levée ni action créée pendant cette recette.
- [Planning chargé](1920-planning-loaded.png) : route globale fonctionnelle, dix groupes, six lignes et six barres réelles ; aucune alerte après la fin du chargement natif.

## Indicateur de lecture restauré

Aucun message du portail n'était déjà lu dans le périmètre contrôlé. Le parent a explicitement autorisé une ouverture avec restauration de l'indicateur : source `ac041f71-6091-4e7b-8242-2ef3b41b435d`, statut avant `read=false`, révision 2 ; après ouverture `read=true`, révision 3 ; restauration avec `expected_revision=3`, HTTP 200, état final `read=false`, révision 4. Dossier, favori et hash du corps identiques avant/après. Aucun changement de source ou de fait, aucun envoi, import ou brouillon serveur.

## Résultat et limite visuelle

Les vérifications fonctionnelles finales sont vertes, sans erreur JavaScript ni HTTP applicative. Le premier passage avait laissé deux vérifications différées : lecture sans message déjà lu et Planning capturé pendant son chargement. Elles ont été résolues séparément ; les résultats bruts restent dans [qa-public-v07.json](qa-public-v07.json) et la preuve finale dans [qa-public-v07-final.json](qa-public-v07-final.json).

**P2 visuel non bloquant signalé au parent** : dans Page du portail, l'aperçu des notes affiche aussi la représentation Markdown de la base Actions (« `| Intitulé | Description…` »), qui alourdit la lecture et duplique les actions. Visible en bas de la capture du dossier. Ce constat ne concerne pas la persistance ou la source des lignes ; aucun correctif applicatif n'a été effectué dans ce lot d'audit.

La conservation des brouillons sur appareil a été testée sur la v0.7 locale directe. Les preuves de brouillons privés côté serveur restent distinctes, dans les tests du service et du moteur ; aucun compte réel n'est connecté par cette recette publique.

## Résolution de la finition Notes

La release `20261115T212740Z-53de17` retire de l’aperçu uniquement la base Actions explicitement identifiée dans un snapshot de lecture. Les autres notes et tableaux restent visibles ; le texte complet et les octets Yjs sont inchangés. Le [retest HTTPS final](notes-final/checks.json) passe ses 15 contrôles à 1920, 390 et 320 px : paragraphes humains présents, absence du tableau Actions brut, trois barres Frise et Frappe, notes et faits stockés identiques, aucun PUT/PATCH ni erreur JavaScript/HTTP. Les [captures finales](notes-final/) complètent la capture initiale conservée. Le P2 visuel ci-dessus est résolu. Le [contrat HTTPS](contract.json) a été revalidé (27/27) sur cette release.
