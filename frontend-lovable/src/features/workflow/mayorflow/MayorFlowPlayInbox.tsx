import React, { useState, useEffect } from 'react';
import { Inbox, CheckCircle2, Clock, AlertTriangle, ShieldCheck, User, Search, Filter, ArrowUpRight, Play, RefreshCw, HandMetal } from 'lucide-react';
import { toast } from 'sonner';
import { MayorFlowTaskExecutionModal } from './MayorFlowTaskExecutionModal';

export function MayorFlowPlayInbox() {
  const [activeTab, setActiveTab] = useState<'my_tasks' | 'service_pool' | 'initiated' | 'completed'>('my_tasks');
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [commissionFilter, setCommissionFilter] = useState<string>('all');
  const [executingTask, setExecutingTask] = useState<any | null>(null);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/workflows/tasks/inbox');
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleClaim = async (task: any) => {
    try {
      const res = await fetch(`/api/v1/workflows/tasks/${task.id}/claim`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux',
        },
      });
      if (!res.ok) {
        throw new Error('Erreur lors de la prise en charge.');
      }
      toast.success(`Tâche « ${task.node_name} » prise en charge avec succès !`);
      fetchTasks();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  // Filter tasks based on activeTab, search, commission
  const filteredTasks = tasks.filter((t) => {
    if (commissionFilter !== 'all' && t.assigned_commission && t.assigned_commission !== commissionFilter) {
      return false;
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchKey = (t.business_key || '').toLowerCase().includes(q);
      const matchName = (t.node_name || '').toLowerCase().includes(q);
      const matchWf = (t.workflow_name || '').toLowerCase().includes(q);
      if (!matchKey && !matchName && !matchWf) return false;
    }
    if (activeTab === 'service_pool') {
      return !t.assigned_user_id;
    }
    if (activeTab === 'my_tasks') {
      return !!t.assigned_user_id || true; // In demo show available
    }
    return true;
  });

  return (
    <div className="space-y-4 font-sans">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-50 border border-blue-200 text-blue-600">
            <Inbox size={22} />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              MayorFlow Play — Boîte de Réception des Tâches Métier
            </h2>
            <p className="text-xs text-slate-500">
              Interface souveraine de traitement des dossiers communaux. Suivez vos délais réglementaires et traitez vos visas en direct.
            </p>
          </div>
        </div>

        <button
          onClick={fetchTasks}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 hover:text-slate-900 hover:bg-slate-100 text-xs transition"
          title="Actualiser les tâches"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          <span>Actualiser</span>
        </button>
      </div>

      {/* Tabs and Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        {/* Tabs */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/70">
          <button
            onClick={() => setActiveTab('my_tasks')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'my_tasks'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Mes Tâches ({tasks.length})
          </button>
          <button
            onClick={() => setActiveTab('service_pool')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'service_pool'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Pool du Service (Non assignées)
          </button>
          <button
            onClick={() => setActiveTab('initiated')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'initiated'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Dossiers Initiés
          </button>
          <button
            onClick={() => setActiveTab('completed')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'completed'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Historique Clôturé
          </button>
        </div>

        {/* Search & Commission Filter */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Rechercher par réf ou intitulé…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-white border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 w-48 shadow-2xs"
            />
          </div>

          <select
            aria-label="Filtrer par commission"
            value={commissionFilter}
            onChange={(e) => setCommissionFilter(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-2xs"
          >
            <option value="all">Toutes Commissions</option>
            <option value="urbanisme">Urbanisme & Cadre de Vie</option>
            <option value="finances">Finances & Marchés</option>
            <option value="social">Solidarités CCAS</option>
            <option value="culture">Culture & Patrimoine</option>
            <option value="voirie">Travaux & CTM</option>
          </select>
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-2.5">
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            Chargement des tâches en cours…
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-500 space-y-2 shadow-sm">
            <CheckCircle2 size={36} className="mx-auto text-emerald-500" />
            <p className="text-sm font-semibold text-slate-800">Aucune tâche en attente dans cette boîte</p>
            <p className="text-xs text-slate-500">Toutes les instructions de votre service sont à jour.</p>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              className="bg-white hover:bg-slate-50/80 border border-slate-200/90 hover:border-blue-400 rounded-xl p-4 transition flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xs"
            >
              {/* Task Details */}
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 border border-blue-200 font-mono font-bold">
                    {task.business_key || 'DOSSIER-MUNICIPAL'}
                  </span>
                  <span className="text-[11px] font-semibold text-slate-600">
                    {task.workflow_name || 'Workflow Communal'}
                  </span>
                  <span className="text-slate-300">•</span>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-slate-100 text-slate-700 border border-slate-200/70">
                    Commission {task.assigned_commission || 'Générale'}
                  </span>

                  {/* Urgency SLA Badge */}
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold font-mono">
                    <Clock size={11} />
                    <span>SLA : 48h ouvrées</span>
                  </span>
                </div>

                <h3 className="text-sm font-bold text-slate-900 tracking-tight">{task.node_name}</h3>
                <p className="text-xs text-slate-500">
                  {task.instance_title || 'Instruction administrative pour la commune de Plougastel-Daoulas'}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                {!task.assigned_user_id && (
                  <button
                    onClick={() => handleClaim(task)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition"
                  >
                    <HandMetal size={13} />
                    <span>Prendre en charge</span>
                  </button>
                )}

                <button
                  onClick={() => setExecutingTask(task)}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-sm transition active:scale-95"
                >
                  <Play size={13} />
                  <span>Traiter la tâche</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Task Execution Modal */}
      <MayorFlowTaskExecutionModal
        task={executingTask}
        onClose={() => setExecutingTask(null)}
        onCompleted={fetchTasks}
      />
    </div>
  );
}
