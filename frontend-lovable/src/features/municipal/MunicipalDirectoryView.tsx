import React, { useState, useEffect, useMemo } from 'react';
import { 
  Users, Shield, UserCheck, UserX, Search, Filter, 
  KeyRound, FileText, CheckCircle2, AlertTriangle, RefreshCw, Building2,
  Lock, Sparkles, ChevronRight, UserPlus, Eye, ArrowUpRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MunicipalJoinSasModal } from './MunicipalJoinSasModal';
import { PositionProfileDrawer, OrganigramNode } from './PositionProfileDrawer';

export interface MunicipalEntry {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
  email: string;
  statut: string;
  direction: string;
  poste: string;
  commission_id: string;
  niveau: number;
  role: 'reader' | 'editor' | 'admin';
  delegation_signature: boolean;
  arrete_delegation?: string | null;
  suppleant_id?: string | null;
  telephone?: string | null;
  active: boolean;
  display_name: string;
}

export interface MunicipalDelegation {
  id: string;
  titulaire_id: string;
  suppleant_id: string;
  scope: string;
  start_date: string;
  end_date?: string | null;
  arrete_reference?: string | null;
  active: boolean;
  titulaire: string;
  suppleant: string;
}

const NIVEAU_BADGES: Record<number, { label: string; color: string; desc: string }> = {
  0: { 
    label: 'Niv. 0 · Public', 
    color: 'bg-slate-100 text-slate-700 border-slate-200', 
    desc: 'Consultation anonyme'
  },
  1: { 
    label: 'Niv. 1 · Lecteur', 
    color: 'bg-blue-50 text-blue-700 border-blue-200', 
    desc: 'Conseiller municipal / suppléant'
  },
  2: { 
    label: 'Niv. 2 · Instructeur', 
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200', 
    desc: 'Rédacteur / agent métier instructeur ADS'
  },
  3: { 
    label: 'Niv. 3 · Chef de Service', 
    color: 'bg-amber-50 text-amber-700 border-amber-200', 
    desc: 'Validation technique & ordonnancement'
  },
  4: { 
    label: 'Niv. 4 · Ordonnateur / Élu', 
    color: 'bg-purple-50 text-purple-700 border-purple-200', 
    desc: 'Maire, Adjoints au Maire & Membres CAO'
  },
  5: { 
    label: 'Niv. 5 · DGS / Admin', 
    color: 'bg-rose-50 text-rose-700 border-rose-200', 
    desc: 'Direction Générale des Services & Sceau Régalien'
  }
};

const COMMISSION_META: Record<string, { label: string; short: string; color: string }> = {
  'all': { 
    label: 'Toutes les commissions (Transverse)', 
    short: 'Transverse', 
    color: 'bg-blue-50 text-blue-700 border-blue-200' 
  },
  'commission-1': { 
    label: '1. Finances & Commande Publique', 
    short: '1. Finances & Marchés', 
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200' 
  },
  'commission-2': { 
    label: '2. Enfance & Solidarités (CCAS)', 
    short: '2. Enfance & CCAS', 
    color: 'bg-amber-50 text-amber-700 border-amber-200' 
  },
  'commission-3': { 
    label: '3. Urbanisme, Travaux & Ports', 
    short: '3. Urbanisme & Ports', 
    color: 'bg-cyan-50 text-cyan-700 border-cyan-200' 
  },
  'commission-4': { 
    label: '4. Culture & Vie Associative', 
    short: '4. Culture & Asso', 
    color: 'bg-purple-50 text-purple-700 border-purple-200' 
  }
};

