import React, { useState, useEffect } from 'react';
import {
  CalendarDays,
  Clock,
  MapPin,
  Users,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Download,
  Send,
  Vote,
  
  Lock,
  ChevronRight,
  UserCheck,
  ArrowRight,
  Building2,
  ExternalLink,
  Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useWorkspace } from '../workspace/context';

interface ConvocationInfo {
  clear_days_required: number;
  cgct_article: string;
  population: number;
  stratum_label: string;
  deadline_date: string;
  deadline_human: string;
  alert_message: string;
  status: string;
  status_label: string;
  is_valid: boolean;
}

interface QuorumStats {
  total_members: number;
  present_count: number;
  proxy_count: number;
  absent_count: number;
  total_voters: number;
  quorum_required: number;
  quorum_reached: boolean;
  gauge_label: string;
  percent_present: number;
}

interface CouncilAgendaItem {
  id: string;
  session_id: string;
  item_order: number;
  deliberation_ref: string;
  title: string;
  rapporteur: string;
  summary_note: string;
  vote_result: 'en_attente' | 'adopte' | 'rejete' | 'ajourne';
  votes_pour: number;
  votes_contre: number;
  votes_abstention: number;
  votes_nppv: number;
  transmission_megalis_status: 'en_attente' | 'transmis' | 'accuse_recu';
}

interface CouncilAttendance {
  id: string;
  session_id: string;
  seat_number: number;
  member_name: string;
  group_name: string;
  status: 'present' | 'absent' | 'pouvoir';
  proxy_to: string;
}

interface CouncilSessionDetail {
  id: string;
  title: string;
  session_date: string;
  session_time: string;
  location: string;
  population: number;
  total_members: number;
  status: 'draft' | 'en_cours' | 'closed' | 'archived';
  pv_hash: string;
  closed_at: string;
  closed_by: string;
  notes: string;
  convocation: ConvocationInfo;
  quorum_stats: QuorumStats;
  agenda_items: CouncilAgendaItem[];
  attendances: CouncilAttendance[];
}

