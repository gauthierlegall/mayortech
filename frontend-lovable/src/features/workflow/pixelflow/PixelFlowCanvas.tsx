import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  ReactFlowProvider,
  useReactFlow
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { 
  Play, 
  Pause, 
  RotateCcw, 
  StepForward, 
  Maximize2,
  Building2,
  FileCheck,
  HardHat,
  Landmark,
  Stamp,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
  GitFork,
  XCircle,
  FileText,
  Check,
  Send,
  ArrowRight,
  SlidersHorizontal
} from 'lucide-react';

import { BpmnTaskNode, BpmnTaskNodeData } from './BpmnTaskNode';
import { ConnectorTaskNode } from './ConnectorTaskNode';
import { BpmnGatewayNode, BpmnGatewayNodeData } from './BpmnGatewayNode';
import { BpmnEndNode, BpmnEndNodeData } from './BpmnEndNode';
import { BpmnLivingEdge, BpmnLivingEdgeData } from './BpmnLivingEdge';
import { BpmnLaneNode, BpmnLaneNodeData } from './BpmnLaneNode';
import { BpmnDrawer, BpmnDrawerDetails } from './BpmnDrawer';
import { ValidationDossier, INITIAL_DOSSIERS } from '../validation/validationData';

// Scenario definitions for demo mode
export type BPMNScenario = 'nominal' | 'missing_pieces' | 'rejection' | 'sla_escalation';

const SCENARIOS: { id: BPMNScenario; label: string; description: string }[] = [
  { id: 'nominal', label: 'Voie Royale (Nominal)', description: 'Instruction nominale jusqu’au scellement cryptographique SHA-256' },
  { id: 'missing_pieces', label: 'Pièces Manquantes', description: 'Relance 3 mois avec suspension d’horloge et risque de rejet tacite' },
  { id: 'rejection', label: 'Rejet PLU', description: 'Avis défavorable motivé et notification officielle de refus' },
  { id: 'sla_escalation', label: 'Escalade SLA DGS', description: 'Dépassement du délai légal avec arbitrage DGS et réaffectation / évocation' }
];

const SCENARIO_STEPS: Record<BPMNScenario, string[]> = {
  nominal: ['depot', 'completude', 'gw1', 'fork_and', 'ctm', 'abf', 'join_and', 'gw2', 'visa', 'scellement'],
  missing_pieces: ['depot', 'completude', 'gw1', 'depot'],
  rejection: ['depot', 'completude', 'gw1', 'fork_and', 'ctm', 'abf', 'join_and', 'gw2', 'rejet'],
  sla_escalation: ['depot', 'completude', 'dgs', 'visa', 'scellement']
};

