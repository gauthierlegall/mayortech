import React, { useState, useEffect } from 'react';
import { 
  UserCheck, UserX, Clock, CheckCircle2, AlertCircle, RefreshCw, 
  ShieldAlert, Building2, FileCheck, ArrowRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface PendingJoinRequest {
  id: string;
  email: string;
  nom: string;
  prenom: string;
  poste_souhaite: string;
  code_organisation: string;
  status: string;
  created_at: string;
}

export function EnrollmentApprovalQueue() {
  const [requests, setRequests] = useState<PendingJoinRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Decision draft state map { requestId: { commission, level, role, reason, busy } }
  const [decisionDrafts, setDecisionDrafts] = useState<Record<string, {
    commission: string;
    level: number;
    role: 'reader' | 'editor' | 'admin';
    reason: string;
    busy: boolean;
  }>>({});

  const fetchRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/organization/join-requests/pending');
      if (!res.ok) throw new Error('Impossible de charger la file d\'attente des adhésions.');
      const data: PendingJoinRequest[] = await res.json();
      setRequests(data);

      // Initialize drafts
      const drafts: Record<string, any> = {};
      data.forEach(r => {
        drafts[r.id] = {
          commission: 'commission-3',
          level: 2,
          role: 'editor',
          reason: 'Habilitation validée par la DGS',
          busy: false
        };
      });
      setDecisionDrafts(drafts);
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleDecision = async (requestId: string, decision: 'approve' | 'reject') => {
    const draft = decisionDrafts[requestId];
    if (!draft) return;

    setDecisionDrafts(prev => ({
      ...prev,
      [requestId]: { ...prev[requestId], busy: true }
    }));

    try {
      const res = await fetch(`/api/v1/organization/join-requests/${requestId}/decision`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux'
        },
        body: JSON.stringify({
          decision,
          assigned_commission: draft.commission,
          assigned_level: draft.level,
          assigned_role: draft.role,
          reason: draft.reason
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error?.message || 'Erreur lors de l’enregistrement de la décision.');
      }

      // Refresh queue
      await fetchRequests();
    } catch (err: any) {
      alert(err.message);
      setDecisionDrafts(prev => ({
        ...prev,
        [requestId]: { ...prev[requestId], busy: false }
      }));
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-7 h-7 text-rose-600" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              File d'Approbation Régalienne (DGS)
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Examen des demandes d'enrôlement · Attribution des commissions et des 6 niveaux d'habilitation
          </p>
        </div>

        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchRequests} 
          disabled={loading}
          className="flex items-center gap-1.5 self-start md:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualiser la File ({requests.length})
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {loading && requests.length === 0 ? (
        <div className="py-12 text-center text-slate-500 space-y-2">
          <Clock className="w-8 h-8  mx-auto text-slate-400" />
          <p className="text-sm font-medium">Chargement de la file d'attente...</p>
        </div>
      ) : requests.length === 0 ? (
        <div className="py-12 border-2 border-dashed border-slate-200 rounded-xl text-center space-y-2 bg-slate-50/50">
          <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
          <h3 className="font-bold text-slate-800 text-base">Aucune demande en attente</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Toutes les demandes d'adhésion ont été examinées et validées par la Direction Générale des Services.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map(req => {
            const draft = decisionDrafts[req.id] || {
              commission: 'commission-3',
              level: 2,
              role: 'editor',
              reason: '',
              busy: false
            };

            return (
              <div 
                key={req.id} 
                className="border rounded-xl p-5 bg-white shadow-xs hover:border-blue-300 transition-all space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-base text-slate-900">
                        {req.prenom} {req.nom}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-semibold flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        En attente
                      </span>
                    </div>
                    <p className="text-xs font-mono text-slate-500 mt-0.5">{req.email}</p>
                    <p className="text-xs text-slate-700 mt-1">
                      Poste souhaité : <strong>{req.poste_souhaite || 'Non spécifié'}</strong>
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="text-[11px] text-slate-400 font-mono">
                      Soumis le {new Date(req.created_at).toLocaleString('fr-FR')}
                    </span>
                    <div className="text-xs text-emerald-700 font-mono mt-0.5">
                      Code validé : <span className="font-bold">{req.code_organisation}</span>
                    </div>
                  </div>
                </div>

                {/* Assignment Controls */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded-lg border">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Commission permanente :
                    </label>
                    <select
                      value={draft.commission}
                      onChange={e => setDecisionDrafts(prev => ({
                        ...prev,
                        [req.id]: { ...prev[req.id], commission: e.target.value }
                      }))}
                      disabled={draft.busy}
                      className="w-full p-2 border rounded bg-white text-xs"
                    >
                      <option value="commission-1">1. Finances & Marchés CAO</option>
                      <option value="commission-2">2. Enfance & CCAS</option>
                      <option value="commission-3">3. Urbanisme, Travaux & Ports</option>
                      <option value="commission-4">4. Culture & Vie Associative</option>
                      <option value="all">Toutes (Direction Générale)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Niveau de responsabilité (0-5) :
                    </label>
                    <select
                      value={draft.level}
                      onChange={e => setDecisionDrafts(prev => ({
                        ...prev,
                        [req.id]: { ...prev[req.id], level: parseInt(e.target.value) }
                      }))}
                      disabled={draft.busy}
                      className="w-full p-2 border rounded bg-white text-xs"
                    >
                      <option value="1">Niveau 1 · Lecteur sectoriel</option>
                      <option value="2">Niveau 2 · Rédacteur / Instructeur</option>
                      <option value="3">Niveau 3 · Chef de Service</option>
                      <option value="4">Niveau 4 · Ordonnateur / Élu</option>
                      <option value="5">Niveau 5 · Administrateur / DGS</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Rôle d'écriture noyau :
                    </label>
                    <select
                      value={draft.role}
                      onChange={e => setDecisionDrafts(prev => ({
                        ...prev,
                        [req.id]: { ...prev[req.id], role: e.target.value as any }
                      }))}
                      disabled={draft.busy}
                      className="w-full p-2 border rounded bg-white text-xs capitalize"
                    >
                      <option value="reader">Lecteur seul (reader)</option>
                      <option value="editor">Éditeur dossiers (editor)</option>
                      <option value="admin">Administrateur (admin)</option>
                    </select>
                  </div>
                </div>

                {/* Actions Bar */}
                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <FileCheck className="w-4 h-4 text-slate-400" />
                    <span>L'approbation génère automatiquement le matricule et active l'accès.</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDecision(req.id, 'reject')}
                      disabled={draft.busy}
                      className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-rose-200"
                    >
                      <UserX className="w-3.5 h-3.5 mr-1" />
                      Refuser
                    </Button>

                    <Button
                      size="sm"
                      onClick={() => handleDecision(req.id, 'approve')}
                      disabled={draft.busy}
                      className="text-xs bg-emerald-700 hover:bg-emerald-800 text-white"
                    >
                      <UserCheck className="w-3.5 h-3.5 mr-1" />
                      {draft.busy ? 'Validation...' : 'Approuver & Habiliter'}
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
