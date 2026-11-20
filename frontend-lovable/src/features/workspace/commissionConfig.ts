export interface SidebarSectionItem {
  label: string;
  to: string;
  iconName: 'chart' | 'clipboard' | 'calendar' | 'file-text' | 'coins' | 'landmark' | 'users' | 'heart' | 'messages-square' | 'building' | 'map';
  badge?: string | number;
}

export interface PinnedItem {
  label: string;
  sub?: string;
  tag?: string;
}

export interface CommissionKpi {
  id: string;
  shortTitle?: string;
  count: number;
  title: string;
  subtitle: string;
  color: 'blue' | 'amber' | 'emerald' | 'purple' | 'rose';
  filterId?: string;
}

export interface CommissionShortcut {
  label: string;
  iconName: 'plus' | 'user-check' | 'alert-triangle' | 'coins' | 'calendar' | 'eye' | 'file-plus' | 'map' | 'building';
  primary?: boolean;
  actionHash: string;
}

export interface CommissionConfig {
  id: string;
  fullName?: string; // 'all' | 'commission-1' | 'commission-2' | 'commission-3' | 'commission-4' | 'elu-maire'
  role?: 'agent' | 'direction' | 'elu';
  number: number;
  name: string;
  shortName: string;
  roleTitle: string;
  accentColor: string; // Hex accent color
  accentBg: string;
  greetingName: string;
  poleLabel: string;
  poleSublabel: string;
  avatarInitials: string;
  allowedDossierIds: string[];
  hasChantiers: boolean;
  sidebarSection: {
    title: string;
    items: SidebarSectionItem[];
  };
  pinnedBlock?: {
    title: string;
    items: PinnedItem[];
  };
  kpis: CommissionKpi[];
  shortcuts: CommissionShortcut[];
}