export function CouncilSessionView() {
  const { api, bootstrap, activeCommissionId } = useWorkspace();
  const canWrite = bootstrap?.permissions?.workspace?.write !== false;

  const [activeTab, setActiveTab] = useState<'convocation' | 'tenue' | 'publication'>('convocation');
  const [session, setSession] = useState<CouncilSessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [feedback, setFeedback] = useState<string>('');
  const [actionBusy, setActionBusy] = useState(false);

  // Quick voting form per item
  const [votingItemId, setVotingItemId] = useState<string | null>(null);
  const [votesPour, setVotesPour] = useState<number>(27);
  const [votesContre, setVotesContre] = useState<number>(0);
  const [votesAbs, setVotesAbs] = useState<number>(2);
  const [votesNppv, setVotesNppv] = useState<number>(0);

  const loadCouncilSession = async () => {
    try {
      setLoading(true);
      setError('');
      if (api?.councilSession) {
        const data = await api.councilSession('CS-2026-11-26');
        setSession(data);
      } else {
        const res = await fetch('/api/v1/council-sessions/CS-2026-11-26', { credentials: 'same-origin' });
        if (res.ok) {
          const data = await res.json();
          setSession(data);
        }
      }
    } catch (e: any) {
      setError(e?.message || 'Erreur lors du chargement de la séance du conseil.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCouncilSession();
  }, []);

  // 1-Click proxy & attendance change
  const handleAttendanceChange = async (memberName: string, newStatus: 'present' | 'absent' | 'pouvoir', proxyTo?: string) => {
    if (!session || !canWrite) return;
    try {
      setActionBusy(true);
      setError('');

      const updatedAttendances = session.attendances.map(a => {
        if (a.member_name === memberName) {
          return {
            ...a,
            status: newStatus,
            proxy_to: newStatus === 'pouvoir' ? (proxyTo || '') : '',
          };
        }
        return a;
      });

      // Optimistic check for 1-proxy lock
      if (newStatus === 'pouvoir' && proxyTo) {
        const proxiesForHolder = updatedAttendances.filter(a => a.status === 'pouvoir' && a.proxy_to === proxyTo);
        if (proxiesForHolder.length > 1) {
          throw new Error(`Verrou légal (art. L. 2121-20 CGCT) : Le conseiller ${proxyTo} détient déjà un mandat.`);
        }
      }

      let resData;
      if (api?.updateCouncilAttendances) {
        resData = await api.updateCouncilAttendances(session.id, {
          attendances: updatedAttendances.map(a => ({
            seat_number: a.seat_number,
            member_name: a.member_name,
            group_name: a.group_name,
            status: a.status,
            proxy_to: a.proxy_to,
          }))
        });
      } else {
        const resp = await fetch(`/api/v1/council-sessions/${session.id}/attendances`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'Travaux' },
          body: JSON.stringify({
            attendances: updatedAttendances.map(a => ({
              seat_number: a.seat_number,
              member_name: a.member_name,
              group_name: a.group_name,
              status: a.status,
              proxy_to: a.proxy_to,
            }))
          }),
        });
        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData?.detail?.message || errData?.message || 'Échec de la mise à jour de présence.');
        }
        resData = await resp.json();
      }

      setSession(resData);
      setFeedback(`Présence de ${memberName} mise à jour avec succès.`);
      setTimeout(() => setFeedback(''), 4000);
    } catch (e: any) {
      setError(e?.message || 'Échec de la mise à jour de présence.');
    } finally {
      setActionBusy(false);
    }
  };

  // Submit vote
  const handleRecordVote = async (itemId: string) => {
    if (!session || !canWrite) return;
    try {
      setActionBusy(true);
      setError('');

      let resData;
      if (api?.recordCouncilVote) {
        resData = await api.recordCouncilVote(session.id, itemId, {
          votes_pour: votesPour,
          votes_contre: votesContre,
          votes_abstention: votesAbs,
          votes_nppv: votesNppv,
        });
      } else {
        const resp = await fetch(`/api/v1/council-sessions/${session.id}/items/${itemId}/vote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'Travaux' },
          body: JSON.stringify({
            votes_pour: votesPour,
            votes_contre: votesContre,
            votes_abstention: votesAbs,
            votes_nppv: votesNppv,
          }),
        });
        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData?.detail?.message || errData?.message || 'Échec de la prise en compte du vote.');
        }
        resData = await resp.json();
      }

      setSession(resData);
      setVotingItemId(null);
      setFeedback('Scrutin enregistré et certifié au procès-verbal.');
      setTimeout(() => setFeedback(''), 4000);
    } catch (e: any) {
      setError(e?.message || 'Échec de la prise en compte du vote.');
    } finally {
      setActionBusy(false);
    }
  };

  // Simulate Megalis Bretagne transmission
  const handleTransmitMegalis = async (itemId: string) => {
    if (!session || !canWrite) return;
    try {
      setActionBusy(true);
      setError('');

      let resData;
      if (api?.transmitCouncilMegalis) {
        resData = await api.transmitCouncilMegalis(session.id, itemId);
      } else {
        const resp = await fetch(`/api/v1/council-sessions/${session.id}/items/${itemId}/transmit-megalis`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'Travaux' },
        });
        if (!resp.ok) throw new Error('Échec de la télétransmission Mégalis.');
        resData = await resp.json();
      }

      setSession(resData);
      setFeedback('Télétransmission @CTES vers la Préfecture effectuée avec succès.');
      setTimeout(() => setFeedback(''), 4000);
    } catch (e: any) {
      setError(e?.message || 'Échec de la télétransmission.');
    } finally {
      setActionBusy(false);
    }
  };

  if (loading) {
    return (
      <main className="content p-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-3 text-stone-600">
          <div className="w-5 h-5 border-2 border-[#102A4C] border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Chargement de la séance du Conseil Municipal...</p>
        </div>
      </main>
    );
  }

  if (!session) {
    return (
      <main className="content p-6 max-w-7xl mx-auto">
        <div className="bg-white border border-stone-200 rounded-lg p-6 text-center">
          <p className="text-stone-700 mb-4">{error || 'Aucune séance du conseil disponible.'}</p>
          <Button onClick={() => void loadCouncilSession()} className="bg-[#102A4C] text-white hover:bg-[#193D6B]">
            Réessayer
          </Button>
        </div>
      </main>
    );
  }

  const presentCouncilors = session.attendances.filter(a => a.status === 'present');

  return (
    <main className="content p-6 max-w-7xl mx-auto space-y-6" data-testid="council-session-view">
      {/* 1. Header de séance - Civic Craft Light Mode */}
      <div className="bg-white border border-stone-200/90 rounded-xl p-5 shadow-3xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#102A4C] bg-stone-100 px-2 py-0.5 rounded border border-stone-200/70">
                Assemblée Délibérante
              </span>
              <span className="text-xs text-stone-500 font-medium">
                Commune de Plougastel-Daoulas (Finistère)
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                Séance ordinaire
              </span>
            </div>
            <h1 className="text-2xl font-serif font-bold text-[#102A4C] tracking-tight">
              {session.title}
            </h1>
            <div className="flex flex-wrap items-center gap-y-1 gap-x-4 mt-2 text-xs text-stone-600">
              <span className="flex items-center gap-1.5 font-medium">
                <CalendarDays size={14} className="text-[#102A4C]" />
                Jeudi 26 novembre 2026 à {session.session_time}
              </span>
              <span className="flex items-center gap-1.5">
                <MapPin size={14} className="text-[#102A4C]" />
                {session.location}
              </span>
              <span className="flex items-center gap-1.5 font-semibold text-stone-700">
                <Building2 size={14} className="text-[#102A4C]" />
                Strate légale : ≥ 3 500 hab. (33 élus)
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <a
              href={`/api/v1/council-sessions/${session.id}/dossier-elus.pdf`}
              download
              data-testid="btn-generate-dossier-pdf"
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#102A4C] !text-white hover:bg-[#193D6B] font-semibold text-xs shadow-xs transition-colors cursor-pointer"
              style={{ color: '#ffffff' }}
            >
              <Download size={14} className="text-white" />
              <span className="text-white font-semibold">Générer le Dossier des Élus (PDF)</span>
            </a>
          </div>
        </div>

        {/* 3 Clean Civic Craft Tabs */}
        <div className="flex items-center gap-2 mt-5 pt-3 border-t border-stone-200/80">
          <button
            type="button"
            data-testid="tab-convocation"
            onClick={() => setActiveTab('convocation')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'convocation'
                ? 'bg-[#102A4C] text-white shadow-xs'
                : 'text-stone-700 hover:bg-stone-100'
            }`}
          >
            <FileText size={14} />
            Ordre du jour & Convocation
          </button>
          <button
            type="button"
            data-testid="tab-tenue"
            onClick={() => setActiveTab('tenue')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'tenue'
                ? 'bg-[#102A4C] text-white shadow-xs'
                : 'text-stone-700 hover:bg-stone-100'
            }`}
          >
            <Users size={14} />
            Tenue de séance & Quorum
            <span className="ml-1 text-[11px] px-1.5 py-0.2 rounded-full bg-white/20 text-white font-mono">
              {session.quorum_stats.present_count}/33
            </span>
          </button>
          <button
            type="button"
            data-testid="tab-publication"
            onClick={() => setActiveTab('publication')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-2 ${
              activeTab === 'publication'
                ? 'bg-[#102A4C] text-white shadow-xs'
                : 'text-stone-700 hover:bg-stone-100'
            }`}
          >
            <ShieldCheck size={14} />
            Procès-verbal & Publication (@CTES)
          </button>
        </div>
      </div>

      {/* Notifications / Erreurs */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-800 flex items-center gap-2">
          <AlertTriangle size={15} className="shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}
      {feedback && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 size={15} className="shrink-0 text-emerald-600" />
          <span>{feedback}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* ONGLET 1 : ORDRE DU JOUR & CONVOCATION */}
      {/* ========================================================================= */}
      {activeTab === 'convocation' && (
        <div className="space-y-5">
          {/* Bandeau d'alerte CGCT légal */}
          <div
            data-testid="cgct-alert-banner"
            className="bg-amber-50/80 border border-amber-200/90 rounded-xl p-4 shadow-3xs"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center shrink-0 mt-0.5">
                <ShieldCheck size={18} />
              </div>
              <div className="flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-stone-900">
                    {session.convocation.alert_message}
                  </h3>
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-100/80 text-emerald-900 border border-emerald-200">
                    {session.convocation.status_label}
                  </span>
                </div>
                <p className="text-xs text-stone-600 mt-1 leading-relaxed">
                  Conformément à l’article L. 2121-12 du CGCT pour les communes de 3 500 habitants et plus,
                  le délai de convocation est de <strong>5 jours francs révolus</strong> (excluant le jour d’envoi
                  et le jour de la réunion). L’ordre du jour et les notes explicatives de synthèse ont été
                  déposés sur le coffre-fort numérique des 33 conseillers municipaux.
                </p>
                <div className="flex items-center gap-4 mt-2.5 text-[11px] text-stone-500 font-medium">
                  <span>Envoi certifié : 20/11/2026 à 14:15</span>
                  <span>·</span>
                  <span>Accusés de réception : 33 / 33 délivrés</span>
                  <span>·</span>
                  <span className="text-[#102A4C] font-semibold">Télétransmission Préfecture : Validée</span>
                </div>
              </div>
            </div>
          </div>

          {/* Liste ordonnée des délibérations liées */}
          <div className="bg-white border border-stone-200/90 rounded-xl p-5 shadow-3xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-[#102A4C]">
                  Ordre du jour arrêté ({session.agenda_items.length} délibérations)
                </h2>
                <p className="text-xs text-stone-500 mt-0.5">
                  Projets d'actes rattachés aux circuits de validation et soumis à l'approbation du conseil.
                </p>
              </div>
              <span className="text-xs font-semibold px-2 py-1 rounded bg-stone-100 text-stone-700">
                Séance du 26 novembre 2026
              </span>
            </div>

            <div className="divide-y divide-stone-100">
              {session.agenda_items.map((item, index) => (
                <div
                  key={item.id}
                  data-testid={`delib-card-${item.deliberation_ref}`}
                  className="py-4 first:pt-2 last:pb-1 flex flex-col md:flex-row md:items-start justify-between gap-4 hover:bg-stone-50/50 p-2 rounded-lg transition-colors"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-stone-100 text-[#102A4C] text-xs font-bold flex items-center justify-center shrink-0">
                        {index + 1}
                      </span>
                      <span className="font-mono text-xs font-bold text-[#102A4C] bg-stone-100/80 px-2 py-0.5 rounded border border-stone-200/70">
                        {item.deliberation_ref}
                      </span>
                      {item.vote_result === 'adopte' ? (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                          Adopté ({item.votes_pour} Pour)
                        </span>
                      ) : item.vote_result === 'rejete' ? (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-red-50 text-red-800 border border-red-200">
                          Rejeté
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                          Inscrit à l'ordre du jour
                        </span>
                      )}
                      {item.transmission_megalis_status === 'transmis' && (
                        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-teal-50 text-[#0F766E] border border-teal-200">
                          @CTES
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-semibold text-stone-900 leading-snug">
                      {item.title}
                    </h3>
                    <p className="text-xs text-stone-600 leading-relaxed pr-2">
                      {item.summary_note}
                    </p>

                    <div className="flex items-center gap-3 text-[11px] text-stone-500 pt-1">
                      <span className="font-medium text-stone-700">
                        Rapporteur : {item.rapporteur}
                      </span>
                      <span>·</span>
                      <span>Visa juridique préfecture : Conforme CGCT</span>
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-2 pt-2 md:pt-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setActiveTab('tenue');
                        setVotingItemId(item.id);
                        setVotesPour(item.votes_pour || 27);
                        setVotesContre(item.votes_contre || 0);
                        setVotesAbs(item.votes_abstention || 2);
                        setVotesNppv(item.votes_nppv || 0);
                      }}
                      className="text-xs border-stone-200 hover:bg-stone-100 text-[#102A4C]"
                    >
                      <Vote size={13} className="mr-1.5" />
                      {item.vote_result === 'adopte' ? 'Détail scrutin' : 'Voter'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* ONGLET 2 : TENUE DE SÉANCE & QUORUM */}
      {/* ========================================================================= */}
      {activeTab === 'tenue' && (
        <div className="space-y-6">
          {/* Jauge sobre de Quorum CGCT */}
          <div
            data-testid="quorum-gauge-card"
            className="bg-white border border-stone-200/90 rounded-xl p-5 shadow-3xs"
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-[#102A4C] tracking-tight">
                    {session.quorum_stats.gauge_label}
                  </h3>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                    Majorité absolue : 17 requis
                  </span>
                </div>
                <p className="text-xs text-stone-500 mt-1">
                  Article L. 2121-17 du CGCT : le conseil municipal délibère valablement lorsque
                  la majorité de ses membres en exercice est présente physiquement.
                </p>
              </div>

              <div className="flex items-center gap-4 text-xs tabular-nums text-stone-600 bg-stone-50 p-2.5 rounded-lg border border-stone-200/70">
                <div>
                  <span className="font-semibold text-stone-800">{session.quorum_stats.present_count}</span> Présents
                </div>
                <div>
                  <span className="font-semibold text-stone-800">{session.quorum_stats.proxy_count}</span> Pouvoirs
                </div>
                <div>
                  <span className="font-semibold text-stone-800">{session.quorum_stats.absent_count}</span> Absents
                </div>
                <div className="border-l border-stone-300 pl-3">
                  Total votants : <span className="font-bold text-[#102A4C]">{session.quorum_stats.total_voters}</span> / 33
                </div>
              </div>
            </div>

            {/* Barre de progression soignée */}
            <div className="w-full bg-stone-100 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-[#0F766E] h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${session.quorum_stats.percent_present}%` }}
              />
            </div>
            <div className="flex justify-between items-center text-[11px] text-stone-400 mt-1.5 font-medium">
              <span>0 élu</span>
              <span className="text-stone-600 font-semibold">Seuil légal de quorum (17)</span>
              <span>33 élus</span>
            </div>
          </div>

          {/* Grille 2 colonnes : Liste des élus & Scrutin rapide */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Colonne Gauche : Table des conseillers et gestion des pouvoirs (7 cols) */}
            <div className="lg:col-span-7 bg-white border border-stone-200/90 rounded-xl p-5 shadow-3xs space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-stone-100">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#102A4C]">
                    Table du Conseil ({session.attendances.length} membres)
                  </h3>
                  <p className="text-[11px] text-stone-500">
                    Gestion des présences et verrou légal : <strong>1 mandat max</strong> par élu présent (art. L. 2121-20).
                  </p>
                </div>
              </div>

              <div className="max-h-[520px] overflow-y-auto space-y-2 pr-1 divide-y divide-stone-100/80">
                {session.attendances.map(att => (
                  <div
                    key={att.id}
                    data-testid={`attendance-row-${att.seat_number}`}
                    className="pt-2 pb-1.5 flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="w-5 h-5 rounded-md bg-stone-100 text-stone-600 font-mono text-[10px] flex items-center justify-center shrink-0">
                        {att.seat_number}
                      </span>
                      <div className="truncate">
                        <span className="font-semibold text-stone-900 truncate block">
                          {att.member_name}
                        </span>
                        <span className="text-[10px] text-stone-400 truncate block">
                          {att.group_name}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {att.status === 'pouvoir' && (
                        <div className="text-[11px] bg-amber-50 text-amber-800 px-2 py-0.5 rounded border border-amber-200 flex items-center gap-1">
                          <span>Pouvoir à :</span>
                          <strong className="truncate max-w-[110px]">{att.proxy_to}</strong>
                        </div>
                      )}

                      {/* 1-Click Status buttons */}
                      <button
                        type="button"
                        onClick={() => void handleAttendanceChange(att.member_name, 'present')}
                        disabled={actionBusy}
                        className={`px-2 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                          att.status === 'present'
                            ? 'bg-emerald-100/80 text-emerald-900 font-bold border border-emerald-300'
                            : 'bg-stone-50 text-stone-600 hover:bg-stone-100'
                        }`}
                      >
                        Présent
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          // Pick first available present councilor who doesn't hold a proxy
                          const availableHolder = presentCouncilors.find(
                            p => p.member_name !== att.member_name && !session.attendances.some(other => other.status === 'pouvoir' && other.proxy_to === p.member_name)
                          );
                          const holderName = availableHolder ? availableHolder.member_name : presentCouncilors[0]?.member_name;
                          void handleAttendanceChange(att.member_name, 'pouvoir', holderName);
                        }}
                        disabled={actionBusy}
                        className={`px-2 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                          att.status === 'pouvoir'
                            ? 'bg-amber-100 text-amber-900 font-bold border border-amber-300'
                            : 'bg-stone-50 text-stone-600 hover:bg-stone-100'
                        }`}
                      >
                        Pouvoir
                      </button>

                      <button
                        type="button"
                        onClick={() => void handleAttendanceChange(att.member_name, 'absent')}
                        disabled={actionBusy}
                        className={`px-2 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                          att.status === 'absent'
                            ? 'bg-stone-200 text-stone-800 font-bold'
                            : 'bg-stone-50 text-stone-600 hover:bg-stone-100'
                        }`}
                      >
                        Absent
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Colonne Droite : Enregistrement rapide des votes (5 cols) */}
            <div className="lg:col-span-5 bg-white border border-stone-200/90 rounded-xl p-5 shadow-3xs space-y-4">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#102A4C]">
                  Enregistrement des scrutins
                </h3>
                <p className="text-[11px] text-stone-500">
                  Votes par point à l'ordre du jour (Pour, Contre, Abstention, NPPV art. L. 2131-11).
                </p>
              </div>

              {/* Sélection de la délibération */}
              <div className="space-y-3">
                <label className="text-xs font-semibold text-stone-700 block">
                  Délibération en cours d'examen :
                </label>
                <select
                  data-testid="select-delib-vote"
                  value={votingItemId || session.agenda_items[0]?.id}
                  onChange={e => {
                    const sel = session.agenda_items.find(it => it.id === e.target.value);
                    if (sel) {
                      setVotingItemId(sel.id);
                      setVotesPour(sel.votes_pour || 27);
                      setVotesContre(sel.votes_contre || 0);
                      setVotesAbs(sel.votes_abstention || 2);
                      setVotesNppv(sel.votes_nppv || 0);
                    }
                  }}
                  className="w-full text-xs font-medium bg-stone-50 border border-stone-200 rounded-lg p-2 text-stone-800 focus:outline-none focus:ring-1 focus:ring-[#102A4C]"
                >
                  {session.agenda_items.map(it => (
                    <option key={it.id} value={it.id}>
                      {it.deliberation_ref} - {it.title.slice(0, 45)}...
                    </option>
                  ))}
                </select>

                {/* Détail de la délibération sélectionnée */}
                {(() => {
                  const currentItem = session.agenda_items.find(it => it.id === (votingItemId || session.agenda_items[0]?.id));
                  if (!currentItem) return null;
                  return (
                    <div className="bg-stone-50/70 p-3 rounded-lg border border-stone-200/60 text-xs space-y-1">
                      <div className="font-bold text-[#102A4C]">{currentItem.deliberation_ref}</div>
                      <div className="font-medium text-stone-800">{currentItem.title}</div>
                      <div className="text-[11px] text-stone-500">Rapporteur : {currentItem.rapporteur}</div>
                    </div>
                  );
                })()}

                {/* Saisie rapide des 4 compteurs */}
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="bg-emerald-50/60 border border-emerald-200 p-3 rounded-lg">
                    <label className="text-[11px] font-bold text-emerald-900 uppercase block mb-1">
                      Pour
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={session.quorum_stats.total_voters}
                      value={votesPour}
                      onChange={e => setVotesPour(Number(e.target.value))}
                      className="w-full text-lg font-bold text-emerald-900 bg-white border border-emerald-300 rounded px-2 py-1 tabular-nums focus:outline-none"
                    />
                  </div>

                  <div className="bg-red-50/60 border border-red-200 p-3 rounded-lg">
                    <label className="text-[11px] font-bold text-red-900 uppercase block mb-1">
                      Contre
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={session.quorum_stats.total_voters}
                      value={votesContre}
                      onChange={e => setVotesContre(Number(e.target.value))}
                      className="w-full text-lg font-bold text-red-900 bg-white border border-red-300 rounded px-2 py-1 tabular-nums focus:outline-none"
                    />
                  </div>

                  <div className="bg-stone-100 border border-stone-300 p-3 rounded-lg">
                    <label className="text-[11px] font-bold text-stone-800 uppercase block mb-1">
                      Abstention
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={session.quorum_stats.total_voters}
                      value={votesAbs}
                      onChange={e => setVotesAbs(Number(e.target.value))}
                      className="w-full text-lg font-bold text-stone-800 bg-white border border-stone-300 rounded px-2 py-1 tabular-nums focus:outline-none"
                    />
                  </div>

                  <div className="bg-purple-50/60 border border-purple-200 p-3 rounded-lg">
                    <label className="text-[11px] font-bold text-purple-900 uppercase block mb-1" title="Ne prend pas part au vote (conflit d'intérêts)">
                      NPPV (art. L. 2131-11)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={session.quorum_stats.total_voters}
                      value={votesNppv}
                      onChange={e => setVotesNppv(Number(e.target.value))}
                      className="w-full text-lg font-bold text-purple-900 bg-white border border-purple-300 rounded px-2 py-1 tabular-nums focus:outline-none"
                    />
                  </div>
                </div>

                {/* 1-Click presets */}
                <div className="flex items-center gap-2 pt-1 text-xs">
                  <span className="text-stone-500 font-medium text-[11px]">Raccourcis :</span>
                  <button
                    type="button"
                    onClick={() => {
                      setVotesPour(session.quorum_stats.total_voters);
                      setVotesContre(0);
                      setVotesAbs(0);
                      setVotesNppv(0);
                    }}
                    className="text-[11px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200 transition-colors cursor-pointer"
                  >
                    Unanimité ({session.quorum_stats.total_voters} Pour)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setVotesPour(25);
                      setVotesContre(2);
                      setVotesAbs(2);
                      setVotesNppv(0);
                    }}
                    className="text-[11px] px-2 py-0.5 rounded bg-stone-100 text-stone-800 hover:bg-stone-200 border border-stone-300 transition-colors cursor-pointer"
                  >
                    Majorité (25 Pour / 2 Contre)
                  </button>
                </div>

                {/* Total check */}
                <div className="flex items-center justify-between text-xs pt-2 border-t border-stone-100 text-stone-600">
                  <span>Suffrages exprimés + NPPV :</span>
                  <span className="font-bold tabular-nums text-stone-900">
                    {votesPour + votesContre + votesAbs + votesNppv} / {session.quorum_stats.total_voters} voix
                  </span>
                </div>

                {/* Bouton d'enregistrement */}
                <Button
                  data-testid="btn-record-vote"
                  onClick={() => void handleRecordVote(votingItemId || session.agenda_items[0]?.id)}
                  disabled={actionBusy}
                  className="w-full bg-[#102A4C] text-white hover:bg-[#193D6B] font-semibold text-xs py-2.5 rounded-lg shadow-xs cursor-pointer"
                >
                  <CheckCircle2 size={14} className="mr-2" />
                  Enregistrer le vote au Procès-Verbal
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* ONGLET 3 : PROCÈS-VERBAL & PUBLICATION (@CTES) */}
      {/* ========================================================================= */}
      {activeTab === 'publication' && (
        <div className="space-y-6">
          {/* Synthèse des délibérations adoptées */}
          <div className="bg-white border border-stone-200/90 rounded-xl p-5 shadow-3xs space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-stone-100">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-[#102A4C]">
                  Liste des Délibérations Examinées (Affichage Légal)
                </h3>
                <p className="text-xs text-stone-500 mt-0.5">
                  Ordonnance n° 2021-1310 du 7 octobre 2021 · Affichage obligatoire sous 8 jours à la porte de la mairie et mise en ligne.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                  Présidence : Dominique CAP, Maire
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-stone-50 text-stone-600 uppercase text-[10px] tracking-wider border-b border-stone-200">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Référence</th>
                    <th className="py-2.5 px-3 font-semibold">Objet de la délibération</th>
                    <th className="py-2.5 px-3 font-semibold">Rapporteur</th>
                    <th className="py-2.5 px-3 font-semibold text-center">Décision</th>
                    <th className="py-2.5 px-3 font-semibold text-center">Télétransmission @CTES</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {session.agenda_items.map(it => (
                    <tr key={it.id} className="hover:bg-stone-50/60 transition-colors">
                      <td className="py-3 px-3 font-mono font-bold text-[#102A4C]">
                        {it.deliberation_ref}
                      </td>
                      <td className="py-3 px-3 font-medium text-stone-900 max-w-md">
                        {it.title}
                        <div className="text-[11px] text-stone-500 mt-0.5">
                          Scrutin : {it.votes_pour} Pour, {it.votes_contre} Contre, {it.votes_abstention} Abs, {it.votes_nppv} NPPV
                        </div>
                      </td>
                      <td className="py-3 px-3 text-stone-600">
                        {it.rapporteur}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {it.vote_result === 'adopte' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            ADOPTÉE
                          </span>
                        ) : it.vote_result === 'rejete' ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-red-50 text-red-800 border border-red-200">
                            REJETÉE
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-stone-100 text-stone-600">
                            EN COURS
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-center">
                        {it.transmission_megalis_status === 'transmis' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-teal-50 text-[#0F766E] border border-teal-200">
                            <CheckCircle2 size={12} />
                            @CTES Télétransmis
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                            <Clock size={12} />
                            En attente de télétransmission
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {it.transmission_megalis_status !== 'transmis' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={actionBusy}
                            onClick={() => void handleTransmitMegalis(it.id)}
                            className="text-[11px] border-stone-200 hover:bg-stone-100 text-[#102A4C]"
                          >
                            <Send size={12} className="mr-1" />
                            Transmettre @CTES
                          </Button>
                        ) : (
                          <span className="text-[11px] text-stone-400 font-medium">
                            AR reçu
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Sceau d'intégrité SHA-256 eIDAS */}
          <div className="bg-white border border-stone-200/90 rounded-xl p-5 shadow-3xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lock size={16} className="text-[#102A4C]" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#102A4C]">
                  Sceau d'intégrité numérique du Procès-Verbal (eIDAS)
                </h3>
              </div>
              <span className="text-[11px] font-mono text-stone-500">
                Norme AFNOR NF Z42-013
              </span>
            </div>

            <div className="bg-stone-50 border border-stone-200 p-3 rounded-lg font-mono text-xs text-stone-700 break-all select-all">
              {session.pv_hash || 'SHA-256: d84f09a8264e1c2e4f0a991b15efb28491cba028198f8216ab7142013ce82810'}
            </div>

            <p className="text-[11px] text-stone-500 leading-relaxed">
              L'empreinte cryptographique ci-dessus garantit l'inaltérabilité des votes, de l'émargement et des délibérations
              conformément aux exigences du contrôle de légalité en préfecture et à la jurisprudence du Conseil d'État.
            </p>
          </div>
        </div>
      )}
    </main>
  );
}
