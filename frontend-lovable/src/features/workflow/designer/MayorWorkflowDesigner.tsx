import React, { useState, useMemo, useCallback } from 'react';
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
  useReactFlow,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  Sparkles,
  Wand2,
  Play,
  Save,
  CheckCircle2,
  Layers,
  ChevronDown,
  ChevronUp,
  FileCode,
  FormInput,
  Building2,
  HardHat,
  Landmark,
  Stamp,
  ShieldCheck,
  Plus,
  Cpu,
  ArrowUp,
  ArrowDown,
  Trash2
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { BpmnTaskNode, BpmnTaskNodeData } from '../pixelflow/BpmnTaskNode';
import { ConnectorTaskNode } from '../pixelflow/ConnectorTaskNode';
import { BpmnGatewayNode, BpmnGatewayNodeData } from '../pixelflow/BpmnGatewayNode';
import { BpmnEndNode, BpmnEndNodeData } from '../pixelflow/BpmnEndNode';
import { BpmnLivingEdge, BpmnLivingEdgeData } from '../pixelflow/BpmnLivingEdge';
import { MayorFlowFormBuilderModal } from '../mayorflow/MayorFlowFormBuilderModal';
import { useOrganizationModules } from '@/features/workspace/organization-modules-context';

const nodeTypes = {
  bpmnTask: BpmnTaskNode,
  connectorTask: ConnectorTaskNode,
  bpmnGateway: BpmnGatewayNode,
  bpmnEnd: BpmnEndNode,
};

const edgeTypes = {
  bpmnLiving: BpmnLivingEdge,
};

interface MayorWorkflowDesignerProps {
  onLaunchSimulation?: () => void;
}