export const COMMISSIONS_CONFIG: Record<string, CommissionConfig> = {
  // 0. Direction Générale (Vue transversale) - Accent Marine #102A4C
  all: {
    id: 'all',
    number: 0,
    role: 'direction',
    fullName: 'Laurence Bernard',
    name: '0. Direction Générale (Vue transversale)',
    shortName: 'Direction Générale',
    roleTitle: 'Direction Générale des Services',
    accentColor: '#102A4C',
    accentBg: 'bg-[#102A4C]/10 text-[#102A4C]',
    greetingName: 'Laurence',
    poleLabel: 'Direction Générale & Élus',
    poleSublabel: 'Coordination transversale',
    avatarInitials: 'DG',
    allowedDossierIds: ['PC-2026-042', 'ARR-2026-019', 'MP-2026-008'], // Pas de CCAS sans habilitation
    hasChantiers: false,
    sidebarSection: {
      title: 'COORDINATION MUNICIPALE',
      items: [
        { label: 'Arbitrages transversaux', to: '/parametres?section=modules', iconName: 'landmark' },
        { label: 'Instances & Séances', to: '/seances', iconName: 'calendar' },
      ],
    },
    pinnedBlock: {
      title: 'DÉCISIONS EN ATTENTE',
      items: [
        { label: 'Visa DGS · Permis Ty-Ar-Braz', sub: 'Échéance 18h', tag: 'ADS' },
        { label: 'Validation CAO · École des Alizés', sub: 'Attribution Lot 2', tag: 'Marché' },
      ],
    },
    kpis: [
      { id: 'kpi-1', count: 3, title: 'Actes à signer', shortTitle: 'À signer', subtitle: 'File d’approbation transversale', color: 'blue', filterId: 'pending' },
      { id: 'kpi-2', count: 1, title: 'Échéance sous 24h', shortTitle: 'Urgences 24h', subtitle: 'Visa régalien ou avis technique', color: 'amber', filterId: 'warning' },
      { id: 'kpi-3', count: 2, title: 'Prochaines séances', shortTitle: 'Séances', subtitle: 'Bureau et Conseil municipal', color: 'purple' },
    ],
    shortcuts: [
      { label: '+ Lancer une validation', iconName: 'plus', primary: true, actionHash: '/workflows?launch=1' },
      { label: 'Déclarer une absence', iconName: 'user-check', actionHash: '#open-delegation' },
    ],
  },

  // Profil Élu · Maire (Dominique Cap) - Espace Élu natif
  'elu-maire': {
    id: 'elu-maire',
    number: 99,
    role: 'elu',
    name: 'Élu · Maire (Dominique Cap)',
    shortName: 'Maire',
    roleTitle: 'Maire de Plougastel-Daoulas',
    fullName: 'Dominique Cap',
    greetingName: 'Dominique',
    accentColor: '#102A4C',
    accentBg: 'bg-[#102A4C]/10 text-[#102A4C]',
    poleLabel: 'Cabinet du Maire & Exécutif',
    poleSublabel: 'Affaires Générales & Décisions',
    avatarInitials: 'DC',
    allowedDossierIds: ['PC-2026-042', 'ARR-2026-019', 'MP-2026-008', 'DELIB-2026-031'],
    hasChantiers: false,
    sidebarSection: {
      title: 'MANDAT & EXÉCUTIF',
      items: [
        { label: 'Signatures prioritaires', to: '/workflows', iconName: 'clipboard' },
        { label: 'Séances & Conseil', to: '/seances', iconName: 'calendar' },
      ],
    },
    kpis: [
      { id: 'kpi-1', count: 2, title: 'Actes à signer', shortTitle: 'À signer', subtitle: 'Arrêtés et marchés en attente de visa', color: 'blue' },
      { id: 'kpi-2', count: 2, title: 'Prochaines séances', shortTitle: 'Séances', subtitle: 'Bureau et Conseil municipal', color: 'purple' },
      { id: 'kpi-3', count: 4, title: 'Dossiers suivis', shortTitle: 'Dossiers', subtitle: 'Grands chantiers communaux', color: 'emerald' },
    ],
    shortcuts: [],
  },

  // 1. Fonctions supports et transitions - Accent Indigo #3730A3
  'commission-1': {
    id: 'commission-1',
    number: 1,
    role: 'agent',
    fullName: 'Valérie Gestin',
    name: '1. Fonctions supports et transitions',
    shortName: 'Finances & Moyens',
    roleTitle: 'DGA Ressources & Finances',
    accentColor: '#3730A3',
    accentBg: 'bg-indigo-50 text-indigo-900',
    greetingName: 'Valérie',
    poleLabel: 'Direction Finances & Commande Publique',
    poleSublabel: 'Administration générale & Marchés',
    avatarInitials: 'VG',
    allowedDossierIds: ['MP-2026-008', 'DELIB-2026-031'],
    hasChantiers: false,
    sidebarSection: {
      title: 'FINANCES & INSTANCES',
      items: [
        { label: 'Arbitrages M57', to: '/parametres?section=modules', iconName: 'coins', badge: '1' },
        { label: 'Marchés Publics (CAO)', to: '/dossiers', iconName: 'file-text', badge: '3' },
        { label: 'Séances & Conseil', to: '/seances', iconName: 'calendar' },
      ],
    },
    pinnedBlock: {
      title: 'INSTANCES & BUDGETS',
      items: [
        { label: 'Budget Primitif 2026', sub: 'Arbitrages M57 en cours', tag: 'BP26' },
        { label: 'CAO Novembre', sub: 'Marché CVC Alizés', tag: 'CAO' },
        { label: 'Conseil du 26 nov.', sub: 'Ordre du jour arrêté', tag: 'Conseil' },
      ],
    },
    kpis: [
      { id: 'kpi-1', count: 2, title: 'Actes financiers à viser', shortTitle: 'À viser', subtitle: 'Marchés et engagements M57', color: 'blue' },
      { id: 'kpi-2', count: 1, title: 'Arbitrage M57 en attente', shortTitle: 'Arbitrages M57', subtitle: 'Virement de crédits Chapitre 21', color: 'amber' },
      { id: 'kpi-3', count: 3, title: 'Marchés en cours', shortTitle: 'Marchés', subtitle: 'Procédures CAO & consultations', color: 'purple' },
    ],
    shortcuts: [
      { label: 'Lancer une validation', iconName: 'plus', primary: true, actionHash: '/workflows?launch=1' },
      { label: 'Saisir un arbitrage M57', iconName: 'coins', actionHash: '/parametres?section=modules' },
      { label: 'Préparer une séance', iconName: 'calendar', actionHash: '/seances' },
    ],
  },

  // 2. Action sociale, enfance et jeunesse - Accent Prune #7E22CE
  'commission-2': {
    id: 'commission-2',
    number: 2,
    role: 'agent',
    fullName: 'Nolwenn Péron',
    name: '2. Action sociale, enfance et jeunesse',
    shortName: 'Action Sociale & CCAS',
    roleTitle: 'Directrice du CCAS & Solidarités',
    accentColor: '#7E22CE',
    accentBg: 'bg-purple-50 text-purple-900',
    greetingName: 'Nolwenn',
    poleLabel: 'Action Sociale, Enfance & CCAS',
    poleSublabel: 'Pôle Solidarités & CCAS',
    avatarInitials: 'NP',
    allowedDossierIds: ['CCAS-2026-089'],
    hasChantiers: false,
    sidebarSection: {
      title: 'ENFANCE & CCAS',
      items: [
        { label: 'Inscriptions scolaires', to: '/enfance', iconName: 'building', badge: '14' },
        { label: 'Quotient Familial', to: '/enfance', iconName: 'coins', badge: '8' },
        { label: 'Aides CCAS · Confidentiel', to: '/workflows?dossier=CCAS-2026-089', iconName: 'heart', badge: '1' },
      ],
    },
    pinnedBlock: {
      title: 'CAMPAGNES & COMMISSIONS',
      items: [
        { label: 'Rentrée scolaire 2026', sub: 'Campagne périscolaire', tag: 'Écoles' },
        { label: 'Commission CCAS', sub: 'Aides secours d’urgence', tag: 'CCAS' },
      ],
    },
    kpis: [
      { id: 'kpi-1', count: 1, title: 'Dossier CCAS confidentiel', shortTitle: 'Aides CCAS', subtitle: 'Aide sociale d’urgence requise', color: 'rose' },
      { id: 'kpi-2', count: 14, title: 'Inscriptions scolaires', shortTitle: 'Inscriptions', subtitle: 'Campagne rentrée 2026-2027', color: 'blue' },
      { id: 'kpi-3', count: 8, title: 'Calculs QF à valider', shortTitle: 'Calculs QF', subtitle: 'Dossiers familles périscolaire', color: 'purple' },
    ],
    shortcuts: [
      { label: 'Demande de secours CCAS', iconName: 'file-plus', primary: true, actionHash: '/workflows?launch=1' },
      { label: 'Instruire un Quotient Familial', iconName: 'coins', actionHash: '/enfance' },
      { label: 'Ouvrir la campagne scolaire', iconName: 'calendar', actionHash: '/enfance' },
    ],
  },

  // 3. Urbanisme, travaux et ports - Accent Pin/Émeraude #0F766E
  'commission-3': {
    id: 'commission-3',
    number: 3,
    role: 'agent',
    fullName: 'Loïc Kerbrat',
    name: '3. Urbanisme, travaux et ports',
    shortName: 'Urbanisme & Travaux',
    roleTitle: 'Directeur des Services Techniques',
    accentColor: '#0F766E',
    accentBg: 'bg-teal-50 text-teal-900',
    greetingName: 'Loïc',
    poleLabel: 'Pôle Urbanisme, Travaux & Ports',
    poleSublabel: 'Aménagement & Cadre de vie',
    avatarInitials: 'LK',
    allowedDossierIds: ['PC-2026-042', 'ARR-2026-019'],
    hasChantiers: true,
    sidebarSection: {
      title: 'TERRAIN & TERRITOIRE',
      items: [
        { label: 'Planning Gantt', to: '/planning', iconName: 'chart' },
        { label: 'Suivi terrain', to: '/terrain', iconName: 'clipboard' },
        { label: 'Carte PLU & Ports', to: '/urbanisme', iconName: 'map' },
      ],
    },
    pinnedBlock: {
      title: 'CHANTIERS EN COURS',
      items: [
        { label: 'Parvis de l’école des Alizés', sub: 'TRV-2026-014 · Gros œuvre', tag: 'En cours' },
        { label: 'Vestiaires des Goélands', sub: 'TRV-2026-017 · Second œuvre', tag: 'En cours' },
        { label: 'Salle du Rivage', sub: 'TRV-2026-008 · Rénovation', tag: 'En cours' },
        { label: 'Rue des Ajoncs', sub: 'TRV-2026-021 · Réseau pluvial', tag: 'En cours' },
      ],
    },
    kpis: [
      { id: 'kpi-1', count: 2, title: 'Arrêtés & Permis à viser', shortTitle: 'À viser', subtitle: 'ADS et réglementation de voirie', color: 'blue' },
      { id: 'kpi-2', count: 1, title: 'Échéance sous 24h', shortTitle: 'Urgences 24h', subtitle: 'Arrêté voirie Port du Tinduff', color: 'amber' },
      { id: 'kpi-3', count: 4, title: 'Chantiers actifs', shortTitle: 'Chantiers', subtitle: 'Opérations et arrêtés de voirie', color: 'emerald' },
    ],
    shortcuts: [
      { label: 'Lancer une validation', iconName: 'plus', primary: true, actionHash: '/workflows?launch=1' },
      { label: 'Signaler un point terrain', iconName: 'alert-triangle', actionHash: '/terrain' },
      { label: 'Consulter cadastre & PLU', iconName: 'map', actionHash: '/urbanisme' },
    ],
  },

  // 4. Culture, sport et vie associative - Accent Terracotta #C2593F
  'commission-4': {
    id: 'commission-4',
    number: 4,
    role: 'agent',
    fullName: 'Jean-Luc Le Gall',
    name: '4. Culture, sport et vie associative',
    shortName: 'Culture & Sport',
    roleTitle: 'Directeur Vie Locale & Associations',
    accentColor: '#C2593F',
    accentBg: 'bg-amber-50 text-amber-900',
    greetingName: 'Gwendal',
    poleLabel: 'Culture, Sport & Vie Associative',
    poleSublabel: 'Associations & Événements',
    avatarInitials: 'GL',
    allowedDossierIds: ['SUBV-2026-012'],
    hasChantiers: false,
    sidebarSection: {
      title: 'VIE LOCALE',
      items: [
        { label: 'Subventions associations', to: '/culture', iconName: 'coins', badge: '1' },
        { label: 'Salles & Équipements', to: '/culture', iconName: 'building', badge: '5' },
        { label: 'Agenda culturel', to: '/agenda', iconName: 'calendar' },
      ],
    },
    pinnedBlock: {
      title: 'ÉQUIPEMENTS & LIEUX',
      items: [
        { label: 'Espace culturel Ty-Ar-Mor', sub: 'Salle de spectacle & Expos', tag: 'Culture' },
        { label: 'Complexe sportif Aven', sub: 'Gymnase & Cale nautique', tag: 'Sport' },
      ],
    },
    kpis: [
      { id: 'kpi-1', count: 1, title: 'Convention de subvention', subtitle: 'Aide aux associations locales', color: 'blue' },
      { id: 'kpi-2', count: 5, title: 'Réservations de salles', subtitle: 'Planning Espace Ty-Ar-Mor', color: 'purple' },
      { id: 'kpi-3', count: 2, title: 'Événements culturels', subtitle: 'Festival Fraises & Expositions', color: 'amber' },
    ],
    shortcuts: [
      { label: '+ Demande de subvention', iconName: 'coins', primary: true, actionHash: '/culture' },
      { label: 'Réserver un équipement', iconName: 'building', actionHash: '/culture' },
      { label: 'Planifier une manifestation', iconName: 'calendar', actionHash: '/agenda' },
    ],
  },
};

export function getCommissionConfig(commissionId?: string | null): CommissionConfig {
  if (!commissionId || commissionId === 'all') {
    return COMMISSIONS_CONFIG.all;
  }
  return COMMISSIONS_CONFIG[commissionId] || COMMISSIONS_CONFIG.all;
}
