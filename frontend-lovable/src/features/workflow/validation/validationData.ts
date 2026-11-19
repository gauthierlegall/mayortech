export interface ValidationStep {
  id: string;
  label: string;
  role: string;
  actor: string;
  status: 'completed' | 'active' | 'upcoming' | 'rejected' | 'returned';
  signedAt?: string;
  comment?: string;
  sha256?: string;
}

export interface ValidationDocument {
  name: string;
  size: string;
  type: string;
  badge?: string;
}

export interface ValidationAuditEntry {
  timestamp: string;
  author: string;
  role: string;
  action: 'depot' | 'visa' | 'renvoi' | 'refus' | 'scellement';
  comment: string;
  sha256?: string;
  stepName: string;
}

export interface ValidationDossier {
  id: string;
  title: string;
  circuitType: 'permis' | 'arrete' | 'marche' | 'deliberation';
  circuitLabel: string;
  commissionId?: string;
  isConfidentialCCAS?: boolean;
  confidentialBadge?: string;
  applicant: string;
  applicantAddress?: string;
  createdAt: string;
  slaDeadline: string;
  slaStatus: 'ok' | 'warning' | 'overdue';
  priority: 'normal' | 'urgent';
  currentStepIndex: number;
  status: 'pending' | 'signed' | 'rejected' | 'returned';
  steps: ValidationStep[];
  documents: ValidationDocument[];
  auditTrail: ValidationAuditEntry[];
  previewArticle: string;
  documentExcerpt?: string;
  isEditedInReview?: boolean;
  editVersion?: string;
  returnFeedback?: {
    initialReason: string;
    agentResponse: string;
    changedParagraph?: string;
  };
}

