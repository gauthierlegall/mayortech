# Master Plan Général : Enrôlement Municipal, Moteur de Workflow Open-Source BPMN 2.0 (Suite MayorFlow) & Simulation PixelFlow

**Collectivité de référence.** Ville de Plougastel-Daoulas (~13 500 habitants)  
**Plateforme.** MayorTech — Plateforme Souveraine d'Aide à la Décision Municipale  
**Coût de licence.** **0 € (100% Logiciel Libre & Open-Source, Zéro Abonnement Propriétaire)**  
**Programme.** Intégration unifiée des 3 chantiers stratégiques :
1. **Chantier A : Processus d'Enrôlement, Annuaire Municipal & Matrice d'Habilitations** (Demande Utilisateur #5)
2. **Chantier B : Moteur de Workflow Open-Source BPMN 2.0 « MayorFlow » (Alternative 100% Libre à Iterop : Play, Studio, Watch)** (Demandes Utilisateur #3 & #6)
3. **Chantier C : Workflow Prompt-to-BPMN & Simulateur Canvas 16-bit « PixelFlow »** (Demande Utilisateur #4)

---

## 0. Déclaration de Souveraineté & Stack 100% Open-Source

Contrairement aux solutions propriétaires et payantes du marché (telles qu'Iterop / Dassault Systèmes ou Visiativ, facturées par utilisateur et par mois avec des coûts d'intégration élevés), la suite **MayorFlow** intégrée à MayorTech repose exclusivement sur des briques **libres, auditables et auto-hébergées à coût de licence nul** :

| Composant Métier | Rôle Fonctionnel (Équivalent Propriétaire) | Brique Open-Source Retenue | Licence Logicielle | Coût Licence |
| :--- | :--- | :--- | :---: | :---: |
| **Moteur d'Exécution BPMN** | Moteur de processus, passerelles, minuteurs | [**SpiffWorkflow**](https://github.com/sartography/SpiffWorkflow) + `TokenEngine` Python | **LGPL / BSD** | **0 €** |
| **Studio Graphique BPMN** | Éditeur visuel drag-and-drop (*Iterop Design*) | [**bpmn-io (`bpmn-js`)**](https://github.com/bpmn-io/bpmn-js) + `diagram-js` | **MIT** | **0 €** |
| **Animation des Flux** | Animation des jetons sur les chemins | [**`bpmn-js-token-simulation`**](https://github.com/bpmn-io/bpmn-js-token-simulation) | **MIT** | **0 €** |
| **Formulaires Dynamiques** | Form builder & saisie contextuelle | **React JSON Schema Form (`@rjsf/core`)** | **Apache 2.0** | **0 €** |
| **Portail Opérationnel** | Inbox agents & suivi de dossiers (*Iterop Play*) | **MayorFlow Play** (React / Tailwind natif) | **MIT / Interne** | **0 €** |
| **Supervision & BAM** | Heatmap des goulots, KPIs (*Iterop Watch*) | **MayorFlow Watch** (Recharts / SVG natif) | **MIT / Interne** | **0 €** |
| **Simulateur Rétro 16-bit** | Vulgarisation des flux de données pour élus | **PixelFlow Canvas HTML5** (Moteur 2D natif) | **MIT / Interne** | **0 €** |
| **Identité & 2FA TOTP** | Sas d'adhésion et contrôle des accès | **Keycloak Community 26.8.2** | **Apache 2.0** | **0 €** |

---

## Sommaire Exécutif & Vue d'Ensemble des 30 Lots

Le plan d'exécution est découpé en **30 lots industriels** répartis en **6 pôles stratégiques** :

```mermaid
graph LR
    subgraph P1["Pôle 1 : Enrôlement & Identités"]
        L01[Lot 01 : Schéma Annuaire]
        L02[Lot 02 : Import CSV Massif]
        L03[Lot 03 : Sas Enrôlement & 2FA]
        L04[Lot 04 : Approbation DGS]
        L05[Lot 05 : Délégation & Départ]
    end

    subgraph P2["Pôle 2 : Organigramme & Droits"]
        L06[Lot 06 : Moteur Hiérarchique]
        L07[Lot 07 : UI Organigramme Interactif]
        L08[Lot 08 : Fiche de Poste & Matrice]
        L09[Lot 09 : Exports Certifiés PDF/SVG]
        L10[Lot 10 : Sync Délibérations]
    end

    subgraph P3["Pôle 3 : Noyau BPMN 2.0 Spiff/Python"]
        L11[Lot 11 : Schéma BPMN Canonique]
        L12[Lot 12 : Moteur à Jetons & Passerelles]
        L13[Lot 13 : Formulaires User Tasks]
        L14[Lot 14 : Minuteurs & Escalade SLA]
        L15[Lot 15 : Tâches Service & Sceau]
    end

    subgraph P4["Pôle 4 : Suite MayorFlow Open-Source"]
        L16[Lot 16 : MayorFlow Play - Inbox]
        L17[Lot 17 : MayorFlow Play - Suivi Live]
        L18[Lot 18 : MayorFlow Studio - bpmn-js]
        L19[Lot 19 : MayorFlow Studio - Form Builder]
        L20[Lot 20 : MayorFlow Watch - BAM & Heatmap]
    end

    subgraph P5["Pôle 5 : Prompt-to-BPMN & Auto-Layout"]
        L21[Lot 21 : Parseur LLM Logic-Core]
        L22[Lot 22 : Validateur de Consistance]
        L23[Lot 23 : Auto-Layout Topologique DAG]
        L24[Lot 24 : 10 Templates Municipaux]
        L25[Lot 25 : Prompt Studio Différentiel]
    end

    subgraph P6["Pôle 6 : Simulateur PixelFlow & Déploiement"]
        L26[Lot 26 : Canvas 16-bit & Tuyauterie]
        L27[Lot 27 : Animation Paquets Pixel]
        L28[Lot 28 : Pupitre Transport & Scénarios]
        L29[Lot 29 : Inspecteur Paquets de Données]
        L30[Lot 30 : Intégration, Sécurité & Hetzner]
    end

    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
```

---

# PÔLE 1 : Enrôlement Municipal, Annuaire Sécurisé & Gouvernance des Accès

### Lot 01 : Modèle de Données de l'Annuaire Municipal & Entités Métier
- **Objectif** : Structurer le socle relationnel immuable décrivant les agents communaux, élus, services, directions et commissions permanentes sans toucher aux 5 fichiers protégés du noyau.
- **Spécifications Techniques** :
  - Création du module `src/travaux/municipal_directory.py`.
  - Tables SQLite : `municipal_directory_entries`, `municipal_departments`, `municipal_position_profiles`, `municipal_tenures`.
  - Prise en charge des statuts statutaires : titulaire, contractuel, élu municipal, vacataire, prestataire certifié.
  - Typage Pydantic v2 strict avec validation regex pour les adresses courriel `@ville-plougastel.bzh`.
- **Definition of Done (DoD)** :
  - Migrations de schéma auto-exécutables sans altération des hashes protégés.
  - 100% de couverture de tests unitaires sur les contraintes d'unicité (matricule, email, mandat).

---

### Lot 02 : Pipeline d'Ingestion Massive CSV & Contrôle Sémantique
- **Objectif** : Permettre à la Direction des Ressources Humaines (DRH) d'importer l'intégralité du personnel municipal via un fichier CSV normalisé en mode dry-run et réel.
- **Spécifications Techniques** :
  - Script CLI d'exploitation : `scripts/enrollement_batch.py`.
  - En-têtes obligatoires : `matricule`, `nom`, `prenom`, `email`, `statut`, `direction`, `poste`, `commission_id`, `niveau`, `role`, `delegation_signature`.
  - Validation des 6 niveaux de privilèges (Niveau 0 à Niveau 5).
  - Détection des doublons, des adresses invalides et des anomalies hiérarchiques (ex: poste de direction sans commission rattachée).
- **Definition of Done (DoD)** :
  - Fichier témoin `data/enrolement_plougastel.csv` de 40 agents/élus importé sans erreur.
  - Rapport d'audit de pré-importation JSON généré avec métriques de conformité.

---

### Lot 03 : Sas d'Auto-Enrôlement avec Code d'Organisation & TOTP 2FA
- **Objectif** : Décentraliser l'inscription des nouveaux agents et élus municipaux tout en garantissant un sas de confinement sécurisé jusqu'à l'approbation formelle.
- **Spécifications Techniques** :
  - Extension de la table `account_join_requests` existante (`workspace.py`).
  - Formulaire front-end React dans `frontend-lovable/src/features/auth/MunicipalJoinModal.tsx`.
  - Saisie du Code Confidentiel Municipal (`PLOUGASTEL-2026`).
  - Intégration Keycloak OIDC avec enrollment obligatoire TOTP (QR-Code FreeOTP / Google Authenticator) avant l'accès au sas.
  - Isolement complet : l'utilisateur en statut `pending` ne peut lire aucun dossier communal.
- **Definition of Done (DoD)** :
  - Test Playwright simulant une inscription avec code valide et avec code erroné.
  - Redirection automatique vers la page d'attente d'approbation régalienne.

---

### Lot 04 : File d'Attente d'Approbation Régalienne DGS & Audit Log
- **Objectif** : Fournir à la Direction Générale des Services (DGS) une interface régalienne pour valider, refuser, corriger ou réassigner les demandes d'enrôlement en temps réel.
- **Spécifications Techniques** :
  - Vue d'administration DGS : `frontend-lovable/src/features/admin/EnrollmentApprovalQueue.tsx`.
  - Endpoints REST :
    - `GET /api/v1/organization/join-requests/pending`
    - `POST /api/v1/organization/join-requests/{id}/decision` (`status: approved | rejected`, `assigned_commission`, `assigned_level`).
  - Enregistrement immédiat dans `governance_audit_log` avec horodatage UTC, IP cliente et empreinte SHA-256 de la décision.
- **Definition of Done (DoD)** :
  - Validation d'un agent débloquant instantanément ses droits dans sa commission sans redémarrage de conteneur.
  - Traçabilité complète vérifiable dans l'audit log.

---

### Lot 05 : Matrice des Délégations, Suppléances ("On Behalf Of") & Révocation
- **Objectif** : Gérer la continuité du service public communal en cas d'absence d'un élu ou d'un cadre, et assurer la révocation instantanée lors d'un départ de la mairie.
- **Spécifications Techniques** :
  - Module `src/travaux/delegation_manager.py`.
  - Table `municipal_delegations` (démissionnaire, suppléant, commission, date début, date fin, arrêté municipal de référence).
  - Mécanisme d'exécution *"On Behalf Of"* : toute signature ou validation par un suppléant est annotée juridiquement avec mention du titulaire et du décret d'intérim.
  - Révocation à chaud : endpoint `POST /api/v1/organization/members/{id}/revoke` désactivant l'accès Keycloak et réassignant les tâches pendantes au pool de service.
- **Definition of Done (DoD)** :
  - Test unitaire vérifiant qu'un suppléant peut viser une fiche financière au nom de l'Adjoint aux Finances absent.
  - Révocation d'un compte révoquant immédiatement sa session active.

---

# PÔLE 2 : Organigramme Interactif & Cartographie des Responsabilités

### Lot 06 : Moteur de Génération de l'Organigramme Hiérarchique & Matriciel
- **Objectif** : Calculer dynamiquement la topologie de l'organisation communale combinant la hiérarchie administrative (DGS -> Pôles -> Services) et la gouvernance politique (Maire -> Adjoints -> Commissions).
- **Spécifications Techniques** :
  - Module `src/travaux/organigram_engine.py`.
  - Endpoint `GET /api/v1/municipal/organigram/topology`.
  - Sortie JSON structurée sous forme d'arborescence multiniveaux enrichie des liens matriciels (élus rattachés à plusieurs commissions).
  - Détection automatique des postes vacants ou à pourvoir pour la DRH.
- **Definition of Done (DoD)** :
  - L'arborescence générée reproduit fidèlement la structure réelle de Plougastel (4 commissions permanentes, 8 services communaux).

---

### Lot 07 : Composant UI d'Organigramme Interactif (Canvas / SVG Pan & Zoom)
- **Objectif** : Offrir aux agents et aux élus une vue visuelle de toute la collectivité avec navigation fluide, recherche en direct et filtres par pôle.
- **Spécifications Techniques** :
  - Composant React `frontend-lovable/src/features/organigram/MunicipalOrganigramCanvas.tsx`.
  - Rendu SVG vectoriel avec support du pinch-to-zoom, pan drag-and-drop et recentrage automatique.
  - Badges visuels distinctifs :
    - Bleu nuit pour les Élus (Pouvoir délibératif).
    - Vert émeraude pour la DGS (Administration générale).
    - Orange terracotta, Rose cerise, Vert forêt, Violet améthyste pour les 4 commissions.
- **Definition of Done (DoD)** :
  - Rendu fluide à 60 FPS sur écran Full HD (1920×1080) et adaptation réactive tactile sur mobile (390×844).

---

### Lot 08 : Fiche de Poste Enrichie & Matrice des Habilitations (Niveaux 0 à 5)
- **Objectif** : Permettre de cliquer sur n'importe quel nœud de l'organigramme pour consulter la fiche de poste, le périmètre d'action et les habilitations exactes de la personne.
- **Spécifications Techniques** :
  - Drawer latéral interactif `frontend-lovable/src/features/organigram/PositionProfileDrawer.tsx`.
  - Affichage :
    - Identité, contact certifié, photo/avatar de rôle.
    - Commission(s) et statut (Titulaire / Élu / Suppléant).
    - Jauge visuelle de responsabilité (Niveau 0 à 5).
    - Droits granulaires (Lecture seule, Dépôt de projet, Visa technique, Vote scellé, Clôture PV).
    - Suppléant désigné en cas d'absence.
- **Definition of Done (DoD)** :
  - Navigation instantanée entre le titulaire et son suppléant par clic croisé.

---

### Lot 09 : Exportations Réglementaires Certifiées (PDF Haute Résolution & SVG)
- **Objectif** : Permettre à la mairie d'exporter l'organigramme officiel pour affichage réglementaire en hôtel de ville, transmission en préfecture ou intégration au recueil des actes administratifs.
- **Spécifications Techniques** :
  - Générateur d'export `src/travaux/organigram_export.py`.
  - Endpoint `POST /api/v1/municipal/organigram/export` (`format: pdf | svg | csv`).
  - Export PDF format A3 / A4 paysage avec cartouche officiel de la Ville de Plougastel-Daoulas, date de validité et signature numérique de la DGS.
- **Definition of Done (DoD)** :
  - Téléchargement opérationnel d'un fichier PDF A3 imprimable vectoriel sans perte de qualité.

---

### Lot 10 : Synchronisation avec le Registre des Délibérations & Déclarations d'Intérêts
- **Objectif** : Lier chaque élu et cadre aux délibérations portant délégation de signature et aux déclarations d'intérêts (prévention des conflits d'intérêts).
- **Spécifications Techniques** :
  - Liaison avec le module des arrêtés municipaux de MayorTech.
  - Affichage des déports obligatoires : si un élu est rattaché à une commission traitant d'un marché avec une société où il détient des intérêts, un avertissement automatique est affiché sur sa fiche d'organigramme.
- **Definition of Done (DoD)** :
  - Avertissement automatique visible lors de la constitution de l'ordre du jour d'une séance de commission.

---

# PÔLE 3 : Moteur de Workflow Open-Source BPMN 2.0 (SpiffWorkflow & Python)

### Lot 11 : Modèle de Données BPMN 2.0 Standard ISO/IEC 19510 & Intégration SpiffWorkflow
- **Objectif** : Créer le modèle de stockage et de versionnage des définitions de processus BPMN 2.0 conforme au standard international ouvert, exécutable nativement en Python sans dépendance propriétaire.
- **Spécifications Techniques** :
  - Module `src/travaux/workflow_engine.py` intégrant le parseur et la structure XML de **`SpiffWorkflow`** (Licence BSD/LGPL).
  - Tables SQLite :
    - `workflow_definitions` (id, key, name, category, commission_id, current_version, created_at).
    - `workflow_versions` (id, definition_id, version_number, bpmn_xml, bpmn_json, state: draft | published | archived).
    - `workflow_instances` (id, version_id, business_key, initiator_id, state: running | completed | terminated, variables_json).
    - `workflow_tokens` (id, instance_id, current_node_id, state: active | waiting | consumed).
- **Definition of Done (DoD)** :
  - Import et export de fichiers `.bpmn` 2.0 standardisés 100% compatibles Camunda Modeler, bpmn-js et SpiffWorkflow.

---

### Lot 12 : Moteur d'Exécution à Jetons (Token Machine) & Passerelles Décisionnelles
- **Objectif** : Implémenter l'algorithme d'exécution à jetons en pur Python FastAPI gérant les transitions d'état séquentielles, parallèles et conditionnelles.
- **Spécifications Techniques** :
  - Moteur `TokenEngine` dans `src/travaux/workflow_token_machine.py`.
  - Prise en charge des passerelles BPMN normalisées :
    - **XOR (Passerelle exclusive)** : Évaluation des expressions logiques Python/JSONPath sur les variables du dossier (ex: `montant_ht > 40000`).
    - **AND (Passerelle parallèle)** : Division d'un jeton en $N$ sous-jetons (fork) et synchronisation de tous les jetons avant franchissement (join).
    - **OR (Passerelle inclusive)** : Activation conditionnelle concurrente.
- **Definition of Done (DoD)** :
  - 10 tests de trajectoires BPMN (linéaire, fork/join, boucle, refus) validés avec passage de jeton certifié sans latence.

---

### Lot 13 : Gestionnaire de Formulaires Dynamiques Open-Source (JSON Schema Form)
- **Objectif** : Permettre de rattacher à chaque étape humaine (User Task) un formulaire de saisie adaptatif au format ouvert JSON Schema (sans aucun abonnement SaaS).
- **Spécifications Techniques** :
  - Intégration frontend de **`@rjsf/core`** (React JSON Schema Form, Licence Apache 2.0).
  - Table `workflow_task_forms` et `workflow_form_fields`.
  - Types de champs supportés : texte, zone de texte, nombre monétaire (€), sélecteur de date, téléversement de pièces jointes (PDF), choix multiple, visa de conformité (checkbox avec horodatage).
  - Validation des schémas côté backend avec Pydantic v2.
- **Definition of Done (DoD)** :
  - Soumission d'un formulaire validant la tâche, enregistrant les variables et propulsant le jeton vers le nœud suivant.

---

### Lot 14 : Minuteurs d'Échéances (Timer Events), Délais Légaux & Escalade SLA
- **Objectif** : Gérer les délais stricts d'instruction communale (délais de recours des tiers, délais d'instruction du permis de construire, notification préfectorale).
- **Spécifications Techniques** :
  - Table `workflow_timers` (task_id, trigger_at, sla_action, reminder_sent).
  - Tâche d'arrière-plan périodique (Scheduler asynchrone FastAPI) vérifiant les minuteurs expirés.
  - Actions d'escalade automatique :
    - Envoi d'une notification de relance au gestionnaire.
    - Réattribution automatique au chef de service (Niveau 3) après expiration du SLA légal.
    - Déclenchement d'une branche BPMN d'urgence (Boundary Timer Event).
- **Definition of Done (DoD)** :
  - Test temporel accéléré validant le déclenchement de la branche de dépassement de délai légal.

---

### Lot 15 : Tâches de Service Automatisées (Python Service Tasks) & Scellement SHA-256
- **Objectif** : Exécuter des actions techniques en arrière-plan sans intervention humaine (génération de délibérations, notifications mails, publication open data, horodatage cryptographique).
- **Spécifications Techniques** :
  - Exécuteurs de tâches de service Python natifs :
    - `generate_decision_pdf` : compilation du document PDF officiel avec mentions légales.
    - `notify_commission_members` : envoi de push/email aux élus de la commission.
    - `seal_decision_hash` : calcul de l'empreinte SHA-256 du dossier complet et enregistrement dans le journal d'audit.
    - `publish_to_display` : bascule de visibilité sur l'affichage légal municipal.
- **Definition of Done (DoD)** :
  - Exécution complète d'une Service Task avec génération de PDF scellé en moins de 500 ms.

---

# PÔLE 4 : Suite MayorFlow Open-Source — Play (Exécution), Studio (Édition) & Watch (Supervision)

### Lot 16 : MayorFlow Play — Boîte de Réception Unifiée & Prise en Charge de Tâches
- **Objectif** : Offrir aux agents et élus une interface ergonomique centralisant toutes leurs tâches à accomplir à travers les différents workflows municipaux (*alternative 100% libre et gratuite à Iterop Play*).
- **Spécifications Techniques** :
  - Composant React `frontend-lovable/src/features/workflow/mayorflow/MayorFlowPlayInbox.tsx`.
  - Onglets : *Mes Tâches à traiter*, *Tâches de mon service (non assignées)*, *Dossiers que j'ai initiés*, *Historique terminé*.
  - Bouton *"Prendre en charge"* pour s'attribuer une tâche du pool commun de la commission.
  - Badges d'urgence colorés selon l'approche de l'échéance légale (Vert > 7 jours, Orange < 48h, Rouge expiré).
- **Definition of Done (DoD)** :
  - Filtrage instantané par commission et recherche textuelle multi-colonnes.

---

### Lot 17 : MayorFlow Play — Visualiseur de Trajet en Temps Réel & Formulaire d'Exécution
- **Objectif** : Permettre à l'instructeur d'exécuter sa tâche tout en visualisant exactement où se situe le dossier dans la chaîne globale de décision.
- **Spécifications Techniques** :
  - Vue d'exécution `frontend-lovable/src/features/workflow/mayorflow/MayorFlowTaskExecutionView.tsx`.
  - Panneau gauche : mini-carte BPMN interactive propulsée par **`bpmn-js/lib/NavigatedViewer`** (Licence MIT) avec surbrillance du nœud courant et jalonnement des étapes.
  - Panneau droit : formulaire dynamique de saisie adapté au rôle avec boutons d'action explicites (*Valider*, *Demander pièces complémentaires*, *Rejeter*).
- **Definition of Done (DoD)** :
  - Mise à jour en temps réel via WebSocket de l'avancement du dossier lors de la validation.

---

### Lot 18 : MayorFlow Studio — Atelier de Modélisation BPMN 2.0 Drag-and-Drop avec `bpmn-js`
- **Objectif** : Fournir aux administrateurs et directeurs de service un éditeur graphique complet pour concevoir des processus communaux sans coder (*alternative 100% libre et gratuite à Iterop Design*).
- **Spécifications Techniques** :
  - Intégration de **`bpmn-js/lib/Modeler`** (Licence MIT) dans `frontend-lovable/src/features/workflow/mayorflow/MayorFlowStudioCanvas.tsx`.
  - Palette d'éléments standard BPMN :
    - Événements de début / fin (Start/End Events).
    - Tâches utilisateur (User Tasks) et Tâches de service (Service Tasks).
    - Passerelles décisionnelles (XOR, AND, Inclusive OR).
    - Connecteurs directionnels orthogonaux avec étiquettes de transition.
  - Import et export de fichiers `.bpmn` XML conformes aux standards ouverts de l'OMG.
- **Definition of Done (DoD)** :
  - Modélisation visuelle par drag-and-drop, alignement magnétique et export XML/SVG instantané.

---

### Lot 19 : MayorFlow Studio — Form Builder JSON Open-Source & Couloirs de Rôles (Swimlanes)
- **Objectif** : Associer chaque étape à un couloir de responsabilité (Adjoint, Chef de service, Instructeur, DGS) et composer ses champs par glisser-déposer sans dépendance externe.
- **Spécifications Techniques** :
  - Prise en charge des couloirs horizontaux (Swimlanes) associés aux 6 niveaux d'habilitation ou aux 4 commissions.
  - Composant `frontend-lovable/src/features/workflow/mayorflow/MayorFlowFormBuilder.tsx`.
  - Génération de définitions JSON Schema standardisées et prévisualisation instantanée desktop/mobile.
- **Definition of Done (DoD)** :
  - Déplacement d'une tâche d'un couloir "Instructeur" vers "Adjoint" réattribuant automatiquement le niveau de privilège requis de Niveau 2 à Niveau 4.

---

### Lot 20 : MayorFlow Watch — Tableau de Bord BAM & Heatmap Thermique des Goulots
- **Objectif** : Donner à la DGS et aux maires adjoints une vision macroscopique de l'efficacité administrative de la commune (*alternative 100% libre et gratuite à Iterop Watch*).
- **Spécifications Techniques** :
  - Dashboard de supervision `frontend-lovable/src/features/workflow/mayorflow/MayorFlowWatchDashboard.tsx`.
  - Indicateurs clés (KPIs) :
    - Délai moyen d'instruction par commission.
    - Nombre de dossiers bloqués ou hors délais légaux.
    - Répartition de la charge de travail entre instructeurs.
  - **Heatmap des goulots** : coloration thermique (vert/jaune/rouge) directement sur les nœuds du diagramme `bpmn-js` via les overlays d'éléments pour repérer les étapes où les dossiers s'accumulent.
  - Bouton DGS de réattribution d'urgence en masse.
- **Definition of Done (DoD)** :
  - Calcul dynamique de la heatmap sur 100 dossiers simulés avec mise en évidence du goulot d'étranglement.

---

# PÔLE 5 : Prompt-to-BPMN & Génération Intelligente de Processus

### Lot 21 : Parseur LLM Prompt-to-Logic-Core & Extraction Sémantique
- **Objectif** : Convertir une description textuelle libre en langage naturel (ex: *"Workflow d'instruction d'un permis de construire avec avis ABF et signature de l'Adjoint"*) en structure logique JSON normalisée.
- **Spécifications Techniques** :
  - Module `src/travaux/workflow_prompt.py`.
  - Architecture inspirée de `Stieges/bpmn-generator` : découplage strict entre l'extraction logique (Logic-Core) et le positionnement spatial.
  - Extraction des entités :
    - Déclencheur initial (Start Event).
    - Tâches et rôles associés (Adjoint, DGS, Instructeur).
    - Nœuds de décision et conditions de branchement.
    - Délais maximaux impartis.
    - Événement de clôture (End Event).
- **Definition of Done (DoD)** :
  - 10 prompts municipaux de test convertis avec succès en JSON Logic-Core valide.

---

### Lot 22 : Validateur de Consistance Sémantique & Réparation Automatique de Graphe
- **Objectif** : Garantir qu'aucun workflow généré par IA ne contienne d'impasse logique, de boucle infinie ou de nœud orphelin.
- **Spécifications Techniques** :
  - Validateur de graphe orienté (DAG Validation) dans `src/travaux/workflow_graph_validator.py`.
  - Règles vérifiées :
    - Exactement un Start Event accessible.
    - Au moins un End Event atteignable depuis toutes les branches.
    - Toute passerelle divergente (Split) doit être refermée par une passerelle convergente (Join) correspondante.
    - Aucune tâche sans acteur assigné.
  - Fonction d'auto-réparation : ajout automatique d'une passerelle de clôture ou d'un nœud de rejet par défaut si le prompt était incomplet.
- **Definition of Done (DoD)** :
  - Test de robustesse : 20 prompts volontairement ambigus ou incomplets réparés et validés automatiquement.

---

### Lot 23 : Algorithme d'Auto-Layout Topologique DAG & Calcul des Connecteurs
- **Objectif** : Calculer les coordonnées $(X, Y)$ harmonieuses de chaque boîte BPMN et tracer les connecteurs sans chevauchement disgracieux.
- **Spécifications Techniques** :
  - Algorithme de disposition par couches (Sugiyama Layout simplifié adapté au BPMN) :
    1. Détermination des rangs topologiques (colonnes d'étapes de gauche à droite).
    2. Réduction des croisements d'arêtes.
    3. Calcul des coordonnées spatiales avec espacement régulier (largeur nœud: 180px, hauteur: 80px, marge horizontale: 90px).
    4. Calcul des chemins orthogonaux à angles droits avec gestion des coudes (waypoints).
- **Definition of Done (DoD)** :
  - Diagramme généré avec 0 collision de nœuds et connecteurs orthogonaux propres.

---

### Lot 24 : Bibliothèque des 10 Templates Métier Municipaux Clés en Main
- **Objectif** : Intégrer en dur dans l'application une bibliothèque de workflows certifiés prêts à l'emploi pour les services de Plougastel.
- **Spécifications Techniques** :
  - Module `src/travaux/workflow_templates.py`.
  - Les 10 processus intégrés :
    1. *Instruction Droit des Sols (Permis de Construire & Déclaration Préalable)*.
    2. *Commission d'Appel d'Offres (CAO) & Attribution de Marché Public*.
    3. *Aide Sociale Facultative CCAS (Instruction confidentielle & commission)*.
    4. *Demande de Subvention aux Associations Culturelles & Sportives*.
    5. *Arrêté de Voirie & Autorisation de Stationnement / Déménagement*.
    6. *Réservation de la Salle Événementielle Avel Vor*.
    7. *Signalement d'Anomalie Voirie / Bâtiment au Centre Technique (CTM)*.
    8. *Campagne d'Inscription Scolaire & Dérogation de Carte Scolaire*.
    9. *Attribution d'un Mouillage au Port du Tinduff ou à l'Auberlac'h*.
    10. *Préparation et Clôture de l'Ordre du Jour du Conseil Municipal*.
- **Definition of Done (DoD)** :
  - Chaque template peut être instancié en un clic et simulé immédiatement.

---

### Lot 25 : Interface Studio "Prompt-to-Workflow" avec Prévisualisation Différentielle
- **Objectif** : Fournir une interface de création assistée par IA où l'utilisateur tape ou dicte son besoin et voit le diagramme se construire en temps réel.
- **Spécifications Techniques** :
  - Composant React `frontend-lovable/src/features/workflow/prompt/PromptWorkflowStudio.tsx`.
  - Zone de saisie avec suggestions guidées (chips de suggestions municipales).
  - Prévisualisation instantanée côte-à-côte :
    - Fenêtre de gauche : prompt et suggestions de modifications incrémentales.
    - Fenêtre de droite : diagramme BPMN interactif recalculé.
  - Historique des versions du prompt avec bouton de retour arrière (Undo/Redo).
- **Definition of Done (DoD)** :
  - Modification d'un workflow existant par prompt incrémental (ex: *"Ajoute une étape de validation financière si le devis dépasse 15 000 €"*) sans écraser les nœuds précédents.

---

# PÔLE 6 : Simulateur PixelFlow 16-bit, Homologation & Déploiement

### Lot 26 : Moteur de Rendu Canvas PixelFlow 16-bit & Tuyauterie de Données
- **Objectif** : Créer un moteur de rendu graphique rétro 16-bit ludique et visuel permettant de vulgariser les flux de données pour les élus et agents néophytes (*100% fait maison, 0 € de dépendance*).
- **Spécifications Techniques** :
  - Composant `frontend-lovable/src/features/workflow/pixelflow/PixelFlowCanvas.tsx`.
  - Rendu HTML5 Canvas avec directive CSS `image-rendering: pixelated`.
  - Rendu des nœuds sous forme de bornes/bâtiments pixelisés rétro (Hôtel de ville, Service Urbanisme, Bureau du Maire, Coffre-fort numérique).
  - Tuyauterie de données : câbles de données néon animés reliant les bâtiments avec effet de clignotement.
- **Definition of Done (DoD)** :
  - Rendu visuel soigné style console 16-bit sans saccade à 60 FPS.

---

### Lot 27 : Animation des Paquets de Données (Pixel Packets) & Particules
- **Objectif** : Matérialiser chaque dossier sous la forme d'un petit paquet de données pixel-art qui se déplace le long des câbles entre les bâtiments.
- **Spécifications Techniques** :
  - Moteur de particules 2D avec interpolation de trajectoire de Bézier le long des segments de câbles.
  - Différenciation visuelle des paquets :
    - Enveloppe jaune dorée pour un dossier standard.
    - Enveloppe bleue pour un dossier prioritaire / urgent.
    - Cadenas rouge pour un dossier confidentiel CCAS.
    - Pièces d'or pour un flux budgétaire.
  - Effets de particules lors de l'entrée dans un bâtiment (splash d'étoiles pixelisées, timbre de tampon administratif).
- **Definition of Done (DoD)** :
  - Trajectoire fluide des paquets avec ralentissement aux carrefours décisionnels.

---

### Lot 28 : Pupitre de Contrôle de Simulation & Toggle de Scénarios
- **Objectif** : Donner à l'utilisateur un panneau de contrôle interactif pour tester tous les embranchements possibles d'un processus communal.
- **Spécifications Techniques** :
  - Barre de transport `frontend-lovable/src/features/workflow/pixelflow/SimulationControlBar.tsx`.
  - Commandes : *Play*, *Pause*, *Step-by-step* (pas à pas), *Reset*, curseur de vitesse (0.5x, 1x, 2x, 5x).
  - Sélecteur de scénario :
    - *Scénario 1 : Voie royale nominale (Accord immédiat, budget validé)*.
    - *Scénario 2 : Pièces manquantes (Boucle de relance usager)*.
    - *Scénario 3 : Rejet pour non-conformité PLU / Dépassement budgétaire*.
    - *Scénario 4 : Dépassement de délai (Escalade automatique vers la DGS)*.
- **Definition of Done (DoD)** :
  - Le changement de scénario redirige instantanément le paquet de données vers la bonne passerelle avec explicitation textuelle.

---

### Lot 29 : Inspecteur de Paquets de Données en Direct (Data Inventory Modal)
- **Objectif** : Permettre de cliquer à tout moment sur un paquet de données en cours de déplacement pour examiner son contenu variable exact.
- **Spécifications Techniques** :
  - Fenêtre modale inspectrice `frontend-lovable/src/features/workflow/pixelflow/DataPacketInspectorModal.tsx`.
  - Affichage :
    - Identifiant unique du jeton (`token_id`).
    - Dossier associé (Demandeur, adresse parcellaire, montant estimé).
    - Variables d'état actuelles (`statut_abf: accord`, `visa_tresorier: en_attente`).
    - Historique chronologique des bâtiments déjà visités avec horodatage.
- **Definition of Done (DoD)** :
  - Clic sur un paquet suspendant automatiquement la simulation pour permettre la lecture détaillée.

---

### Lot 30 : Intégration Transverse, Vérification des Invariants & Déploiement Hetzner
- **Objectif** : Fédérer l'ensemble des modules dans MayorTech, vérifier la stricte préservation des 5 hashes invariants, exécuter les tests end-to-end complets et déployer sur Hetzner.
- **Spécifications Techniques** :
  - Intégration du nouvel onglet **« Workflows & Processus (MayorFlow) »** dans la barre latérale globale de MayorTech.
  - Contrôle d'intégrité strict des 5 fichiers protégés :
    - `repository.py` : `AF7C56E2`
    - `workspace.py` : `D5717BA8`
    - `auth.py` : `4123A8BF`
    - `jobs.py` : `7F7F46DF`
    - `governance.py` : `9E5A5160`
  - Campagne de tests Playwright couvrant :
    - Inscription d'un agent via sas et approbation DGS.
    - Consultation de l'organigramme municipal interactif.
    - Génération d'un workflow par prompt et modification graphique via `bpmn-js`.
    - Lancement de la simulation PixelFlow avec inspection de paquet.
  - Déploiement de la mise à jour sur le serveur de production Hetzner (`178.105.35.246`) pour le site public démo et l'espace souverain Keycloak.
- **Definition of Done (DoD)** :
  - 100% des tests passants (pytest + node + playwright).
  - Screenshots de validation Full HD (1920×1080) et Mobile (390×844).
  - Déploiement en production vérifié sans indisponibilité ni régression.

---

## Matrice de Recouvrement des Requêtes Utilisateur & Alternatives Libres

| Demande Utilisateur | Pôles Stratégiques Couverts | Lots Dédiés | Briques Open-Source Déployées | Équivalent Propriétaire Remplacé (Coût Évité) |
| :--- | :--- | :--- | :--- | :--- |
| **Workflow Métier (Demande #3 & #6)** | Pôle 3 & Pôle 4 | **Lots 11 à 20** (10 lots) | **SpiffWorkflow (Python)** + **`bpmn-js` (MIT)** + **React JSON Schema Form** | **Iterop Play, Design & Watch** (~15 à 30 €/mois/agent + intégration = milliers d'€ économisés) |
| **Prompt-to-BPMN & PixelFlow (Demande #4)** | Pôle 5 & Pôle 6 | **Lots 21 à 29** (9 lots) | **Parseur LLM Logic-Core** + **Canvas HTML5 16-bit** | Innovation exclusive MayorTech (Non disponible dans les BPM du marché) |
| **Enrôlement & Organigramme (Demande #5)** | Pôle 1 & Pôle 2 | **Lots 01 à 10** (10 lots) | **Keycloak OIDC (Apache 2.0)** + **Batch CSV Python** + **SVG interactif** | Gestionnaires d'identités propriétaires payants |
| **Intégration & Déploiement** | Pôle 6 | **Lot 30** (1 lot) | **Hetzner Cloud VPS** + **Docker** + **Caddy** | Cloud propriétaire verrouillé |

---

## Calendrier d'Exécution & Méthodologie par Itérations de 10 Passes

Chaque lot de ce Master Plan suivra le cycle d'assurance qualité en 10 passes :
1. *Passe 1 : Spécification fine & validation des types d'entrée/sortie.*
2. *Passe 2 : Modélisation des données & écriture des tests d'intégration (TDD).*
3. *Passe 3 : Développement du composant backend / logique métier Python.*
4. *Passe 4 : Développement du composant frontend React & styled components.*
5. *Passe 5 : Raccordement API & gestion des états de chargement/erreurs.*
6. *Passe 6 : Revue d'accessibilité RGAA & navigation clavier intégrale.*
7. *Passe 7 : Test de performance & fluidité à 60 FPS (Canvas & SVG).*
8. *Passe 8 : Vérification de la non-régression des 5 hashes protégés.*
9. *Passe 9 : Capture des captures d'écran certifiées Full HD et Mobile.*
10. *Passe 10 : Packaging de production, audit de sécurité & scellement SHA-256.*
