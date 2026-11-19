import React, {useState, useEffect} from 'react';
import {
  HeartHandshake,
  ShieldAlert,
  Plus,
  CheckCircle,
  AlertCircle,
  FileText,
  Euro,
  Scale,
  Calendar,
  Check,
  Calculator
} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog, DialogContent, DialogTitle, DialogDescription} from '@/components/ui/dialog';
import {useWorkspace} from '../workspace/context';
import {CANTEEN_BRACKETS_INFO, getBracketForQF} from './SchoolCampaignPanel';
import './school.css';

export interface SocialAidRecord {
  id: string;
  project_id?: string;
  aid_type: string;
  confidential_ref: string;
  amount_cents: number;
  commission_decision: 'accorde' | 'refuse' | 'ajourne';
  deliberation_ref: string;
  notes: string;
  created_at: string;
}

export function SocialAidPanel({projectId}: {projectId: string}) {
  const {api, bootstrap} = useWorkspace();
  const canWrite = bootstrap?.permissions?.workspace?.write !== false;

  const [records, setRecords] = useState<SocialAidRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [aidType, setAidType] = useState('secours_urgence');
  const [confRef, setConfRef] = useState('CCAS-PLOUG-2027-');
  const [amountEuros, setAmountEuros] = useState(150);
  const [decision, setDecision] = useState<'accorde' | 'refuse' | 'ajourne'>('accorde');
  const [delibRef, setDelibRef] = useState('DELIB-CCAS-2027-01');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Quick simulator
  const [quickQF, setQuickQF] = useState(480);

  useEffect(() => {
    let alive = true;
    async function loadAids() {
      try {
        setLoading(true);
        const res = await (api as any).projectSocialAid(projectId);
        if (!alive) return;
        setRecords(res?.items || []);
      } catch (err: any) {
        if (alive) setError(err.message || 'Impossible de charger le registre des aides.');
      } finally {
        if (alive) setLoading(false);
      }
    }
    loadAids();
    return () => {
      alive = false;
    };
  }, [api, projectId]);

  async function handleCreateAid() {
    try {
      setSubmitting(true);
      setError('');
      const created = await (api as any).createProjectSocialAid(projectId, {
        aid_type: aidType,
        confidential_ref: confRef,
        amount_cents: Math.round(amountEuros * 100),
        commission_decision: decision,
        deliberation_ref: delibRef,
        notes: notes,
      });
      setRecords(prev => [created, ...prev]);
      setSuccess(`Aide ${confRef} enregistrée avec décision : ${decision.toUpperCase()}.`);
      setDialogOpen(false);
      setNotes('');
    } catch (err: any) {
      setError(err.message || 'Échec de l’enregistrement de l’aide.');
    } finally {
      setSubmitting(false);
    }
  }

  const bracket = getBracketForQF(quickQF);
  const bracketInfo = CANTEEN_BRACKETS_INFO[bracket];

  return (
    <div className="school-panel">
      {/* Header */}
      <div className="school-panel-header">
        <div className="school-title-group">
          <h2>
            <HeartHandshake className="text-emerald-600" size={26} />
            Action Sociale, CCAS & Vie Scolaire
          </h2>
          <p>Dossier et interventions de solidarité sous contrôle de la Commission 2</p>
        </div>
        <div className="school-actions">
          {canWrite && (
            <Button onClick={() => setDialogOpen(true)}>
              <Plus size={16} className="mr-1" />
              Nouvelle demande d’aide
            </Button>
          )}
        </div>
      </div>

      {/* Confidentiality Warning */}
      <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-md text-sm flex items-start gap-2.5">
        <ShieldAlert className="text-amber-600 shrink-0 mt-0.5" size={18} />
        <div>
          <strong>Données sociales confidentielles :</strong> Ce registre fait l’objet d’une stricte traçabilité
          auprès du CCAS de Plougastel-Daoulas. Les identifiants nominatifs sont pseudonymisés conformément au secret professionnel.
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {success && (
        <div className="p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm flex items-center gap-2">
          <CheckCircle size={16} />
          {success}
        </div>
      )}

      {/* Social Aid Applications List */}
      <section>
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <Scale size={18} />
            Aides communales et secours d’urgence enregistrés ({records.length})
          </h3>
        </div>

        {records.length === 0 ? (
          <div className="p-6 bg-gray-50 border rounded text-center text-muted-foreground">
            Aucun enregistrement d’aide sociale pour ce dossier. Cliquez sur "Nouvelle demande d’aide" pour enregistrer une décision.
          </div>
        ) : (
          <div className="aid-cards-grid">
            {records.map(r => (
              <div key={r.id} className="aid-card">
                <div className="aid-card-header">
                  <span className="aid-ref">{r.confidential_ref}</span>
                  <span className="aid-type-pill">{r.aid_type.replace('_', ' ')}</span>
                </div>
                <div className="aid-amount">{(r.amount_cents / 100).toFixed(2)} €</div>
                <div>
                  <span className={`aid-decision ${r.commission_decision}`}>
                    {r.commission_decision === 'accorde' ? (
                      <Check size={14} />
                    ) : (
                      <AlertCircle size={14} />
                    )}
                    {r.commission_decision === 'accorde'
                      ? 'ACCORDÉ'
                      : r.commission_decision === 'refuse'
                      ? 'REFUSÉ'
                      : 'AJOURNÉ'}
                  </span>
                </div>
                {r.deliberation_ref && (
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    <FileText size={12} />
                    Délibération : <strong>{r.deliberation_ref}</strong>
                  </div>
                )}
                {r.notes && <p className="text-xs text-gray-600 mt-1">{r.notes}</p>}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Simulator Mini-Card */}
      <section className="simulator-card mt-2">
        <div className="simulator-header">
          <h3>
            <Calculator size={18} className="text-blue-600" />
            Vérificateur d’éligibilité tarification sociale cantine
          </h3>
          <span className="text-xs text-muted-foreground">Restauration scolaire Plougastel</span>
        </div>
        <div className="simulator-body">
          <div className="qf-input-group">
            <label htmlFor="quick-qf">Quotient Familial du foyer (€) :</label>
            <input
              id="quick-qf"
              type="number"
              min="0"
              value={quickQF}
              onChange={e => setQuickQF(Math.max(0, parseInt(e.target.value || '0', 10)))}
            />
          </div>
          <div className={`bracket-result-banner ${bracketInfo.css}`}>
            <div>
              <div className="bracket-name">{bracketInfo.label}</div>
              <div className="bracket-subsidy">{bracketInfo.subsidy}</div>
            </div>
            <div className="text-right">
              <span className="text-xs text-muted-foreground block">Reste à charge par repas :</span>
              <span className="bracket-price">{bracketInfo.rate}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Dialog: Create Aid */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogTitle>Enregistrer une décision d’aide sociale CCAS</DialogTitle>
          <DialogDescription>
            Traçabilité formelle de l’attribution d’aide votée en séance de commission.
          </DialogDescription>
          <div className="space-y-3 pt-2">
            <div>
              <label className="text-xs font-semibold block mb-1">Type d’aide :</label>
              <select
                className="w-full p-2 border rounded text-sm bg-white"
                value={aidType}
                onChange={e => setAidType(e.target.value)}
              >
                <option value="secours_urgence">Secours d'urgence</option>
                <option value="aide_energie">Aide énergie / chauffage</option>
                <option value="aide_alimentaire">Aide alimentaire</option>
                <option value="aide_periscolaire">Aide aux activités périscolaires & sorties</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Identifiant confidentiel :</label>
              <input
                type="text"
                className="w-full p-2 border rounded font-mono text-sm"
                value={confRef}
                onChange={e => setConfRef(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Montant (€) :</label>
              <input
                type="number"
                min="0"
                step="5"
                className="w-full p-2 border rounded text-sm"
                value={amountEuros}
                onChange={e => setAmountEuros(Math.max(0, parseFloat(e.target.value || '0')))}
              />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Décision de la commission :</label>
              <select
                className="w-full p-2 border rounded text-sm bg-white"
                value={decision}
                onChange={e => setDecision(e.target.value as any)}
              >
                <option value="accorde">Accordé (favorable)</option>
                <option value="refuse">Refusé</option>
                <option value="ajourne">Ajourné (demande d'éléments complémentaires)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Référence de délibération :</label>
              <input
                type="text"
                className="w-full p-2 border rounded font-mono text-sm"
                value={delibRef}
                onChange={e => setDelibRef(e.target.value)}
                placeholder="DELIB-CCAS-2027-01"
              />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Observations / Motif :</label>
              <textarea
                className="w-full p-2 border rounded text-sm h-16"
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Ex : Prise en charge exceptionnelle sur fonds de solidarité communale."
              />
            </div>
            <div className="flex justify-end gap-2 pt-3">
              <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                Annuler
              </Button>
              <Button onClick={handleCreateAid} disabled={submitting || !confRef}>
                <Plus size={15} className="mr-1" />
                {submitting ? 'Enregistrement…' : 'Enregistrer la décision'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
