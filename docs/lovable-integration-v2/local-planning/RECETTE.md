# Planning Lovable v2 — recette locale

Version groupée finale 0.7.0 sur `http://127.0.0.1:8766`, Chrome headless réel. **31 contrôles passent**, sans erreur JavaScript ni HTTP. Les captures ont été relues après exécution sur le client compilé avec le formulaire Responsable/Statut et les lignes de 65 px.

Le harnais réutilise seulement le dossier fictif `QA-PROP-F25014BA7A`, id `749e7ac0-d3ba-4e61-86bc-652e204dc0b3`. Il y conserve une action clairement nommée « Recette planning — action entièrement fictive ». Après chaque exécution, Début, Échéance, Avancement, Responsable et Statut sont remis à leurs valeurs initiales ; identifiant, priorité et description sont préservés. Les six actions planifiées par l’opérateur dans les dossiers principaux ne sont pas éditées.

## Contrôles exercés

- L’échéance seule reste À planifier, sans barre ni début déduit.
- Le formulaire global renseigne les vraies bornes Yjs. Le filtre n’affiche que le chantier choisi.
- Le choix du responsable conserve son propriétaire initial et propose les membres de l’organisation. Le changement de responsable et de statut est persisté dans cette même ligne, puis confirmé après rechargement et dans le formulaire du chantier.
- Mois précédent et suivant changent réellement la plage. Une action extérieure est masquée dans la grille sans modifier ses dates.
- Le jalon de livraison confirmé au 15 décembre reste distinct des dates d’intervention en novembre.
- Le rechargement restitue les mêmes dates et le pourcentage vide reste vide.
- Le dossier affiche la même ligne dans sa frise mensuelle et dans le mode Déplacer.
- Le constructeur Frappe corrigé affiche réellement une barre dont l’avancement n’est pas renseigné. Aucun curseur de pourcentage n’est proposé sur cette barre.
- Un vrai mouvement du pointeur déplace la barre d’un jour et déclenche un seul PUT natif. Le formulaire global retrouve immédiatement cette modification sur le même identifiant.
- Aux largeurs 390 et 320, la liste est le défaut à l’ouverture. La frise reste accessible, défile à l’intérieur de sa région et garde les noms fixes à gauche.
- Formulaires, listes et frises ne provoquent aucun débordement horizontal de la page.
- Les lignes d’action sont mesurées à 65 px de haut comme la référence Lovable, avec une cible de 44 px pour leur titre.
- Les faits confirmés du dossier sont inchangés après la recette.

Les valeurs et résultats détaillés sont dans `checks.json`, avec la restauration finale. Les treize captures citées par ce rapport couvrent FHD 1920×1080, mobile 390×844 et 320×760.

Reprise depuis le répertoire du produit :

```powershell
../../.venv/Scripts/python -X utf8 ../../work/qa_lovable_planning_v2.py
```

## Validation de la finition

La comparaison aux captures de référence a conduit à retirer le padding vertical qui portait les lignes d’action à 90 px autour de leurs cibles de 44 px : la valeur de 65 px a été confirmée sur toutes les lignes planifiées du run final. Les sous-textes redondants ont aussi été retirés et les commandes du planning d’un dossier réunies. Le typecheck complet passe. Les tests du modèle/lifecycle comptent 11 succès, et le test Chromium du moteur Frappe corrigé passe également.
