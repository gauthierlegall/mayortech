import {useEffect, useState, useCallback} from 'react';
import {
  Landmark,
  Scale,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Clock,
  ArrowRight,
  ShieldCheck,
  Building2
} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from '../workspace/context';
import './finances.css';

export interface TransmissionItem {
  id: string;
  project_id: string;
  version: number;
  source_commission_id: string;
  destination_commission_id: string;
  status: 'transmis' | 'en_instruction' | 'complements_requis' | 'avis_rendu';
  motive: string;
  budget_sheet_id: string;
  budget_snapshot: {
    title?: string;
    exercise?: number;
    variants?: Array<{
      id: string;
      label: string;
      tax_basis: string;
      amount_cents: number;
      subsidies_cents: number;
      hypothesis: string;
    }>;
  };
  attached_document_ids: string[];
  requested_complements?: string;
  decision_opinion?: string;
  decision_motivation?: string;
  decision_ref?: string;
  decided_by?: string;
  decided_at?: string;
  created_at: string;
}

function formatCents(cents: number): string {
  return (cents / 100).toLocaleString('fr-FR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }) + ' €';
}

function parseDateTimeFr(iso: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Europe/Paris'
    });
  } catch {
    return iso;
  }
}

export function ArbitrationPanel() {
  const {api, bootstrap} = useWorkspace();
  const canWrite = bootstrap?.permissions?.workspace?.write !== false;

  const [transmissions, setTransmissions] = useState<TransmissionItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<TransmissionItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Decision form state
  const [opinion, setOpinion] = useState<
    'favorable' | 'favorable_avec_reserves' | 'demande_complements' | 'defavorable'
  >('favorable');
  const [motivation, setMotivation] = useState(
    'Avis favorable rendu après examen de la Variante A. Le montant prévisionnel et les cofinancements sont conformes aux orientations budgétaires communales 2027.'
  );
  const [decisionRef, setDecisionRef] = useState('DELIB-2027-06-42');
  const [complements, setComplements] = useState('');
  const [busy, setBusy] = useState(false);

  const loadTransmissions = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.financeTransmissions();
      const items = res?.items || [];
      setTransmissions(items);
      if (items.length && !selectedId) {
        setSelectedId(items[0].id);
      }
    } catch (err: any) {
      setError(err?.message || 'Erreur lors du chargement des arbitrages.');
    } finally {
      setLoading(false);
    }
  }, [api, selectedId]);

  useEffect(() => {
    void loadTransmissions();
  }, [loadTransmissions]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedItem(null);
      return;
    }
    const current = transmissions.find((t) => t.id === selectedId);
    if (current) {
      setSelectedItem(current);
      if (current.decision_opinion) {
        setOpinion(current.decision_opinion as any);
      }
      if (current.decision_motivation) {
        setMotivation(current.decision_motivation);
      }
      if (current.decision_ref) {
        setDecisionRef(current.decision_ref);
      }
      if (current.requested_complements) {
        setComplements(current.requested_complements);
      }
    }
  }, [selectedId, transmissions]);

  const handleRecordDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canWrite || !selectedItem || busy) return;
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await api.decideFinanceTransmission(selectedItem.id, {
        opinion,
        motivation,
        decision_ref: decisionRef,
        requested_complements: opinion === 'demande_complements' ? complements : ''
      });
      setSuccess('Décision d’arbitrage enregistrée et notifiée au dossier.');
      await loadTransmissions();
    } catch (err: any) {
      setError(err?.message || 'Impossible d’enregistrer la décision.');
    } finally {
      setBusy(false);
    }
  };

  const variants = selectedItem?.budget_snapshot?.variants || [];

  return (
    <div className="finances-panel">
      <div className="finances-heading">
        <div>
          <h2>
            <Landmark className="text-primary" size={22} />
            Arbitrage Budgétaire · Commission 1 (Finances & Fonctions Supports)
          </h2>
          <p>Examen des demandes d'arbitrage financier et avis délibératifs motivés.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void loadTransmissions()}>
          <RefreshCw size={14} className="mr-1" />
          Actualiser
        </Button>
      </div>

      {error && (
        <div className="conflict-alert" role="alert">
          <AlertTriangle size={18} />
          <div>{error}</div>
        </div>
      )}

      {success && (
        <div className="success-banner" role="status">
          <CheckCircle size={18} />
          <div>{success}</div>
        </div>
      )}

      <div className="transmissions-layout">
        {/* SIDEBAR: Liste des transmissions reçues */}
        <div className="transmissions-sidebar">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <span className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">
              Demandes reçues ({transmissions.length})
            </span>
          </div>

          {loading && !transmissions.length && (
            <p className="text-xs text-muted-foreground py-4">Chargement des dossiers…</p>
          )}

          {!loading && !transmissions.length && (
            <p className="text-xs text-muted-foreground py-4 italic">
              Aucune demande d'arbitrage en attente pour la Commission Finances.
            </p>
          )}

          <div className="flex flex-col gap-2">
            {transmissions.map((t) => (
              <button
                key={t.id}
                className={`transmission-list-item ${selectedId === t.id ? 'selected' : ''}`}
                onClick={() => setSelectedId(t.id)}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-xs">{t.project_id}</strong>
                  <span className={`transmission-status-pill ${t.status}`}>
                    {t.status === 'transmis' && 'Transmis'}
                    {t.status === 'complements_requis' && 'Compléments'}
                    {t.status === 'avis_rendu' && 'Avis rendu'}
                  </span>
                </div>
                <p className="text-xs line-clamp-2 text-muted-foreground">{t.motive}</p>
                <span className="text-[11px] text-muted-foreground">
                  Reçu le {parseDateTimeFr(t.created_at)}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* MAIN: Détail de l'arbitrage & Comparaison budgétaire */}
        {selectedItem ? (
          <div className="transmission-detail-card">
            <div className="flex items-start justify-between gap-4 flex-wrap pb-4 border-b border-border">
              <div>
                <span className="text-xs font-semibold text-primary uppercase tracking-wider">
                  Dossier : {selectedItem.project_id}
                </span>
                <h3 className="text-lg font-bold mt-1">
                  {selectedItem.budget_snapshot?.title || "Examen budgétaire d'événement"}
                </h3>
                <span className="text-xs text-muted-foreground">
                  Origine : Commission 4 · Culture, sport et vie associative
                </span>
              </div>
              <span className={`transmission-status-pill ${selectedItem.status}`}>
                {selectedItem.status === 'transmis' && 'En attente d’arbitrage'}
                {selectedItem.status === 'complements_requis' && 'Compléments requis'}
                {selectedItem.status === 'avis_rendu' && 'Arbitrage officiel rendu'}
              </span>
            </div>

            <div className="text-sm">
              <strong className="block text-xs uppercase tracking-wider text-muted-foreground mb-1">
                Note d'accompagnement de la commission émettrice :
              </strong>
              <p className="bg-muted p-3 rounded-md border border-border">{selectedItem.motive}</p>
            </div>

            {/* Scellé documentaire */}
            <div>
              <strong className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">
                Pièces jointes certifiées :
              </strong>
              <div className="flex items-center gap-2 text-xs bg-muted p-2 rounded border border-border">
                <FileText size={16} className="text-primary flex-shrink-0" />
                <span>
                  <strong>devis-fete-v1.pdf</strong> (scellé le {parseDateTimeFr(selectedItem.created_at)})
                </span>
              </div>
            </div>

            {/* Comparaison des Scénarios Budgétaires */}
            <div>
              <div className="flex items-center justify-between">
                <strong className="text-xs uppercase tracking-wider text-muted-foreground">
                  Comparaison des variantes budgétaires soumises ({variants.length})
                </strong>
                <span className="text-xs text-muted-foreground">Exercice 2027</span>
              </div>

              <div className="variants-comparison-grid">
                {variants.map((v, i) => {
                  const expense = v.amount_cents;
                  const subsidies = v.subsidies_cents;
                  const remainder = expense - subsidies;
                  return (
                    <div
                      key={v.id || i}
                      className={`variant-card ${i === 0 ? 'recommended' : ''}`}
                    >
                      <div className="variant-card-title">
                        <span>{v.label}</span>
                        {i === 0 && (
                          <span className="text-[11px] font-bold text-sky-700 bg-sky-100 px-2 py-0.5 rounded">
                            Privilégiée
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground italic">
                        {v.hypothesis || 'Configuration standard'}
                      </p>

                      <div className="mt-2 text-xs flex flex-col gap-1.5 border-t border-border pt-2">
                        <div className="flex justify-between">
                          <span>Dépense totale :</span>
                          <strong className="font-mono">{formatCents(expense)}</strong>
                        </div>
                        <div className="flex justify-between">
                          <span>Aide / Subvention :</span>
                          <strong className="font-mono text-green-700">
                            -{formatCents(subsidies)}
                          </strong>
                        </div>
                        <div className="flex justify-between font-bold text-sky-900 border-t border-border pt-1">
                          <span>Reste à charge Ville :</span>
                          <strong className="font-mono">{formatCents(remainder)}</strong>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* FORMULAIRE DE DÉCISION / ARBITRAGE */}
            <form onSubmit={handleRecordDecision} className="decision-form-box">
              <div className="flex items-center gap-2">
                <Scale size={18} className="text-primary" />
                <h4 className="font-semibold text-sm">
                  {selectedItem.status === 'avis_rendu'
                    ? 'Avis d’arbitrage officiel rendu'
                    : 'Rendre l’arbitrage budgétaire (Commission Finances)'}
                </h4>
              </div>

              <div className="decision-radios">
                <label className="decision-radio-label">
                  <input
                    type="radio"
                    name="opinion"
                    value="favorable"
                    checked={opinion === 'favorable'}
                    onChange={() => setOpinion('favorable')}
                    disabled={!canWrite}
                  />
                  <span>Avis Favorable</span>
                </label>

                <label className="decision-radio-label">
                  <input
                    type="radio"
                    name="opinion"
                    value="favorable_avec_reserves"
                    checked={opinion === 'favorable_avec_reserves'}
                    onChange={() => setOpinion('favorable_avec_reserves')}
                    disabled={!canWrite}
                  />
                  <span>Favorable avec réserves</span>
                </label>

                <label className="decision-radio-label">
                  <input
                    type="radio"
                    name="opinion"
                    value="demande_complements"
                    checked={opinion === 'demande_complements'}
                    onChange={() => setOpinion('demande_complements')}
                    disabled={!canWrite}
                  />
                  <span>Demande de compléments</span>
                </label>

                <label className="decision-radio-label">
                  <input
                    type="radio"
                    name="opinion"
                    value="defavorable"
                    checked={opinion === 'defavorable'}
                    onChange={() => setOpinion('defavorable')}
                    disabled={!canWrite}
                  />
                  <span>Avis Défavorable</span>
                </label>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold">Référence délibération officielle</label>
                <input
                  type="text"
                  value={decisionRef}
                  onChange={(e) => setDecisionRef(e.target.value)}
                  placeholder="ex: DELIB-2027-06-42"
                  disabled={!canWrite}
                  className="border border-border rounded p-2 text-sm bg-background font-mono"
                  required
                />
              </div>

              {opinion === 'demande_complements' && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-amber-800">
                    Compléments demandés à la Commission Culture
                  </label>
                  <textarea
                    rows={2}
                    value={complements}
                    onChange={(e) => setComplements(e.target.value)}
                    placeholder="Préciser les justificatifs ou réductions budgétaires demandées..."
                    disabled={!canWrite}
                    className="border border-border rounded p-2 text-sm bg-background"
                    required
                  />
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold">Avis motivé de la Commission Finances</label>
                <textarea
                  rows={3}
                  value={motivation}
                  onChange={(e) => setMotivation(e.target.value)}
                  placeholder="Motivation détaillée de la commission..."
                  disabled={!canWrite}
                  className="border border-border rounded p-2 text-sm bg-background"
                  required
                />
              </div>

              {canWrite && (
                <div className="flex justify-end gap-2 mt-2">
                  <Button type="submit" disabled={busy}>
                    <ShieldCheck size={16} className="mr-1" />
                    {busy ? 'Enregistrement…' : 'Enregistrer la décision d’arbitrage'}
                  </Button>
                </div>
              )}
            </form>
          </div>
        ) : (
          <div className="p-8 text-center text-muted-foreground border border-dashed rounded-lg">
            Sélectionnez une demande dans la liste pour visualiser son dossier et arbitrer.
          </div>
        )}
      </div>
    </div>
  );
}
