---
name: civic-distill
description: Guide de design engineering minimaliste et d'épuration stricte pour MayorTech (Light Mode Civic Craft, 1 seul CTA plein par écran, zéro boîte imbriquée, divulgation progressive, régime sec des badges, zéro ornement tech).
---

# Civic Distill — Design Engineering & Épuration Radicale

Ce skill impose une discipline stricte d'ingénierie visuelle pour concevoir des interfaces d'administration publique sobres, dignes et zéro-friction.
Il s'applique obligatoirement à toute passe de développement frontend sur MayorTech.

## 1. Règle du 1 seul bouton plein par écran
- Une vue ou un écran ne peut contenir qu'**UN SEUL** bouton plein à fond coloré (le CTA principal de l'écran, ex. `Signer et transmettre` en Vert Sceau `#0F766E`).
- Toutes les autres actions (ex. `+ Nouvelle validation`, `Mode Parapheur`, `Filtres`, `Exporter`) doivent être :
  - Soit des boutons fantômes ou légers avec filet fin (`bg-white border border-stone-200 text-stone-800 hover:border-stone-400 font-medium`),
  - Soit des liens texte discrets (`hover:underline`),
  - Soit regroupées dans un menu contextuel `···`.
- **Interdiction absolue** d'afficher un bouton plein répété sur chaque ligne d'un tableau ou d'une liste (`✓ Traiter` sur 10 lignes). La ligne entière doit être cliquable avec un simple indicateur typographique ou flèche fine `→`.

## 2. Zéro boîte imbriquée (No Card-in-Card)
- Interdiction stricte d'encapsuler des cartes bordées à l'intérieur d'une autre carte déjà bordée.
- Remplacer les empilements de boîtes par des surfaces plates posées directement sur le fond Vélin `#F7F7F5`.
- Pour structurer les éléments internes, privilégier des filets séparateurs fins `1px` (`divide-y divide-stone-200` ou `border-b border-stone-200/80`) et un espacement vertical régulier.

## 3. Divulgation progressive (Progressive Disclosure)
- Aucun champ de formulaire facultatif vide ne doit être affiché ouvert par défaut (ex. zone de texte `Observation facultative`).
  - Le masquer derrière un lien discret `+ Ajouter une observation` qui déploie le champ au clic, ou l'ouvrir contextuellement lors d'un renvoi.
- L'édition de correction mineure (ex. coquille dans un acte) se fait par clic direct sur le texte concerné plutôt que par un bouton permanent `Corriger une coquille`.

## 4. Régime sec des badges (Max 2 par ligne)
- **Références administratives** (`PC-2026-042`, `DELIB-2026-031`, `MP-2026-008`) : affichage en texte brut `font-mono text-xs text-stone-500` sans bordure ni fond coloré.
- **Échéances & SLA** : texte sobre coloré (ambre foncé `text-amber-700` si urgent, gris `text-stone-500` sinon), sans pilule ni cadre.
- **Réserver les badges encadrés** exclusivement aux alertes critiques ou statuts juridiques réglementaires (ex. `Secret professionnel CCAS`, `SLA dépassé`).

## 5. Règle Zéro Gadget (Anti-ornement tech)
- Interdiction formelle d'introduire :
  - Des métriques de latence fictives (`< 50 ms`, ping, millisecondes),
  - Des pastilles vertes de statut/présence décoratives (`●`),
  - Des animations pulsantes (`animate-pulse`, `animate-ping`) sans justification critique,
  - Des mentions marketing ou faussement dynamiques (`Temps réel`, `Live`, `60 FPS`),
  - Des icônes paillettes ou baguettes magiques (`Sparkles`, `Wand2`, `✨`),
  - Des slogans UX ou phrases de remplissage (`Vérifiez les visas puis signez d'un clic`).
- Chaque pastille ou micro-texte doit porter une donnée métier réelle et vérifiable.

## 6. Test du retrait obligatoire
Avant de clore une intervention, l'agent doit lister explicitement au moins **3 éléments visuels supprimés** sans aucune perte fonctionnelle pour l'utilisateur.