// Node catalog details for drawer
const NODE_DETAILS: Record<string, BpmnDrawerDetails> = {
  depot: {
    id: 'depot',
    title: 'Guichet & Dépôt Cerfa 13406*12',
    actor: 'Guichetier ADS · Mairie de Plougastel',
    sla: 'SLA < 2h',
    description: 'Enregistrement de la demande de Permis de Construire Cerfa 13406*12 déposée par le pétitionnaire. Horodatage officiel et délivrance immédiate du récépissé.',
    piecesCerfa: [
      'Cerfa 13406*12 renseigné et signé',
      'PCMI1 : Plan de situation du terrain',
      'Récépissé de dépôt horodaté (Art. R.423-3)'
    ],
    articlesPlu: [
      'Art. R.423-1 Code de l’Urbanisme',
      'Zone UB & Zone AUP du PLU de Plougastel-Daoulas'
    ],
    status: 'valid'
  },
  completude: {
    id: 'completude',
    title: 'Vérification Complétude',
    actor: 'Instructeur ADS · Pôle Urbanisme',
    sla: 'SLA 1 mois (R.423-22)',
    description: 'Contrôle des pièces obligatoires sous le délai légal impératif d’un mois (Art. R.423-22). Si incomplet, notification des pièces manquantes sous 1 mois et suspension du délai d’instruction (délai usager de 3 mois).',
    piecesCerfa: [
      'PCMI2 : Plan de masse coté dans les 3 dimensions',
      'PCMI3 : Plan en coupe du terrain et de la construction',
      'PCMI4 : Notice descriptive de terrain et matériaux'
    ],
    articlesPlu: [
      'Art. R.423-22 & R.423-38 Code de l’Urbanisme',
      'Règlement graphique du PLU (servitudes et reculs)'
    ],
    status: 'valid'
  },
  ctm: {
    id: 'ctm',
    title: 'Avis Technique CTM & Réseaux',
    actor: 'Centre Technique Municipal (CTM)',
    sla: 'SLA 8j',
    description: 'Instruction technique en parallèle : raccordements voirie, assainissement collectif pluvial et défense incendie avec les services techniques municipaux.',
    piecesCerfa: [
      'Schéma de raccordement eau potable et eaux usées',
      'Notice de desserte voirie et emprise communale'
    ],
    articlesPlu: [
      'Art. UB.4 du PLU : Desserte par les réseaux',
      'Schéma directeur d’assainissement de Brest Métropole'
    ],
    status: 'valid'
  },
  abf: {
    id: 'abf',
    title: 'Consultation ABF & Patrimoine',
    actor: 'Architecte des Bâtiments de France (ABF)',
    sla: 'SLA 15j',
    description: 'Instruction patrimoniale en parallèle dans le périmètre de protection des monuments historiques (Calvaire de Plougastel et chapelles côtières).',
    piecesCerfa: [
      'PCMI6 : Document graphique d’insertion paysagère 3D',
      'Photographies en environnement proche et lointain'
    ],
    articlesPlu: [
      'Art. L.621-32 Code du Patrimoine',
      'Nuancier communal des toitures (ardoise naturelle)'
    ],
    status: 'valid'
  },
  visa: {
    id: 'visa',
    title: 'Visa & Signature Maire / Adjoint',
    actor: 'Jean-Luc LE GALL · Adjoint Urbanisme / Dominique CAP · Maire',
    sla: 'SLA 72h',
    description: 'Arbitrage régalien et signature officielle de l’arrêté de permis de construire par l’autorité municipale délégataire.',
    piecesCerfa: [
      'Projet d’arrêté municipal de permis de construire',
      'Synthèse des avis favorables réputés conformes'
    ],
    articlesPlu: [
      'Art. L.422-1 Code de l’Urbanisme',
      'Délégation de signature légale Arrêté 2026-DEL-03'
    ],
    status: 'valid'
  },
  scellement: {
    id: 'scellement',
    title: 'Scellement & Télétransmission @CTES',
    actor: 'Coffre-fort Électronique DGS · Titulaire DGS',
    sla: 'SLA Immédiat',
    description: 'Calcul de l’empreinte cryptographique SHA-256 du dossier complet et transmission légale en Préfecture via l’application @CTES conforme eIDAS/RGS**.',
    piecesCerfa: [
      'Arrêté signé électroniquement au format PAdES',
      'Bordereau de télétransmission Préfecture @CTES'
    ],
    articlesPlu: [
      'Art. L.2131-1 CGCT (Caractère exécutoire des actes)',
      'Décret n° 2021-1311 Télétransmission Préfecture'
    ],
    sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    status: 'valid'
  },
  rejet: {
    id: 'rejet',
    title: 'Notification de Rejet PLU',
    actor: 'Guichetier ADS · Pôle Urbanisme',
    sla: 'Clôture',
    description: 'Notification officielle du refus motivé d’autorisation pour non-conformité aux dispositions réglementaires du Plan Local d’Urbanisme.',
    piecesCerfa: [
      'Arrêté de refus motivé d’autorisation d’urbanisme',
      'Notification des voies et délais de recours (TA de Rennes)'
    ],
    articlesPlu: [
      'Art. L.424-3 Code de l’Urbanisme',
      'Infraction caractérisée aux règles de gabarit / hauteur'
    ],
    status: 'rejected'
  },
  dgs: {
    id: 'dgs',
    title: 'Arbitrage DGS & Escalade',
    actor: 'Direction Générale des Services (DGS)',
    sla: 'Alerte 24h',
    description: 'Procédure d’arbitrage régalien par la DGS suite à dépassement de délai légal ou incident. Deux issues possibles : réaffectation avec nouveau SLA d’instruction, ou évocation directe vers la signature de l’élu.',
    piecesCerfa: [
      'Rapport d’instruction technique consolidé',
      'Fiche d’arbitrage préalable DGS'
    ],
    articlesPlu: [
      'Art. R.423-19 Code de l’Urbanisme',
      'Délégation générale DGS 2026/04'
    ],
    status: 'valid'
  }
};

const nodeTypes = {
  bpmnLane: BpmnLaneNode,
  bpmnTask: BpmnTaskNode,
  connectorTask: ConnectorTaskNode,
  bpmnGateway: BpmnGatewayNode,
  bpmnEnd: BpmnEndNode,
};

const edgeTypes = {
  bpmnLiving: BpmnLivingEdge,
};

