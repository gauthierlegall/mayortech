# CONTEXTE MAÎTRE DE SESSION — MAYORTECH (`travaux-mairie`)

> **Usage :** Charger ce document en début de toute nouvelle session Antigravity (ex. `@CONTEXTE_ANTIGRAVITY_MAYORTECH.md`) avant d'exécuter un nouveau lot. Il fait foi sur l'architecture, le design system, les règles métier municipales, les interdits absolus et le protocole de validation visuelle.

---

## 1. VISION PRODUIT & POSITIONNEMENT

**MayorTech** (dépôt `travaux-mairie`, collectivité pilote : **Ville de Plougastel-Daoulas**, Finistère) est un **cockpit opérationnel et orchestrateur souverain de gestion municipale** (open-source, local-first, Light Mode).

* **Positionnement stratégique** : MayorTech ne cherche pas à imposer le remplacement brutal des ERP réglementaires lourds (Berger-Levrault, JVS, Ciril, Plat'AU). Il se déploie **à la carte** (en surcouche agile pour les communes déjà équipées, ou en socle complet pour les petites/moyennes communes) pour combler le vide entre **Exchange, Excel, le suivi terrain et les circuits de validation internes**.
* **Cible utilisateur** : Agents de mairie (y compris non-informaticiens / catégorie C), Chefs de service (CTM, ADS, Finances, CCAS), Directrice Générale des Services (DGS), Adjoints et Maire.
* **Principe d'adoption** : Zéro friction pour les décideurs, séparation stricte entre l'ergonomie d'exécution (ultra-directive) et la modélisation technique (masquée aux décideurs).

---

## 2. STACK TECHNIQUE & VERROUS D'INTÉGRITÉ

### 2.1. Stack Active
* **Frontend (`frontend-lovable/`)** : React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, `@xyflow/react` (React Flow v12), AFFiNE / BlockSuite `0.22.4` (CRDT Yjs natif sans iframe), Frappe Gantt, Leaflet.
* **Backend (`src/travaux/`)** : FastAPI (Python 3.11+), SQLite en mode WAL (`FOREIGN KEYS` activées) + recherche plein texte FTS5/BM25 (RAG local déterministe), moteur BPMN 2.0 `SpiffWorkflow` (Machine à Jetons déterministe + `WorkflowGraphValidator` anti-deadlocks + `PromptToBpmnEngine`), Keycloak/OIDC + Casbin RBAC, collecteur Exchange EWS / CalDAV / EML.
* **Packaging** : le frontend compilé (`npm run build`) doit **toujours** être packagé dans les assets servis par FastAPI (`package_frontend.py` ou script équivalent) avant toute capture Playwright.

### 2.2. Les 5 Noyaux Souverains (`Sovereign Kernels` — INTANGIBLES)
**RÈGLE CRITIQUE** : ne jamais casser la signature, les contrats ni les empreintes des 5 noyaux souverains :
1. `src/travaux/repository.py`
2. `src/travaux/workspace.py`
3. `src/travaux/auth.py`
4. `src/travaux/governance.py`
5. `src/travaux/jobs.py`

Toute nouvelle persistance ou intégration externe doit passer par des tables/modules isolés (ex. `src/travaux/connectors/` ou modules dédiés).

---

## 3. DIRECTION ARTISTIQUE — « CIVIC CRAFT » (LIGHT MODE STRICT)

L'application doit dégager une esthétique institutionnelle française contemporaine (précision type Linear / design suisse + sobriété éditoriale), loin des templates Tailwind bleus génériques et **totalement opposée au dark mode terminal**.

### 3.1. Palette & Tokens Visuels
* **Fonds** :
  * Fond global de l'application : **Papier Vélin clair (`#F7F7F5`)**.
  * Sidebar : **`#FBFBF9`** avec bordure droite nette `border-stone-200/80`.
  * Cartes & panneaux : **`#FFFFFF`**, bordure `1px` nette `border-stone-200/90`, ombre quasi plate `shadow-[0_1px_2px_rgba(16,42,76,0.04)]`.
  * Feuille d'acte officiel (`PROJET D'ACTE MUNICIPAL`) : fond papier chaud **`#FFFEFC`** coiffé d'un **micro-filet tricolore discret de 2px** (`#102A4C` / `#FFFFFF` / `#B91C1C`) uniquement sur le bord supérieur du document.
* **Couleurs d'action & sémantiques** :
  * Primaire (CTA, onglet actif, liens forts) : **Bleu Encre Marine (`#102A4C`, hover `#193D6B`)** — ne plus utiliser le bleu Tailwind `#2563EB` partout.
  * Validé / Signé : **Vert Sceau (`#0F766E` / fond `#F0FDFA`)**.
  * Renvoi / Vigilance SLA : **Ambre institutionnel (`#B45309` / fond `#FFFBEB`)**.
  * Refus / Dépassement critique : **Carmin (`#9F1239` / fond `#FFF1F2`)**.
* **Géométrie & Typographie** :
  * Conteneurs en `rounded-lg`, boutons / champs / badges de référence en `rounded-md` (éviter l'abus de `rounded-full` partout).
  * **Toujours mettre `whitespace-nowrap shrink-0`** sur les badges de référence (`PC-2026-042`, `ARR-2026-019`, `MP-2026-008`) et les boutons d'action pour qu'ils ne se coupent jamais sur 2 ou 3 lignes.
  * Police UI : `DM Sans` + `tabular-nums` sur tous les compteurs, dates, montants et SLA + micro-labels en `text-[11px] uppercase tracking-[0.08em] font-semibold text-stone-500`.
  * Police Actes Officiels : **Serif éditoriale sobre** (`Source Serif 4` ou `Newsreader`, fallback `Georgia, serif`) réservée au corps des arrêtés et visas juridiques.
  * `font-mono` réservée **strictement** aux références brutes (`PC-2026-042`), délais SLA et empreintes `SHA-256`.

### 3.2. Interdits Absolus sur l'UI (Tolérance Zéro)
* **Zéro mode sombre forcé** : interdiction des fonds `#070B14`, des cartes semi-transparentes « gris boueux » (`bg-slate-900/50`, `bg-slate-800/40`) sur fond clair, et des bordures néon.
* **Zéro jargon technique dans les écrans métier** : ne jamais afficher `SpiffWorkflow`, `PixelFlow`, `Sugiyama`, `React Flow`, `JSON Schema`, `Bento` ou des slugs bruts (`flow_instruction_...`) dans l'interface utilisateur.
* **Zéro badge marketing/debug** : ne jamais afficher `60 FPS`, `DYNAMIQUE`, `0 € Iterop`, `Licence : 0 € Propriétaire`, ni citer le nom d'un concurrent (`Iterop`) dans un preset ou libellé.
* **Zéro doublon de navigation** : ne jamais dupliquer le bouton `Focus Élu` ni afficher 2 barres d'onglets identiques en `Mode Focus Élu`, ni dupliquer un CTA dans le header et le footer d'un même Drawer.

---

## 4. LOGIQUE MÉTIER MUNICIPALE STRICTE

### 4.1. Séparation Stricte par Commission (`commissionConfig.ts`)
Les éléments « Travaux » (`CHANTIERS`, `Planning Gantt`, `Suivi terrain`, `Chantiers actifs`, `Signaler un point terrain`) ne doivent **JAMAIS** apparaître dans les autres commissions.

| Profil / Commission | Accent | Section métier Sidebar | Éléments épinglés | Dossiers & Circuits visibles |
| :--- | :--- | :--- | :--- | :--- |
| **0. Direction Générale** *(Maire / DGS)* | Marine `#102A4C` | Accès transversal + Supervision SLA | Arbitrages DGS prioritaires | Tous les dossiers arrivés à l'étape DGS/Maire *(hors CCAS nominatif sans habilitation)* |
| **1. Fonctions supports & transitions** | Indigo `#3730A3` | `FINANCES & INSTANCES` : Arbitrages M57, Marchés Publics (CAO), Séances & Conseil | `INSTANCES & BUDGETS` (`BP 2026`, `CAO Nov.`, `Conseil 26 nov.`) | Marchés publics (`MP-2026-008`), Délibérations, Arbitrages M57, RH. **Zéro chantier.** |
| **2. Action sociale, enfance & jeunesse** | Prune `#7E22CE` | `ENFANCE & CCAS` : Inscriptions scolaires, Quotient Familial, Aides CCAS | `CAMPAGNES` (`Rentrée scolaire`, `Commission CCAS`) | **Cloisonnement légal absolu (secret professionnel)** : les dossiers CCAS (`CCAS-2026-089`) ne fuitent jamais hors de cette commission. |
| **3. Urbanisme, travaux & ports** | Pin `#0F766E` | `TERRAIN & TERRITOIRE` : Planning Gantt, Suivi terrain, Carte PLU & Ports | **`CHANTIERS`** (*Alizés*, *Goélands*, *Rivage*, *Ajoncs*) | ADS (`PC-2026-042`, `DP-2026-051`), Voirie (`ARR-2026-019`), AOT portuaires. **Passerelle** : bouton `Demander un engagement M57 / Marché` vers Commission 1. |
| **4. Culture, sport & vie associative** | Terracotta `#C2593F` | `VIE LOCALE` : Subventions assos, Salles & Équipements, Agenda culturel | `ÉQUIPEMENTS` (*Espace culturel*, *Complexe sportif*) | Subventions, conventions associatives, manifestations publiques. |

* **Cohérence d'identité** : le prénom dans `Bonjour [Prénom]`, le pôle affiché en bas de la sidebar (épinglé et toujours visible sur 1080p via `overflow-y-auto` sur la zone centrale) et le rôle actif dans `À valider` doivent toujours correspondre.

### 4.2. Périmètre Modulaire par Organisation (`useOrganizationModules()`)
À la création d'une collectivité (Wizard 3 étapes) et à chaud dans `Paramètres > Modules & Périmètre` (désactivation **non destructive**, zéro perte SQLite) :
* **Socle obligatoire (verrouillé)** : `core_directory` (Annuaire & Organigramme), `core_workflows` (Circuits de validation), `core_documents` (Documents & Coffre SHA-256).
* **Modules métiers cochables** : `urbanisme_ads`, `ports_littoral`, `travaux_terrain`, `enfance_ccas`, `finances_m57`, `conseil_seances`, `messagerie_eml`.
* **Options & Connecteurs cochables** : `ai_assistant`, `connector_ctes`, `connector_eidas`, `mobile_alerts`.
* **4 Presets 1 clic** (avec surbrillance active synchronisée) : `Circuits seuls`, `Commune rurale`, `Ville complète`, `Commune littorale`.
* **Impact réel** : un module décoché disparaît de la sidebar, de la navigation mobile, des onglets internes (ne jamais laisser un onglet `Arbitrages financiers` vide avec avertissement brut si `finances_m57` est désactivé), des modèles de `+ Lancer une validation`, et renvoie `403` côté FastAPI.

### 4.3. Exactitude Juridique & Données Cohérentes
* **Urbanisme** : ne pas mélanger Déclaration Préalable (`Cerfa 13404`, pièces `DP2/DP3`) et Permis de Construire (`Cerfa 13406*12`, pièces `PCMI2/PCMI3/PCMI4`, ex. `PC-2026-042`). Délais réglementaires : notification pièces manquantes sous **1 mois** (Art. R.423-22), délai usager de **3 mois** pour compléter (délai d'instruction suspendu, puis `Rejet tacite` si expiré).
* **Valeur probante** : une empreinte locale **SHA-256** garantit l'intégrité interne du journal d'audit ; elle ne remplace pas une signature qualifiée eIDAS. Toujours formuler : *« Empreinte d'intégrité SHA-256 (compatible parapheur eIDAS / RGS\*\*) »*.
* **Libellés dynamiques** : ne pas écrire `"documents certifiés Cerfa"` sur un marché public (`MP-2026-008`) ou un arrêté de voirie (`ARR-2026-019`) ; utiliser `"pièces justificatives certifiées"` ou `"documents joints"`.

---

## 5. ARCHITECTURE FONCTIONNELLE DÉJÀ EN PLACE (À PRÉSERVER)

1. **Navigation globale épurée** :
   * Desktop : `Accueil`, `Validations` (badge compteur), `Messagerie`, `Dossiers`, `Tâches & Suivi`, section métier de la commission active, `Absence & Suppléant`, `Paramètres`.
   * Header : Fil d'Ariane + Barre de recherche universelle `Ctrl+K` (`CommandPaletteModal.tsx`) + bouton unique `Focus Élu`.
   * Mobile (`390x844`) : barre basse avec accès direct `Accueil`, `À valider` (badge), `Dossiers`, `Messages`, `Tâches`. Aucun chevauchement du FAB `Assistant` sur les boutons d'action.
2. **Circuits de validation (`MayorFlowView.tsx` — 3 onglets uniquement + CTA `+ Lancer une validation`)** :
   * **`À valider` (`MayorValidationInbox.tsx`)** : split view, stepper 4 acteurs, acte officiel en serif, historique des visas SHA-256, édition de coquille tracée en ligne (`Corriger une coquille` → v1.1), bandeau de surlignage après renvoi, panneau décision sticky **dynamiquement synchronisé sur l'étape `En cours`** du dossier sélectionné, modale `Renvoyer à une étape` avec option *« Renvoi direct hors boucle standard »* et motif obligatoire, `Mode Parapheur` en rafale.
   * **`Suivi du circuit` (`PixelFlowCanvas.tsx` sur `@xyflow/react`)** : sélecteur de dossier réel, mode démo/simulation caché derrière un toggle, passerelles `AND` parallèles (CTM + ABF simultanés), rail d'escalade SLA déporté à gauche sans croisement de cartes ni collision de labels, `Arbitrage DGS & Escalade` relié à 2 sorties (`Réaffectation` et `Évocation directe`, zéro deadlock), tiroir latéral propre (`top-[72px]`, 1 seul CTA). Mobile = timeline verticale avec `<select>` compact + barre fixe `Valider & Signer` / `Renvoyer`.
   * **`Concepteur` (`MayorWorkflowDesigner.tsx`)** : React Flow unifié + prompt `<textarea rows={2}>` + palette manuelle (`+ Étape`, `+ Passerelle XOR`, `+ Parallèle AND`) + éditeur de champs de formulaire.
3. **Accueil (`TodayDashboardView.tsx`) & `Mode Focus Élu`** :
   * `Bonjour [Prénom]` + date sobre + 3 KPIs adaptés à la commission + priorités à traiter (badges référence sur 1 ligne) + activité récente cohérente + prochaines échéances + raccourcis.
   * `Mode Focus Élu` : 1 seule barre supérieure minimaliste (`À signer`, `Agenda & Séances`, `Dossiers suivis`, `Revenir à la vue complète`), zéro distraction.

---

## 6. FEUILLE DE ROUTE DES PROCHAINS LOTS (À EXÉCUTER SUR DEMANDE UNIQUEMENT)

Ne jamais lancer un lot ci-dessous sans ordre explicite de l'utilisateur :

* **Lot A — Finalisation Civic Craft & Commissions** : appliquer intégralement les sections 3 et 4.1 si pas encore validées par captures dans `AUDIT_CIVIC_CRAFT_METIER`.
* **Lot B — Workflow d'Enrôlement Mairie (`Paramètres > Structure & Enrôlement`)** :
  * Double hiérarchie (Élus / Administration), délégations de signature (avec arrêté PDF), suppléances/intérim, statut `Ghost User`.
  * Wizard 4 étapes : (1) Commune INSEE + strate + pôle pilote, (2) Import PDF/CSV organigramme OU liens d'auto-enrôlement par pôle `/join/:poleToken` OU SSO/Exchange, (3) Approbation des demandes d'enrôlement directement dans `À valider`, (4) Organigramme React Flow interactif + Check-list de santé.
* **Lot C — Hub d'Interconnectivité Souveraine (`Paramètres > Connexions`) & Ergonomie Zéro Friction** :
  * Bus d'adaptateurs `src/travaux/connectors/` (`ConnectorAdapter` + Mode Bac à sable local) : **ProConnect** (OIDC), **Pastell / i-Parapheur / Maarch** (`@CTES` + signature RGS\*\*/eIDAS + simulation webhook), **Grist** (La Suite Numérique : M57, QF, Ports), **Tchap / Matrix & Ntfy** (alertes souveraines remplaçant Telegram par défaut), **Gotenberg** (export PDF/A réel dans `À valider`), **Docling** (parsing PDF organigrammes & PLU pour le RAG).
  * Ergonomie avancée : `Lien magique Élu` (`/quick-sign/:token` ultra-épuré mobile), bascule 1 clic depuis `Messagerie` vers `+ Lancer une validation`, `Vue Liste simple` synchronisée avec le graphe dans `Concepteur`, gestion `Absence & Suppléant` en 1 clic.

---

## 7. PROTOCOLE DE QUALITÉ & VALIDATION VISUELLE (`visual-qa` — OBLIGATOIRE)

À la fin de **chaque** lot de développement, respecter scrupuleusement cette séquence sans aucune exception :

1. **Intégrité** : confirmer que les 5 noyaux souverains n'ont subi aucune régression.
2. **Build & Packaging** : exécuter `npm run build`, packager le frontend dans FastAPI et redémarrer le serveur local (vérifier qu'aucun ancien bundle n'est servi).
3. **Audit Playwright bloquant** : exécuter `node .agent/skills/visual-qa/scripts/audit.mjs <URL>` en Desktop (`1920x1080`) et Mobile (`390x844`). Corriger **toute** erreur bloquante :
   * `0` erreur console ou `pageerror`
   * `0` débordement horizontal (`scrollWidth <= innerWidth`)
   * `0` titre invisible (contraste nul)
   * `0` bouton, badge ou onglet coupé hors viewport ou masqué par un FAB / barre mobile
4. **Inspection visuelle honnête** : ouvrir et inspecter réellement chaque PNG produit. **Interdiction de simuler des passes factices ou de déclarer un écran conforme s'il contient encore un chevauchement, une troncature ou une incohérence métier.** Signaler explicitement ce qui reste à améliorer.

---

## 8. AMORCE TYPE POUR DÉMARRER UNE NOUVELLE SESSION ANTIGRAVITY

Copier-coller ce bloc dans un **nouveau chat Antigravity** :

```text
Lis intégralement `@CONTEXTE_ANTIGRAVITY_MAYORTECH.md` et applique-le comme référence stricte pour toute cette session (Design System Civic Craft Light Mode, scoping strict par commission, 5 noyaux souverains intacts, zéro jargon technique, protocole `visual-qa` bloquant).

Ta mission unique pour cette session : [DÉCRIRE LE LOT PRÉCIS ICI — ex. Lot A / Lot B / Lot C].
Ne déborde pas sur les autres lots. À la fin : build, packaging FastAPI, `audit.mjs`, inspection réelle des PNG demandés et compte-rendu factuel court.
```