import React, { useState, useRef } from 'react';
import {
  Download,
  Plus,
  Trash2,
  Settings2,
  FileCode,
  Play,
  Layers,
  Save,
  CheckCircle2,
  FormInput,
  ZoomIn,
  ZoomOut,
  Maximize2
} from 'lucide-react';
import { toast } from 'sonner';
import { MayorFlowFormBuilderModal } from './MayorFlowFormBuilderModal';

interface StudioNode {
  id: string;
  type: 'startEvent' | 'userTask' | 'serviceTask' | 'exclusiveGateway' | 'parallelGateway' | 'endEvent';
  name: string;
  role?: string;
  commission?: string;
  sla_hours?: number;
  action?: string;
  x: number;
  y: number;
}

interface StudioEdge {
  id: string;
  sourceRef: string;
  targetRef: string;
  condition?: string;
}

export function MayorFlowStudioCanvas({ onLaunchSimulation }: { onLaunchSimulation?: (data: any) => void }) {
  const [nodes, setNodes] = useState<StudioNode[]>([
    { id: 'start', type: 'startEvent', name: 'Dépôt CERFA ADS', x: 80, y: 140 },
    { id: 'task_completude', type: 'userTask', name: 'Contrôle de complétude', role: 'instructeur_ads', commission: 'urbanisme', sla_hours: 48, x: 220, y: 120 },
    { id: 'gate_1', type: 'exclusiveGateway', name: 'Dossier complet ?', x: 440, y: 135 },
    { id: 'task_abf', type: 'userTask', name: 'Consultation ABF', role: 'abf_consultant', commission: 'urbanisme', sla_hours: 72, x: 550, y: 120 },
    { id: 'service_seal', type: 'serviceTask', name: 'Scellement SHA-256', action: 'seal_decision_hash', x: 770, y: 120 },
    { id: 'end', type: 'endEvent', name: 'Arrêté notifié', x: 990, y: 140 },
  ]);

  const [edges, setEdges] = useState<StudioEdge[]>([
    { id: 'f1', sourceRef: 'start', targetRef: 'task_completude' },
    { id: 'f2', sourceRef: 'task_completude', targetRef: 'gate_1' },
    { id: 'f3', sourceRef: 'gate_1', targetRef: 'task_abf', condition: 'pieces_completes == True' },
    { id: 'f4', sourceRef: 'task_abf', targetRef: 'service_seal' },
    { id: 'f5', sourceRef: 'service_seal', targetRef: 'end' },
  ]);

  const [selectedNode, setSelectedNode] = useState<StudioNode | null>(null);
  const [formBuilderNode, setFormBuilderNode] = useState<StudioNode | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [connectingFrom, setConnectingFrom] = useState<string | null>(null);

  const [zoom, setZoom] = useState<number>(1);

  // Add new element from palette
  const addElement = (type: StudioNode['type']) => {
    const id = `node_${Date.now()}`;
    const newNode: StudioNode = {
      id,
      type,
      name:
        type === 'startEvent'
          ? 'Départ'
          : type === 'endEvent'
          ? 'Fin'
          : type === 'exclusiveGateway'
          ? 'XOR Décision'
          : type === 'serviceTask'
          ? 'Tâche Service Auto'
          : 'Tâche Agent',
      x: 300 + Math.random() * 80,
      y: 140 + Math.random() * 60,
      sla_hours: type === 'userTask' ? 48 : 0,
      role: type === 'userTask' ? 'instructeur_communal' : undefined,
    };
    setNodes([...nodes, newNode]);
    setSelectedNode(newNode);
    toast.info(`Nœud « ${newNode.name} » ajouté.`);
  };

  const removeSelectedNode = () => {
    if (!selectedNode) return;
    setNodes(nodes.filter((n) => n.id !== selectedNode.id));
    setEdges(edges.filter((e) => e.sourceRef !== selectedNode.id && e.targetRef !== selectedNode.id));
    setSelectedNode(null);
    toast.info('Nœud supprimé.');
  };

  // Node Drag handlers
  const handleMouseDown = (node: StudioNode, e: React.MouseEvent) => {
    if (connectingFrom) {
      if (connectingFrom !== node.id) {
        // Create edge
        const newEdge: StudioEdge = {
          id: `flow_${connectingFrom}_${node.id}`,
          sourceRef: connectingFrom,
          targetRef: node.id,
        };
        setEdges([...edges, newEdge]);
        toast.success(`Liaison créée entre ${connectingFrom} et ${node.name}.`);
      }
      setConnectingFrom(null);
      return;
    }
    setSelectedNode(node);
    setDraggingNodeId(node.id);
    setDragOffset({ x: e.clientX - node.x, y: e.clientY - node.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggingNodeId) return;
    setNodes((prev) =>
      prev.map((n) => {
        if (n.id === draggingNodeId) {
          return {
            ...n,
            x: Math.max(20, e.clientX - dragOffset.x),
            y: Math.max(20, e.clientY - dragOffset.y),
          };
        }
        return n;
      })
    );
  };

  const handleMouseUp = () => {
    setDraggingNodeId(null);
  };

  // Export BPMN 2.0 XML
  const handleExportBpmnXml = () => {
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Definitions_1" targetNamespace="http://mayortech.fr/bpmn">
  <bpmn:process id="Process_Plougastel" isExecutable="true">
${nodes.map((n) => `    <bpmn:${n.type} id="${n.id}" name="${n.name}" />`).join('\n')}
${edges.map((e) => `    <bpmn:sequenceFlow id="${e.id}" sourceRef="${e.sourceRef}" targetRef="${e.targetRef}" />`).join('\n')}
  </bpmn:process>
</bpmn:definitions>`;

    const blob = new Blob([xml], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-plougastel-${Date.now()}.bpmn`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Fichier standard ISO/IEC 19510 BPMN 2.0 téléchargé avec succès !');
  };

  return (
    <div className="space-y-4 font-sans select-none" onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}>
      {/* Top Controls Bar */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
        {/* Palette Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1">
            Palette :
          </span>
          <button
            onClick={() => addElement('startEvent')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 text-xs font-semibold transition"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>Début</span>
          </button>
          <button
            onClick={() => addElement('userTask')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition"
          >
            <span className="w-2.5 h-2.5 rounded bg-blue-500" />
            <span>Tâche Agent</span>
          </button>
          <button
            onClick={() => addElement('serviceTask')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-50 border border-purple-200 text-purple-700 hover:bg-purple-100 text-xs font-semibold transition"
          >
            <span className="w-2.5 h-2.5 rounded bg-purple-500" />
            <span>Service SHA-256</span>
          </button>
          <button
            onClick={() => addElement('exclusiveGateway')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 hover:bg-amber-100 text-xs font-semibold transition"
          >
            <span className="w-2.5 h-2.5 rotate-45 bg-amber-500" />
            <span>XOR Décision</span>
          </button>
          <button
            onClick={() => addElement('endEvent')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100 text-xs font-semibold transition"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <span>Fin</span>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setConnectingFrom(selectedNode?.id || null)}
            disabled={!selectedNode}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition ${
              connectingFrom
                ? 'bg-blue-50 text-blue-700 border-blue-400 animate-pulse'
                : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 disabled:opacity-40'
            }`}
          >
            <Plus size={13} />
            <span>{connectingFrom ? 'Cliquez sur la cible…' : 'Lier Nœud'}</span>
          </button>

          <button
            onClick={handleExportBpmnXml}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition"
          >
            <Download size={13} />
            <span>Export BPMN 2.0 (XML)</span>
          </button>

          {onLaunchSimulation && (
            <button
              onClick={() => onLaunchSimulation({ nodes, edges })}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-sm transition active:scale-95"
            >
              <Play size={13} />
              <span>Simuler PixelFlow</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Studio Viewport */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* SVG Canvas */}
        <div className="lg:col-span-9 bg-slate-50 border border-slate-200 rounded-2xl relative min-h-[500px] overflow-hidden shadow-xs">
          {/* Subtle dots grid */}
          <div className="absolute inset-0 bg-[radial-gradient(#cbd5e1_1.2px,transparent_1.2px)] [background-size:20px_20px] pointer-events-none" />

          {/* SVG Modeler */}
          <svg className="w-full h-[520px] cursor-grab active:cursor-grabbing">
            <defs>
              <marker id="arrow-studio" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
              </marker>
            </defs>

            {/* Render Edges */}
            {edges.map((e) => {
              const fromN = nodes.find((n) => n.id === e.sourceRef);
              const toN = nodes.find((n) => n.id === e.targetRef);
              if (!fromN || !toN) return null;

              const x1 = fromN.x + (fromN.type in { startEvent: 1, endEvent: 1 } ? 18 : 75);
              const y1 = fromN.y + (fromN.type in { startEvent: 1, endEvent: 1 } ? 18 : 32);
              const x2 = toN.x;
              const y2 = toN.y + (toN.type in { startEvent: 1, endEvent: 1 } ? 18 : 32);

              return (
                <g key={e.id}>
                  <path
                    d={`M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`}
                    fill="none"
                    stroke="#94a3b8"
                    strokeWidth="2"
                    markerEnd="url(#arrow-studio)"
                  />
                  {e.condition && (
                    <text
                      x={(x1 + x2) / 2}
                      y={(y1 + y2) / 2 - 8}
                      fill="#475569"
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {e.condition}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Render Nodes */}
            {nodes.map((n) => {
              const isSelected = selectedNode?.id === n.id;
              const isStart = n.type === 'startEvent';
              const isEnd = n.type === 'endEvent';
              const isGateway = n.type === 'exclusiveGateway' || n.type === 'parallelGateway';
              const isService = n.type === 'serviceTask';

              if (isStart || isEnd) {
                return (
                  <g
                    key={n.id}
                    data-node-id={n.id}
                    transform={`translate(${n.x}, ${n.y})`}
                    onMouseDown={(e) => handleMouseDown(n, e)}
                    className="cursor-move"
                  >
                    <circle
                      r="18"
                      cx="18"
                      cy="18"
                      fill={isStart ? '#ecfdf5' : '#fff1f2'}
                      stroke={isSelected ? '#3b82f6' : isStart ? '#10b981' : '#f43f5e'}
                      strokeWidth={isSelected ? 3 : 2}
                    />
                    <text x="18" y="48" fill="#1e293b" fontSize="9" fontWeight="bold" textAnchor="middle">
                      {n.name}
                    </text>
                  </g>
                );
              }

              if (isGateway) {
                return (
                  <g
                    key={n.id}
                    data-node-id={n.id}
                    transform={`translate(${n.x}, ${n.y})`}
                    onMouseDown={(e) => handleMouseDown(n, e)}
                    className="cursor-move"
                  >
                    <rect
                      x="0"
                      y="0"
                      width="36"
                      height="36"
                      transform="rotate(45 18 18)"
                      fill="#fffbeb"
                      stroke={isSelected ? '#3b82f6' : '#f59e0b'}
                      strokeWidth={isSelected ? 3 : 2}
                    />
                    <text x="18" y="22" fill="#b45309" fontSize="12" fontWeight="bold" textAnchor="middle">
                      X
                    </text>
                    <text x="18" y="58" fill="#92400e" fontSize="9" fontWeight="bold" textAnchor="middle">
                      {n.name}
                    </text>
                  </g>
                );
              }

              return (
                <g
                  key={n.id}
                  data-node-id={n.id}
                  transform={`translate(${n.x}, ${n.y})`}
                  onMouseDown={(e) => handleMouseDown(n, e)}
                  className="cursor-move"
                >
                  <rect
                    width="150"
                    height="64"
                    rx="10"
                    fill="#ffffff"
                    stroke={isSelected ? '#3b82f6' : isService ? '#c084fc' : '#cbd5e1'}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                  />
                  <rect x="0" y="0" width="5" height="64" rx="2" fill={isService ? '#a855f7' : '#3b82f6'} />
                  <text x="14" y="22" fill="#0f172a" fontSize="11" fontWeight="bold">
                    {n.name.length > 18 ? n.name.slice(0, 16) + '…' : n.name}
                  </text>
                  <text x="14" y="38" fill="#64748b" fontSize="8">
                    {n.role || (isService ? 'Service SHA-256' : 'Instructeur')}
                  </text>
                  <text x="14" y="52" fill={isService ? '#7e22ce' : '#1d4ed8'} fontSize="8" fontFamily="monospace">
                    {isService ? 'Scellement Auto' : `SLA: ${n.sla_hours || 48}h`}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Right Property Inspector Panel */}
        <div className="lg:col-span-3 bg-white border border-slate-200/90 rounded-2xl p-4 space-y-4 text-xs text-slate-700 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div className="flex items-center gap-1.5 font-bold text-slate-900">
              <Settings2 size={15} className="text-blue-600" />
              <span>Propriétés du Nœud</span>
            </div>
            {selectedNode && (
              <button
                onClick={removeSelectedNode}
                className="p-1 text-slate-400 hover:text-rose-600 rounded transition"
                title="Supprimer ce nœud"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>

          {selectedNode ? (
            <div className="space-y-3">
              <div className="space-y-1">
                <label htmlFor="studio-node-name" className="text-[10px] text-slate-500 uppercase tracking-wider block">Nom du nœud</label>
                <input
                  id="studio-node-name"
                  type="text"
                  value={selectedNode.name}
                  onChange={(e) => {
                    const updated = { ...selectedNode, name: e.target.value };
                    setSelectedNode(updated);
                    setNodes(nodes.map((n) => (n.id === updated.id ? updated : n)));
                  }}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              {selectedNode.type === 'userTask' && (
                <>
                  <div className="space-y-1">
                    <label htmlFor="studio-node-role" className="text-[10px] text-slate-500 uppercase tracking-wider block">Rôle assigné</label>
                    <input
                      id="studio-node-role"
                      type="text"
                      value={selectedNode.role || ''}
                      onChange={(e) => {
                        const updated = { ...selectedNode, role: e.target.value };
                        setSelectedNode(updated);
                        setNodes(nodes.map((n) => (n.id === updated.id ? updated : n)));
                      }}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <label htmlFor="studio-node-sla" className="text-[10px] text-slate-500 uppercase tracking-wider block">Délai SLA (heures)</label>
                    <input
                      id="studio-node-sla"
                      type="number"
                      value={selectedNode.sla_hours || 48}
                      onChange={(e) => {
                        const updated = { ...selectedNode, sla_hours: parseInt(e.target.value) || 48 };
                        setSelectedNode(updated);
                        setNodes(nodes.map((n) => (n.id === updated.id ? updated : n)));
                      }}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <button
                    onClick={() => setFormBuilderNode(selectedNode)}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 transition font-semibold text-xs mt-2"
                  >
                    <FormInput size={14} />
                    <span>Éditer Formulaire JSON</span>
                  </button>
                </>
              )}

              {selectedNode.type === 'serviceTask' && (
                <div className="space-y-1">
                  <label htmlFor="studio-node-action" className="text-[10px] text-slate-500 uppercase tracking-wider block">Action Python Automatisée</label>
                  <select
                    id="studio-node-action"
                    value={selectedNode.action || 'seal_decision_hash'}
                    onChange={(e) => {
                      const updated = { ...selectedNode, action: e.target.value };
                      setSelectedNode(updated);
                      setNodes(nodes.map((n) => (n.id === updated.id ? updated : n)));
                    }}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-900 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="seal_decision_hash">Scellement SHA-256 Intégrité</option>
                    <option value="generate_decision_pdf">Génération Arrêté PDF/A</option>
                    <option value="notify_commission_members">Notification Push Élus</option>
                    <option value="publish_to_display">Affichage Légal Municipal</option>
                  </select>
                </div>
              )}
            </div>
          ) : (
            <p className="text-slate-400 text-xs italic">
              Cliquez sur un élément du canvas pour configurer ses paramètres métier.
            </p>
          )}
        </div>
      </div>

      {/* Form Builder Modal */}
      {formBuilderNode && (
        <MayorFlowFormBuilderModal
          definitionId="urbanisme_ads"
          nodeId={formBuilderNode.id}
          nodeName={formBuilderNode.name}
          onClose={() => setFormBuilderNode(null)}
        />
      )}
    </div>
  );
}
