import React, { useState, useEffect, useRef } from 'react';
import { 
  Building2, ZoomIn, ZoomOut, RotateCcw, Download, Printer, 
  Search, Shield, Eye, Filter, Users, RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PositionProfileDrawer, OrganigramNode } from './PositionProfileDrawer';

interface OrganigramTopology {
  city: string;
  generated_at: string;
  total_nodes: number;
  total_links: number;
  active_delegations_count: number;
  nodes: OrganigramNode[];
  links: { source: string; target: string; type: string }[];
}

export function MunicipalOrganigramCanvas() {
  const [topology, setTopology] = useState<OrganigramTopology | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<OrganigramNode | null>(null);
  const [activeCommissionFilter, setActiveCommissionFilter] = useState('all');

  // Zoom & Pan state (y: 80 to position Maire node neatly below floating bar)
  const [scale, setScale] = useState(0.85);
  const [pan, setPan] = useState({ x: 20, y: 150 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const canvasRef = useRef<HTMLDivElement>(null);

  const fetchTopology = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/municipal/organigram/topology');
      if (!res.ok) throw new Error('Impossible de charger la topologie de l’organigramme.');
      const data: OrganigramTopology = await res.json();
      setTopology(data);
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement de l’organigramme.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopology();
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleZoom = (delta: number) => {
    setScale(prev => Math.min(Math.max(0.4, prev + delta), 2.0));
  };

  const resetView = () => {
    setScale(0.85);
    setPan({ x: 20, y: 150 });
  };

  const handleExportSVG = async () => {
    try {
      const res = await fetch('/api/v1/municipal/organigram/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux'
        },
        body: JSON.stringify({ format: 'svg' })
      });
      if (!res.ok) throw new Error('Erreur lors de la génération de l’export SVG');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `organigramme-plougastel-${new Date().toISOString().split('T')[0]}.svg`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handlePrintA3 = () => {
    window.open('/api/v1/municipal/organigram/export?format=html', '_blank');
  };

  const filteredNodes = (topology?.nodes || []).filter(n => {
    if (activeCommissionFilter === 'all') return true;
    if (n.id === 'node-maire' || n.id === 'node-dgs') return true;
    if (activeCommissionFilter === 'commission-1' && (n.color === '#c2410c')) return true;
    if (activeCommissionFilter === 'commission-2' && (n.color === '#be185d')) return true;
    if (activeCommissionFilter === 'commission-3' && (n.color === '#15803d')) return true;
    if (activeCommissionFilter === 'commission-4' && (n.color === '#6b21a8')) return true;
    return false;
  });

  const nodeMap = new Map((topology?.nodes || []).map(n => [n.id, n]));

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] bg-slate-900 select-none overflow-hidden relative cursor-grab active:cursor-grabbing">
      {/* Top Floating Control Bar */}
      <div className="absolute top-4 left-4 right-4 z-20 flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 backdrop-blur-md p-2.5 sm:p-3 rounded-xl border border-slate-700/80 shadow-2xl">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="p-1.5 sm:p-2 bg-blue-600/30 text-blue-400 rounded-lg border border-blue-500/30">
            <Building2 className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div>
            <h1 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-2">
              <span className="hidden sm:inline">Organigramme Réglementaire · Ville de Plougastel-Daoulas</span>
              <span className="sm:hidden">Organigramme Plougastel</span>
              <span className="text-[9px] sm:text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Certifié DGS
              </span>
            </h1>
            <p className="text-[10px] sm:text-[11px] text-slate-400">
              Navigation vectorielle · {topology?.total_nodes || 0} entités & commissions
            </p>
          </div>
        </div>

        {/* Filter Chips */}
        <div className="hidden lg:flex items-center gap-1.5 bg-slate-800/80 p-1 rounded-lg border border-slate-700">
          <button
            onClick={() => setActiveCommissionFilter('all')}
            className={`text-xs px-2.5 py-1 rounded-md transition-all font-medium ${
              activeCommissionFilter === 'all'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            Tous les Pôles
          </button>
          <button
            onClick={() => setActiveCommissionFilter('commission-1')}
            className={`text-xs px-2.5 py-1 rounded-md transition-all font-medium ${
              activeCommissionFilter === 'commission-1'
                ? 'bg-orange-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            1. Finances & CAO
          </button>
          <button
            onClick={() => setActiveCommissionFilter('commission-2')}
            className={`text-xs px-2.5 py-1 rounded-md transition-all font-medium ${
              activeCommissionFilter === 'commission-2'
                ? 'bg-pink-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            2. Enfance & CCAS
          </button>
          <button
            onClick={() => setActiveCommissionFilter('commission-3')}
            className={`text-xs px-2.5 py-1 rounded-md transition-all font-medium ${
              activeCommissionFilter === 'commission-3'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            3. Urbanisme & Ports
          </button>
          <button
            onClick={() => setActiveCommissionFilter('commission-4')}
            className={`text-xs px-2.5 py-1 rounded-md transition-all font-medium ${
              activeCommissionFilter === 'commission-4'
                ? 'bg-purple-600 text-white shadow-xs'
                : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            4. Culture & Asso
          </button>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5 border border-slate-700">
            <button
              onClick={() => handleZoom(0.1)}
              className="p-1.5 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors"
              title="Zoom avant"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <span className="text-[10px] font-mono px-2 text-slate-300">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={() => handleZoom(-0.1)}
              className="p-1.5 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors"
              title="Zoom arrière"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={resetView}
              className="p-1.5 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors border-l border-slate-700 ml-0.5"
              title="Réinitialiser la vue"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportSVG}
            className="text-xs h-8 bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"
            title="Télécharger en format vectoriel SVG certifié"
          >
            <Download className="w-3.5 h-3.5 mr-1" />
            SVG
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handlePrintA3}
            className="text-xs h-8 bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"
            title="Affichage et impression grand format A3 officiel"
          >
            <Printer className="w-3.5 h-3.5 mr-1" />
            Imprimer A3
          </Button>
        </div>
      </div>

      {/* Interactive SVG Canvas Area */}
      <div 
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`flex-1 w-full h-full cursor-grab active:cursor-grabbing relative overflow-hidden`}
        style={{
          backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px)',
          backgroundSize: '24px 24px'
        }}
      >
        <div 
          className="origin-top-left transition-transform duration-75 ease-out"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`
          }}
        >
          <svg width="1350" height="950" className="overflow-visible">
            {/* Draw links */}
            <g id="canvas-links">
              {(topology?.links || []).map((link, idx) => {
                const src = nodeMap.get(link.source);
                const tgt = nodeMap.get(link.target);
                if (!src || !tgt) return null;

                // Check filter
                if (activeCommissionFilter !== 'all') {
                  const srcMatch = filteredNodes.some(n => n.id === src.id);
                  const tgtMatch = filteredNodes.some(n => n.id === tgt.id);
                  if (!srcMatch || !tgtMatch) return null;
                }

                const sx = (src as any).x !== undefined ? (src as any).x + 110 : 0;
                const sy = (src as any).y !== undefined ? (src as any).y + 55 : 0;
                const tx = (tgt as any).x !== undefined ? (tgt as any).x + 110 : 0;
                const ty = (tgt as any).y !== undefined ? (tgt as any).y : 0;

                const pathData = `M ${sx} ${sy} C ${sx} ${(sy + ty) / 2}, ${tx} ${(sy + ty) / 2}, ${tx} ${ty}`;

                return (
                  <path
                    key={`link-${idx}`}
                    d={pathData}
                    fill="none"
                    stroke={tgt.color || '#64748b'}
                    strokeWidth="2.5"
                    strokeDasharray={link.type === 'functional' ? '5 5' : 'none'}
                    className="opacity-75 hover:opacity-100 transition-opacity"
                  />
                );
              })}
            </g>

            {/* Draw nodes */}
            <g id="canvas-nodes">
              {filteredNodes.map(node => {
                const x = (node as any).x || 100;
                const y = (node as any).y || 100;
                const isSelected = selectedNode?.id === node.id;

                return (
                  <g
                    key={node.id}
                    data-node-id={node.id}
                    transform={`translate(${x}, ${y})`}
                    onClick={() => setSelectedNode(node)}
                    className="cursor-pointer group"
                  >
                    {/* Node Card Background */}
                    <rect
                      width="220"
                      height="65"
                      rx="8"
                      fill="#1e293b"
                      stroke={isSelected ? '#38bdf8' : node.color}
                      strokeWidth={isSelected ? '3' : '2'}
                      className="group-hover:brightness-125 transition-all shadow-xl"
                    />

                    {/* Left Accent Stripe */}
                    <rect
                      x="0"
                      y="0"
                      width="6"
                      height="65"
                      rx="3"
                      fill={node.color}
                    />

                    {/* Node Text Content */}
                    <text
                      x="14"
                      y="18"
                      fontSize="10"
                      fontWeight="bold"
                      fill={node.color}
                      className="uppercase tracking-wider font-mono"
                    >
                      {node.title.slice(0, 30)}
                    </text>

                    <text
                      x="14"
                      y="36"
                      fontSize="13"
                      fontWeight="600"
                      fill="#f8fafc"
                    >
                      {node.holder}
                    </text>

                    <text
                      x="14"
                      y="52"
                      fontSize="10"
                      fill="#94a3b8"
                      className="font-mono"
                    >
                      {node.matricule} · Niveau {node.niveau} ({node.role})
                    </text>

                    {/* Indicator Badge */}
                    {node.delegation_signature && (
                      <circle
                        cx="205"
                        cy="16"
                        r="5"
                        fill="#10b981"
                        className=""
                      />
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
        </div>
      </div>

      {/* Profile Drawer Component */}
      <PositionProfileDrawer
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}
