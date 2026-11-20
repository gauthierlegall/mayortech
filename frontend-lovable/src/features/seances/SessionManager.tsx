import React, { useState, useEffect } from 'react';
import {
  ScrollText,
  Calendar,
  Clock,
  MapPin,
  Users,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Plus,
  ArrowUp,
  ArrowDown,
  Gavel,
  Landmark,
  FileCheck,
  Building2,
  Lock,
  Vote,
  
  ChevronRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { useWorkspace } from '../workspace/context';
import './sessions.css';

export interface CommissionSession {
  id: string;
  commission_id: string;
  session_type: string;
  title: string;
  session_date: string;
  session_time: string;
  location: string;
  status: 'draft' | 'en_cours' | 'closed' | 'archived';
  quorum_required: number;
  quorum_present: number;
  pv_hash?: string;
  closed_at?: string;
  closed_by?: string;
  notes?: string;
  items_count?: number;
  agenda_items?: AgendaItem[];
  attendances?: SessionAttendance[];
}

export interface AgendaItem {
  id: string;
  session_id: string;
  item_order: number;
  title: string;
  description: string;
  project_id?: string;
  project_version_snapshot?: Record<string, any>;
  rapporteur: string;
  deliberation_ref: string;
  vote_result: 'en_attente' | 'favorable' | 'defavorable' | 'reserve' | 'ajourne';
  votes_for: number;
  votes_against: number;
  votes_abstention: number;
  official_decision: string;
}

export interface SessionAttendance {
  member_name: string;
  member_role: 'titulaire' | 'suppleant' | 'invite' | 'secretaire';
  status: 'present' | 'absent_excuse' | 'absent' | 'pouvoir';
  proxy_to?: string;
}

export interface SpecializedInstance {
  id: string;
  instance_type: 'CAO' | 'CCSPL' | 'CCID';
  name: string;
  mandate_period: string;
  president_name: string;
  megalis_reference?: string;
  cadastre_scope?: string;
  public_service_delegations?: string;
  config?: Record<string, any>;
}

export interface SpecializedRecord {
  id: string;
  instance_id: string;
  record_type: string;
  reference: string;
  title: string;
  status: string;
  details?: Record<string, any>;
  created_at?: string;
}

export function SessionManager() {
  const { api, bootstrap, activeCommissionId, state } = useWorkspace();
  const canWrite = bootstrap?.permissions?.workspace?.write !== false;

  const [activeTab, setActiveTab] = useState<'sessions' | 'specialized'>('sessions');
  const [selectedInstanceId, setSelectedInstanceId] = useState<'cao' | 'ccspl' | 'ccid'>('cao');

  const [sessions, setSessions] = useState<CommissionSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<CommissionSession | null>(null);
  const [sessionDetailTab, setSessionDetailTab] = useState<'agenda' | 'attendance' | 'pv'>('agenda');

  const [specializedInstances, setSpecializedInstances] = useState<SpecializedInstance[]>([]);
  const [instanceRecords, setInstanceRecords] = useState<SpecializedRecord[]>([]);

  // Modals state
  const [createSessionOpen, setCreateSessionOpen] = useState(false);
  const [addItemOpen, setAddItemOpen] = useState(false);
  const [closeMeetingOpen, setCloseMeetingOpen] = useState(false);
  const [createRecordOpen, setCreateRecordOpen] = useState(false);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  // Load sessions on mount or when commission changes
  const loadSessions = async () => {
    try {
      if (api?.sessions) {
        const res = await api.sessions({ commission_id: activeCommissionId });
        if (res?.items) {
          setSessions(res.items);
          if (res.items.length > 0 && !selectedSession) {
            // Load full details of the first session
            const first = await (api.commissionSession || api.session)(res.items[0].id);
            setSelectedSession(first);
          }
        }
      }
    } catch (e: any) {
      console.warn('Could not load sessions:', e);
    }
  };

  const loadSpecialized = async () => {
    try {
      if (api?.specializedInstances) {
        const res = await api.specializedInstances();
        if (res?.items) {
          setSpecializedInstances(res.items);
        }
      }
      if (api?.specializedRecords) {
        const recs = await api.specializedRecords(selectedInstanceId);
        if (recs?.items) {
          setInstanceRecords(recs.items);
        }
      }
    } catch (e: any) {
      console.warn('Could not load specialized instances:', e);
    }
  };

  useEffect(() => {
    void loadSessions();
    void loadSpecialized();
  }, [activeCommissionId, selectedInstanceId]);

  const selectSessionById = async (id: string) => {
    try {
      setBusy(true);
      const detail = await (api.commissionSession || api.session)(id);
      setSelectedSession(detail);
    } catch (e: any) {
      setError(e.message || 'Erreur lors du chargement de la séance.');
    } finally {
      setBusy(false);
    }
  };

  // Actions
  const handleCreateSession = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canWrite) return;
    const form = new FormData(e.currentTarget);
    try {
      setBusy(true);
      setError('');
      const created = await api.createSession({
        commission_id: activeCommissionId,
        session_type: 'commission',
        title: String(form.get('title')),
        session_date: String(form.get('session_date')),
        session_time: String(form.get('session_time')),
        location: String(form.get('location')),
        quorum_required: Number(form.get('quorum_required') || 3),
        notes: String(form.get('notes') || ''),
      });
      setCreateSessionOpen(false);
      await loadSessions();
      setSelectedSession(created);
    } catch (e: any) {
      setError(e.message || 'Échec de la création de la séance.');
    } finally {
      setBusy(false);
    }
  };

  const handleAddAgendaItem = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedSession || !canWrite) return;
    const form = new FormData(e.currentTarget);
    try {
      setBusy(true);
      setError('');
      const updated = await api.addAgendaItem(selectedSession.id, {
        title: String(form.get('title')),
        description: String(form.get('description') || ''),
        project_id: String(form.get('project_id') || ''),
        rapporteur: String(form.get('rapporteur') || ''),
      });
      setAddItemOpen(false);
      setSelectedSession(updated);
      await loadSessions();
    } catch (e: any) {
      setError(e.message || "Échec de l'ajout du point à l'ordre du jour.");
    } finally {
      setBusy(false);
    }
  };

  const handleVote = async (itemId: string, result: AgendaItem['vote_result'], pFor: number, pAgainst: number, pAbs: number) => {
    if (!selectedSession || !canWrite || selectedSession.status === 'closed') return;
    try {
      setBusy(true);
      const updated = await api.recordVote(selectedSession.id, itemId, {
        vote_result: result,
        votes_for: pFor,
        votes_against: pAgainst,
        votes_abstention: pAbs,
        official_decision: `Vote validé (${pFor} Pour, ${pAgainst} Contre, ${pAbs} Abs)`,
      });
      setSelectedSession(updated);
    } catch (e: any) {
      setError(e.message || 'Échec de la prise en compte du vote.');
    } finally {
      setBusy(false);
    }
  };

  const handleMoveItem = async (itemId: string, direction: 'up' | 'down') => {
    if (!selectedSession || !selectedSession.agenda_items || selectedSession.status === 'closed') return;
    const items = [...selectedSession.agenda_items];
    const index = items.findIndex(it => it.id === itemId);
    if (index < 0) return;
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === items.length - 1) return;

    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const temp = items[index];
    items[index] = items[targetIndex];
    items[targetIndex] = temp;

    try {
      setBusy(true);
      const updated = await api.reorderAgenda(selectedSession.id, {
        ordered_item_ids: items.map(it => it.id),
      });
      setSelectedSession(updated);
    } catch (e: any) {
      setError(e.message || 'Impossible de réordonner les points.');
    } finally {
      setBusy(false);
    }
  };

  const handleCloseMeeting = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedSession || !canWrite) return;
    const form = new FormData(e.currentTarget);
    try {
      setBusy(true);
      setError('');
      const closed = await api.closeSession(selectedSession.id, {
        closed_by: String(form.get('closed_by') || 'Secrétaire de Séance'),
        force_quorum: form.get('force_quorum') === 'true',
      });
      setCloseMeetingOpen(false);
      setSelectedSession(closed);
      await loadSessions();
    } catch (e: any) {
      setError(e.message || 'Échec de la clôture formelle.');
    } finally {
      setBusy(false);
    }
  };

  const handleCreateRecord = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canWrite) return;
    const form = new FormData(e.currentTarget);
    try {
      setBusy(true);
      setError('');
      await api.createSpecializedRecord(selectedInstanceId, {
        record_type: selectedInstanceId === 'cao' ? 'cao_marche' : selectedInstanceId === 'ccspl' ? 'ccspl_rapport' : 'ccid_evaluation',
        reference: String(form.get('reference')),
        title: String(form.get('title')),
        status: 'en_cours',
        details: {
          registre: selectedInstanceId.toUpperCase(),
          remarques: String(form.get('notes') || ''),
          montant_ou_valeur: String(form.get('amount') || ''),
        },
      });
      setCreateRecordOpen(false);
      await loadSpecialized();
    } catch (e: any) {
      setError(e.message || "Échec de l'enregistrement de l'instance.");
    } finally {
      setBusy(false);
    }
  };

  const isQuorumReached = selectedSession
    ? selectedSession.quorum_present >= selectedSession.quorum_required
    : false;

  return (
    <div className="sessions-container" id="sessions-management-root">
      {/* Top Header Card */}
      <div className="sessions-header-card">
        <div className="flex justify-between items-start flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-2">
              <ScrollText className="h-6 w-6 text-indigo-600" />
              <h2 className="text-xl font-bold tracking-tight text-slate-900">
                Séances, Délibérations & Instances Spécialisées
              </h2>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Gouvernance municipale, gestion de l'ordre du jour, quorum CGCT et scellement cryptographique des procès-verbaux.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {canWrite && activeTab === 'sessions' && (
              <Button onClick={() => setCreateSessionOpen(true)} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                <Plus className="h-4 w-4 mr-1" />
                Nouvelle séance
              </Button>
            )}
            {canWrite && activeTab === 'specialized' && (
              <Button onClick={() => setCreateRecordOpen(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                <Plus className="h-4 w-4 mr-1" />
                Nouvel enregistrement {selectedInstanceId.toUpperCase()}
              </Button>
            )}
          </div>
        </div>

        {/* Primary View Switcher */}
        <div className="sessions-nav-tabs">
          <Button
            variant={activeTab === 'sessions' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('sessions')}
            className="flex items-center gap-1.5"
          >
            <Gavel className="h-4 w-4" />
            Séances de Commission ({sessions.length})
          </Button>
          <Button
            variant={activeTab === 'specialized' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('specialized')}
            className="flex items-center gap-1.5"
          >
            <Building2 className="h-4 w-4" />
            Instances Spécialisées (CAO / CCSPL / CCID)
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* VIEW 1: SESSIONS MANAGEMENT */}
      {activeTab === 'sessions' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sessions List Sidebar */}
          <div className="lg:col-span-4 flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-slate-600 uppercase tracking-wider">
              Séances de la commission
            </h3>
            {sessions.length === 0 ? (
              <div className="p-6 bg-white border border-slate-200 rounded-lg text-center text-slate-500">
                <Calendar className="h-8 w-8 mx-auto text-slate-400 mb-2" />
                <p>Aucune séance programmée pour cette commission.</p>
              </div>
            ) : (
              sessions.map(s => (
                <div
                  key={s.id}
                  onClick={() => selectSessionById(s.id)}
                  className={`p-4 bg-white border rounded-xl cursor-pointer transition-all ${
                    selectedSession?.id === s.id
                      ? 'border-indigo-600 shadow-sm ring-1 ring-indigo-600'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <span className="font-semibold text-slate-900 line-clamp-1">{s.title}</span>
                    <span className={`session-badge ${s.status}`}>
                      {s.status === 'closed' ? 'Clôturée' : s.status === 'en_cours' ? 'En cours' : 'Brouillon'}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      {s.session_date}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {s.session_time}
                    </span>
                    <span className="flex items-center gap-1">
                      <ScrollText className="h-3.5 w-3.5" />
                      {s.items_count ?? s.agenda_items?.length ?? 0} pts
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Active Session Detail Workspace */}
          <div className="lg:col-span-8 flex flex-col gap-4">
            {selectedSession ? (
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                {/* Cryptographic Seal Banner if Closed */}
                {selectedSession.status === 'closed' && (
                  <div className="session-seal-banner">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-6 w-6 text-emerald-300" />
                        <span className="font-bold tracking-wide">PROCÈS-VERBAL SCELLÉ & CERTIFIÉ CONFORME</span>
                      </div>
                      <span className="text-xs bg-emerald-900/60 text-emerald-200 px-2 py-1 rounded">
                        Horodaté le {selectedSession.closed_at?.substring(0, 10)}
                      </span>
                    </div>
                    <p className="text-xs text-emerald-100">
                      Clôturé par <strong>{selectedSession.closed_by || 'Secrétaire de séance'}</strong>. L'ordre du jour, les votes et les états des dossiers examinés sont verrouillés de manière immuable conformément au CGCT.
                    </p>
                    <div className="session-seal-hash">
                      SHA-256 : {selectedSession.pv_hash}
                    </div>
                  </div>
                )}

                {/* Session Header Info */}
                <div className="flex justify-between items-start flex-wrap gap-4 border-b border-slate-100 pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">{selectedSession.title}</h3>
                    <div className="flex items-center flex-wrap gap-4 text-xs text-slate-500 mt-1">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        {selectedSession.session_date} à {selectedSession.session_time}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5" />
                        {selectedSession.location}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {canWrite && selectedSession.status !== 'closed' && (
                      <Button
                        size="sm"
                        onClick={() => setCloseMeetingOpen(true)}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
                      >
                        <Lock className="h-3.5 w-3.5 mr-1" />
                        Clôturer et sceller le PV
                      </Button>
                    )}
                  </div>
                </div>

                {/* Quorum Bar */}
                <div className="my-4">
                  <div className="quorum-tracker">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-slate-600" />
                      <span className="text-xs font-semibold text-slate-700">
                        Quorum légal (CGCT L2121-17) :
                      </span>
                    </div>
                    <div className="quorum-bar-container">
                      <div
                        className={`quorum-bar-fill ${isQuorumReached ? 'reached' : 'unreached'}`}
                        style={{
                          width: `${Math.min(100, (selectedSession.quorum_present / (selectedSession.quorum_required || 1)) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-bold text-slate-800">
                      {selectedSession.quorum_present} / {selectedSession.quorum_required} requis
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-semibold ${
                        isQuorumReached ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {isQuorumReached ? 'Quorum atteint' : 'Quorum insuffisant'}
                    </span>
                  </div>
                </div>

                {/* Sub-tabs */}
                <div className="flex gap-2 border-b border-slate-200 pb-2 mb-4">
                  <Button
                    variant={sessionDetailTab === 'agenda' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setSessionDetailTab('agenda')}
                  >
                    Ordre du jour & Délibérations ({selectedSession.agenda_items?.length || 0})
                  </Button>
                  <Button
                    variant={sessionDetailTab === 'attendance' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setSessionDetailTab('attendance')}
                  >
                    Émargement & Présences ({selectedSession.attendances?.length || 0})
                  </Button>
                </div>

                {/* TAB 1: AGENDA ITEMS & VOTES */}
                {sessionDetailTab === 'agenda' && (
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs font-semibold text-slate-500 uppercase">
                        Points inscrits à la séance
                      </span>
                      {canWrite && selectedSession.status !== 'closed' && (
                        <Button size="sm" variant="outline" onClick={() => setAddItemOpen(true)}>
                          <Plus className="h-3.5 w-3.5 mr-1" />
                          Ajouter un point
                        </Button>
                      )}
                    </div>

                    <div className="agenda-items-list">
                      {(!selectedSession.agenda_items || selectedSession.agenda_items.length === 0) ? (
                        <p className="text-sm text-slate-500 italic p-4 text-center bg-slate-50 rounded-lg">
                          Aucun point n'est encore inscrit à l'ordre du jour.
                        </p>
                      ) : (
                        selectedSession.agenda_items.map((it, idx) => (
                          <div key={it.id} className="agenda-item-card">
                            <div className="agenda-item-header">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-bold text-slate-400">Point {it.item_order}</span>
                                  <span className="delib-ref-badge">{it.deliberation_ref}</span>
                                </div>
                                <h4 className="text-base font-semibold text-slate-900 mt-1">{it.title}</h4>
                                {it.description && (
                                  <p className="text-xs text-slate-600 mt-0.5">{it.description}</p>
                                )}
                                <div className="flex items-center gap-4 text-xs text-slate-500 mt-2">
                                  {it.rapporteur && <span>Rapporteur : <strong>{it.rapporteur}</strong></span>}
                                  {it.project_id && (
                                    <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-700">
                                      Dossier lié : {it.project_version_snapshot?.title || it.project_id}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Ordering Controls */}
                              {canWrite && selectedSession.status !== 'closed' && (
                                <div className="flex items-center gap-1">
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    disabled={idx === 0}
                                    onClick={() => handleMoveItem(it.id, 'up')}
                                    title="Monter le point"
                                  >
                                    <ArrowUp className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    size="icon"
                                    variant="ghost"
                                    disabled={idx === (selectedSession.agenda_items?.length || 1) - 1}
                                    onClick={() => handleMoveItem(it.id, 'down')}
                                    title="Descendre le point"
                                  >
                                    <ArrowDown className="h-4 w-4" />
                                  </Button>
                                </div>
                              )}
                            </div>

                            {/* Voting & Decision Box */}
                            <div className="voting-box">
                              <div className="voting-counts">
                                <span className="vote-pill for">
                                  <CheckCircle2 className="h-4 w-4" /> {it.votes_for} Pour
                                </span>
                                <span className="vote-pill against">
                                  <AlertTriangle className="h-4 w-4" /> {it.votes_against} Contre
                                </span>
                                <span className="vote-pill abstention">
                                  <Users className="h-4 w-4" /> {it.votes_abstention} Abs.
                                </span>
                                <span
                                  className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                                    it.vote_result === 'favorable'
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : it.vote_result === 'defavorable'
                                      ? 'bg-red-100 text-red-800'
                                      : 'bg-slate-100 text-slate-700'
                                  }`}
                                >
                                  Avis : {it.vote_result}
                                </span>
                              </div>

                              {/* Live vote triggers if session is not closed */}
                              {canWrite && selectedSession.status !== 'closed' && (
                                <div className="flex items-center gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50"
                                    onClick={() =>
                                      handleVote(
                                        it.id,
                                        'favorable',
                                        it.votes_for + 1,
                                        it.votes_against,
                                        it.votes_abstention
                                      )
                                    }
                                  >
                                    +1 Pour
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="text-xs text-red-700 border-red-200 hover:bg-red-50"
                                    onClick={() =>
                                      handleVote(
                                        it.id,
                                        'defavorable',
                                        it.votes_for,
                                        it.votes_against + 1,
                                        it.votes_abstention
                                      )
                                    }
                                  >
                                    +1 Contre
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="text-xs text-slate-700 border-slate-200 hover:bg-slate-50"
                                    onClick={() =>
                                      handleVote(
                                        it.id,
                                        'reserve',
                                        it.votes_for,
                                        it.votes_against,
                                        it.votes_abstention + 1
                                      )
                                    }
                                  >
                                    +1 Abs.
                                  </Button>
                                </div>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* TAB 2: ATTENDANCE */}
                {sessionDetailTab === 'attendance' && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-700 mb-2">
                      Membres émargés et mandats de vote
                    </h4>
                    {(!selectedSession.attendances || selectedSession.attendances.length === 0) ? (
                      <p className="text-sm text-slate-500 italic p-4 text-center bg-slate-50 rounded-lg">
                        Aucun membre n'est encore inscrit sur la feuille d'émargement.
                      </p>
                    ) : (
                      <div className="attendance-grid">
                        {selectedSession.attendances.map((att, i) => (
                          <div key={i} className="attendance-card">
                            <div>
                              <strong className="text-sm text-slate-900 block">{att.member_name}</strong>
                              <span className="text-xs text-slate-500 capitalize">{att.member_role}</span>
                              {att.proxy_to && (
                                <span className="text-xs text-sky-700 block">Pouvoir à : {att.proxy_to}</span>
                              )}
                            </div>
                            <span className={`attendance-status-badge ${att.status}`}>
                              {att.status === 'present'
                                ? 'Présent'
                                : att.status === 'pouvoir'
                                ? 'Pouvoir'
                                : att.status === 'absent_excuse'
                                ? 'Excusé'
                                : 'Absent'}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 bg-white border border-slate-200 rounded-xl text-center text-slate-500">
                Sélectionnez une séance pour afficher son ordre du jour et ses délibérations.
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 2: SPECIALIZED INSTANCES (CAO, CCSPL, CCID) */}
      {activeTab === 'specialized' && (
        <div className="flex flex-col gap-6">
          {/* Instance Selection Tabs */}
          <div className="flex gap-3">
            <Button
              variant={selectedInstanceId === 'cao' ? 'secondary' : 'outline'}
              onClick={() => setSelectedInstanceId('cao')}
              className="flex items-center gap-2"
            >
              <FileCheck className="h-4 w-4 text-emerald-600" />
              CAO (Marchés & Mégalis)
            </Button>
            <Button
              variant={selectedInstanceId === 'ccspl' ? 'secondary' : 'outline'}
              onClick={() => setSelectedInstanceId('ccspl')}
              className="flex items-center gap-2"
            >
              <Landmark className="h-4 w-4 text-sky-600" />
              CCSPL (Services Publics & DSP)
            </Button>
            <Button
              variant={selectedInstanceId === 'ccid' ? 'secondary' : 'outline'}
              onClick={() => setSelectedInstanceId('ccid')}
              className="flex items-center gap-2"
            >
              <Building2 className="h-4 w-4 text-purple-600" />
              CCID (Impôts & Cadastre)
            </Button>
          </div>

          {/* Instance Context Card */}
          {selectedInstanceId === 'cao' && (
            <div className="specialized-instance-hero instance-cao">
              <h3 className="text-lg font-bold text-emerald-950 flex items-center gap-2">
                <FileCheck className="h-5 w-5 text-emerald-700" />
                Commission d'Appel d'Offres (CAO) · Mégalis Bretagne
              </h3>
              <p className="text-sm text-emerald-800 mt-1">
                Instruction des marchés publics formalisés, seuils réglementaires (Travaux : 5 382 000 € HT / Fournitures : 215 000 € HT), traçabilité de l'ouverture des plis et attribution.
              </p>
              <div className="flex flex-wrap gap-4 mt-3 text-xs font-semibold text-emerald-900">
                <span>Plateforme : <strong>Mégalis Bretagne</strong></span>
                <span>Mandat : <strong>2026-2032</strong></span>
                <span>Présidence : <strong>Maire de Plougastel-Daoulas</strong></span>
              </div>
            </div>
          )}

          {selectedInstanceId === 'ccspl' && (
            <div className="specialized-instance-hero instance-ccspl">
              <h3 className="text-lg font-bold text-sky-950 flex items-center gap-2">
                <Landmark className="h-5 w-5 text-sky-700" />
                Commission Consultative des Services Publics Locaux (CCSPL)
              </h3>
              <p className="text-sm text-sky-800 mt-1">
                Contrôle annuel des délégations de service public : eau potable, assainissement collectif (Eau du Ponant), gestion du port de plaisance du Tinduff, et rapport sur le prix et la qualité des services.
              </p>
              <div className="flex flex-wrap gap-4 mt-3 text-xs font-semibold text-sky-900">
                <span>Délégations suivies : <strong>Eau, Assainissement, Déchets, Port</strong></span>
                <span>Périodicité des rapports : <strong>Annuelle</strong></span>
              </div>
            </div>
          )}

          {selectedInstanceId === 'ccid' && (
            <div className="specialized-instance-hero instance-ccid">
              <h3 className="text-lg font-bold text-purple-950 flex items-center gap-2">
                <Building2 className="h-5 w-5 text-purple-700" />
                Commission Communale des Impôts Directs (CCID)
              </h3>
              <p className="text-sm text-purple-800 mt-1">
                Évaluation et mise à jour des valeurs locatives cadastrales des locaux commerciaux et d'habitation sur l'ensemble des sections cadastrales communales, en liaison avec le Service des Impôts des Particuliers (SIP Brest Ouest).
              </p>
              <div className="flex flex-wrap gap-4 mt-3 text-xs font-semibold text-purple-900">
                <span>Commissaires : <strong>8 titulaires & 8 suppléants</strong></span>
                <span>Périmètre : <strong>Sections A à Z (Plougastel)</strong></span>
              </div>
            </div>
          )}

          {/* Records Table */}
          <div className="records-table-container">
            <table className="records-table">
              <thead>
                <tr>
                  <th>RÉFÉRENCE</th>
                  <th>OBJET / INTITULÉ</th>
                  <th>STATUT</th>
                  <th>DÉTAILS MÉTIER</th>
                  <th>ENREGISTRÉ LE</th>
                </tr>
              </thead>
              <tbody>
                {instanceRecords.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-6 text-slate-500 italic">
                      Aucun enregistrement pour cette instance spécialisée.
                    </td>
                  </tr>
                ) : (
                  instanceRecords.map(rec => (
                    <tr key={rec.id}>
                      <td className="font-mono font-bold text-slate-800">{rec.reference}</td>
                      <td className="font-semibold text-slate-900">{rec.title}</td>
                      <td>
                        <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-semibold uppercase">
                          {rec.status}
                        </span>
                      </td>
                      <td className="text-xs text-slate-600">
                        {rec.details?.montant_ou_valeur && <div>Montant : {rec.details.montant_ou_valeur}</div>}
                        {rec.details?.remarques && <div>{rec.details.remarques}</div>}
                      </td>
                      <td className="text-xs text-slate-500">{rec.created_at?.substring(0, 10)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* DIALOG: NOUVELLE SÉANCE */}
      <Dialog open={createSessionOpen} onOpenChange={setCreateSessionOpen}>
        <DialogContent className="max-w-lg">
          <DialogTitle>Créer une séance de commission</DialogTitle>
          <DialogDescription>
            Convoquez une nouvelle séance avec fixation de la date, du lieu et du seuil de quorum légal.
          </DialogDescription>
          <form className="form-stack mt-4" onSubmit={handleCreateSession}>
            <label className="block text-sm font-semibold text-slate-700">
              Intitulé de la séance
              <input
                name="title"
                required
                defaultValue="Commission Ordinaire - Séance plénière"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <div className="grid grid-cols-2 gap-4">
              <label className="block text-sm font-semibold text-slate-700">
                Date de séance
                <input
                  type="date"
                  name="session_date"
                  required
                  defaultValue="2027-04-15"
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                />
              </label>
              <label className="block text-sm font-semibold text-slate-700">
                Heure
                <input
                  type="time"
                  name="session_time"
                  required
                  defaultValue="18:30"
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                />
              </label>
            </div>
            <label className="block text-sm font-semibold text-slate-700">
              Lieu de réunion
              <input
                name="location"
                required
                defaultValue="Hôtel de Ville de Plougastel-Daoulas"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Quorum requis (membres présents/représentés)
              <input
                type="number"
                name="quorum_required"
                required
                min={1}
                max={50}
                defaultValue={3}
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="outline" onClick={() => setCreateSessionOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" disabled={busy} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                {busy ? 'Création…' : 'Créer la séance'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* DIALOG: AJOUTER UN POINT */}
      <Dialog open={addItemOpen} onOpenChange={setAddItemOpen}>
        <DialogContent className="max-w-lg">
          <DialogTitle>Inscrire un point à l'ordre du jour</DialogTitle>
          <DialogDescription>
            Rattachez un dossier de la commission, spécifiez le rapporteur et attribuez la référence de délibération.
          </DialogDescription>
          <form className="form-stack mt-4" onSubmit={handleAddAgendaItem}>
            <label className="block text-sm font-semibold text-slate-700">
              Objet du point
              <input
                name="title"
                required
                placeholder="Ex. Approbation du marché de voirie communale"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Description / Notes d'instruction
              <textarea
                name="description"
                rows={3}
                placeholder="Synthèse des enjeux, pièces soumises à l'avis de la commission…"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Rapporteur
              <input
                name="rapporteur"
                defaultValue="Maire-Adjoint délégué"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Dossier rattaché (optionnel)
              <select name="project_id" className="w-full mt-1 px-3 py-2 border rounded-md">
                <option value="">-- Aucun dossier lié --</option>
                {state.projects.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.ref} - {p.title}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="outline" onClick={() => setAddItemOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" disabled={busy} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                {busy ? 'Inscription…' : 'Inscrire le point'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* DIALOG: CLÔTURE FORMELLE & SCEAU */}
      <Dialog open={closeMeetingOpen} onOpenChange={setCloseMeetingOpen}>
        <DialogContent className="max-w-md">
          <DialogTitle className="flex items-center gap-2 text-emerald-800">
            <Lock className="h-5 w-5 text-emerald-600" />
            Clôturer et sceller le procès-verbal
          </DialogTitle>
          <DialogDescription>
            Cette action fige l'ordre du jour, les votes enregistrés et l'état des dossiers examinés. Un sceau cryptographique SHA-256 sera calculé et certifié.
          </DialogDescription>
          {!isQuorumReached && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded text-amber-800 text-xs flex items-center gap-2 my-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>Attention : le quorum légal ({selectedSession?.quorum_present}/{selectedSession?.quorum_required}) n'est pas satisfait.</span>
            </div>
          )}
          <form className="form-stack mt-4" onSubmit={handleCloseMeeting}>
            <label className="block text-sm font-semibold text-slate-700">
              Signataire / Clôturé par
              <input
                name="closed_by"
                required
                defaultValue="Directeur Général des Services"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            {!isQuorumReached && (
              <label className="flex items-center gap-2 text-xs text-amber-900 mt-2">
                <input type="checkbox" name="force_quorum" value="true" />
                Dérogation expresse de quorum sous la responsabilité du président
              </label>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="outline" onClick={() => setCloseMeetingOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" disabled={busy} className="bg-emerald-700 hover:bg-emerald-800 text-white">
                {busy ? 'Scellement…' : 'Confirmer et sceller le PV'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* DIALOG: NOUVEL ENREGISTREMENT INSTANCE SPÉCIALISÉE */}
      <Dialog open={createRecordOpen} onOpenChange={setCreateRecordOpen}>
        <DialogContent className="max-w-lg">
          <DialogTitle>
            Enregistrer dans l'instance {selectedInstanceId.toUpperCase()}
          </DialogTitle>
          <DialogDescription>
            {selectedInstanceId === 'cao'
              ? 'Enregistrez un marché public Mégalis Bretagne avec ses lots et montants.'
              : selectedInstanceId === 'ccspl'
              ? 'Enregistrez un rapport annuel de délégation de service public.'
              : 'Enregistrez une évaluation cadastrale et valeur locative communale.'}
          </DialogDescription>
          <form className="form-stack mt-4" onSubmit={handleCreateRecord}>
            <label className="block text-sm font-semibold text-slate-700">
              Référence officielle
              <input
                name="reference"
                required
                placeholder={
                  selectedInstanceId === 'cao'
                    ? 'Ex. MEGALIS-BRETAGNE-2027-T09'
                    : selectedInstanceId === 'ccspl'
                    ? 'Ex. RAPPORT-DSP-EAU-2026'
                    : 'Ex. CCID-2027-SECTION-AD-15'
                }
                className="w-full mt-1 px-3 py-2 border rounded-md font-mono"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Intitulé / Objet
              <input
                name="title"
                required
                placeholder="Ex. Réfection de voirie ou Audit concession"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Montant estimé ou Valeur locative
              <input
                name="amount"
                placeholder="Ex. 180 000 € HT ou VL 2 400 €"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-700">
              Remarques et instruction
              <textarea
                name="notes"
                rows={2}
                placeholder="Détails du pli, lots retenus, conformité réglementaire…"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </label>
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="outline" onClick={() => setCreateRecordOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" disabled={busy} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                {busy ? 'Enregistrement…' : "Créer l'enregistrement"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