// Native Swimlanes 1400px x (180px, 230px, 180px)
const initialNodes: Node[] = [
  // 3 Native Swimlane Backgrounds
  {
    id: 'lane-1',
    type: 'bpmnLane',
    position: { x: 20, y: 15 },
    zIndex: -1,
    selectable: false,
    draggable: false,
    data: {
      title: '1 · ADS Guichet (Dépôt & Complétude)',
      dotColor: '#3b82f6',
      width: 1520,
      height: 185,
    }
  },
  {
    id: 'lane-2',
    type: 'bpmnLane',
    position: { x: 20, y: 235 },
    zIndex: -1,
    selectable: false,
    draggable: false,
    data: {
      title: '2 · CTM & ABF (Avis Techniques & Patrimoine)',
      dotColor: '#10b981',
      width: 1520,
      height: 235,
    }
  },
  {
    id: 'lane-3',
    type: 'bpmnLane',
    position: { x: 20, y: 495 },
    zIndex: -1,
    selectable: false,
    draggable: false,
    data: {
      title: '3 · Direction Générale & Exécutif (Arbitrage DGS, Visa & Scellement @CTES)',
      dotColor: '#8b5cf6',
      width: 1520,
      height: 185,
    }
  },

  // Lane 1 Task Nodes (Y = 70)
  {
    id: 'depot',
    type: 'bpmnTask',
    position: { x: 50, y: 70 },
    data: {
      title: 'Guichet & Dépôt Cerfa 13406*12',
      actor: 'Guichetier ADS',
      sla: 'SLA < 2h',
      iconName: 'Building2',
      iconColor: '#2563eb',
      bgColor: '#eff6ff',
      stepNumber: 1,
      isActive: false
    }
  },
  {
    id: 'completude',
    type: 'bpmnTask',
    position: { x: 380, y: 70 },
    data: {
      title: 'Vérification Complétude',
      actor: 'Instructeur ADS',
      sla: 'SLA 1 mois (R.423-22)',
      iconName: 'FileCheck',
      iconColor: '#0284c7',
      bgColor: '#f0f9ff',
      stepNumber: 2,
      isActive: false
    }
  },
  {
    id: 'gw1',
    type: 'bpmnGateway',
    position: { x: 740, y: 85 },
    data: {
      label: 'Dossier Conforme ?',
      gatewayType: 'exclusive',
      isActive: false
    }
  },
  {
    id: 'rejet_tacite',
    type: 'bpmnEnd',
    position: { x: 1060, y: 87 },
    data: {
      label: 'Rejet tacite (3 mois)',
      type: 'reject',
      isActive: false
    }
  },

  // Lane 2 Parallel Fork & Synchronisation Nodes (AND / +)
  {
    id: 'fork_and',
    type: 'bpmnGateway',
    position: { x: 240, y: 325 },
    data: {
      label: 'Parallèle (AND)',
      gatewayType: 'parallel',
      isActive: false
    }
  },
  {
    id: 'ctm',
    type: 'bpmnTask',
    position: { x: 380, y: 255 },
    data: {
      title: 'Avis Technique CTM & Réseaux',
      actor: 'Voirie & Réseaux',
      sla: 'SLA 8j',
      iconName: 'HardHat',
      iconColor: '#059669',
      bgColor: '#ecfdf5',
      stepNumber: 3,
      isActive: false
    }
  },
  {
    id: 'abf',
    type: 'bpmnTask',
    position: { x: 380, y: 365 },
    data: {
      title: 'Consultation ABF & Patrimoine',
      actor: 'Architecte Bâtiments France',
      sla: 'SLA 15j',
      iconName: 'Landmark',
      iconColor: '#d97706',
      bgColor: '#fffbeb',
      stepNumber: 4,
      isActive: false
    }
  },
  {
    id: 'join_and',
    type: 'bpmnGateway',
    position: { x: 740, y: 325 },
    data: {
      label: 'Synchro (AND)',
      gatewayType: 'parallel',
      isActive: false
    }
  },
  {
    id: 'gw2',
    type: 'bpmnGateway',
    position: { x: 860, y: 325 },
    data: {
      label: 'Avis Favorable ?',
      gatewayType: 'exclusive',
      isActive: false
    }
  },
  {
    id: 'rejet',
    type: 'bpmnEnd',
    position: { x: 1160, y: 327 },
    data: {
      label: 'Rejet PLU',
      type: 'reject',
      isActive: false
    }
  },

  // Lane 3 Task Nodes (Y = 550)
  {
    id: 'dgs',
    type: 'bpmnTask',
    position: { x: 380, y: 550 },
    data: {
      title: 'Arbitrage DGS & Escalade',
      actor: 'Direction Générale (DGS)',
      sla: 'Alerte 24h',
      iconName: 'ShieldAlert',
      iconColor: '#e11d48',
      bgColor: '#fff1f2',
      stepNumber: 7,
      isActive: false
    }
  },
  {
    id: 'visa',
    type: 'bpmnTask',
    position: { x: 820, y: 550 },
    data: {
      title: 'Visa & Signature Maire / Adjoint',
      actor: 'Adjoint Urbanisme / Maire',
      sla: 'SLA 72h',
      iconName: 'Stamp',
      iconColor: '#7c3aed',
      bgColor: '#f5f3ff',
      stepNumber: 5,
      isActive: false
    }
  },
  {
    id: 'scellement',
    type: 'connectorTask',
    position: { x: 1180, y: 550 },
    data: {
      title: 'Scellement & Télétransmission @CTES',
      connectorName: 'i-Parapheur / Pastell',
      connectorType: 'parapheur',
      sla: 'SLA Immédiat',
      externalStatus: 'signed_acknowledged',
      statusLabel: 'Signé & Acquitté @CTES',
      stepNumber: 6,
      isActive: false,
      isCompleted: true
    }
  }
];