export function MunicipalDirectoryView() {
  const [entries, setEntries] = useState<MunicipalEntry[]>([]);
  const [delegations, setDelegations] = useState<MunicipalDelegation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCommission, setSelectedCommission] = useState('all');
  const [selectedNiveau, setSelectedNiveau] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<'directory' | 'delegations'>('directory');

  // Modal & Drawer states
  const [showDelegationModal, setShowDelegationModal] = useState(false);
  const [showSasModal, setShowSasModal] = useState(false);
  const [selectedNode, setSelectedNode] = useState<OrganigramNode | null>(null);
  const [selectedTitulaire, setSelectedTitulaire] = useState<MunicipalEntry | null>(null);
  const [suppleantId, setSuppleantId] = useState('');
  const [delegationScope, setDelegationScope] = useState('signature');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState('');
  const [arreteRef, setArreteRef] = useState('');
  const [delegationSaving, setDelegationSaving] = useState(false);

  const handleInspect = (entry: MunicipalEntry) => {
    setSelectedNode({
      id: entry.id,
      type: 'agent',
      title: entry.poste,
      holder: entry.display_name,
      matricule: entry.matricule,
      niveau: entry.niveau,
      role: entry.role,
      color: entry.niveau >= 4 ? '#7c3aed' : entry.niveau === 3 ? '#d97706' : '#0284c7',
      category: COMMISSION_META[entry.commission_id]?.short || 'Transverse',
      email: entry.email,
      delegation_signature: entry.delegation_signature,
      telephone: entry.telephone || '02 98 37 57 57',
    });
  };

  const fetchDirectory = async () => {
    setLoading(true);
    setError(null);
    try {
      const [resDir, resDel] = await Promise.all([
        fetch('/api/v1/municipal/directory'),
        fetch('/api/v1/municipal/delegations')
      ]);
      if (!resDir.ok) throw new Error('Impossible de charger le répertoire municipal.');
      const dataDir = await resDir.json();
      const dataDel = resDel.ok ? await resDel.json() : [];
      setEntries(dataDir);
      setDelegations(dataDel);
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDirectory();
  }, []);

  const handleOpenDelegation = (entry: MunicipalEntry) => {
    setSelectedTitulaire(entry);
    setSuppleantId('');
    setArreteRef(`Arrêté 2026-DEL-${entry.matricule}`);
    setShowDelegationModal(true);
  };

  const handleSaveDelegation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTitulaire || !suppleantId) return;
    setDelegationSaving(true);
    try {
      const res = await fetch('/api/v1/municipal/delegations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux'
        },
        body: JSON.stringify({
          titulaire_id: selectedTitulaire.id,
          suppleant_id: suppleantId,
          scope: delegationScope,
          start_date: startDate,
          end_date: endDate || null,
          arrete_reference: arreteRef || null
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error?.message || 'Erreur lors de l’enregistrement de la délégation');
      }
      setShowDelegationModal(false);
      await fetchDirectory();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setDelegationSaving(false);
    }
  };

  const handleRevoke = async (entry: MunicipalEntry) => {
    if (!confirm(`Confirmez-vous la révocation des habilitations de ${entry.display_name} (${entry.matricule}) ? Ses accès seront révoqués immédiatement.`)) {
      return;
    }
    try {
      const res = await fetch(`/api/v1/municipal/directory/${entry.id}/revoke`, {
        method: 'POST',
        headers: { 'X-Requested-With': 'Travaux' }
      });
      if (!res.ok) throw new Error('Erreur lors de la révocation.');
      await fetchDirectory();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const filteredEntries = useMemo(() => {
    return entries.filter(e => {
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = 
        e.display_name.toLowerCase().includes(searchLower) ||
        e.nom.toLowerCase().includes(searchLower) ||
        e.prenom.toLowerCase().includes(searchLower) ||
        e.matricule.toLowerCase().includes(searchLower) ||
        e.poste.toLowerCase().includes(searchLower) ||
        e.direction.toLowerCase().includes(searchLower) ||
        e.email.toLowerCase().includes(searchLower);

      const matchesCommission = selectedCommission === 'all' || e.commission_id === selectedCommission || e.commission_id === 'all';
      const matchesNiveau = selectedNiveau === 'all' || e.niveau.toString() === selectedNiveau;

      return matchesSearch && matchesCommission && matchesNiveau;
    });
  }, [entries, searchTerm, selectedCommission, selectedNiveau]);

  const stats = useMemo(() => {
    const total = entries.length;
    const ordonnateurs = entries.filter(e => e.niveau >= 4).length;
    const instructeurs = entries.filter(e => e.niveau === 2 || e.niveau === 3).length;
    const delegationsCount = delegations.filter(d => d.active).length;
    return { total, ordonnateurs, instructeurs, delegationsCount };
  }, [entries, delegations]);

  return (
    <div className="space-y-4 font-sans text-slate-900">
      {/* 4 Bento Telemetry Cards - Pure Light Mode */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Card 1: Effectif */}
        <div className="rounded-xl bg-white border border-slate-200 p-4 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Effectif Municipal</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
              <Users size={16} />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
              {stats.total}
            </span>
            <span className="text-xs font-medium text-slate-600">profils actifs</span>
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>Synchronisé CSV RH Plougastel</span>
          </div>
        </div>

        {/* Card 2: Matrice RBAC */}
        <div className="rounded-xl bg-white border border-slate-200 p-4 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Matrice des Rôles</span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
              <Shield size={16} />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
              6
            </span>
            <span className="text-xs font-medium text-slate-600">niveaux (0 à 5)</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            <span className="font-semibold text-purple-700">{stats.ordonnateurs}</span> ordonnateurs · <span className="font-semibold text-emerald-700">{stats.instructeurs}</span> instructeurs
          </div>
        </div>

        {/* Card 3: Délégations */}
        <div className="rounded-xl bg-white border border-slate-200 p-4 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Suppléances & Intérims</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
              <KeyRound size={16} />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
              {stats.delegationsCount}
            </span>
            <span className="text-xs font-medium text-slate-600">délégation(s)</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            <span>Arrêtés municipaux « On Behalf Of »</span>
          </div>
        </div>

        {/* Card 4: Sas d'Enrôlement */}
        <div className="rounded-xl bg-white border border-slate-200 p-4 shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Sas Zero-Trust</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
              <UserCheck size={16} />
            </div>
          </div>
          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-base font-bold text-emerald-700 font-mono">
              PLOUGASTEL-2026
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
            <span>Code secret DGS requis</span>
            <button
              onClick={() => setShowSasModal(true)}
              className="text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-0.5"
            >
              Ouvrir <ArrowUpRight size={11} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight">
            Référentiel des Postes & Habilitations Municipales
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Matrice des 6 niveaux de responsabilité (RBAC / ABAC) & Suppléances légales
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center p-0.5 rounded-lg bg-slate-100 border border-slate-200">
            <button
              onClick={() => setActiveTab('directory')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition ${
                activeTab === 'directory'
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Annuaire ({entries.length})
            </button>
            <button
              onClick={() => setActiveTab('delegations')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition ${
                activeTab === 'delegations'
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              Délégations ({delegations.length})
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSasModal(true)}
            className="flex items-center gap-1.5 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 h-8"
          >
            <UserPlus className="w-3.5 h-3.5 text-emerald-600" />
            Sas d'Auto-Enrôlement
          </Button>

          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchDirectory} 
            disabled={loading}
            className="flex items-center gap-1 text-xs text-slate-700 border-slate-300 hover:bg-slate-50 h-8"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg flex items-center gap-2.5 text-xs">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      {/* Directory Tab View */}
      {activeTab === 'directory' && (
        <div className="space-y-3">
          {/* Controls Bar */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5 bg-slate-50 p-2.5 rounded-xl border border-slate-200">
            <div className="relative md:col-span-6">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Rechercher par matricule, nom, prénom, direction, poste..."
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-900 placeholder-slate-400"
              />
            </div>

            <div className="md:col-span-3">
              <select
                value={selectedCommission}
                onChange={e => setSelectedCommission(e.target.value)}
                className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-800"
              >
                <option value="all">Toutes les commissions</option>
                <option value="commission-1">1. Finances & Commande Publique</option>
                <option value="commission-2">2. Enfance & Solidarités (CCAS)</option>
                <option value="commission-3">3. Urbanisme, Travaux & Ports</option>
                <option value="commission-4">4. Culture & Vie Associative</option>
              </select>
            </div>

            <div className="md:col-span-3">
              <select
                value={selectedNiveau}
                onChange={e => setSelectedNiveau(e.target.value)}
                className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-800"
              >
                <option value="all">Tous les niveaux (0 à 5)</option>
                <option value="5">Niveau 5 (DGS & Direction Générale)</option>
                <option value="4">Niveau 4 (Maire & Adjoints Délégués)</option>
                <option value="3">Niveau 3 (Chefs de Service & Pôles)</option>
                <option value="2">Niveau 2 (Instructeurs & Rédacteurs)</option>
                <option value="1">Niveau 1 (Conseillers & Lecteurs)</option>
                <option value="0">Niveau 0 (Invité / Public)</option>
              </select>
            </div>
          </div>

          {/* Quick Filter Pills : Commissions */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-[11px] font-semibold text-slate-500 mr-1 flex items-center gap-1">
              <Filter size={11} /> Commissions :
            </span>
            <button
              onClick={() => setSelectedCommission('all')}
              className={`px-2 py-0.5 rounded-md font-medium transition text-[11px] ${
                selectedCommission === 'all'
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              Toutes
            </button>
            <button
              onClick={() => setSelectedCommission('commission-1')}
              className={`px-2 py-0.5 rounded-md font-medium transition text-[11px] ${
                selectedCommission === 'commission-1'
                  ? 'bg-emerald-600 text-white font-semibold'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-emerald-50 hover:text-emerald-700'
              }`}
            >
              1. Finances
            </button>
            <button
              onClick={() => setSelectedCommission('commission-2')}
              className={`px-2 py-0.5 rounded-md font-medium transition text-[11px] ${
                selectedCommission === 'commission-2'
                  ? 'bg-amber-600 text-white font-semibold'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-amber-50 hover:text-amber-700'
              }`}
            >
              2. Enfance & CCAS
            </button>
            <button
              onClick={() => setSelectedCommission('commission-3')}
              className={`px-2 py-0.5 rounded-md font-medium transition text-[11px] ${
                selectedCommission === 'commission-3'
                  ? 'bg-cyan-600 text-white font-semibold'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-cyan-50 hover:text-cyan-700'
              }`}
            >
              3. Urbanisme & Ports
            </button>
            <button
              onClick={() => setSelectedCommission('commission-4')}
              className={`px-2 py-0.5 rounded-md font-medium transition text-[11px] ${
                selectedCommission === 'commission-4'
                  ? 'bg-purple-600 text-white font-semibold'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-purple-50 hover:text-purple-700'
              }`}
            >
              4. Culture
            </button>
          </div>

          {/* Directory Table Bento Card */}
          <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-2xs">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-3 min-w-[260px]">Matricule & Identité</th>
                  <th className="py-2.5 px-3 min-w-[220px]">Direction & Poste</th>
                  <th className="py-2.5 px-3 min-w-[180px]">Commission Rattachée</th>
                  <th className="py-2.5 px-3 min-w-[170px]">Responsabilité & Rôle</th>
                  <th className="py-2.5 px-3 min-w-[150px]">Délégation Signature</th>
                  <th className="py-2.5 px-3 min-w-[170px] text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredEntries.map(entry => {
                  const badge = NIVEAU_BADGES[entry.niveau] || NIVEAU_BADGES[1];
                  const comm = COMMISSION_META[entry.commission_id] || COMMISSION_META['all'];
                  return (
                    <tr key={entry.id} className="hover:bg-slate-50/75 transition-colors group">
                      {/* Matricule & Identite */}
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-bold whitespace-nowrap shrink-0">
                            {entry.matricule}
                          </span>
                          <span className="font-semibold text-slate-900 text-xs">
                            {entry.display_name}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-0.5 font-mono">
                          {entry.email}
                        </p>
                      </td>

                      {/* Direction & Poste */}
                      <td className="py-2.5 px-3">
                        <p className="font-medium text-slate-800 text-xs">{entry.poste}</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">{entry.direction}</p>
                      </td>

                      {/* Commission */}
                      <td className="py-2.5 px-3">
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border inline-block whitespace-nowrap ${comm.color}`}>
                          {comm.short}
                        </span>
                      </td>

                      {/* Responsabilite & Role */}
                      <td className="py-2.5 px-3">
                        <div className="flex flex-col gap-0.5 items-start">
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border inline-block whitespace-nowrap ${badge.color}`}>
                            {badge.label}
                          </span>
                          <span className="text-[9px] text-slate-500 uppercase tracking-wider font-mono">
                            Rôle : <strong className="text-slate-700">{entry.role}</strong>
                          </span>
                        </div>
                      </td>

                      {/* Delegation Signature */}
                      <td className="py-2.5 px-3">
                        {entry.delegation_signature ? (
                          <div className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 whitespace-nowrap">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Oui</span>
                            {entry.arrete_delegation && (
                              <span className="text-emerald-800/80 font-mono text-[9px]">({entry.arrete_delegation})</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400">Non</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-2.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-[11px] h-6 px-2 text-slate-700 border-slate-300 hover:bg-slate-100 rounded-md"
                            onClick={() => handleInspect(entry)}
                            title="Consulter la fiche d'habilitation"
                          >
                            <Eye className="w-3 h-3 mr-1 text-slate-500" />
                            Fiche
                          </Button>

                          {entry.niveau >= 3 && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-[11px] h-6 px-2 text-purple-700 border-purple-200 hover:bg-purple-50 rounded-md"
                              onClick={() => handleOpenDelegation(entry)}
                              title="Organiser une suppléance"
                            >
                              <KeyRound className="w-3 h-3 mr-1 text-purple-600" />
                              Déléguer
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-[11px] h-6 px-1.5 text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-md"
                            onClick={() => handleRevoke(entry)}
                            title="Révoquer l'accès"
                          >
                            <UserX className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {filteredEntries.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      Aucun profil municipal ne correspond à vos filtres.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Delegations Tab View */}
      {activeTab === 'delegations' && (
        <div className="space-y-3">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-amber-900 text-xs flex items-start gap-2.5">
            <Shield className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-900">Continuité du Service Public & Suppléances (« On Behalf Of »)</p>
              <p className="text-slate-600 mt-0.5">
                Conformément au Code Général des Collectivités Territoriales (CGCT), toute suppléance active autorise le suppléant à viser ou signer les pièces officielles au nom du titulaire absent.
              </p>
            </div>
          </div>

          <div className="border border-slate-200 rounded-xl bg-white overflow-hidden shadow-2xs">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600 uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-3">Titulaire Absent</th>
                  <th className="py-2.5 px-3">Suppléant Habilité</th>
                  <th className="py-2.5 px-3">Périmètre Délégation</th>
                  <th className="py-2.5 px-3">Période de Validité</th>
                  <th className="py-2.5 px-3">Arrêté Municipal</th>
                  <th className="py-2.5 px-3 text-right">Statut</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {delegations.map(del => (
                  <tr key={del.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{del.titulaire}</td>
                    <td className="py-2.5 px-3 text-blue-700 font-medium">{del.suppleant}</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 font-semibold">
                        {del.scope}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-xs font-mono text-slate-600">
                      Du {del.start_date} {del.end_date ? `au ${del.end_date}` : '(indéterminé)'}
                    </td>
                    <td className="py-2.5 px-3 text-xs font-mono text-slate-500">
                      {del.arrete_reference || 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {del.active ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                          Active
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-500">
                          Expirée
                        </span>
                      )}
                    </td>
                  </tr>
                ))}

                {delegations.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      Aucune délégation de suppléance active enregistrée actuellement.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal Delegation Form */}
      {showDelegationModal && selectedTitulaire && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-5 space-y-4 border border-slate-200 text-slate-900">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-purple-600" />
                <h3 className="font-bold text-sm text-slate-900">
                  Arrêté de Suppléance / Délégation d'Intérim
                </h3>
              </div>
              <button 
                onClick={() => setShowDelegationModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveDelegation} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Titulaire en titre :</label>
                <div className="p-2 rounded-lg bg-slate-50 border text-slate-800 font-medium">
                  {selectedTitulaire.display_name} ({selectedTitulaire.poste}) · <span className="font-mono text-slate-600">{selectedTitulaire.matricule}</span>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Choisir le suppléant désigné (Niveau ≥ 2) :
                </label>
                <select
                  required
                  value={suppleantId}
                  onChange={e => setSuppleantId(e.target.value)}
                  className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-purple-600 bg-white"
                >
                  <option value="">-- Sélectionner un agent ou élu --</option>
                  {entries
                    .filter(e => e.id !== selectedTitulaire.id && e.niveau >= 2)
                    .map(e => (
                      <option key={e.id} value={e.id}>
                        {e.display_name} ({e.poste}) · {NIVEAU_BADGES[e.niveau]?.label}
                      </option>
                    ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Périmètre légal :</label>
                  <select
                    value={delegationScope}
                    onChange={e => setDelegationScope(e.target.value)}
                    className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-purple-600 bg-white"
                  >
                    <option value="signature">Signature & Ordres de paiement</option>
                    <option value="visa">Visa technique dossiers</option>
                    <option value="commission">Présidence commission</option>
                    <option value="all">Plein exercice (Tous pouvoirs)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Arrêté municipal :</label>
                  <input
                    type="text"
                    value={arreteRef}
                    onChange={e => setArreteRef(e.target.value)}
                    placeholder="ex: Arrêté 2026-DEL-04"
                    className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-purple-600 bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Date d'effet (début) :</label>
                  <input
                    type="date"
                    required
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                    className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-purple-600 bg-white"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Date de fin (optionnel) :</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={e => setEndDate(e.target.value)}
                    className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-purple-600 bg-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setShowDelegationModal(false)}
                  disabled={delegationSaving}
                  className="text-slate-700 border-slate-300 hover:bg-slate-100 font-medium text-xs"
                >
                  Annuler
                </Button>
                <Button 
                  type="submit" 
                  disabled={delegationSaving || !suppleantId}
                  className="bg-purple-700 hover:bg-purple-800 text-white font-medium text-xs shadow-xs"
                >
                  {delegationSaving ? 'Enregistrement...' : 'Activer la Suppléance'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sas d'Auto-Enrôlement Modal */}
      <MunicipalJoinSasModal
        isOpen={showSasModal}
        onClose={() => setShowSasModal(false)}
        onSuccess={() => {
          setShowSasModal(false);
          fetchDirectory();
        }}
      />

      {/* Sovereign Position Profile Drawer */}
      <PositionProfileDrawer
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}