function InnerMayorWorkflowDesigner({ onLaunchSimulation }: MayorWorkflowDesignerProps) {
  const { hasModule } = useOrganizationModules();
  const [viewMode, setViewMode] = useState<'list' | 'bpmn'>('list');
  const [promptText, setPromptText] = useState(
    "Instruction Permis de Construire : Guichet Cerfa 13406*12, Vérification Complétude 48h, Consultation ABF 15j, Visa Adjoint aux Travaux 72h, et Scellement & Télétransmission @CTES."
  );
  const [isAiBarOpen, setIsAiBarOpen] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [workflowTitle, setWorkflowTitle] = useState("Circuit d'instruction Permis de Construire (ADS)");
  const [workflowCategory, setWorkflowCategory] = useState("urbanisme");
  const [formBuilderNode, setFormBuilderNode] = useState<{ id: string; name: string } | null>(null);

  const { fitView } = useReactFlow();

  // Helper to parse natural text prompt into real nodes and edges
  const parsePromptToNodesAndEdges = (text: string) => {
    const t = text.toLowerCase();
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    let currentX = 60;
    const yCenter = 180;
    const spacing = 320;

    // Detect steps mentioned in prompt:
    // 1. Guichet / Dépôt
    newNodes.push({
      id: 'step_depot',
      type: 'bpmnTask',
      position: { x: currentX, y: yCenter },
      data: {
        title: t.includes('13406') ? 'Guichet & Dépôt Cerfa 13406*12' : t.includes('voirie') ? 'Dépôt Demande Voirie' : 'Dépôt Dossier Initial',
        actor: t.includes('voirie') ? 'Agent Voirie CTM' : 'Guichetier ADS',
        sla: 'SLA < 2h',
        iconName: 'Building2',
        iconColor: '#2563eb',
        bgColor: '#eff6ff',
        stepNumber: 1,
      }
    });

    let prevNodeId = 'step_depot';

    // 2. Complétude / Instruction
    currentX += spacing;
    const completudeSla = t.includes('48h') ? 'SLA 48h' : t.includes('24h') ? 'SLA 24h' : 'SLA 1 mois (R.423-22)';
    newNodes.push({
      id: 'step_completude',
      type: 'bpmnTask',
      position: { x: currentX, y: yCenter },
      data: {
        title: 'Vérification Complétude',
        actor: 'Instructeur ADS · Pôle Urbanisme',
        sla: completudeSla,
        iconName: 'FileCheck',
        iconColor: '#0284c7',
        bgColor: '#f0f9ff',
        stepNumber: 2,
      }
    });
    newEdges.push({
      id: `e-${prevNodeId}-step_completude`,
      source: prevNodeId,
      sourceHandle: 'right',
      target: 'step_completude',
      targetHandle: 'left',
      type: 'bpmnLiving',
      data: { color: 'blue', curveType: 'smoothstep' }
    });
    prevNodeId = 'step_completude';

    // 3. Technical / Consultation ABF or CTM
    if (t.includes('abf') || t.includes('patrimoine') || t.includes('15j')) {
      currentX += spacing;
      const abfSla = t.includes('15j') ? 'SLA 15j' : t.includes('8j') ? 'SLA 8j' : 'SLA 15j';
      newNodes.push({
        id: 'step_abf',
        type: 'bpmnTask',
        position: { x: currentX, y: yCenter },
        data: {
          title: 'Consultation ABF & Patrimoine',
          actor: 'Architecte Bâtiments France',
          sla: abfSla,
          iconName: 'Landmark',
          iconColor: '#d97706',
          bgColor: '#fffbeb',
          stepNumber: 3,
        }
      });
      newEdges.push({
        id: `e-${prevNodeId}-step_abf`,
        source: prevNodeId,
        sourceHandle: 'right',
        target: 'step_abf',
        targetHandle: 'left',
        type: 'bpmnLiving',
        data: { color: 'emerald', curveType: 'smoothstep' }
      });
      prevNodeId = 'step_abf';
    } else if (t.includes('ctm') || t.includes('voirie') || t.includes('technique')) {
      currentX += spacing;
      newNodes.push({
        id: 'step_ctm',
        type: 'bpmnTask',
        position: { x: currentX, y: yCenter },
        data: {
          title: 'Avis Technique CTM & Réseaux',
          actor: 'Chef Services Techniques (CTM)',
          sla: 'SLA 8j',
          iconName: 'HardHat',
          iconColor: '#059669',
          bgColor: '#ecfdf5',
          stepNumber: 3,
        }
      });
      newEdges.push({
        id: `e-${prevNodeId}-step_ctm`,
        source: prevNodeId,
        sourceHandle: 'right',
        target: 'step_ctm',
        targetHandle: 'left',
        type: 'bpmnLiving',
        data: { color: 'emerald', curveType: 'smoothstep' }
      });
      prevNodeId = 'step_ctm';
    }

    // 4. Visa Adjoint / Maire
    currentX += spacing;
    const visaTitle = t.includes('travaux') ? 'Visa Adjoint aux Travaux' : t.includes('maire') ? 'Visa & Signature du Maire' : 'Visa Régalien de l’Adjoint';
    const visaActor = t.includes('travaux') ? 'Jean-Luc LE GALL · Adjoint Travaux' : t.includes('maire') ? 'Dominique CAP · Maire' : 'Adjoint Urbanisme';
    const visaSla = t.includes('72h') ? 'SLA 72h' : t.includes('24h') ? 'SLA 24h' : 'SLA 48h';
    newNodes.push({
      id: 'step_visa',
      type: 'bpmnTask',
      position: { x: currentX, y: yCenter },
      data: {
        title: visaTitle,
        actor: visaActor,
        sla: visaSla,
        iconName: 'Stamp',
        iconColor: '#7c3aed',
        bgColor: '#f5f3ff',
        stepNumber: 4,
      }
    });
    newEdges.push({
      id: `e-${prevNodeId}-step_visa`,
      source: prevNodeId,
      sourceHandle: 'right',
      target: 'step_visa',
      targetHandle: 'left',
      type: 'bpmnLiving',
      data: { color: 'emerald', curveType: 'smoothstep' }
    });
    prevNodeId = 'step_visa';

    // 5. Scellement & Télétransmission @CTES
    currentX += spacing;
    newNodes.push({
      id: 'step_scellement',
      type: 'bpmnTask',
      position: { x: currentX, y: yCenter },
      data: {
        title: 'Scellement & Télétransmission @CTES',
        actor: 'Coffre-fort DGS · Parapheur eIDAS',
        sla: 'SLA Immédiat',
        iconName: 'ShieldCheck',
        iconColor: '#4f46e5',
        bgColor: '#eef2ff',
        stepNumber: 5,
      }
    });
    newEdges.push({
      id: `e-${prevNodeId}-step_scellement`,
      source: prevNodeId,
      sourceHandle: 'right',
      target: 'step_scellement',
      targetHandle: 'left',
      type: 'bpmnLiving',
      data: { color: 'emerald', curveType: 'smoothstep' }
    });

    return { nodes: newNodes, edges: newEdges };
  };

  const initialParsed = useMemo(() => parsePromptToNodesAndEdges(promptText), []);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialParsed.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialParsed.edges);

  const handleGenerateFromPrompt = (overrideText?: string) => {
    const textToUse = overrideText || promptText;
    if (!textToUse.trim()) return;

    setIsGenerating(true);
    setTimeout(() => {
      const parsed = parsePromptToNodesAndEdges(textToUse);
      setNodes(parsed.nodes);
      setEdges(parsed.edges);
      setIsGenerating(false);

      if (textToUse.toLowerCase().includes('voirie')) {
        setWorkflowTitle("Arrêté Temporaire de Voirie & Déviation");
        setWorkflowCategory("voirie");
      } else if (textToUse.toLowerCase().includes('marché')) {
        setWorkflowTitle("Marché Public de Fournitures & CAO");
        setWorkflowCategory("finances");
      } else {
        setWorkflowTitle("Instruction Permis de Construire (ADS)");
        setWorkflowCategory("urbanisme");
      }

      toast.success("Circuit de validation généré avec succès.");
      setTimeout(() => fitView({ padding: 0.15, duration: 400 }), 100);
    }, 350);
  };

  // Mini toolbar manual node handlers
  const handleAddStepNode = () => {
    const newId = `step_manual_${Date.now()}`;
    const lastNode = nodes[nodes.length - 1];
    const newX = lastNode ? lastNode.position.x + 320 : 100;
    const newY = lastNode ? lastNode.position.y : 180;

    const newNode: Node = {
      id: newId,
      type: 'bpmnTask',
      position: { x: newX, y: newY },
      data: {
        title: 'Nouvelle Étape d’Instruction',
        actor: 'Instructeur Référent',
        sla: 'SLA 48h',
        iconName: 'FileCheck',
        iconColor: '#0284c7',
        bgColor: '#f0f9ff',
        stepNumber: nodes.length + 1,
      },
    };

    setNodes((nds) => [...nds, newNode]);
    if (lastNode) {
      setEdges((eds) => [
        ...eds,
        {
          id: `e-${lastNode.id}-${newId}`,
          source: lastNode.id,
          sourceHandle: 'right',
          target: newId,
          targetHandle: 'left',
          type: 'bpmnLiving',
          data: { color: 'blue', curveType: 'smoothstep' },
        },
      ]);
    }
    toast.success("Nouvelle étape ajoutée au canvas !");
  };

  const handleAddXorGateway = () => {
    const newId = `gw_xor_${Date.now()}`;
    const lastNode = nodes[nodes.length - 1];
    const newX = lastNode ? lastNode.position.x + 300 : 100;
    const newY = lastNode ? lastNode.position.y + 15 : 195;

    const newNode: Node = {
      id: newId,
      type: 'bpmnGateway',
      position: { x: newX, y: newY },
      data: {
        label: 'Décision XOR ?',
        gatewayType: 'exclusive',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    if (lastNode) {
      setEdges((eds) => [
        ...eds,
        {
          id: `e-${lastNode.id}-${newId}`,
          source: lastNode.id,
          sourceHandle: 'right',
          target: newId,
          targetHandle: 'left',
          type: 'bpmnLiving',
          data: { color: 'amber', curveType: 'smoothstep' },
        },
      ]);
    }
    toast.success("Passerelle XOR ajoutée !");
  };

  const handleAddAndGateway = () => {
    const newId = `gw_and_${Date.now()}`;
    const lastNode = nodes[nodes.length - 1];
    const newX = lastNode ? lastNode.position.x + 300 : 100;
    const newY = lastNode ? lastNode.position.y + 15 : 195;

    const newNode: Node = {
      id: newId,
      type: 'bpmnGateway',
      position: { x: newX, y: newY },
      data: {
        label: 'Parallèle (AND)',
        gatewayType: 'parallel',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    if (lastNode) {
      setEdges((eds) => [
        ...eds,
        {
          id: `e-${lastNode.id}-${newId}`,
          source: lastNode.id,
          sourceHandle: 'right',
          target: newId,
          targetHandle: 'left',
          type: 'bpmnLiving',
          data: { color: 'emerald', curveType: 'smoothstep' },
        },
      ]);
    }
    toast.success("Passerelle Parallèle (AND) ajoutée !");
  };

  return (
    <div className="space-y-3 font-sans text-slate-900">
      {/* Integrated Prompt-to-BPMN IA Banner */}
      {hasModule('ai_assistant') && (
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-cyan-50 border border-cyan-200 text-cyan-600 flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Assistant de Modélisation Prompt-to-BPMN 2.0
                </h2>
                <p className="text-[11px] text-slate-500 font-medium">
                  Génération automatique du circuit et des délais légaux à partir d'une description métier
                </p>
              </div>
            </div>

            <button
              onClick={() => setIsAiBarOpen(!isAiBarOpen)}
              className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
            >
              {isAiBarOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {isAiBarOpen && (
            <div className="pt-1 space-y-3">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                <div className="relative flex-1">
                  <textarea
                    rows={2}
                    value={promptText}
                    onChange={(e) => setPromptText(e.target.value)}
                    placeholder="Ex : Instruction Permis de Construire : Guichet Cerfa 13406*12, Complétude 48h, Consultation ABF 15j, Visa Adjoint aux Travaux 72h..."
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs text-slate-900 font-medium shadow-2xs resize-none"
                  />
                </div>

                <Button
                  onClick={() => handleGenerateFromPrompt()}
                  disabled={isGenerating}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 flex items-center gap-1.5 shadow-xs shrink-0 cursor-pointer"
                >
                  <Wand2 className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
                  <span>{isGenerating ? 'Génération...' : 'Générer le circuit'}</span>
                </Button>
              </div>

              {/* Quick Municipal Presets */}
              <div className="flex items-center gap-1.5 flex-wrap text-[11px]">
                <span className="font-bold text-slate-400 uppercase text-[10px]">Exemples types :</span>
                <button
                  onClick={() => {
                    const p = "Instruction Permis de Construire : Guichet Cerfa 13406*12, Vérification Complétude 48h, Consultation ABF 15j, Visa Adjoint aux Travaux 72h, et Scellement & Télétransmission @CTES.";
                    setPromptText(p);
                    handleGenerateFromPrompt(p);
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 border border-slate-200 transition-colors font-medium shadow-2xs"
                >
                  Permis de Construire (ADS & ABF 15j)
                </button>
                <button
                  onClick={() => {
                    const p = "Arrêté de Voirie : Dépôt Demande Voirie, Avis Technique CTM 8j, Visa Adjoint aux Travaux 48h, et Scellement & Télétransmission @CTES.";
                    setPromptText(p);
                    handleGenerateFromPrompt(p);
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 border border-slate-200 transition-colors font-medium shadow-2xs"
                >
                  Arrêté de Voirie (CTM 8j)
                </button>
                <button
                  onClick={() => {
                    const p = "Marché Public : Dépôt Dossier Initial, Vérification Complétude 24h, Avis Technique CTM 8j, Visa & Signature du Maire 72h, et Scellement & Télétransmission @CTES.";
                    setPromptText(p);
                    handleGenerateFromPrompt(p);
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 border border-slate-200 transition-colors font-medium shadow-2xs"
                >
                  Marché Public (Maire 72h)
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Toolbar / Actions Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Modèle :</span>
          <span className="font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
            {workflowTitle}
          </span>
          <span className="text-[10px] text-blue-700 bg-blue-50 px-2 py-0.5 rounded font-mono font-semibold border border-blue-200">
            {nodes.length} étapes
          </span>
        </div>

        {/* Dual View Segmented Control */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              viewMode === 'list'
                ? 'bg-white text-blue-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Vue Liste simple
          </button>
          <button
            onClick={() => {
              setViewMode('bpmn');
              setTimeout(() => fitView({ padding: 0.2 }), 50);
            }}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              viewMode === 'bpmn'
                ? 'bg-white text-blue-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Vue Graphe BPMN
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setFormBuilderNode({ id: 'step_completude', name: 'Formulaire de Complétude' })}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 font-semibold shadow-2xs cursor-pointer"
          >
            <FormInput className="w-3.5 h-3.5 text-blue-600" />
            <span>Champs du formulaire</span>
          </button>

          {onLaunchSimulation && (
            <button
              onClick={onLaunchSimulation}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-xs cursor-pointer"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Ouvrir dans Suivi du circuit</span>
            </button>
          )}
        </div>
      </div>

      {/* Conditional Dual View Rendering */}
      {viewMode === 'list' ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Séquence d'instruction du circuit (Vue directive)
              </h3>
              <p className="text-xs text-slate-500">
                Ordre chronologique des visas, affectations par service et connecteurs réglementaires.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddStepNode}
                className="text-xs font-semibold text-blue-700 hover:bg-blue-50 border-blue-200"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                <span>+ Ajouter une étape</span>
              </Button>
            </div>
          </div>

          {/* Sequential Step Cards */}
          <div className="space-y-2.5">
            {nodes
              .filter(n => n.type === 'bpmnTask' || n.type === 'connectorTask')
              .map((node, index, taskArray) => {
                const d = node.data as any;
                const isConnector = node.type === 'connectorTask' || (d.title && d.title.includes('@CTES'));

                return (
                  <div
                    key={node.id}
                    className={`p-3.5 rounded-xl border transition-all duration-150 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isConnector
                        ? 'bg-indigo-50/20 border-indigo-200 hover:border-indigo-300'
                        : 'bg-white border-slate-200 hover:border-slate-300 shadow-2xs'
                    }`}
                  >
                    <div className="flex items-start sm:items-center gap-3">
                      <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-slate-100 text-slate-800 font-mono font-bold text-xs flex items-center justify-center border border-slate-200">
                        {String(index + 1).padStart(2, '0')}
                      </span>

                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="text-xs font-bold text-slate-900">
                            {d.title || 'Étape sans titre'}
                          </h4>
                          {isConnector && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                              <Cpu className="w-3 h-3" />
                              Connecteur eIDAS @CTES
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                          <span className="font-semibold text-slate-700">{d.actor || 'Agent instructeur'}</span>
                          <span>·</span>
                          <span className="font-mono text-slate-600 bg-slate-100 px-1.5 py-0.2 rounded text-[10px]">{d.sla || 'SLA 48h'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 self-end sm:self-center">
                      <button
                        onClick={() => {
                          if (index === 0) return;
                          const newNodes = [...nodes];
                          const idx1 = nodes.findIndex(n => n.id === node.id);
                          const prevTask = taskArray[index - 1];
                          const idx2 = nodes.findIndex(n => n.id === prevTask.id);
                          const tempPos = newNodes[idx1].position;
                          newNodes[idx1].position = newNodes[idx2].position;
                          newNodes[idx2].position = tempPos;
                          const temp = newNodes[idx1];
                          newNodes[idx1] = newNodes[idx2];
                          newNodes[idx2] = temp;
                          setNodes(newNodes);
                          toast.success('Ordre des étapes mis à jour.');
                        }}
                        disabled={index === 0}
                        className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 disabled:opacity-30 cursor-pointer"
                        title="Monter"
                      >
                        <ArrowUp className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => {
                          if (index === taskArray.length - 1) return;
                          const newNodes = [...nodes];
                          const idx1 = nodes.findIndex(n => n.id === node.id);
                          const nextTask = taskArray[index + 1];
                          const idx2 = nodes.findIndex(n => n.id === nextTask.id);
                          const tempPos = newNodes[idx1].position;
                          newNodes[idx1].position = newNodes[idx2].position;
                          newNodes[idx2].position = tempPos;
                          const temp = newNodes[idx1];
                          newNodes[idx1] = newNodes[idx2];
                          newNodes[idx2] = temp;
                          setNodes(newNodes);
                          toast.success('Ordre des étapes mis à jour.');
                        }}
                        disabled={index === taskArray.length - 1}
                        className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 disabled:opacity-30 cursor-pointer"
                        title="Descendre"
                      >
                        <ArrowDown className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => setFormBuilderNode({ id: node.id, name: d.title })}
                        className="px-2.5 py-1 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold"
                        title="Éditer le formulaire associé"
                      >
                        <FormInput className="w-3.5 h-3.5 text-blue-600 mr-1 inline" />
                        <span>Formulaire</span>
                      </button>

                      <button
                        onClick={() => {
                          setNodes(prev => prev.filter(n => n.id !== node.id));
                          setEdges(prev => prev.filter(e => e.source !== node.id && e.target !== node.id));
                          toast.info(`Étape « ${d.title} » supprimée.`);
                        }}
                        className="p-1.5 rounded-lg border border-slate-200 hover:border-rose-300 hover:bg-rose-50 text-slate-400 hover:text-rose-600 cursor-pointer"
                        title="Supprimer cette étape"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      ) : (
        /* Unified React Flow Canvas (Light Mode Native) */
        <div className="relative w-full h-[540px] bg-slate-50 border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
          {/* Discrete Mini-Toolbar in Top-Left Corner */}
          <div className="absolute top-3 left-3 z-10 flex items-center gap-1.5 bg-white/95 backdrop-blur-xs border border-slate-200/90 rounded-xl p-1 shadow-sm">
            <button
              onClick={handleAddStepNode}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg hover:bg-slate-100 text-slate-700 font-semibold text-[11px] transition-colors cursor-pointer"
              title="Ajouter une tâche manuelle"
            >
              <Plus className="w-3 h-3 text-blue-600" />
              <span>Étape</span>
            </button>
            <div className="w-px h-3.5 bg-slate-200" />
            <button
              onClick={handleAddXorGateway}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg hover:bg-slate-100 text-slate-700 font-semibold text-[11px] transition-colors cursor-pointer"
              title="Ajouter une passerelle exclusive XOR"
            >
              <Plus className="w-3 h-3 text-amber-600" />
              <span>Passerelle XOR</span>
            </button>
            <div className="w-px h-3.5 bg-slate-200" />
            <button
              onClick={handleAddAndGateway}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg hover:bg-slate-100 text-slate-700 font-semibold text-[11px] transition-colors cursor-pointer"
              title="Ajouter une passerelle parallèle AND"
            >
              <Plus className="w-3 h-3 text-emerald-600" />
              <span>Parallèle AND</span>
            </button>
          </div>

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            minZoom={0.3}
            maxZoom={1.5}
            fitView
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
      )}

      {/* JSON Schema Form Builder Modal */}
      {formBuilderNode && (
        <MayorFlowFormBuilderModal
          definitionId="circuit_municipal_2026"
          nodeId={formBuilderNode.id}
          nodeName={formBuilderNode.name}
          onClose={() => setFormBuilderNode(null)}
        />
      )}
    </div>
  );
}

export function MayorWorkflowDesigner(props: MayorWorkflowDesignerProps) {
  return (
    <ReactFlowProvider>
      <InnerMayorWorkflowDesigner {...props} />
    </ReactFlowProvider>
  );
}