// Initial edges layout (Orthogonal smoothstep / Corridor without crossing)
const initialEdges: Edge[] = [
  // Lane 1: depot -> completude
  {
    id: 'e-depot-completude',
    source: 'depot',
    sourceHandle: 'right',
    target: 'completude',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: '', color: 'blue', curveType: 'smoothstep' }
  },
  // Lane 1: completude -> gw1
  {
    id: 'e-completude-gw1',
    source: 'completude',
    sourceHandle: 'right',
    target: 'gw1',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: '', color: 'blue', curveType: 'smoothstep' }
  },
  // Feedback Loop: gw1 (top) -> depot (top) [NON] Relance pièces · 3 mois (Bezier upward loop)
  {
    id: 'e-gw1-depot-loop',
    source: 'gw1',
    sourceHandle: 'top',
    target: 'depot',
    targetHandle: 'top',
    type: 'bpmnLiving',
    data: { label: '[NON] Relance pièces · 3 mois (Délai suspendu)', color: 'amber', curveType: 'bezier' }
  },
  // Exit: gw1 -> rejet_tacite (If no answer within 3 months)
  {
    id: 'e-gw1-rejet-tacite',
    source: 'gw1',
    sourceHandle: 'right',
    target: 'rejet_tacite',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: '[Délai 3 mois expiré] Rejet tacite', color: 'rose', curveType: 'smoothstep' }
  },
  // Descent Lane 1 -> Lane 2: gw1 (bottom) -> fork_and (top-target) [OUI] Conforme
  {
    id: 'e-gw1-fork',
    source: 'gw1',
    sourceHandle: 'bottom',
    target: 'fork_and',
    targetHandle: 'top-target',
    type: 'bpmnLiving',
    data: { label: '[OUI] Conforme', color: 'emerald', curveType: 'smoothstep' }
  },
  // Parallel split from fork_and -> ctm & abf
  {
    id: 'e-fork-ctm',
    source: 'fork_and',
    sourceHandle: 'right',
    target: 'ctm',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: 'Voie CTM (8j)', color: 'emerald', curveType: 'smoothstep' }
  },
  {
    id: 'e-fork-abf',
    source: 'fork_and',
    sourceHandle: 'bottom',
    target: 'abf',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: 'Voie ABF (15j)', color: 'emerald', curveType: 'smoothstep' }
  },
  // Parallel join into join_and
  {
    id: 'e-ctm-join',
    source: 'ctm',
    sourceHandle: 'right',
    target: 'join_and',
    targetHandle: 'top-target',
    type: 'bpmnLiving',
    data: { label: '', color: 'emerald', curveType: 'smoothstep' }
  },
  {
    id: 'e-abf-join',
    source: 'abf',
    sourceHandle: 'right',
    target: 'join_and',
    targetHandle: 'bottom-target',
    type: 'bpmnLiving',
    data: { label: '', color: 'emerald', curveType: 'smoothstep' }
  },
  // join_and -> gw2
  {
    id: 'e-join-gw2',
    source: 'join_and',
    sourceHandle: 'right',
    target: 'gw2',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: '', color: 'emerald', curveType: 'smoothstep' }
  },
  // gw2 -> rejet PLU (clean spacing 270px)
  {
    id: 'e-gw2-rejet',
    source: 'gw2',
    sourceHandle: 'right',
    target: 'rejet',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: '[NON] Rejet PLU', color: 'rose', curveType: 'smoothstep' }
  },
  // gw2 -> visa (bottom descent into Lane 3)
  {
    id: 'e-gw2-visa',
    source: 'gw2',
    sourceHandle: 'bottom',
    target: 'visa',
    targetHandle: 'top',
    type: 'bpmnLiving',
    data: { label: '[OUI] Avis Favorable', color: 'emerald', curveType: 'smoothstep' }
  },
  // Escalade SLA: completude (bottom) -> dgs (left), ROUTED PROPERLY IN OUTER LEFT CORRIDOR (x: 180, y: 210)
  // Completely to the left of Parallèle (AND) at x: 240, zero node intersections!
  {
    id: 'e-completude-dgs',
    source: 'completude',
    sourceHandle: 'bottom',
    target: 'dgs',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { 
      label: 'Escalade SLA (Alerte 24h)', 
      color: 'rose', 
      corridorX: 180,
      corridorY: 210,
      customLabelPos: { x: 135, y: 380 }
    }
  },
  // SORTIE 1 FROM DGS: Réaffectation vers instruction avec nouveau SLA (corridorX: 700, zero overlap)
  {
    id: 'e-dgs-completude',
    source: 'dgs',
    sourceHandle: 'right',
    target: 'completude',
    targetHandle: 'right',
    type: 'bpmnLiving',
    data: { 
      label: 'Réaffectation (nouveau SLA)', 
      color: 'blue', 
      corridorX: 700,
      customLabelPos: { x: 700, y: 210 }
    }
  },
  // SORTIE 2 FROM DGS: Évocation directe vers Visa Élu
  {
    id: 'e-dgs-visa',
    source: 'dgs',
    sourceHandle: 'right',
    target: 'visa',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { 
      label: 'Évocation directe', 
      color: 'emerald', 
      curveType: 'smoothstep' 
    }
  },
  // visa -> scellement
  {
    id: 'e-visa-scellement',
    source: 'visa',
    sourceHandle: 'right',
    target: 'scellement',
    targetHandle: 'left',
    type: 'bpmnLiving',
    data: { label: 'Arrêté signé', color: 'emerald', curveType: 'smoothstep' }
  }
];

export interface PixelFlowCanvasProps {
  onOpenDecision?: () => void;
  onOpenValidation?: (dossierId?: string) => void;
  onOpenStudio?: () => void;
  selectedDossierId?: string;
  onSelectDossierId?: (id: string) => void;
  dossiers?: ValidationDossier[];
}

