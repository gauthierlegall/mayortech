# Recette après corrections ciblées — 14 novembre 2026

Cette recette clôt les corrections du complément web identifiées dans [l'audit initial](audit-avant.md), **avant le raccordement du nouvel éditeur natif AFFiNE**. Elle ne valide pas ce raccordement, une instance AppFlowy, un déploiement municipal ni la conformité RGPD. Les données et les sauvegardes simulées de test sont fictives.

| Domaine | Contrôle après correction | Résultat |
| --- | --- | --- |
| Accessibility | Tab mobile, panneau fermé/ouvert, Échap, retour de focus, resize desktop→mobile, compteur live | Liens cachés `inert`, état ARIA synchronisé, focus visible ; compteur de recherche `role=status` |
| Layout |28 rendus1440/720/390/320px ; ordre accueil/liste | Aucun débordement global ; changements avant les chantiers ; chantier ayant des propositions en premier |
| Writing | Nom/référence et nature de l'information visibles | Valeur « Proposition · Avancement » avec chantier et référence ; ancien avancement explicitement « confirmé ». Deux constats du baseline restent au moteur documentaire entrant, ci-dessous |
| Typography | Texte à200%, saisies mobiles | Sidebar contenue et défilante, tous les liens accessibles ; saisies16px sur mobile. Les mots longs peuvent revenir à la ligne dans la navigation agrandie |
| Colors | Paires calculées et DOM rendu | Proposition sélectionnée **6,562:1** ; bordure de saisie sur blanc **3,113:1** ; aucun texte sous seuil parmi les éléments inspectés sur7 routes |
| UI | Filtre terminé, brouillon note, échec/succès de sauvegarde | Filtre « Terminés » accepte `completed` et l'alias `closed` ; brouillon restauré ; aucune perte avant confirmation du serveur |

## Changements vérifiés

| Avant | Après observé | Preuve |
| --- | --- | --- |
|8 liens invisibles reçoivent Tab dans la sidebar mobile fermée | Premier Tab après le lien d'évitement : bouton menu visible x13px ; panneau fermé absent du parcours ; Échap donne `aria-expanded=false` ; resize déplace le focus caché vers le menu | [Mesures clavier](evidence-apres/mesures-extra.json), tests UI |
| Note perdue après changement d'onglet | Texte intact après Notes→Mémoire→Notes et après liste→retour au chantier ; rechargement déclenche l'avertissement natif et son annulation préserve la saisie | Test `test_note_draft_survives_tabs_and_chantier_navigation_and_warns_on_reload` |
| Saisie sans état intermédiaire préservé | Un échec503 de sauvegarde conserve le texte ; succès simulé affiche la note confirmée et vide le brouillon uniquement ensuite. Les réponses POST sont interceptées par le navigateur, sans mutation du serveur | Test `test_note_failure_keeps_draft_and_success_clears_it_only_after_confirmation` |
| Le filtre ne trouve pas le chantier « Terminé » | « Terminés » affiche Éclairage du port des Dunes ; recherche référence exacte conserve le bon résultat | [Filtre](evidence-apres/390-filter-closed.png), [mesures](evidence-apres/mesures.json), tests Node et UI |
| Changements après6 chantiers, valeurs masquées | Trois changements nommés/identifiés et leurs valeurs apparaissent avant la liste ; le chantier concerné ouvre la liste avec son avancement confirmé | [Accueil390](evidence-apres/390-overview.png), [accueil desktop](evidence-apres/1440-overview.png), [liste320](evidence-apres/320-projects.png) |
| Texte de sélection4,289:1 et bordure1,558:1 | Couleur de sélection verte sombre et limite de saisie plus marquée | [Mesures](evidence-apres/verification.json), [revue](evidence-apres/390-review.png) |
| Barre latérale déborde à200% | Largeur et scrollWidth restent236px, défilement vertical propre ; le fond reste sous le contenu défilant | [Texte200%](evidence-apres/1440-notes-text200.png), [mesures](evidence-apres/mesures-extra.json) |

Les brouillons de note restent **uniquement en mémoire JavaScript**, par chantier. Aucune note n'est écrite dans `localStorage`, `sessionStorage` ou IndexedDB. Ce mécanisme protège la navigation courante ; il ne garantit pas la récupération après arrêt brutal du navigateur. Une sauvegarde réelle confirmée par le serveur reste nécessaire.

## Tests exécutés

TDD : les2 nouveaux tests Node et7 premiers tests UI ont d'abord échoué sur les défauts constatés, avant implémentation. Après correction :

- `node --test web/tests/model.test.mjs` : **8 réussis,0 échec**.
- `node --check web/app.js` : sortie0.
- `.venv/Scripts/python.exe -m pytest ../../work/test_ux_regressions.py -q` : **8 réussis,0 échec**. Le test supplémentaire couvre le contrat d'échec puis succès de la sauvegarde, avec fixtures HTTP au navigateur.
- Captures Playwright/Chrome après correction :28 vues, zéro erreur JavaScript observée, aucune requête de mutation transmise au serveur ; aucun débordement horizontal global. Les tableaux sources sont des fiches étiquetées à320px, sans colonnes supprimées.
- Suite projet complète lancée : `.venv/Scripts/python.exe -m pytest -q`. **Échec de collecte** sur `tests/test_workspace_pages.py:7` : `ModuleNotFoundError: travaux.workspace`. Ce fichier venait d'être ajouté pendant le chantier parallèle du moteur natif. La suite complète n'est donc pas déclarée verte ; elle devra être relancée une fois ce chantier intégré.

Les mesures sources et captures sont conservées dans [evidence-apres](evidence-apres/). Les scripts d'audit et tests de navigateur se trouvent dans `work/`. Les premières captures1440 d'erreur/vide des scripts exploratoires montrent l'amorçage ; elles ne sont pas utilisées comme preuve de ces états. Les états chargement/vide/503 ont été inspectés séparément dans la recette initiale.

## Reste à vérifier avec le moteur natif

- **MEDIUM — lecture du récapitulatif** : remplacer la restitution Markdown brute et ses anciennes clés métier internes par une vraie lecture documentaire ; vérifier ensuite citations, édition, enregistrement et version approuvée dans l'éditeur intégré.
- **MEDIUM — provenance humaine** : afficher les origines réellement retournées par le nouveau moteur et « auteur non vérifié » lorsque c'est le cas ; aucun identifiant technique ne doit servir de nom humain. Le test initial `manual_appflowy` documente le contrat ancien, pas un raccordement AFFiNE.
- Après raccordement AFFiNE : refaire les parcours320/390, clavier, texte200%, liens de preuve et saisie de note. La présente recette ne préjuge pas de la hauteur, des menus ni de l'édition mobile du composant natif.
- Non vérifiés : restitution audio réelle NVDA/VoiceOver, zoom Chrome par raccourci, Safari/iOS physique. Le test720 CSS px couvre le reflow équivalent à une fenêtre1440px au zoom200% ; le redimensionnement du texte est testé séparément. Ceci ne constitue pas un audit RGAA complet.

**Verdict : Approve pour les corrections ciblées du complément web inspecté.** Les5 défauts HIGH du baseline sont corrigés et testés dans ce périmètre. Les2 constats MEDIUM documentaires ci-dessus et la recette du nouveau moteur demeurent ouverts ; la suite projet complète attend la fin de son intégration.