export const INITIAL_DOSSIERS: ValidationDossier[] = [
  {
    id: 'PC-2026-042',
    title: 'Permis de Construire · Extension & Toiture Ardoise Ty-Ar-Braz',
    circuitType: 'permis',
    circuitLabel: 'Permis de Construire (ADS)',
    commissionId: 'commission-3',
    applicant: 'M. & Mme Tanguy KERVADEC',
    applicantAddress: '14 Chemin de Ty-Ar-Braz · 29470 Plougastel-Daoulas',
    createdAt: '17/11/2026 à 10:15',
    slaDeadline: '20/11/2026 (Reste 18h)',
    slaStatus: 'warning',
    priority: 'urgent',
    currentStepIndex: 2, // 0: Agent, 1: CTM, 2: DGS, 3: Maire
    status: 'pending',
    steps: [
      {
        id: 'step-agent',
        label: 'Agent instructeur',
        role: 'Instructeur ADS · Pôle Urbanisme',
        actor: 'Gwenn LE BIHAN',
        status: 'completed',
        signedAt: '18/11/2026 à 14:20',
        comment: 'Dossier complet et pièces conformes au PLU en zone UB.',
        sha256: '4e9f1a8b2d7c03e5',
      },
      {
        id: 'step-ctm',
        label: 'Chef Services Techniques',
        role: 'Responsable CTM & Réseaux',
        actor: 'Erwan KERVRAN',
        status: 'completed',
        signedAt: '19/11/2026 à 09:45',
        comment: 'Avis technique favorable pour raccordement eaux pluviales et voirie communale.',
        sha256: '8c3b2e5f1a9d47c6',
      },
      {
        id: 'step-dgs',
        label: 'Direction Générale (DGS)',
        role: 'Arbitrage Régalien & Légalité',
        actor: 'Marie ROLLAND (DGS)',
        status: 'active',
      },
      {
        id: 'step-maire',
        label: 'Maire de Plougastel',
        role: 'Signature Arrêté Municipal',
        actor: 'Dominique CAP (Maire)',
        status: 'upcoming',
      },
    ],
    documents: [
      { name: 'Cerfa_13406_12_Signe.pdf', size: '1.8 Mo', type: 'Formulaire Cerfa 13406*12', badge: 'Certifié' },
      { name: 'PCMI2_Plan_de_masse_cote.pdf', size: '3.4 Mo', type: 'Plan de masse 3D', badge: 'Conforme PLU' },
      { name: 'PCMI3_Plan_en_coupe_terrain.pdf', size: '2.1 Mo', type: 'Plan en coupe', badge: 'Art. R.431-10' },
      { name: 'PCMI4_Notice_descriptive_materiaux.pdf', size: '1.2 Mo', type: 'Notice architecturale', badge: 'Ardoise naturelle' },
      { name: 'Avis_Patrimoine_ABF_Favorable.pdf', size: '840 Ko', type: 'Avis ABF', badge: 'ABF Favorable' },
    ],
    auditTrail: [
      {
        timestamp: '17/11/2026 · 10:15',
        author: 'Guichet ADS Plougastel',
        role: 'Guichetier ADS',
        action: 'depot',
        stepName: 'Dépôt & Enregistrement',
        comment: 'Dépôt Cerfa 13406*12 horodaté au guichet unique de la mairie. Récépissé délivré.',
      },
      {
        timestamp: '18/11/2026 · 14:20',
        author: 'Gwenn LE BIHAN',
        role: 'Instructrice ADS',
        action: 'visa',
        stepName: 'Contrôle de complétude',
        comment: 'Instruction réglementaire favorable sous délai légal 1 mois (R.423-22). Pièces PCMI2, PCMI3 et PCMI4 complètes.',
        sha256: '4e9f1a8b2d7c03e5',
      },
      {
        timestamp: '19/11/2026 · 09:45',
        author: 'Erwan KERVRAN',
        role: 'Responsable CTM',
        action: 'visa',
        stepName: 'Avis technique CTM',
        comment: 'Capacité de desserte pluviale validée. Pas d’empiètement sur le domaine public communal.',
        sha256: '8c3b2e5f1a9d47c6',
      },
    ],
    previewArticle: 'ARTICLE 1ER : Les travaux déclarés sous le formulaire Cerfa 13406*12 numéro PC-2026-042 portant sur la rénovation de toiture en ardoise naturelle et extension de 38 m² sont AUTORISÉS, sous réserve du strict respect des prescriptions de l’Architecte des Bâtiments de France.\n\nARTICLE 2 : Les eaux pluviales devront impérativement être infiltrées à la parcelle conformément au schéma directeur d’assainissement de Brest Métropole.\n\nARTICLE 3 : Le présent arrêté est transmis à la Préfecture du Finistère au titre du contrôle de légalité (@CTES) et certifié exécutoire.',
  },
  {
    id: 'ARR-2026-019',
    title: 'Arrêté Municipal · Réglementation Temporaire Voirie Port du Tinduff',
    circuitType: 'arrete',
    circuitLabel: 'Arrêté de Voirie & Police',
    commissionId: 'commission-3',
    applicant: 'Entreprise Morbihan Travaux Publics',
    applicantAddress: 'Quai du Tinduff · 29470 Plougastel-Daoulas',
    createdAt: '18/11/2026 à 15:40',
    slaDeadline: '20/11/2026 (Reste 6h)',
    slaStatus: 'warning',
    priority: 'urgent',
    currentStepIndex: 1, // Chef CTM
    status: 'pending',
    steps: [
      {
        id: 'step-agent',
        label: 'Agent instructeur',
        role: 'Agent Voirie Communale',
        actor: 'Julien MOREL',
        status: 'completed',
        signedAt: '19/11/2026 à 08:30',
        comment: 'Plan de signalisation et déviation vérifiés.',
        sha256: '7b2a9e4d1c8f30b5',
      },
      {
        id: 'step-ctm',
        label: 'Chef Services Techniques',
        role: 'Responsable CTM & Voirie',
        actor: 'Erwan KERVRAN',
        status: 'active',
      },
      {
        id: 'step-dgs',
        label: 'Direction Générale (DGS)',
        role: 'Contrôle Légalité',
        actor: 'Marie ROLLAND (DGS)',
        status: 'upcoming',
      },
      {
        id: 'step-maire',
        label: 'Maire de Plougastel',
        role: 'Signature Arrêté',
        actor: 'Dominique CAP (Maire)',
        status: 'upcoming',
      },
    ],
    documents: [
      { name: 'Projet_Arrete_Port_Tinduff.pdf', size: '620 Ko', type: 'Arrêté voirie', badge: 'Projet légal' },
      { name: 'Plan_Deviation_Vehicules.pdf', size: '2.1 Mo', type: 'Schéma circulation', badge: 'Validé Police' },
    ],
    auditTrail: [
      {
        timestamp: '18/11/2026 · 15:40',
        author: 'Guichet Voirie',
        role: 'Agent Accueil',
        action: 'depot',
        stepName: 'Dépôt demande de voirie',
        comment: 'Demande d’arrêté pour réfection de la cale de carénage.',
      },
      {
        timestamp: '19/11/2026 · 08:30',
        author: 'Julien MOREL',
        role: 'Agent Voirie',
        action: 'visa',
        stepName: 'Instruction technique voirie',
        comment: 'Balisage et feux tricolores temporaires validés.',
        sha256: '7b2a9e4d1c8f30b5',
      },
    ],
    previewArticle: 'ARTICLE 1ER : La circulation sur le Quai du Tinduff sera régulée par alternat par feux tricolores du 24 novembre au 28 novembre 2026.\n\nARTICLE 2 : Le stationnement de tout véhicule sera interdit sur une distance de 50 mètres de part et d’autre de la zone de chantier jusqu’au 28 novembre 2026 inclus.',
    returnFeedback: {
      initialReason: 'Préciser la date de fin d’interdiction de stationnement et joindre l’arrêté de voirie complémentaire.',
      agentResponse: 'Date modifiée au 28 novembre 2026 et plan de déviation CTM joint au dossier.',
      changedParagraph: 'ARTICLE 2 : Le stationnement de tout véhicule sera interdit sur une distance de 50 mètres de part et d’autre de la zone de chantier jusqu’au 28 novembre 2026 inclus.',
    },
  },
  {
    id: 'MP-2026-008',
    title: 'Marché Public · Réhabilitation Énergétique École des Alizés (Lot 2 CVC)',
    circuitType: 'marche',
    circuitLabel: 'Marché Public (CAO)',
    commissionId: 'commission-1',
    applicant: 'Commission d’Appel d’Offres (CAO)',
    applicantAddress: 'Hôtel de Ville · 1 Rue Jean Moulin',
    createdAt: '15/11/2026 à 09:00',
    slaDeadline: '22/11/2026 (Reste 48h)',
    slaStatus: 'ok',
    priority: 'normal',
    currentStepIndex: 3, // Maire
    status: 'pending',
    steps: [
      {
        id: 'step-agent',
        label: 'Agent instructeur',
        role: 'Responsable Marchés Publics',
        actor: 'Claire TANGUY',
        status: 'completed',
        signedAt: '16/11/2026 à 11:00',
        comment: 'Offres conformes et régularité juridique vérifiée.',
        sha256: '3d9f7a2b1c8e54a0',
      },
      {
        id: 'step-ctm',
        label: 'Chef Services Techniques',
        role: 'Directeur des Bâtiments',
        actor: 'Erwan KERVRAN',
        status: 'completed',
        signedAt: '17/11/2026 à 16:30',
        comment: 'Rapport d’analyse des offres approuvé. Note technique 18/20.',
        sha256: '6a1c8f3b2d9e74e1',
      },
      {
        id: 'step-dgs',
        label: 'Direction Générale (DGS)',
        role: 'Contrôle Financier & Légalité',
        actor: 'Marie ROLLAND (DGS)',
        status: 'completed',
        signedAt: '19/11/2026 à 10:15',
        comment: 'Imputation budgétaire conforme (Compte 21312 Bâtiments scolaires).',
        sha256: '9f86d081884c7d65',
      },
      {
        id: 'step-maire',
        label: 'Maire de Plougastel',
        role: 'Signature Acte d’Engagement',
        actor: 'Dominique CAP (Maire)',
        status: 'active',
      },
    ],
    documents: [
      { name: 'Acte_Engagement_Alizes_Lot2.pdf', size: '1.2 Mo', type: 'Marché public', badge: 'Dossier CAO' },
      { name: 'Rapport_Analyse_Offres_Signe.pdf', size: '4.5 Mo', type: 'Rapport technique', badge: 'Approuvé' },
    ],
    auditTrail: [
      {
        timestamp: '15/11/2026 · 09:00',
        author: 'Service Marchés',
        role: 'Instructeur CAO',
        action: 'depot',
        stepName: 'Transmission PV CAO',
        comment: 'Attribution du Lot 2 à l’entreprise Armor Climatisation.',
      },
      {
        timestamp: '16/11/2026 · 11:00',
        author: 'Claire TANGUY',
        role: 'Responsable Achats',
        action: 'visa',
        stepName: 'Visa Marchés Publics',
        comment: 'Dossier administratif certifié sans réserve.',
        sha256: '3d9f7a2b1c8e54a0',
      },
      {
        timestamp: '17/11/2026 · 16:30',
        author: 'Erwan KERVRAN',
        role: 'Directeur Bâtiments',
        action: 'visa',
        stepName: 'Visa Technique Bâtiments',
        comment: 'Planning d’intervention compatible avec les vacances scolaires de Noël.',
        sha256: '6a1c8f3b2d9e74e1',
      },
      {
        timestamp: '19/11/2026 · 10:15',
        author: 'Marie ROLLAND',
        role: 'Directrice Générale',
        action: 'visa',
        stepName: 'Visa Financier DGS',
        comment: 'Crédits votés disponibles sur le budget d’investissement 2026.',
        sha256: '9f86d081884c7d65',
      },
    ],
    previewArticle: 'ARTICLE 1ER : Le marché de travaux pour la réhabilitation énergétique de l’école des Alizés (Lot 2 CVC) est ATTRIBUÉ à la société Armor Climatisation pour un montant de 142 500 € HT.\n\nARTICLE 2 : La dépense sera imputée sur l’opération d’investissement OP-2026-ECOLES du budget principal communal.',
  },
  {
    id: 'CCAS-2026-089',
    title: 'Aide Exceptionnelle d’Urgence · Précarité Énergétique Hiver 2026',
    circuitType: 'arrete',
    circuitLabel: 'Aide Sociale Légale & Facultative (CCAS)',
    commissionId: 'commission-2',
    isConfidentialCCAS: true,
    confidentialBadge: 'Accès restreint · Secret professionnel CCAS',
    applicant: 'Famille B. (Dossier Anonymisé Réf #7412)',
    applicantAddress: 'Résidence du Tinduff · 29470 Plougastel',
    createdAt: '19/11/2026 à 08:30',
    slaDeadline: '21/11/2026 (Reste 24h)',
    slaStatus: 'warning',
    priority: 'urgent',
    currentStepIndex: 1, // 0: Travailleur Social, 1: Adjointe Affaires Sociales, 2: Maire / Présidence CCAS
    status: 'pending',
    steps: [
      {
        id: 'step-ts',
        label: 'Travailleur Social référent',
        role: 'Assistant Social CCAS',
        actor: 'Nolwenn LE GALL',
        status: 'completed',
        signedAt: '19/11/2026 à 10:00',
        comment: 'Évaluation sociale favorable. Reste à charge après secours d’urgence : 0 €.',
        sha256: '9a8b7c6d5e4f3210',
      },
      {
        id: 'step-adjointe',
        label: 'Adjointe Affaires Sociales',
        role: 'Vice-Présidente du CCAS',
        actor: 'Valérie BERTHOU (Adjointe)',
        status: 'active',
      },
      {
        id: 'step-president',
        label: 'Président du CCAS (Maire)',
        role: 'Exécutif CCAS',
        actor: 'Dominique CAP (Maire)',
        status: 'upcoming',
      },
    ],
    documents: [
      { name: 'Rapport_Evaluation_Sociale_Confidentiel.pdf', size: '480 Ko', type: 'Dossier social', badge: 'Secret Pro L.226-13' },
      { name: 'Facture_Energie_Impayee_Justificatif.pdf', size: '1.1 Mo', type: 'Justificatif de dépense', badge: 'Vérifié CCAS' },
    ],
    auditTrail: [
      {
        timestamp: '19/11/2026 · 08:30',
        author: 'Guichet CCAS',
        role: 'Agent Accueil Social',
        action: 'depot',
        stepName: 'Instruction demande de secours',
        comment: 'Dossier instruit sous le sceau de la confidentialité et du secret professionnel.',
      },
      {
        timestamp: '19/11/2026 · 10:00',
        author: 'Nolwenn LE GALL',
        role: 'Assistante Sociale',
        action: 'visa',
        stepName: 'Évaluation médico-sociale',
        comment: 'Avis favorable pour allocation directe énergie (450 €).',
        sha256: '9a8b7c6d5e4f3210',
      },
    ],
    previewArticle: 'ARTICLE 1ER : Une aide financière exceptionnelle d’un montant de 450,00 € est accordée au titre du Fonds de Solidarité Énergie du CCAS de Plougastel-Daoulas.\n\nARTICLE 2 : Le versement sera opéré directement auprès du fournisseur d’énergie au bénéfice de l’usager (Dossier nominatif confidentiel #7412).\n\nARTICLE 3 : En application de l’article L.226-13 du Code Pénal et du Code de l’Action Sociale et des Familles, la présente décision est soumise au secret professionnel strict.',
  },
  {
    id: 'DELIB-2026-031',
    title: 'Délibération · Révision des Tarifs Périscolaires et Cantine M57',
    circuitType: 'deliberation',
    circuitLabel: 'Délibération Conseil Municipal',
    commissionId: 'commission-1',
    applicant: 'Direction des Finances & Moyens',
    applicantAddress: 'Hôtel de Ville · Plougastel',
    createdAt: '16/11/2026 à 14:00',
    slaDeadline: '24/11/2026 (Reste 72h)',
    slaStatus: 'ok',
    priority: 'normal',
    currentStepIndex: 1, // 0: DAF, 1: DGS, 2: Maire
    status: 'pending',
    steps: [
      {
        id: 'step-daf',
        label: 'Responsable Finances M57',
        role: 'Direction Financière',
        actor: 'Stéphane LE CORRE',
        status: 'completed',
        signedAt: '17/11/2026 à 15:30',
        comment: 'Modélisation budgétaire M57 équilibrée. Taux d’effort proportionnel validé.',
        sha256: '5f4e3d2c1b0a9876',
      },
      {
        id: 'step-dgs',
        label: 'Direction Générale (DGS)',
        role: 'Visa de Légalité',
        actor: 'Laurence GUIVARC’H (DGS)',
        status: 'active',
      },
      {
        id: 'step-maire',
        label: 'Maire de Plougastel',
        role: 'Inscription à l’Ordre du Jour',
        actor: 'Dominique CAP (Maire)',
        status: 'upcoming',
      },
    ],
    documents: [
      { name: 'Projet_Deliberation_Tarifs_2026.pdf', size: '750 Ko', type: 'Projet d’acte', badge: 'Conforme M57' },
      { name: 'Grille_Quotient_Familial_Simulee.pdf', size: '1.4 Mo', type: 'Annexe financière', badge: 'Chiffrage validé' },
    ],
    auditTrail: [
      {
        timestamp: '16/11/2026 · 14:00',
        author: 'Service Finances',
        role: 'Instructeur M57',
        action: 'depot',
        stepName: 'Dépôt du projet délibératif',
        comment: 'Transmission avant commission finances préparatoire.',
      },
      {
        timestamp: '17/11/2026 · 15:30',
        author: 'Stéphane LE CORRE',
        role: 'Responsable DAF',
        action: 'visa',
        stepName: 'Validation financière préalable',
        comment: 'Recettes prévisionnelles annuelles estimées à 280 000 €.',
        sha256: '5f4e3d2c1b0a9876',
      },
    ],
    previewArticle: 'ARTICLE 1ER : Les tarifs de la restauration scolaire et de l’accueil périscolaire pour l’année 2026-2027 sont fixés selon la grille indiciaire M57 annexée à la présente délibération.\n\nARTICLE 2 : Les tarifs sont indexés sur le quotient familial CAF avec un taux plancher de 1,10 € par repas et un plafond de 5,40 €.\n\nARTICLE 3 : La présente délibération sera transmise au Représentant de l’État au titre du contrôle de légalité (@CTES) et affichée au recueil des actes administratifs.',
  },
  {
    id: 'SUBV-2026-012',
    title: 'Convention · Subvention Municipale Club Nautique du Tinduff',
    circuitType: 'marche',
    circuitLabel: 'Convention Pluriannuelle Associative',
    commissionId: 'commission-4',
    applicant: 'Club Nautique de Plougastel (CNP)',
    applicantAddress: 'Cale du Tinduff · 29470 Plougastel',
    createdAt: '17/11/2026 à 11:30',
    slaDeadline: '25/11/2026',
    slaStatus: 'ok',
    priority: 'normal',
    currentStepIndex: 1, // 0: Service Culture/Sport, 1: Adjointe Vie Associative, 2: Maire
    status: 'pending',
    steps: [
      {
        id: 'step-service',
        label: 'Pôle Culture & Sport',
        role: 'Instructeur Associations',
        actor: 'Loïc KERBOUL',
        status: 'completed',
        signedAt: '18/11/2026 à 16:00',
        comment: 'Bilan d’activité et comptes certifiés conformes (SIRET 412 890 120 00018).',
        sha256: '1a2b3c4d5e6f7a8b',
      },
      {
        id: 'step-adjointe',
        label: 'Adjointe Vie Associative',
        role: 'Arbitrage Subventions',
        actor: 'Gaëlle ROUDAUT (Adjointe)',
        status: 'active',
      },
      {
        id: 'step-maire',
        label: 'Maire de Plougastel',
        role: 'Signature Convention',
        actor: 'Dominique CAP (Maire)',
        status: 'upcoming',
      },
    ],
    documents: [
      { name: 'Convention_Objectifs_CNP_2026.pdf', size: '1.3 Mo', type: 'Convention légale', badge: 'Conforme Loi 1901' },
      { name: 'Bilan_Financier_Association_2025.pdf', size: '2.4 Mo', type: 'Bilan financier', badge: 'Comptes approuvés' },
    ],
    auditTrail: [
      {
        timestamp: '17/11/2026 · 11:30',
        author: 'Guichet Associations',
        role: 'Agent Pôle Vie Locale',
        action: 'depot',
        stepName: 'Dépôt dossier subvention',
        comment: 'Dossier complet conforme au règlement municipal des aides associatives.',
      },
      {
        timestamp: '18/11/2026 · 16:00',
        author: 'Loïc KERBOUL',
        role: 'Coordonnateur Sport',
        action: 'visa',
        stepName: 'Instruction technique & bilan',
        comment: 'Avis favorable pour subvention de fonctionnement de 6 500 € et mise à disposition de la cale.',
        sha256: '1a2b3c4d5e6f7a8b',
      },
    ],
    previewArticle: 'ARTICLE 1ER : Une subvention annuelle de fonctionnement de 6 500,00 € est allouée au Club Nautique de Plougastel pour l’exercice 2026.\n\nARTICLE 2 : En contrepartie, l’association s’engage à assurer l’initiation nautique des élèves des écoles publiques de la commune dans le cadre des activités périscolaires.\n\nARTICLE 3 : La dépense sera imputée sur les crédits ouverts à l’article 6574 du budget communal principal.',
  },
  {
    id: 'ARR-2026-012',
    title: 'Arrêté · Alignement de clôture Rue de la Fontaine',
    circuitType: 'arrete',
    circuitLabel: 'Arrêté de Voirie & Police',
    commissionId: 'commission-3',
    applicant: 'M. François ROSTREN',
    applicantAddress: '8 Rue de la Fontaine · 29470 Plougastel',
    createdAt: '12/11/2026 à 14:00',
    slaDeadline: '15/11/2026',
    slaStatus: 'ok',
    priority: 'normal',
    currentStepIndex: 3,
    status: 'signed',
    steps: [
      { id: 'step-agent', label: 'Agent instructeur', role: 'Agent', actor: 'Gwenn LE BIHAN', status: 'completed', signedAt: '13/11/2026' },
      { id: 'step-ctm', label: 'Chef Services Techniques', role: 'CTM', actor: 'Erwan KERVRAN', status: 'completed', signedAt: '14/11/2026' },
      { id: 'step-dgs', label: 'Direction Générale (DGS)', role: 'DGS', actor: 'Marie ROLLAND', status: 'completed', signedAt: '15/11/2026' },
      { id: 'step-maire', label: 'Maire de Plougastel', role: 'Maire', actor: 'Dominique CAP', status: 'completed', signedAt: '15/11/2026' },
    ],
    documents: [
      { name: 'Arrete_2026_012_Scelle.pdf', size: '940 Ko', type: 'Arrêté scellé', badge: 'SHA-256 Certifié' },
    ],
    auditTrail: [
      {
        timestamp: '15/11/2026 · 17:00',
        author: 'Dominique CAP (Maire)',
        role: 'Maire',
        action: 'scellement',
        stepName: 'Signature et Scellement',
        comment: 'Arrêté signé électroniquement et télétransmis en Préfecture.',
        sha256: 'a1b2c3d4e5f60718',
      },
    ],
    previewArticle: 'ARTICLE 1ER : La limite d’alignement de la parcelle cadastrée AB 128 est fixée à 1,50 m de l’axe de la voie publique.\n\nARTICLE 2 : Le présent arrêté est exécutoire dès sa publication et transmission en préfecture.',
  },
];
