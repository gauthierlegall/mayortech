import React, { useState } from 'react';
import { SlidersHorizontal, ArrowRight, CheckCircle2, RotateCcw, Box, Layers, Play, Save, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface PromptResult {
  key: string;
  name: string;
  category: string;
  description: string;
  bpmn_xml: string;
  bpmn_json: {
    nodes: any[];
    edges: any[];
  };
}

interface PromptWorkflowStudioProps {
  onWorkflowSaved?: (def: any) => void;
  onLaunchSimulation?: (workflowData: any) => void;
}

export function PromptWorkflowStudio({ onWorkflowSaved, onLaunchSimulation }: PromptWorkflowStudioProps) {
  const [prompt, setPrompt] = useState<string>(
    "Workflow d'instruction d'un permis de construire avec contrôle de complétude par l'instructeur, consultation ABF, visa de l'Adjoint à l'Urbanisme puis arrêté municipal scellé."
  );
  const [category, setCategory] = useState<string>('urbanisme');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<PromptResult | null>(null);

  const quickChips = [
    {
      label: 'Permis de Construire (ADS)',
      cat: 'urbanisme',
      prompt: "Instruction ADS : complétude instructeur, si complet avis ABF, puis visa Adjoint Urbanisme et génération de l'arrêté scellé.",
    },
    {
      label: 'Commission Marchés (CAO)',
      cat: 'finances',
      prompt: "Adjudication marché public : vérification cahier des charges, si montant > 40000 € passage en séance CAO, puis visa du Maire et notification.",
    },
    {
      label: 'CCAS Secours d’Urgence',
      cat: 'ccas',
      prompt: "Secours CCAS : entretien assistante sociale, si urgence délivrance bon d'urgence DGS, sinon examen commission permanente et mandatement trésorier.",
    },
    {
      label: 'Subvention Associations',
      cat: 'culture',
      prompt: "Campagne subventions : contrôle pièces CERFA service culture, avis commission culture & sport, délibération du Conseil et conventionnement.",
    },
    {
      label: 'Arrêté Voirie & Travaux',
      cat: 'voirie',
      prompt: "Arrêté temporaire de stationnement : avis technique CTM, visa Police Municipale, signature Adjoint aux Travaux et publication registre légal.",
    },
  ];

  const handleGenerate = async (customPrompt?: string, customCat?: string) => {
    const textToUse = customPrompt || prompt;
    const catToUse = customCat || category;
    if (!textToUse || textToUse.length < 5) {
      toast.error('Veuillez décrire le processus attendu en quelques mots.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/v1/workflows/prompt/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux',
        },
        body: JSON.stringify({
          prompt: textToUse,
          category_hint: catToUse,
          base_workflow_id: result?.key ? undefined : undefined,
        }),
      });
      if (!res.ok) {
        throw new Error('Erreur lors de la génération du workflow.');
      }
      const data = await res.json();
      setResult(data);
      toast.success('Diagramme BPMN 2.0 généré et mis en page avec succès !');
    } catch (err: any) {
      toast.error(err.message || 'Impossible de générer le workflow.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToDefinitions = async () => {
    if (!result) return;
    try {
      const res = await fetch('/api/v1/workflows/definitions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux',
        },
        body: JSON.stringify({
          key: result.key,
          name: result.name,
          category: result.category,
          description: result.description,
          bpmn_xml: result.bpmn_xml,
          bpmn_json: result.bpmn_json,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Erreur lors de la sauvegarde.');
      }
      const saved = await res.json();
      toast.success(`Workflow « ${saved.name} » instancié dans MayorFlow !`);
      if (onWorkflowSaved) onWorkflowSaved(saved);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-blue-50 border border-blue-200 text-blue-600">
            <SlidersHorizontal size={22} />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Atelier Prompt-to-BPMN & Auto-Layout Topologique
            </h2>
            <p className="text-xs text-slate-500">
              Décrivez votre circuit municipal en langage naturel. Le moteur extrait le graphe logique,
              résout les embranchements conditionnels (XOR) et calcule les coordonnées orthogonales harmonieuses.
            </p>
          </div>
        </div>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap gap-2 pt-2">
          <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider self-center mr-1">
            Modèles types :
          </span>
          {quickChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => {
                setPrompt(chip.prompt);
                setCategory(chip.cat);
                handleGenerate(chip.prompt, chip.cat);
              }}
              className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 hover:text-blue-700 hover:border-blue-300 hover:bg-blue-50 transition text-[11px]"
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Prompt Input */}
        <div className="lg:col-span-5 bg-white border border-slate-200/90 rounded-2xl p-5 space-y-4 shadow-sm flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label htmlFor="workflow-prompt-text" className="text-xs font-semibold text-slate-700">Description du Processus</label>
              <select
                aria-label="Sélectionner la commission"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="urbanisme">Urbanisme & Cadre de Vie</option>
                <option value="finances">Finances & Administration</option>
                <option value="ccas">Solidarités & CCAS</option>
                <option value="culture">Culture & Patrimoine</option>
                <option value="voirie">Travaux & CTM</option>
                <option value="general">Gouvernance Générale</option>
              </select>
            </div>

            <textarea
              id="workflow-prompt-text"
              aria-label="Description du processus"
              rows={6}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ex: Instruction d'une demande de mouillage au port du Tinduff. Contrôle du navire par le maître de port, puis arbitrage en commission nautique et signature de l'arrêté..."
              className="w-full bg-slate-50/60 border border-slate-200 rounded-xl p-3 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-sans resize-none"
            />

            <div className="flex items-center justify-between pt-1">
              <button
                onClick={() => handleGenerate()}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold transition active:scale-95 text-xs shadow-sm disabled:opacity-50"
              >
                <SlidersHorizontal size={15} />
                <span>{loading ? 'Génération en cours…' : 'Générer le Workflow BPMN'}</span>
              </button>

              {result && (
                <button
                  onClick={() => handleGenerate(prompt + " Ajoute une étape de validation financière si le montant dépasse 15 000 €.")}
                  className="text-xs text-blue-600 hover:text-blue-700 underline font-medium"
                >
                  + Ajouter étape conditionnelle
                </button>
              )}
            </div>
          </div>

          {result && (
            <div className="pt-4 border-t border-slate-100 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900">{result.name}</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 border border-blue-200 font-mono">
                  {result.key}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 line-clamp-2">{result.description}</p>

              <div className="flex items-center gap-2 pt-2">
                <button
                  onClick={handleSaveToDefinitions}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition text-xs shadow-sm"
                >
                  <Save size={14} />
                  <span>Enregistrer dans MayorFlow</span>
                </button>
                {onLaunchSimulation && (
                  <button
                    onClick={() => onLaunchSimulation(result)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 transition text-xs font-semibold"
                  >
                    <Play size={14} />
                    <span>Simuler PixelFlow</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Live BPMN Interactive Graph Preview */}
        <div className="lg:col-span-7 bg-white border border-slate-200/90 rounded-2xl p-4 min-h-[420px] shadow-sm flex flex-col justify-between overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
            <div className="flex items-center gap-2">
              <Layers size={16} className="text-blue-600" />
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Prévisualisation Topologique Sugiyama (BPMN 2.0)
              </span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Départ/Fin
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-blue-500" /> Tâche Agent
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rotate-45 bg-amber-500" /> Passerelle XOR
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-purple-500" /> Scellement SHA-256
              </span>
            </div>
          </div>

          {/* SVG Diagram Canvas */}
          <div className="flex-1 w-full overflow-auto flex items-center justify-center p-2 min-h-[300px] bg-slate-50 border border-slate-200/70 rounded-xl">
            {result ? (
              <svg className="w-full h-[320px] overflow-visible select-none">
                <defs>
                  <marker
                    id="arrowhead-prompt"
                    markerWidth="8"
                    markerHeight="6"
                    refX="7"
                    refY="3"
                    orient="auto"
                  >
                    <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
                  </marker>
                </defs>

                {/* Edges */}
                {result.bpmn_json.edges.map((e: any, i: number) => {
                  const pts = e.waypoints || [];
                  if (pts.length < 2) return null;
                  const pathStr = pts.reduce(
                    (acc: string, pt: any, idx: number) =>
                      idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`,
                    ''
                  );
                  return (
                    <g key={i}>
                      <path
                        d={pathStr}
                        fill="none"
                        stroke="#94a3b8"
                        strokeWidth="2"
                        markerEnd="url(#arrowhead-prompt)"
                      />
                      {e.condition && (
                        <text
                          x={(pts[0].x + pts[1]?.x || 0) / 2}
                          y={pts[0].y - 8}
                          fill="#475569"
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight="bold"
                        >
                          [{e.condition}]
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Nodes */}
                {result.bpmn_json.nodes.map((n: any, i: number) => {
                  const isStart = n.type === 'startEvent';
                  const isEnd = n.type === 'endEvent';
                  const isGateway = n.type === 'exclusiveGateway' || n.type === 'parallelGateway';
                  const isService = n.type === 'serviceTask';

                  if (isStart || isEnd) {
                    return (
                      <g key={i} transform={`translate(${n.x}, ${n.y})`}>
                        <circle
                          r="18"
                          cx="18"
                          cy="18"
                          fill={isStart ? '#ecfdf5' : '#fff1f2'}
                          stroke={isStart ? '#10b981' : '#f43f5e'}
                          strokeWidth="2"
                        />
                        <text
                          x="18"
                          y="48"
                          fill="#334155"
                          fontSize="9"
                          fontWeight="bold"
                          textAnchor="middle"
                        >
                          {n.name}
                        </text>
                      </g>
                    );
                  }

                  if (isGateway) {
                    return (
                      <g key={i} transform={`translate(${n.x}, ${n.y})`}>
                        <rect
                          x="0"
                          y="0"
                          width="36"
                          height="36"
                          transform="rotate(45 18 18)"
                          fill="#fffbeb"
                          stroke="#f59e0b"
                          strokeWidth="2"
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
                    <g key={i} transform={`translate(${n.x}, ${n.y})`}>
                      <rect
                        width="150"
                        height="64"
                        rx="8"
                        fill="#ffffff"
                        stroke={isService ? '#c084fc' : '#93c5fd'}
                        strokeWidth="1.5"
                      />
                      <rect
                        x="0"
                        y="0"
                        width="5"
                        height="64"
                        rx="2"
                        fill={isService ? '#a855f7' : '#3b82f6'}
                      />
                      <text x="14" y="20" fill="#0f172a" fontSize="10" fontWeight="bold">
                        {n.name.length > 20 ? n.name.slice(0, 18) + '…' : n.name}
                      </text>
                      <text x="14" y="38" fill="#64748b" fontSize="8">
                        Rôle : {n.role || (isService ? 'Service Auto' : 'Agent')}
                      </text>
                      <text x="14" y="52" fill={isService ? '#7e22ce' : '#1d4ed8'} fontSize="8" fontFamily="monospace">
                        {isService ? 'Scellement SHA-256' : `SLA: ${n.sla_hours || 48}h`}
                      </text>
                    </g>
                  );
                })}
              </svg>
            ) : (
              <div className="text-center py-12 text-slate-400 space-y-2">
                <Box size={36} className="mx-auto text-slate-300 opacity-60" />
                <p className="text-xs">Tapez une description à gauche ou choisissez un modèle type pour voir le diagramme se construire.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
