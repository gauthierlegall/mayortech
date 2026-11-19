# Planning des chantiers — code réemployé

La vue mensuelle reprend le JSX et le CSS du **Planning Lovable v2 fourni par l’utilisateur**. Le mode **Déplacer** utilise **Frappe Gantt 1.2.2, sous licence MIT**, pour le déplacement des vraies actions. Les neuf fichiers JavaScript/CSS du paquet installé sont copiés dans `frontend-lovable/src/vendor/frappe-gantt/`. Les fichiers de rendu SVG, barres, flèches, dates et styles restent ceux du projet amont, avec les adaptations ciblées décrites ci-dessous. La licence est conservée dans `LICENSE.txt` et dans les notices du client compilé.

L’[inventaire des empreintes](../../frontend-lovable/src/vendor/frappe-gantt/UPSTREAM.json) distingue les sources originales des adaptations. **Sept fichiers sont inchangés, `index.js` et `bar.js` sont adaptés** : le gestionnaire global `document.mouseup` devient nommé et une méthode `destroy()` le retire à la fermeture du planning ; l’ajout des classes d’une barre transmet un argument par classe à `DOMTokenList.add`. Un fichier de déclarations TypeScript local documente la frontière de la bibliothèque. Le test de vingt montages/démontages échoue avec la version amont dépourvue de destruction, puis passe avec l’adaptation.

## Comparaison des briques

| Brique consultée | Intérêt et décision |
| --- | --- |
| [Frappe Gantt](https://github.com/frappe/gantt) | Bibliothèque MIT légère, barres éditables et code lisible. Retenue pour garder les contrôles et les données du produit existant. [Code des événements](https://github.com/frappe/gantt/blob/master/src/index.js), [code des barres](https://github.com/frappe/gantt/blob/master/src/bar.js), [licence](https://github.com/frappe/gantt/blob/master/license.txt). |
| [SVAR React Gantt](https://github.com/svar-widgets/react-gantt) | Le dépôt actuel annonce MIT et React 19, avec grille, hiérarchie et interactions plus étendues. Alternative crédible si le suivi évolue vers l’ordonnancement de ressources. Pas de deuxième moteur de tâches intégré pour ce premier planning. |
| [FullCalendar](https://fullcalendar.io/license) | Les plugins Standard sont MIT. Scheduler/Premium relève d’autres conditions ; la licence actuelle prévoit une option AGPLv3 couvrant l’ensemble de l’application, ou une licence commerciale. Utile pour une vue agenda, pas nécessaire pour cette frise d’actions. |

Les affirmations ci-dessus ont été vérifiées sur les sources primaires le 15 novembre 2026. Le paquet exact installé, son intégrité NPM et les empreintes sont épinglés indépendamment de la branche amont.

## Intégration effective

`Planning.tsx` projette les lignes du document **Yjs AFFiNE existant**, via `native-actions.ts`. Le Gantt, la liste mobile et les formulaires modifient les mêmes identifiants de lignes. Les propriétés ajoutées au SDK sont Début et Avancement ; Fin prévue réemploie l’échéance native existante.

`GlobalPlanning.tsx` charge ces mêmes lignes pour les chantiers autorisés et propose un filtre chantier réel. `PlanningTimeline.tsx` partage la grille mensuelle entre la vue globale et le dossier. `PlanningActionDialog.tsx` partage le formulaire de dates, responsable, statut et avancement, sans créer une seconde collection d’actions. Les choix du responsable proviennent des membres de l’organisation et conservent le propriétaire actuel ; les statuts proposent les valeurs natives et préservent une éventuelle valeur personnalisée actuelle. Les champs inchangés de responsable/statut ne sont pas réécrits.

La reprise Lovable provient du ZIP `mayor-project-hub (1).zip`, SHA-256 `5667d2a6d1d03259a3067863c2478243dc5ed582cd7ebd5bcd3812119fe46680`, notamment `src/features/workspace/Planning.tsx` et `src/styles.css`. Les éléments réemployés sont la navigation mensuelle, le découpage projet/actions, les classes `gantt-line`, `gantt-label`, `gantt-track`, les colonnes fixes de 260 px, les lignes de 65 px, les week-ends et les barres de 25 px avec leurs états. Les barres conservent une cible de 44 px autour de leur forme visuelle. Le code de placement mensuel est repris avec validation des dates et calcul en jours UTC. Le mois fixe, les mutations de données de démonstration et l’inférence `start=due` du prototype sont remplacés par le vrai mois navigable, les données Yjs et des bornes explicites. Les extraits et captures de référence se trouvent dans `docs/lovable-integration-v2`.

Le code amont émet des changements de dates pendant le déplacement du pointeur. L’adaptateur les regroupe et n’enregistre qu’au relâchement, avec le contrôle de révision de la ligne native puis celui du document. Un échec rétablit la frise et conserve un message de récupération. Les titres sont échappés avant le point d’insertion SVG `innerHTML` de la bibliothèque, et son popup HTML est désactivé au profit du formulaire React.

Une action sans début ou sans fin valide reste « À planifier ». Aucun début n’est déduit d’un courriel et aucun pourcentage n’est déduit du statut. Une valeur d’avancement absente est distincte de zéro. Retirer une action de la frise efface seulement son début ; l’échéance, l’avancement et le lien du mail restent conservés.

Les dates confirmées du dossier et les annonces à vérifier sont séparées de la planification humaine. Les déplacer n’approuve ni une nouvelle date de livraison ni un nouveau montant de devis. Les rendez-vous proviennent de `GET /calendars/events?project_id=…` et n’apparaissent que lorsqu’ils sont explicitement rattachés au chantier.

## Recette

Les captures et les contrôles réels sont dans [local/checks.json](local/checks.json). Les tests couvrent le formulaire, le déplacement de barre, la persistance après rechargement, la progression, le lien source, le clavier, la liste mobile et le refus d’écrasement après modification concurrente. Les seuls champs de planification modifiés pour cette recette sont remis à leur valeur initiale, sans retirer les lignes préexistantes ni réinitialiser le dossier.

La vue mobile privilégie la liste éditable, avec la frise disponible sur demande. Le rendu est observé à 1920 × 1080, 390 × 844 et 320 × 760 ; il ne s’agit pas d’un essai sur appareil physique.

La recette de la grille Lovable v2 et du formulaire partagé compte 31 contrôles réels réussis, avec mesures de densité à 65 px, navigation mensuelle, filtre, persistance global/chantier, mise à jour propriétaire/statut, mouvement réel du pointeur et restauration de l’action fictive. Les preuves finales sont dans `docs/lovable-integration-v2/local-planning`.

La recette publique a également révélé le 15 novembre un défaut amont jusque-là masqué par les essais sur des actions dont l’avancement était renseigné : `classList.add('planning-task progress-unknown')` provoque une exception `InvalidCharacterError`. Le test navigateur `tests/test_gantt_browser.py` reproduit réellement l’échec sur Chromium avant correction, puis vérifie le rendu de trois cas : avancement absent, zéro explicite et statut terminé. Il contrôle aussi que le pourcentage absent ne présente aucun curseur et que le titre SVG échappé reste du texte. La correction tokenize uniquement les classes ; elle ne change ni les tâches, ni les dates, ni l’avancement, ni la CSP.
