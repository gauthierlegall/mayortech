# RAPPORT GLOBAL ET SYNTHÈSE EXHAUSTIVE D'ARCHITECTURE & RÉALISATION
## PROJET : MAYORTECH / TRAVAUX — ESPACE NUMÉRIQUE SOUVERAIN DE GESTION MUNICIPALE
### Ville de Plougastel-Daoulas (Finistère, Bretagne)
**Date du document :** 19 Novembre 2026  
**Auteur :** Antigravity (Google DeepMind Agentic Pair Programmer) & Équipe Ingénierie Territoriale  
**Destinataire :** Modèle d'analyse Gemini (Format Chat) / Direction Générale des Services / Direction des Systèmes d'Information

---

## RÉSUMÉ EXÉCUTIF (EXECUTIVE SUMMARY)

Le projet **MayorTech** (nom de code de développement `travaux-mairie`) est une plateforme d'administration municipale intégrée, hautement souveraine et open-source, conçue sur mesure pour les besoins opérationnels, réglementaires et décisionnels de la collectivité territoriale de **Plougastel-Daoulas** (13 500 habitants).

Construit en rupture totale avec les SaaS américains propriétaires opaques (Monday, Asana, Notion cloud, Airtable, Jira) et les suites logicielles publiques vieillissantes et fragmentées, **MayorTech** unifie dans une interface Web fluide en **Light Mode épuré** (style Stripe / Linear / n8n / Iterop) :
1. **La gestion documentaire collaborative et native** (moteur Yjs / AFFiNE BlockSuite 0.22.4 embarqué sans iframe).
2. **La gestion de chantiers, d'interventions techniques et du suivi terrain** (Planning Gantt Frappe, fiches anomalies, réserves géolocalisées).
3. **Le raccordement non destructif aux serveurs de messagerie municipaux** (Exchange EWS, CalDAV, archives EML avec conservation de la preuve juridique).
4. **Un moteur d'orchestration de processus métier BPMN 2.0 standardisé** (SpiffWorkflow pur Python, conforme ISO/IEC 19510), doté d'une machine à jetons (Token Machine) déterministe et d'un générateur de circuits par IA en langage naturel.
5. **Une interface directive de décision et de signature d'actes municipaux (style Iterop)**, réduisant la complexité BPMN à un stepper d'approbation à 4 acteurs (*Agent instructeur -> Chef Services Techniques -> Directrice Générale des Services -> Maire*), avec scellement d'intégrité SHA-256 et clause de renvoi direct hors boucle.
6. **Quatre pôles d'activités territoriales complets** : Urbanisme & Ports, Bâtiments & Services Techniques, Enfance & CCAS, Finances M57 & Séances du Conseil Municipal.
7. **Un banc d'essai qualité automatisé (`visual-qa`)** piloté par Playwright bloquant toute régression graphique (zéro débordement mobile 390px, zéro texte invisible, zéro erreur de console).

---

## 1. CONTEXTE POLITIQUE, RÉGLEMENTAIRE ET PHILOSOPHIE DU PROJET

### 1.1. La Problématique des Collectivités Territoriales Françaises
Les mairies françaises font face à un triple paradoxe informatique :
- **L'éparpillement des outils** : Les agents naviguent entre un logiciel de gestion des courriers (souvent obsolète), un ERP comptable austère (type Berger-Levrault ou Cegid), des tableurs Excel locaux non sécurisés pour le suivi de voirie, et des échanges d'emails non tracés sur des boîtes Exchange.
- **La fracture ergonomique** : Les logiciels "métier" publics français souffrent d'une ergonomie des années 2000, complexe, lente et inadaptée aux écrans mobiles des agents sur le terrain ou aux tablettes des élus en commission. À l'inverse, l'adoption de SaaS modernes (Notion, Monday) expose la collectivité à l'extraterritorialité du Cloud Act américain, en violation des recommandations de l'ANSSI et du RGPD.
- **L'exigence de légalité régalienne** : Chaque décision municipale (délivrance d'un permis de construire, arrêté temporaire de circulation, bon de commande public, délibération du conseil municipal) doit scrupuleusement respecter le **Code Général des Collectivités Territoriales (CGCT)**, le **Code de l'Urbanisme**, la nomenclature budgétaire **M57**, et être dotée d'une chaîne de traçabilité opposable en cas de recours devant le Tribunal Administratif.

