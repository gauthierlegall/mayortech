---
name: visual-qa
description: Audit visuel et DOM bloquant (Desktop 1920x1080 et Mobile 390x844) avec captures Playwright. À exécuter après toute modification UI.
---

# Skill Visual QA : Validation DOM & Rendu Sans Régression

Ce skill exécute un audit automatisé bloquant du DOM et du rendu graphique afin de garantir l'intégrité visuelle de la suite logicielle MayorTech en Light Mode.

## Procédure d'exécution

1. **Lancement de l'audit Playwright** :
   ```bash
   node .agent/skills/visual-qa/scripts/audit.mjs <URL>
   ```
   Exemple :
   ```bash
   node .agent/skills/visual-qa/scripts/audit.mjs http://127.0.0.1:19860/demo.html
   ```

2. **Assertions bloquantes (Exit code 1 en cas d'échec)** :
   - Aucune exception console ni `pageerror`.
   - Aucun débordement horizontal (`document.documentElement.scrollWidth <= window.innerWidth`).
   - Visibilité stricte des titres (`h1`, `h2`, `h3`) sans contraste blanc sur blanc ou noir sur noir.
   - Aucun bouton, badge ou onglet tronqué hors du viewport (`rect.right <= window.innerWidth + 2`).
   - Hauteur du canvas React Flow supérieure ou égale à `450px` sur desktop (1920x1080).

3. **Inspection visuelle obligatoire des captures** :
   - Examiner `.agent/tmp/qa/desktop.png` (1920x1080).
   - Examiner `.agent/tmp/qa/mobile.png` (390x844).
   - Vérifier la clarté typographique, l'alignement des éléments, l'absence de coupure et le respect scrupuleux du Light Mode.
