import React, { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle2, Flame, RefreshCw, ShieldAlert, Users, Clock, ArrowUpRight } from 'lucide-react';
import { toast } from 'sonner';

interface WatchMetrics {
  active_instances: number;
  completed_instances: number;
  terminated_instances: number;
  sla_breaches: number;
  node_heatmap: {
    node_id: string;
    node_name: string;
    workflow_name: string;
    count: number;
    severity: 'normal' | 'warning' | 'bottleneck';
  }[];
  timestamp: string;
}

export function MayorFlowWatchDashboard() {
  const [metrics, setMetrics] = useState<WatchMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [reallocating, setReallocating] = useState<boolean>(false);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/workflows/watch/metrics');
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const handleDgsEmergencyReallocation = async () => {
    setReallocating(true);
    try {
      const res = await fetch('/api/v1/workflows/timers/check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux',
        },
      });
      if (!res.ok) throw new Error('Erreur lors de la réattribution DGS.');
      const data = await res.json();
      toast.success(
        `Réattribution d'urgence exécutée : ${data.escalated_count} tâche(s) en goulot réassignée(s) à la DGS.`
      );
      fetchMetrics();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setReallocating(false);
    }
  };

  return (
    <div className="space-y-4 font-sans">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-600">
            <Activity size={22} />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              MayorFlow Watch — Supervision BAM & Heatmap des Goulots
            </h2>
            <p className="text-xs text-slate-500">
              Tableau de bord de pilotage régalien pour la DGS et les Élus. Détectez les points de blocage et régulez la charge communale.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchMetrics}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 hover:text-slate-900 hover:bg-slate-100 text-xs transition"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Actualiser</span>
          </button>

          <button
            onClick={handleDgsEmergencyReallocation}
            disabled={reallocating}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs shadow-sm transition active:scale-95 disabled:opacity-50"
          >
            <ShieldAlert size={14} />
            <span>{reallocating ? 'Réattribution…' : 'Réattribution DGS d’Urgence'}</span>
          </button>
        </div>
      </div>

      {/* KPI Bento Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Dossiers En Cours
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-blue-600 tabular-nums">
              {metrics?.active_instances ?? 0}
            </span>
            <span className="text-[11px] text-slate-500 font-medium">actifs</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Dossiers Clôturés
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-emerald-600 tabular-nums">
              {metrics?.completed_instances ?? 0}
            </span>
            <span className="text-[11px] text-slate-500 font-medium">scellés</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Dépassements SLA
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-rose-600 tabular-nums">
              {metrics?.sla_breaches ?? 0}
            </span>
            <span className="text-[11px] text-slate-500 font-medium">urgences</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Délai Moyen Ville
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-amber-600 tabular-nums">1.8</span>
            <span className="text-[11px] text-slate-500 font-medium">jours / dossier</span>
          </div>
        </div>
      </div>

      {/* Thermal Heatmap of Bottlenecks */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Flame size={18} className="text-rose-500" />
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">
              Heatmap Thermique des Étapes & Files d'Attente
            </h3>
          </div>
          <div className="flex items-center gap-3 text-[11px] font-medium">
            <span className="flex items-center gap-1.5 text-emerald-800">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-2xs" /> Fluide (0-2)
            </span>
            <span className="flex items-center gap-1.5 text-amber-800">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-2xs" /> Vigilance (3-5)
            </span>
            <span className="flex items-center gap-1.5 text-rose-800">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-2xs" /> Goulot Critique (&gt;5)
            </span>
          </div>
        </div>

        {/* Heatmap Nodes Table */}
        <div className="space-y-2">
          {metrics?.node_heatmap && metrics.node_heatmap.length > 0 ? (
            metrics.node_heatmap.map((node, i) => {
              const isBottleneck = node.severity === 'bottleneck';
              const isWarning = node.severity === 'warning';
              return (
                <div
                  key={i}
                  className={`flex items-center justify-between p-3 rounded-xl border transition ${
                    isBottleneck
                      ? 'bg-rose-50/70 border-rose-200 text-rose-900'
                      : isWarning
                      ? 'bg-amber-50/70 border-amber-200 text-amber-900'
                      : 'bg-slate-50 border-slate-200/80 text-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold font-mono ${
                        isBottleneck
                          ? 'bg-rose-600 text-white'
                          : isWarning
                          ? 'bg-amber-500 text-white'
                          : 'bg-white border border-slate-200 text-slate-700 shadow-2xs'
                      }`}
                    >
                      {node.count}
                    </span>
                    <div>
                      <span className="font-bold text-slate-900 block text-xs">{node.node_name}</span>
                      <span className="text-[11px] text-slate-500 block font-sans">
                        {node.workflow_name}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        isBottleneck
                          ? 'bg-rose-100 text-rose-700 border border-rose-200'
                          : isWarning
                          ? 'bg-amber-100 text-amber-700 border border-amber-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}
                    >
                      {isBottleneck ? 'Goulot Bloquant' : isWarning ? 'Tension Modérée' : 'Débit Optimal'}
                    </span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="py-8 text-center text-slate-400 text-xs">
              Aucun goulot d'étranglement détecté sur les circuits actifs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