### 1.2. Les Piliers Doctrinaux de MayorTech
1. **Souveraineté des données et « Sovereign Kernels »** :
   - Zéro dépendance envers un cloud propriétaire obligatoire.
   - Base de données SQLite locale avec journalisation WAL (Write-Ahead Logging) et indexation plein texte FTS5 / BM25.
   - Intégrité cryptographique : chaque visa d'élu ou d'agent génère une empreinte numérique SHA-256 scellée dans l'historique d'audit.
2. **Esthétique Light Mode & Ergonomie Directive** :
   - Règle absolue : aucun "mode sombre" forcé, aucun "gris boueux". L'interface adopte les codes visuels du design scandinave et des outils SaaS de référence (Linear, Stripe, Vercel) : fond blanc pur `#FFFFFF` et ardoise claire `#F8FAFC`, bordures discrètes `#E2E8F0`, typographie DM Sans auto-hébergée, contraste strict conforme aux normes d'accessibilité WCAG AA.
   - Ergonomie directive : le maire et la DGS ne doivent pas manipuler des diagrammes BPMN complexes pour signer un arrêté. L'interface sépare la **décision métier** (stepper épuré à boutons d'action clairs) de la **supervision technique** (canvas de modélisation).
3. **Vérité du terrain et non-intrusion de l'IA** :
   - L'IA générative (Mistral ou fallback heuristique) n'est jamais autorisée à modifier silencieusement des faits ou à signer des actes à la place d'un être humain.
   - L'IA n'intervient que comme un assistant de saisie (génération de squelettes BPMN à partir d'un prompt, proposition de résumé de courriels, pré-remplissage de formulaires Cerfa soumis à relecture obligatoire).

---

## 2. ARCHITECTURE TECHNIQUE GLOBALE

```
+---------------------------------------------------------------------------------------+
|                                    NAVIGATEUR CLIENT                                  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  |                     FRONTEND REACT 18 + TYPESCRIPT + VITE                       |  |
|  |                                                                                 |  |
|  |  +---------------------+  +------------------------+  +-----------------------+ |  |
|  |  | Onglet « À valider »|  | Onglet « Suivi & BPMN »|  |  Onglet « Concepteur »| |  |
|  |  |  - Stepper 4 acteurs|  |  - @xyflow/react canvas|  |  - Studio visuel BPMN | |  |
|  |  |  - Acte & visas PDF |  |  - Living Edges animés |  |  - Prompt Studio IA   | |  |
|  |  |  - Décision sticky  |  |  - Sélecteur dossiers  |  |  - Form Builder JSON  | |  |
|  |  |  - Modale Renvoi    |  |  - Toggle Mode Démo    |  |    Schema             | |  |
|  |  +---------------------+  +------------------------+  +-----------------------+ |  |
|  |                                                                                 |  |
|  |  +---------------------------------------------------------------------------+  |  |
|  |  | PÔLES : Urbanisme (Leaflet) · Chantiers (Gantt) · Enfance · Finances M57  |  |  |
|  |  +---------------------------------------------------------------------------+  |  |
|  |  | MOTEUR DOCUMENTAIRE NATIF : AFFiNE / BlockSuite 0.22.4 (CRDT Yjs)          |  |  |
|  |  +---------------------------------------------------------------------------+  |  |
|  +---------------------------------------------------------------------------------+  |
+-------------------------------------------|-------------------------------------------+
                                            | REST API / JSON / WebSocket
+-------------------------------------------v-------------------------------------------+
|                               BACKEND FASTAPI (PYTHON 3.11+)                          |
|                                                                                       |
|  +--------------------+  +--------------------+  +---------------------------------+  |
|  |  API GATEWAY / OIDC|  |   SPIFFWORKFLOW    |  |      SOVEREIGN KERNELS          |  |
|  |  - Keycloak / RBAC |  |   BPMN 2.0 ENGINE  |  |  - repository.py (SQLite WAL)   |  |
|  |  - Casbin Domains  |  |  - Token Machine   |  |  - workspace.py                 |  |
|  |  - Zero-Trust      |  |  - Graph Validator |  |  - auth.py / governance.py      |  |
|  |  - Session cookies |  |  - Prompt-to-BPMN  |  |  - jobs.py / maintenance.py     |  |
|  +--------------------+  +--------------------+  +---------------------------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  |                      SERVICES MÉTIERS ET INTÉGRATIONS                           |  |
|  |  - collector.py / mailbox.py (Exchange EWS, CalDAV, parseur EML sans traceurs)  |  |
|  |  - signature_workflow.py (Scellement d'actes SHA-256, chaîne de paraphes)       |  |
|  |  - organigram_engine.py / municipal_directory.py (Arbre hiérarchique et rôles)|  |
|  |  - telegram_bridge.py / telegram_transport.py (Alertes chiffrées Bot Telegram) |  |
|  |  - retrieval.py / conversations.py (RAG SQLite FTS5 / BM25 local déterministe)  |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  |                       STOCKAGE LOCAL SOUVERAIN (PERSISTANCE)                     |  |
|  |  - Base de données : gallery.sqlite3 (SQLite avec WAL, FOREIGN KEYS)            |  |
|  |  - Coffre-fort documentaire : EML d'origine, PDF Cerfa, hashes SHA-256         |  |
|  |  - Snapshots Yjs documentaires binaires                                         |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

---

## 3. LE MOTEUR DE WORKFLOWS & LES CIRCUITS DE VALIDATION (AU CŒUR DU SYSTÈME)

La gestion des processus municipaux constitue la clé de voûte de MayorTech. Elle repose sur l'intégration du standard international **BPMN 2.0 (ISO/IEC 19510)** via la bibliothèque Python **SpiffWorkflow**, interfacée avec un visualiseur moderne et une boîte de décision inspirée de la solution française **Iterop**.

### 3.1. Le Backend SpiffWorkflow & La Machine à Jetons (Token Machine)
Fichiers sources :
- `src/travaux/workflow_engine.py`
- `src/travaux/workflow_token_machine.py`
- `src/travaux/workflow_graph_validator.py`
- `src/travaux/workflow_prompt.py`
- `src/travaux/workflow_routes.py`
- `src/travaux/workflow_templates.py`

#### Fonctionnalités clés :
1. **Persistance des définitions et versions** :
   Chaque circuit possède un cycle de vie complet : création en brouillon, validation de graphe, et publication d'une version immuable comportant le code standard `bpmn_xml` et sa représentation JSON normalisée pour le visualiseur (`bpmn_json`).
2. **Validateur de graphe formel (`WorkflowGraphValidator`)** :
   Avant toute exécution, le moteur analyse la topologie du diagramme :
   - Vérification de l'existence d'au moins un événement de début (`StartEvent`) et d'un événement de fin (`EndEvent`).
   - Détection des culs-de-sac (nœuds sans issue) et des orphelins (nœuds inaccessibles).
   - Analyse des divergences / convergences pour éviter les interblocages (*deadlocks*) sur les passerelles parallèles (`ParallelGateway`) ou exclusives (`ExclusiveGateway`).
3. **Machine à Jetons déterministe (`TokenEngine`)** :
   Modélise le cheminement réel de l'information :
   - Démarrage d'une instance associée à une clé métier (`business_key` type `PC-2026-042`).
   - Progression des jetons (*tokens*) d'état en état.
   - Suspension du jeton lors de l'arrivée sur une tâche utilisateur (`UserTask`), en attente d'une intervention humaine (formulaire rempli ou signature).
   - Calcul dynamique des SLA (délais limites d'instruction réglementaire).
4. **Générateur Assisté par IA (`PromptToBpmnEngine`)** :
   Permet à un cadre administratif de saisir en français naturel :  
   *« Créer un circuit pour les arrêtés de voirie temporaires : dépôt par l'entreprise, contrôle technique par le CTM sous 48h, validation juridique DGS, signature du Maire et envoi à la Police Municipale. »*  
   Le moteur génère automatiquement le graphe BPMN 2.0 conforme avec couloirs d'acteurs (*Swimlanes*), passerelles conditionnelles et formulaires de saisie associés.

---

### 3.2. La Refonte Ergonomique : Du "BPMN Brut" à la "Boîte de Décision Iterop"

Initialement, le système affichait une multitude d'onglets techniques (8 onglets) et forçait les utilisateurs à interagir directement sur un canvas BPMN complexe, générant de la confusion pour les élus.
La refonte récente a radicalement simplifié l'interface autour d'une philosophie directive en **3 onglets uniques** :

```
[ Circuits de validation ] (Badge: Ville de Plougastel-Daoulas)   [ + Lancer une validation ]
--------------------------------------------------------------------------------------------
[ À valider (3) ]         [ Suivi & BPMN ]         [ Concepteur ]
```

#### A. Onglet 1 : « À valider » (Interface de Décision Métier Directive)
Fichier source : `frontend-lovable/src/features/workflow/validation/MayorValidationInbox.tsx`
- **Barre supérieure de filtres rapides** : *Mes validations (1)*, *Service / Pool (1)*, *En attente DGS / Maire (2)*, *Historique / Signés (1)* + champ de recherche en texte clair.
- **Liste des dossiers en attente** : Badges d'urgence SLA (`21/11/2026 - Reste 18h`), intitulé clair, demandeur et rôle assigné.
- **Vue scindée (Split View) du dossier ouvert** :
  1. **Stepper Horizontal des 4 Acteurs Municipaux** :
     - `01 Agent instructeur (Gwenn LE BIHAN)` : Statut Signé (Vert) avec horodatage et empreinte.
     - `02 Chef Services Techniques (Erwan KERVRAN)` : Statut Signé (Vert) avec avis favorable voirie.
     - `03 Direction Générale DGS (Marie ROLLAND)` : Statut En cours (Badge bleu pulsant).
     - `04 Maire de Plougastel (Dominique CAP)` : Statut À venir.
     - Bouton rapide d'accès contextuel : `Voir le graphe BPMN`.
  2. **Zone Gauche : Visualiseur d'Acte Municipal Authentique** :
     - En-tête solennel : *RÉPUBLIQUE FRANÇAISE / VILLE DE PLOUGASTEL-DAOULAS / Direction Générale des Services*.
     - Visas juridiques complets : *Vu le Code Général des Collectivités Territoriales... Vu le Code de l'Urbanisme... Vu la demande déposée...*
     - Dispositif exécutoire : *ARTICLE 1ER, ARTICLE 2...*
     - Pièces justificatives certifiées téléchargeables (Cerfa 13404, Plan de masse coté, Avis ABF).
  3. **Zone Droite : Panneau de Décision Sticky** :
     - Champ de texte libre : *Observation / Motif du visa (facultatif)*.
     - **Bouton Primaire Vert Émeraude** : `Valider & Signer le dossier` -> applique immédiatement le visa régalien, scelle l'empreinte SHA-256 dans l'audit trail et avance le dossier vers l'étape du Maire.
     - **Bouton Secondaire Ambré** : `Renvoyer à une étape amont` -> ouvre la modale de renvoi.
     - **Bouton Tertiaire Rouge** : `Refuser le dossier`.
  4. **Modale Régalien de Renvoi (`Renvoyer le dossier`)** :
     - Sélection par bouton radio de l'étape amont cible (ex: Chef CTM ou Agent instructeur ADS).
     - **Case à cocher cruciale** : `Renvoi direct (exception hors boucle BPMN)` -> permet un recul discrétionnaire immédiat sans exiger une transition cyclique rigide pré-dessinée dans SpiffWorkflow.
     - Champ de saisie obligatoire : *Motif circonstancié du renvoi* (garantie de traçabilité juridique).

#### B. Onglet 2 : « Suivi & BPMN » (Living BPMN 2.0 sur React Flow)
Fichiers sources :
- `frontend-lovable/src/features/workflow/pixelflow/PixelFlowCanvas.tsx`
- `frontend-lovable/src/features/workflow/pixelflow/BpmnTaskNode.tsx`
- `frontend-lovable/src/features/workflow/pixelflow/BpmnGatewayNode.tsx`
- `frontend-lovable/src/features/workflow/pixelflow/BpmnLivingEdge.tsx`
- `frontend-lovable/src/features/workflow/pixelflow/BpmnDrawer.tsx`
- `frontend-lovable/src/features/workflow/pixelflow/DataPacketInspectorModal.tsx`

- **Moteur technique** : Construit à 100% sur `@xyflow/react` (React Flow v12) avec arrière-plan en grille de points (`BackgroundVariant.Dots`), minimap et contrôles de zoom/pan natifs.
- **Sélecteur de Dossier Réel** : Barre supérieure permettant de basculer instantanément entre les dossiers municipaux en cours (`PC-2026-042 Permis de Construire`, `ARR-2026-019 Arrêté Municipal`, `MP-2026-008 Marché Public`).
- **Coloration Dynamique du Chemin Réel** :
  - Les étapes antérieures validées sont surlignées en **vert émeraude discret** avec pastille `Validé ✓`.
  - L'étape active est mise en valeur par un **jeton ambré pulsant** (`PC-2026`) et son badge SLA (`Alerte 24h`).
  - Les étapes futures restent en contour neutre ardoise.
- **Cartes Nœuds Bento (`w-[270px]`)** :
  - Zéro troncature : titres de tâches complets sur 2 lignes avec icônes Lucide précises (*Guichet & Dépôt Cerfa 13404*, *Avis Technique CTM & Réseaux*, *Arbitrage DGS & Escalade*, *Visa Régalien de l'Adjoint*, *Scellement SHA-256*).
- **Arêtes Vivantes (`BpmnLivingEdge`)** :
  - Courbes `bezier` ou `smoothstep` avec pastilles de conditions posées directement sur la courbe (`[OUI] Conforme`, `[NON] Relance 30j`, `[NON] Rejet PLU`).
  - Animation de particules fluides à 60 FPS symbolisant le flux de données.
- **Tiroir d'Inspection & Bouton d'Action Immédiate** :
  - Clic sur un nœud ouvrant un tiroir latéral affichant les métadonnées, l'acteur assigné, les variables de formulaire, et un bouton direct : `Traiter ce dossier dans « À valider »`.
- **Sobriété Opérationnelle** :
  - Les commandes de simulation (Play, x1, x2, x4) sont masquées par défaut sous un toggle `Mode démo / simulation` afin de ne pas perturber l'expérience de supervision administrative réelle.

#### C. Onglet 3 : « Concepteur » (Studio BPMN Unifié & Prompt IA)
Fichier source : `frontend-lovable/src/features/workflow/designer/MayorWorkflowDesigner.tsx`
- Réunit le modeleur visuel par glisser-déposer de nœuds BPMN (Événements, Tâches Utilisateur, Passerelles, Fin de processus).
- Intègre un bandeau dépliable d'assistant IA : saisie d'un prompt métier avec génération de schéma en un clic.
- Éditeur de formulaires dynamiques JSON Schema intégré (`MayorFlowFormBuilderModal`), permettant d'associer des champs typés à chaque tâche humaine.

#### D. Le Bouton Global `+ Lancer une validation`
Fichier source : `frontend-lovable/src/features/workflow/validation/MayorValidationLaunchModal.tsx`
- Accessible en permanence depuis le header principal.
- Permet de démarrer immédiatement une procédure en choisissant parmi les modèles territoriaux :
  - *Permis de Construire (ADS)*
  - *Arrêté Temporaire de Voirie & Circulation*
  - *Marché Public & Bon de Commande*
  - *Projet de Délibération du Conseil Municipal*
- Champs de métadonnées, assignation du niveau d'urgence SLA, et zone de glisser-déposer de pièces justificatives PDF.

---

## 4. LES 4 PÔLES MÉTIERS MUNICIPAUX COUVERTS

MayorTech n'est pas un simple outil de workflow abstrait ; il intègre en profondeur la réalité des services d'une commune littorale comme Plougastel-Daoulas :

```
+---------------------------------------------------------------------------------------+
|                             LES 4 PÔLES MÉTIERS DE LA VILLE                           |
+---------------------------------------------------------------------------------------+
| 1. URBANISME, AMÉNAGEMENT & PORTS                                                     |
|    - Application du Droit des Sols (ADS) : instruction des permis et déclarations.    |
|    - Cartographie interactive (Leaflet / GeoJSON) : cadastre, parcelles et zonage PLU.|
|    - Gestion maritime : concessions de mouillages, cales de carénage, capitainerie.  |
+---------------------------------------------------------------------------------------+
| 2. SERVICES TECHNIQUES, BÂTIMENTS & CHANTIERS                                         |
|    - Conduite des opérations de travaux municipaux (Écoles, gymnases, voirie).        |
|    - Planning d'avancement Gantt (Frappe Gantt) avec jalons et dépendances Yjs.       |
|    - Suivi de terrain mobile : signalement d'anomalies, fiches réserves et photos.   |
+---------------------------------------------------------------------------------------+
| 3. ENFANCE, JEUNESSE & ACTION SOCIALE (CCAS)                                          |
|    - Campagnes d'inscriptions scolaires et périscolaires (cantine, garderie).        |
|    - Calcul automatique du Quotient Familial (QF) municipal selon barèmes CAF.       |
|    - Gestion des aides d'urgence du Centre Communal d'Action Sociale (CCAS).          |
+---------------------------------------------------------------------------------------+
| 4. FINANCES PUBLIQUES (M57), CULTURE & SÉANCES DU CONSEIL                             |
|    - Arbitrage budgétaire et engagements de dépenses selon l'instruction M57.        |
|    - Subventions aux associations culturelles et sportives.                           |
|    - Gestion solennelle des Séances : convocations, quorum, délibérations, PVs.      |
+---------------------------------------------------------------------------------------+
```

---

## 5. MOTEUR DOCUMENTAIRE NATIF (AFFiNE / BLOCKSUITE) & MESSAGERIE MUNICIPALE

### 5.1. Édition Collaborative Native Yjs
Fichiers sources : `native-editor/`, `src/travaux/native.py`, `frontend-lovable/src/features/workspace/BlockEditor.tsx`
- Au lieu d'intégrer des iframes tierces instables, MayorTech embarque directement les paquets npm open-source d'**AFFiNE / BlockSuite (v0.22.4)**.
- Les documents de chantier sont stockés sous forme de CRDTs binaires Yjs, sérialisés dans la base SQLite locale.
- Supporte la structuration en blocs riches (titres, listes, citations, tableaux de données dynamiques, bases de données en vue Kanban et Tableau).
- Contrôle strict de concurrence optimiste et reprise d'erreurs en cas de coupure réseau.

### 5.2. Hub de Messagerie et Preuve Juridique
Fichiers sources : `src/travaux/mailbox.py`, `src/travaux/collector.py`, `src/travaux/integrations/exchange.py`
- Connectivité aux boîtes mail de service via **Exchange Web Services (EWS)** ou fichiers standards EML.
- Les emails sont analysés de façon déterministe en texte brut. **Aucun traceur espion ni script HTML distant n'est exécuté**, protégeant les postes de la mairie des attaques de phishing et de pistage.
- Les pièces jointes (PDF, DOCX, plans de cadastre) sont extraites dans un bac à sable sécurisé sans fuite de mémoire.
- Les emails rattachés à un dossier conservent leur fichier original scellé, garantissant leur valeur probante en cas de contentieux.

---

## 6. ASSURANCE QUALITÉ, SKILL VISUAL-QA & TESTS AUTOMATISÉS

Le projet impose des critères de qualité industrielle stricts pour interdire toute régression esthétique ou fonctionnelle.

### 6.1. Le Skill Permanent `visual-qa`
Fichiers sources :
- `.agent/skills/visual-qa/SKILL.md`
- `.agent/skills/visual-qa/scripts/audit.mjs`

Ce skill utilise **Playwright** pour auditer chaque écran en double résolution : **Desktop (1920×1080)** et **Mobile (390×844)**.
Le script échoue immédiatement (`exit code 1`) de manière bloquante si :
1. Une erreur JavaScript (`pageerror`) ou une erreur console de niveau `error` est émise.
2. Un débordement horizontal est constaté : `document.documentElement.scrollWidth > window.innerWidth`.
3. Un texte d'en-tête (`h1, h2, h3`) ou un bouton essentiel est invisible (contraste texte/fond nul, couleur blanche sur fond blanc).
4. Un bouton d'action ou un onglet est recouvert ou inaccessible dans le viewport mobile.

### 6.2. Script de Capture Haute Fidélité (`capture_circuits_validation.py`)
Fichier source : `scripts/capture_circuits_validation.py`
Ce script autonome démarre le serveur FastAPI en tâche de fond sur le port local `19860`, initialise un contexte Playwright Chromium, navigue dans l'application, sélectionne les dossiers, actionne les modales et enregistre les captures d'écran en haute résolution dans le dossier :  
`C:\Users\Utilisateur\Desktop\GALERIE_CIRCUITS_VALIDATION` :
- `01_onglet_a_valider_dossier_ouvert.png`
- `02_modale_renvoyer_a_une_etape.png`
- `03_onglet_suivi_bpmn_metier.png`
- `04_version_mobile_390x844.png`

---

## 7. CARTOGRAPHIE EXHAUSTIVE DU CODE SOURCE

### 7.1. Backend Python (`src/travaux/`)

| Fichier | Lignes | Rôle et Responsabilité |
| :--- | :--- | :--- |
| `api.py` | ~450 | Point d'entrée principal FastAPI, enregistrement des routeurs, gestion CORS et CSRF. |
| `workflow_engine.py` | ~380 | Dépôt et gestionnaire des définitions SpiffWorkflow, stockage des versions XML/JSON. |
| `workflow_token_machine.py` | ~420 | Machine à jetons BPMN, transition d'états, orchestration des tâches humaines et calcul SLA. |
| `workflow_graph_validator.py` | ~210 | Validateur topologique de graphes BPMN 2.0 (détection de deadlocks, orphelins, cycles). |
| `workflow_prompt.py` | ~260 | Moteur de conversion Prompt Français -> Graphe BPMN 2.0 avec schémas de formulaires. |
| `workflow_routes.py` | ~260 | Endpoints REST `/api/v1/workflows/*` (définitions, instances, tokens, avancement). |
| `workflow_templates.py` | ~340 | Jeux de données initiaux : 10 modèles de circuits territoriaux prêts à l'emploi. |
| `signature_workflow.py` | ~290 | Moteur de visa régalien, chaîne d'approbation et scellement d'empreintes SHA-256. |
| `organigram_engine.py` | ~280 | Modélisation de la hiérarchie municipale (Maire, Adjoints, DGS, Responsables de pôles). |
| `municipal_directory.py` | ~310 | Annuaire des agents municipaux, matricules, rôles Casbin et délégations de signature. |
| `culture_finances.py` | ~350 | Pôle 4 : gestion budgétaire M57, engagements, subventions aux associations. |
| `enfance_sociale.py` | ~320 | Pôle 3 : inscriptions scolaires, quotient familial, aides CCAS d'urgence. |
| `urbanisme_ports.py` | ~340 | Pôle 1 : gestion du PLU, cadastre, autorisations de voirie, concessions portuaires. |
| `seances_instances.py` | ~310 | Gestion des conseils municipaux : ordres du jour, votes, délibérations officielles. |
| `field_reports.py` | ~250 | Pôle 2 : fiches d'interventions terrain, constats, réserves chantiers et photos. |
| `mailbox.py` & `collector.py` | ~580 | Collecteur d'emails Exchange/EML, nettoyage anti-phishing, extraction de pièces jointes. |
| `conversations.py` & `retrieval.py` | ~420 | Moteur RAG municipal avec recherche FTS5/BM25 sur base SQLite locale. |
| `telegram_bridge.py` & `telegram_transport.py`| ~310 | Passerelle de notification chiffrée sur canal Telegram pour alertes urgentes DGS/Maire. |
| `repository.py`, `workspace.py`, `auth.py`, `governance.py` | ~1200 | **Sovereign Kernels** : cœur persistant, isolation SQLite WAL, contrôle d'accès Casbin. |
| `native.py` | ~220 | Adaptateur de persistance Yjs pour l'éditeur de blocs BlockSuite. |

---

### 7.2. Frontend React / TypeScript (`frontend-lovable/src/`)

| Fichier / Répertoire | Rôle et Responsabilité |
| :--- | :--- |
| `features/workflow/MayorFlowView.tsx` | Conteneur principal des **Circuits de validation** avec header régalien et 3 onglets. |
| `features/workflow/validation/MayorValidationInbox.tsx` | **Interface directive « À valider » (style Iterop)** : stepper, acte PDF, panneau décision sticky. |
| `features/workflow/validation/MayorValidationLaunchModal.tsx` | Modale de création instantanée d'un circuit avec dépôt de pièces. |
| `features/workflow/validation/validationData.ts` | Modèle de données TypeScript pour les dossiers, étapes d'audit et initialisation démo. |
| `features/workflow/pixelflow/PixelFlowCanvas.tsx` | Canvas BPMN `@xyflow/react` Light Mode avec sélecteur de dossiers réels. |
| `features/workflow/pixelflow/BpmnTaskNode.tsx` | Composant de nœud Bento (`w-[270px]`) avec badges SLA, rôles et statuts. |
| `features/workflow/pixelflow/BpmnGatewayNode.tsx` | Losanges de décision XOR/AND avec icônes Lucide précises. |
| `features/workflow/pixelflow/BpmnLivingEdge.tsx` | Arêtes animées à 60 FPS avec pastilles de conditions intégrées. |
| `features/workflow/pixelflow/BpmnDrawer.tsx` | Tiroir d'inspection avec bouton `Traiter ce dossier dans « À valider »`. |
| `features/workflow/designer/MayorWorkflowDesigner.tsx` | Studio de modélisation visuelle BPMN unifié avec générateur de prompt IA. |
| `features/workflow/mayorflow/MayorFlowFormBuilderModal.tsx` | Constructeur visuel de formulaires dynamiques JSON Schema pour tâches humaines. |
| `features/urbanisme/GeoMap.tsx` | Cartographie Leaflet des parcelles cadastrales de Plougastel et zones du PLU. |
| `features/workspace/BlockEditor.tsx` | Éditeur natif AFFiNE / BlockSuite 0.22.4 avec synchronisation temps réel Yjs. |
| `features/workspace/GlobalPlanning.tsx` | Planning des travaux avec moteur Gantt Frappe et gestion des dépendances. |
| `features/workspace/Conversation.tsx` | Fenêtre pop-up de l'Assistant conversationnel avec sourçage documentaire exact. |

---

## 8. ÉTAT DES LIEUX À DATE (CE QUI EST FAIT ET VALIDÉ)

### Ce qui est 100% Fonctionnel et Vérifié :
1. **Refonte Ergonomique Complète (Style Iterop)** :
   - Header unifié avec titre *Circuits de validation*, badge territorial et bouton `+ Lancer une validation`.
   - Réduction stricte à **3 onglets métiers** (`À valider`, `Suivi & BPMN`, `Concepteur`).
   - Split view d'approbation d'actes municipaux (visas CGCT/CU, pièces jointes, stepper 4 acteurs).
   - Panneau de décision sticky avec signature instantanée SHA-256 et modale de renvoi avec dérogation administrative directe.
2. **Supervision BPMN Réactive sur React Flow** :
   - Remplacement de l'ancien canvas sombre par un canvas Light Mode élégant sur fond ardoise et points gris.
   - Nœuds Bento larges sans troncature de texte.
   - Synchronisation en temps réel avec le dossier sélectionné (traçage du chemin parcouru en vert émeraude, étape active pulsante).
   - Contrôles de simulation dissimulés pour préserver l'ergonomie opérationnelle.
3. **Studio et Générateur de Workflows par Prompt IA** :
   - Traduction fluide de prompts rédigés en français en modèles BPMN 2.0 valides.
   - Association de schémas de formulaires dynamiques JSON Schema aux tâches utilisateur.
4. **Pôles Métiers Territoriaux Opérationnels** :
   - Fiches d'urbanisme, cartographie cadastre, calcul du QF enfance, arbitrage budgétaire M57, gestion des conseils municipaux.
5. **Assurance Qualité & Conformité DOM** :
   - Zéro régression responsive : parfait affichage sur iPhone (390×844) et écrans Full HD (1920×1080).
   - Validation 100% réussie du script bloquant `audit.mjs` de Playwright.
   - Build Vite sans warning et packaging automatisé des assets statiques dans le backend FastAPI.

---

## 9. QUESTIONS STRATÉGIQUES ET PISTES D'ANALYSE RECOMMANDÉES POUR GEMINI

En tant qu'intelligence artificielle analysant ce dossier de projet, voici les axes prioritaires sur lesquels votre analyse critique et vos recommandations sont attendues :

1. **Robustesse Juridique et Opposabilité Administrative** :
   - La chaîne de visa numérique mise en place (empreintes SHA-256 scellées dans l'audit trail avec horodatage) est-elle suffisante pour résister à un recours devant le Tribunal Administratif ?
   - Quelles recommandations apporteriez-vous pour l'intégration d'un tiers de confiance pour signature électronique qualifiée conforme au règlement européen **eIDAS** et au référentiel **RGS\*\*** (clés cryptographiques matérielles USB Token pour le Maire) ?
2. **Performance et Scalabilité du Moteur SpiffWorkflow** :
   - Pour une collectivité gérant plusieurs centaines d'arrêtés et permis simultanés, quel dimensionnement de base de données SQLite (ou bascule PostgreSQL avec conservation de l'isolation tenant) préconiseriez-vous pour la Machine à Jetons ?
   - Comment optimiser l'exécution asynchrone des tâches de fond (Celery / Redis vs SQLite worker actuel) lors de montées en charge sur les alertes SLA ?
3. **Extension de l'Assistant IA Territorial** :
   - Comment enrichir le moteur de prompt pour permettre la génération automatique de visas juridiques complexes à partir de la jurisprudence administrative locale (accès aux bases Légifrance / OpenData Justice) ?
   - Quelles précautions déontologiques et réglementaires maintenir pour éviter toute dérive d'automatisation abusive sur les refus de permis de construire ?
4. **Ergonomie et Conduite du Changement** :
   - L'approche inspirée d'Iterop (stepper directif 4 acteurs) est-elle la plus pertinente pour les agents communaux de catégorie C peu accoutumés aux outils numériques ? Quels ajustements d'accessibilité (RGAA niveau AA) pourraient encore être apportés ?

---
*Fin du document de synthèse — MayorTech v2.0 (Novembre 2026)*