function InnerPixelFlowCanvas({
  onOpenDecision,
  onOpenValidation,
  onOpenStudio,
  selectedDossierId,
  onSelectDossierId,
  dossiers = INITIAL_DOSSIERS,
}: PixelFlowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { fitView } = useReactFlow();

  // Mode Démo / Simulation (Default FALSE: sober real dossier view)
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Active dossier selected
  const [currentDossierId, setCurrentDossierId] = useState<string>(
    selectedDossierId || dossiers[0]?.id || 'PC-2026-042'
  );

  useEffect(() => {
    if (selectedDossierId) {
      setCurrentDossierId(selectedDossierId);
    }
  }, [selectedDossierId]);

  // Simulation states (when demo mode is enabled)
  const [selectedScenario, setSelectedScenario] = useState<BPMNScenario>('nominal');
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speedMultiplier, setSpeedMultiplier] = useState<1 | 2 | 4>(1);
  const [selectedDrawerNode, setSelectedDrawerNode] = useState<BpmnDrawerDetails | null>(null);

  const activeDossier = dossiers.find((d) => d.id === currentDossierId) || dossiers[0];

  const activeSteps = useMemo(() => {
    if (isDemoMode) {
      return SCENARIO_STEPS[selectedScenario];
    }
    // Real dossier mode
    if (activeDossier?.id === 'ARR-2026-019') {
      return ['depot', 'fork_and', 'ctm', 'join_and', 'gw2', 'dgs', 'visa'];
    }
    if (activeDossier?.id === 'MP-2026-008') {
      return ['depot', 'fork_and', 'ctm', 'abf', 'join_and', 'gw2', 'dgs', 'visa', 'scellement'];
    }
    return ['depot', 'completude', 'gw1', 'fork_and', 'ctm', 'abf', 'join_and', 'gw2', 'dgs', 'visa', 'scellement'];
  }, [isDemoMode, selectedScenario, activeDossier]);

  const currentNodeId = useMemo(() => {
    if (isDemoMode) {
      return activeSteps[currentStepIndex] || null;
    }
    if (activeDossier?.id === 'ARR-2026-019') return 'ctm';
    if (activeDossier?.id === 'MP-2026-008') return 'scellement';
    return 'visa'; // PC-2026-042 at Visa Adjoint/Maire
  }, [isDemoMode, activeSteps, currentStepIndex, activeDossier]);

  // Fit view automatically on mount or scenario change
  useEffect(() => {
    const timer = setTimeout(() => {
      fitView({ padding: 0.1, duration: 400 });
    }, 200);
    return () => clearTimeout(timer);
  }, [fitView, selectedScenario, currentDossierId, isDemoMode]);

  // Handle Play/Pause simulation timer
  useEffect(() => {
    if (!isPlaying || !isDemoMode) return;

    const intervalTime = 2000 / speedMultiplier;
    const timer = setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev >= activeSteps.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalTime);

    return () => clearInterval(timer);
  }, [isPlaying, speedMultiplier, activeSteps, isDemoMode]);

  // Sync active node, traversed completed nodes, overdue badges & edges highlight
  useEffect(() => {
    const completedNodeIds = new Set<string>();

    if (isDemoMode) {
      activeSteps.slice(0, currentStepIndex).forEach((id) => completedNodeIds.add(id));
    } else {
      // In real dossier mode:
      if (activeDossier?.id === 'PC-2026-042') {
        completedNodeIds.add('depot');
        completedNodeIds.add('completude');
        completedNodeIds.add('gw1');
        completedNodeIds.add('fork_and');
        completedNodeIds.add('ctm');
        completedNodeIds.add('abf');
        completedNodeIds.add('join_and');
        completedNodeIds.add('gw2');
      } else if (activeDossier?.id === 'ARR-2026-019') {
        completedNodeIds.add('depot');
      } else if (activeDossier?.id === 'MP-2026-008') {
        completedNodeIds.add('depot');
        completedNodeIds.add('fork_and');
        completedNodeIds.add('ctm');
        completedNodeIds.add('abf');
        completedNodeIds.add('join_and');
        completedNodeIds.add('gw2');
        completedNodeIds.add('dgs');
        completedNodeIds.add('visa');
      }
    }

    // Update nodes
    setNodes((prevNodes) =>
      prevNodes.map((n) => {
        if (n.type === 'bpmnLane') return n;

        const isCurrent = n.id === currentNodeId;
        const isCompleted = completedNodeIds.has(n.id);

        if (n.type === 'bpmnTask') {
          // Special handling for missing_pieces scenario
          if (isDemoMode && selectedScenario === 'missing_pieces' && n.id === 'completude') {
            return {
              ...n,
              data: {
                ...n.data,
                isActive: false,
                isCompleted: false,
                isOverdue: false,
                customBadgeText: 'Incomplet · Suspendu 3m',
                customBadgeColor: 'amber',
                subBadge: undefined,
                tokenColor: 'amber',
              },
            };
          }

          // Special handling for sla_escalation scenario
          if (isDemoMode && selectedScenario === 'sla_escalation') {
            if (n.id === 'dgs') {
              return {
                ...n,
                data: {
                  ...n.data,
                  isActive: true,
                  isCompleted: false,
                  isOverdue: true,
                  overdueLabel: 'Alerte 24h',
                  customBadgeText: 'Alerte 24h',
                  customBadgeColor: 'rose',
                  tokenColor: 'rose',
                },
              };
            }
            if (n.id === 'completude') {
              return {
                ...n,
                data: {
                  ...n.data,
                  isActive: false,
                  isCompleted: true,
                  isOverdue: true,
                  customBadgeText: 'SLA Dépassé',
                  customBadgeColor: 'rose',
                  tokenColor: 'rose',
                },
              };
            }
            if (n.id === 'depot') {
              return {
                ...n,
                data: {
                  ...n.data,
                  isActive: false,
                  isCompleted: true,
                },
              };
            }
          }

          const isOverdue =
            (isDemoMode && selectedScenario === 'sla_escalation' && n.id === 'dgs');

          const isMissingLoopDepot = isDemoMode && selectedScenario === 'missing_pieces' && n.id === 'depot' && isCurrent;

          return {
            ...n,
            data: {
              ...n.data,
              isActive: isCurrent,
              isCompleted: isCompleted && !isCurrent,
              isOverdue,
              overdueLabel: isOverdue ? 'Alerte 24h' : undefined,
              customBadgeText: (!isDemoMode && activeDossier?.id === 'PC-2026-042' && n.id === 'visa') ? 'En cours · Reste 18h' : undefined,
              customBadgeColor: (!isDemoMode && activeDossier?.id === 'PC-2026-042' && n.id === 'visa') ? 'blue' : undefined,
              subBadge: undefined,
              tokenColor: isOverdue ? 'rose' : isMissingLoopDepot ? 'amber' : isCurrent ? 'blue' : 'blue',
            },
          };
        }

        if (n.type === 'bpmnGateway') {
          return {
            ...n,
            data: {
              ...n.data,
              isActive: isCurrent || isCompleted,
            },
          };
        }

        if (n.type === 'bpmnEnd') {
          return {
            ...n,
            data: {
              ...n.data,
              isActive: isCurrent,
            },
          };
        }

        return n;
      })
    );

    // Update edges
    setEdges((prevEdges) =>
      prevEdges.map((e) => {
        let isEdgeActive = false;
        let isEdgeCompleted = false;

        if (isDemoMode) {
          if (selectedScenario === 'sla_escalation') {
            if (e.source === 'depot' && e.target === 'completude') {
              isEdgeCompleted = true;
            }
            if (e.id === 'e-completude-dgs' || (e.source === 'completude' && e.target === 'dgs')) {
              isEdgeActive = true;
            }
            if (currentStepIndex > 2) {
              const fromStep = activeSteps[currentStepIndex - 1];
              const toStep = activeSteps[currentStepIndex];
              if (e.source === fromStep && e.target === toStep) {
                isEdgeActive = true;
              }
              for (let i = 2; i < currentStepIndex; i++) {
                const u = activeSteps[i];
                const v = activeSteps[i + 1];
                if (e.source === u && e.target === v) {
                  isEdgeCompleted = true;
                }
              }
            }
          } else {
            if (currentStepIndex > 0) {
              const fromStep = activeSteps[currentStepIndex - 1];
              const toStep = activeSteps[currentStepIndex];
              if (e.source === fromStep && e.target === toStep) {
                isEdgeActive = true;
              }
            }

            // Mark completed edges
            for (let i = 0; i < currentStepIndex; i++) {
              const u = activeSteps[i];
              const v = activeSteps[i + 1];
              if (e.source === u && e.target === v) {
                isEdgeCompleted = true;
              }
            }
          }
        } else {
          // Real dossier PC-2026-042 path:
          if (activeDossier?.id === 'PC-2026-042') {
            const traversedPairs = [
              ['depot', 'completude'],
              ['completude', 'gw1'],
              ['gw1', 'fork_and'],
              ['fork_and', 'ctm'],
              ['fork_and', 'abf'],
              ['ctm', 'join_and'],
              ['abf', 'join_and'],
              ['join_and', 'gw2'],
            ];
            if (traversedPairs.some(([s, t]) => e.source === s && e.target === t)) {
              isEdgeCompleted = true;
            }
            if (e.source === 'gw2' && e.target === 'visa') {
              isEdgeActive = true;
            }
          }
        }

        return {
          ...e,
          data: {
            ...e.data,
            isActive: isEdgeActive,
            isCompleted: isEdgeCompleted && !isEdgeActive,
          },
        };
      })
    );
  }, [
    isDemoMode,
    selectedScenario,
    currentStepIndex,
    activeSteps,
    currentNodeId,
    activeDossier,
    setNodes,
    setEdges,
  ]);

  // Open drawer on node click
  const handleNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.stopPropagation();
      const details = NODE_DETAILS[node.id];
      if (details) {
        setSelectedDrawerNode(details);
      }
    },
    []
  );

  useEffect(() => {
    const handleNodeSelected = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail && detail.id) {
        const d = NODE_DETAILS[detail.id];
        if (d) setSelectedDrawerNode(d);
      }
    };
    window.addEventListener('bpmn-node-selected', handleNodeSelected);
    return () => window.removeEventListener('bpmn-node-selected', handleNodeSelected);
  }, []);

  return (
    <div className="relative w-full h-[calc(100vh-210px)] min-h-[620px] bg-slate-50 border border-slate-200 rounded-2xl overflow-hidden shadow-xs flex flex-col font-sans">
      {/* Top Dossier Switcher Bar */}
      <div className="p-2.5 sm:p-3 bg-white border-b border-slate-200/90 flex items-center justify-between gap-2 z-20">
        {/* Desktop View: Pills */}
        <div className="hidden md:flex items-center gap-2 flex-wrap text-xs">
          <span className="font-bold text-slate-500 uppercase tracking-wider text-[10px] mr-1">
            Dossier municipal en cours :
          </span>
          {dossiers.map((d) => {
            const isSel = d.id === currentDossierId;
            return (
              <button
                key={d.id}
                onClick={() => {
                  setCurrentDossierId(d.id);
                  onSelectDossierId?.(d.id);
                }}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer border ${
                  isSel
                    ? 'bg-blue-600 text-white border-blue-600 shadow-2xs font-semibold'
                    : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'
                }`}
              >
                <span className="font-mono font-bold mr-1.5">{d.id}</span>
                <span>{d.circuitLabel}</span>
              </button>
            );
          })}
        </div>

        {/* Mobile View: 1-line Compact <select> + Small Demo Button */}
        <div className="flex md:hidden items-center justify-between gap-2 w-full">
          <div className="flex-1 min-w-0">
            <select
              value={currentDossierId}
              onChange={(e) => {
                setCurrentDossierId(e.target.value);
                onSelectDossierId?.(e.target.value);
              }}
              className="w-full text-xs font-semibold text-slate-800 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 truncate"
            >
              {dossiers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.id} · {d.circuitLabel}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setIsDemoMode(!isDemoMode)}
            className={`px-2.5 py-1.5 rounded-lg border text-[10px] font-semibold transition-colors flex items-center gap-1 shrink-0 ${
              isDemoMode
                ? 'bg-blue-50 text-blue-800 border-blue-300 ring-1 ring-blue-300'
                : 'bg-slate-50 text-slate-600 border-slate-200'
            }`}
          >
            <SlidersHorizontal className="w-3 h-3 text-slate-500" />
            <span>Démo</span>
          </button>
        </div>

        {/* Desktop Action & Demo Buttons */}
        <div className="hidden md:flex items-center gap-2">
          {onOpenDecision && (
            <button
              onClick={onOpenDecision}
              className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center gap-1.5 shadow-2xs transition-colors cursor-pointer whitespace-nowrap"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Traiter dans « À valider »</span>
            </button>
          )}

          {/* Toggle Mode Démo / Simulation Desktop */}
          <button
            onClick={() => setIsDemoMode(!isDemoMode)}
            className={`px-2.5 py-1.5 rounded-xl border text-[11px] font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs whitespace-nowrap ${
              isDemoMode
                ? 'bg-blue-50 text-blue-800 border-blue-300 ring-2 ring-blue-400/20'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
            title="Activer/désactiver les commandes de transport pour démonstration"
          >
            <SlidersHorizontal className="w-3 h-3 text-slate-500" />
            <span>Mode démo / simulation</span>
          </button>
        </div>
      </div>

      {/* Demo Controls Bar (Only visible when isDemoMode is TRUE) */}
      {isDemoMode && (
        <div className="px-4 py-2 bg-blue-50/60 border-b border-blue-200 flex flex-wrap items-center justify-between gap-3 text-xs z-20 animate-in fade-in duration-150">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-bold text-blue-900 text-[11px] mr-1">Scénario de test :</span>
            {SCENARIOS.map((sc) => (
              <button
                key={sc.id}
                onClick={() => {
                  setSelectedScenario(sc.id);
                  setCurrentStepIndex(sc.id === 'sla_escalation' ? 2 : 0);
                  setIsPlaying(false);
                }}
                className={`px-2 py-0.5 rounded-md font-medium text-[11px] border transition-colors ${
                  selectedScenario === sc.id
                    ? 'bg-blue-600 text-white border-blue-600 shadow-2xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-blue-100/50'
                }`}
              >
                {sc.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 shadow-xs flex items-center gap-1 font-semibold text-[11px] px-2.5"
            >
              {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              <span>{isPlaying ? 'Pause' : 'Lecture'}</span>
            </button>
            <button
              onClick={() => {
                setCurrentStepIndex((prev) => Math.min(activeSteps.length - 1, prev + 1));
              }}
              className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 text-[11px] flex items-center gap-1"
            >
              <StepForward className="w-3 h-3" />
              <span>Pas à pas</span>
            </button>
            <button
              onClick={() => {
                setCurrentStepIndex(selectedScenario === 'sla_escalation' ? 2 : 0);
                setIsPlaying(false);
              }}
              className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-500 hover:bg-slate-100"
              title="Réinitialiser"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
            <div className="flex items-center border border-slate-200 rounded-lg overflow-hidden bg-white text-[10px]">
              {([1, 2, 4] as const).map((spd) => (
                <button
                  key={spd}
                  onClick={() => setSpeedMultiplier(spd)}
                  className={`px-2 py-1 font-mono font-bold ${
                    speedMultiplier === spd ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Desktop View: Full React Flow Canvas */}
      <div className="hidden md:block relative z-10 w-full h-full flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          minZoom={0.25}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
          className="bg-transparent"
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#CBD5E1" />
          <Controls 
            showInteractive={false} 
            className="!bg-white !border !border-slate-200 !shadow-sm !rounded-xl !text-slate-700 m-4" 
          />
        </ReactFlow>
      </div>

      {/* Mobile View (< 768px): Continuous Vertical Timeline */}
      <div className="block md:hidden w-full h-full overflow-y-auto px-4 py-3 pb-36 flex-1">
        {/* Compact Header */}
        <div className="mb-3 bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md">
              {activeDossier?.id || 'PC-2026-042'}
            </span>
            <span className="text-[10px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" />
              <span>{activeDossier?.slaDeadline || 'Reste 18h'}</span>
            </span>
          </div>
          <h2 className="text-sm font-bold text-slate-900 leading-snug">
            {activeDossier?.title}
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Demandeur : <strong className="text-slate-700">{activeDossier?.applicant}</strong>
          </p>
        </div>

        {/* Vertical Timeline with Continuous Guide Line */}
        <div className="relative max-w-md mx-auto">
          {/* Continuous Vertical Guide Line */}
          <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-slate-200 -z-0" />

          <div className="space-y-4">
            {activeSteps.map((stepId, idx) => {
              const isGateway = stepId === 'gw1' || stepId === 'gw2' || stepId === 'fork_and' || stepId === 'join_and';
              const isEnd = stepId === 'rejet' || stepId === 'rejet_tacite';
              const isCurrent = stepId === currentNodeId;
              const isCompleted = isDemoMode ? idx < currentStepIndex : (activeDossier?.currentStepIndex || 0) > idx;
              const details = NODE_DETAILS[stepId];

              if (isGateway) {
                const label = 
                  stepId === 'fork_and' ? 'Passerelle Parallèle (AND)' :
                  stepId === 'join_and' ? 'Synchronisation Parallèle (AND)' :
                  stepId === 'gw1' ? 'Décision : Dossier Conforme ?' : 
                  'Décision : Avis Favorable ?';

                return (
                  <div key={idx} className="relative z-10 flex items-center gap-3 pl-1">
                    <div className="w-6 h-6 rounded-full bg-amber-100 border-2 border-amber-400 flex items-center justify-center shrink-0">
                      <GitFork className="w-3 h-3 text-amber-700" />
                    </div>
                    <div className="px-2.5 py-1 rounded-full bg-amber-50/80 border border-amber-200 text-[10px] font-bold text-amber-800">
                      {label}
                    </div>
                  </div>
                );
              }

              if (!details) return null;

              return (
                <div
                  key={idx}
                  onClick={() => setSelectedDrawerNode(details)}
                  className="relative z-10 flex items-start gap-3 pl-1 cursor-pointer"
                >
                  {/* Step Dot on continuous line */}
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-2 border-2 ${
                    isCurrent
                      ? 'bg-blue-600 border-blue-400 ring-4 ring-blue-300/40 text-white '
                      : isCompleted
                      ? 'bg-emerald-500 border-emerald-300 text-white'
                      : 'bg-white border-slate-300 text-slate-400'
                  }`}>
                    {isCompleted ? (
                      <Check className="w-3 h-3 stroke-[3]" />
                    ) : (
                      <span className="text-[10px] font-bold">{idx + 1}</span>
                    )}
                  </div>

                  {/* Card Content */}
                  <div className={`flex-1 bg-white rounded-xl border p-3 shadow-2xs transition-all ${
                    isCurrent
                      ? 'border-blue-500 ring-2 ring-blue-400/20 shadow-xs'
                      : isCompleted
                      ? 'border-emerald-200 bg-emerald-50/15'
                      : 'border-slate-200'
                  }`}>
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <h4 className="text-xs font-bold text-slate-900 leading-snug">
                        {details.title}
                      </h4>
                      {isCompleted ? (
                        <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[9px] font-semibold px-1.5 py-0.5 rounded flex items-center gap-0.5 shrink-0">
                          <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />
                          <span>Validé</span>
                        </span>
                      ) : isCurrent ? (
                        <span className="bg-blue-50 text-blue-700 border border-blue-300 text-[9px] font-bold px-1.5 py-0.5 rounded flex items-center gap-0.5 shrink-0 ">
                          <span>En cours</span>
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                          {details.sla}
                        </span>
                      )}
                    </div>
                    <p className="text-[10.5px] text-slate-500 font-medium">
                      {details.actor}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Clean Fixed Action Bar on Mobile Above Navigation */}
        <div className="fixed bottom-[56px] inset-x-0 bg-white/95 backdrop-blur-md border-t border-slate-200 p-2.5 flex items-center justify-between gap-2 z-30 shadow-lg max-w-md mx-auto">
          <button
            onClick={() => {
              if (onOpenDecision) onOpenDecision();
              else onOpenValidation?.(currentDossierId);
            }}
            className="flex-1 py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Valider & Signer</span>
          </button>
          <button
            onClick={() => {
              if (onOpenDecision) onOpenDecision();
              else onOpenValidation?.(currentDossierId);
            }}
            className="py-2 px-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Renvoyer</span>
          </button>
        </div>
      </div>

      {/* Lateral Drawer for Node Inspection (Never cuts header) */}
      <BpmnDrawer
        details={selectedDrawerNode}
        onClose={() => setSelectedDrawerNode(null)}
        onOpenDecision={onOpenDecision || (() => onOpenValidation?.(currentDossierId))}
      />
    </div>
  );
}

export function PixelFlowCanvas(props: PixelFlowCanvasProps) {
  return (
    <ReactFlowProvider>
      <InnerPixelFlowCanvas {...props} />
    </ReactFlowProvider>
  );
}
