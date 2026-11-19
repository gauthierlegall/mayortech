import {useEffect, useState, useCallback} from 'react';
import {
  CalendarDays,
  Building2,
  FileSpreadsheet,
  Send,
  AlertTriangle,
  CheckCircle,
  Download,
  Plus,
  Trash2,
  Clock,
  Landmark,
  Scale,
  RefreshCw,
  FileText
} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog, DialogContent, DialogTitle, DialogDescription} from '@/components/ui/dialog';
import {useWorkspace} from '../workspace/context';
import './culture.css';

export interface Room {
  id: string;
  name: string;
  capacity?: number;
}

export interface Reservation {
  id: string;
  project_id: string;
  room_id?: string;
  resource_id?: string;
  room_name?: string;
  resource_name?: string;
  start_time: string;
  end_time: string;
  status: string;
  notes?: string;
}

export interface BudgetVariant {
  id: string;
  label: string;
  tax_basis: 'ttc' | 'ht' | string;
  amount_cents: number;
  subsidies_cents: number;
  hypothesis: string;
}

export interface BudgetSheet {
  id: string;
  project_id: string;
  version: number;
  title: string;
  exercise: number;
  status: string;
  variants: BudgetVariant[];
}

export interface FinanceTransmission {
  id: string;
  project_id: string;
  version: number;
  status: 'transmis' | 'en_instruction' | 'complements_requis' | 'avis_rendu';
  motive: string;
  budget_snapshot: {
    title?: string;
    exercise?: number;
    variants?: BudgetVariant[];
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

export function CulturePanel({projectId}: {projectId: string}) {
  const {api, bootstrap} = useWorkspace();
  const canWrite = bootstrap?.permissions?.workspace?.write !== false;

  const [rooms, setRooms] = useState<Room[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [eventDetails, setEventDetails] = useState<any>(null);
  const [budgetSheet, setBudgetSheet] = useState<BudgetSheet | null>(null);
  const [transmission, setTransmission] = useState<FinanceTransmission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Reservation form state
  const [selectedRoom, setSelectedRoom] = useState('salle-avel-vor');
  const [resDate, setResDate] = useState('2027-06-12');
  const [resStart, setResStart] = useState('15:00');
  const [resEnd, setResEnd] = useState('18:00');
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);

  // Budget variant selected tab
  const [activeVariantIndex, setActiveVariantIndex] = useState(0);

  // Transmission dialog
  const [transmitting, setTransmitting] = useState(false);
  const [transMotive, setTransMotive] = useState(
    "Demande d'arbitrage financier pour la Fête des associations 2027. Variante A privilégiée avec cofinancement départemental."
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [roomsRes, resRes, eventRes, budgetRes, transRes] = await Promise.allSettled([
        api.cultureRooms(),
        api.projectReservations(projectId),
        api.eventDetails(projectId),
        api.budgetSheet(projectId),
        api.projectTransmission(projectId)
      ]);

      if (roomsRes.status === 'fulfilled' && roomsRes.value?.items) {
        setRooms(roomsRes.value.items);
      }
      if (resRes.status === 'fulfilled' && resRes.value?.items) {
        setReservations(resRes.value.items);
      }
      if (eventRes.status === 'fulfilled' && eventRes.value) {
        setEventDetails(eventRes.value);
      }
      if (budgetRes.status === 'fulfilled' && budgetRes.value?.sheet) {
        setBudgetSheet(budgetRes.value.sheet);
      }
      if (transRes.status === 'fulfilled' && transRes.value?.transmission) {
        setTransmission(transRes.value.transmission);
      }
    } catch (e: any) {
      setError(e?.message || 'Erreur lors du chargement des données culture.');
    } finally {
      setLoading(false);
    }
  }, [api, projectId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Live anti-conflict interval check
  useEffect(() => {
    if (!resDate || !resStart || !resEnd || !selectedRoom) {
      setConflictWarning(null);
      return;
    }
    // Paris local time is UTC+2 in summer (CEST)
    const reqStart = new Date(`${resDate}T${resStart}:00+02:00`).getTime();
    const reqEnd = new Date(`${resDate}T${resEnd}:00+02:00`).getTime();

    if (isNaN(reqStart) || isNaN(reqEnd) || reqStart >= reqEnd) {
      setConflictWarning(null);
      return;
    }

    const conflict = reservations.find((r) => {
      const rRoom = r.room_id || r.resource_id;
      if (rRoom !== selectedRoom || r.status === 'cancelled') return false;
      const exStart = new Date(r.start_time).getTime();
      const exEnd = new Date(r.end_time).getTime();
      // semi-open interval conflict: max(s1, s2) < min(e1, e2)
      return Math.max(reqStart, exStart) < Math.min(reqEnd, exEnd);
    });

    if (conflict) {
      const roomName = rooms.find((r) => r.id === selectedRoom)?.name || selectedRoom;
      setConflictWarning(
        `Conflit d'intervalle : La salle ${roomName} est déjà réservée de ${parseDateTimeFr(
          conflict.start_time
        )} à ${parseDateTimeFr(conflict.end_time)}.`
      );
    } else {
      setConflictWarning(null);
    }
  }, [selectedRoom, resDate, resStart, resEnd, reservations, rooms]);

  const handleCreateReservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canWrite) return;
    setError('');
    setSuccess('');
    try {
      const roomObj = rooms.find((r) => r.id === selectedRoom);
      const startIso = `${resDate}T${resStart}:00+02:00`;
      const endIso = `${resDate}T${resEnd}:00+02:00`;

      await api.createReservation(projectId, {
        resource_id: selectedRoom,
        resource_name: roomObj?.name || selectedRoom,
        start_time: startIso,
        end_time: endIso,
        status: 'confirmed'
      });

      setSuccess('Créneau réservé avec succès.');
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Erreur lors de la réservation de salle.');
    }
  };

  const handleCancelReservation = async (reservationId: string) => {
    if (!canWrite) return;
    if (!confirm('Confirmer l’annulation de cette réservation ?')) return;
    try {
      await api.cancelReservation(projectId, reservationId);
      setSuccess('Réservation annulée.');
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Impossible d’annuler la réservation.');
    }
  };

  const handleSaveDefaultBudget = async () => {
    if (!canWrite) return;
    try {
      setError('');
      await api.saveBudgetSheet(projectId, {
        title: 'Budget Prévisionnel Manifestation 2027',
        exercise: 2027,
        variants: [
          {
            id: 'var-a',
            label: 'Variante A (Standard)',
            tax_basis: 'ttc',
            amount_cents: 960000,
            subsidies_cents: 250000,
            hypothesis: 'Configuration standard Avel Vor + cofinancement départemental'
          },
          {
            id: 'var-b',
            label: 'Variante B (Scène étendue)',
            tax_basis: 'ttc',
            amount_cents: 1170000,
            subsidies_cents: 250000,
            hypothesis: 'Configuration avec scène extérieure et renfort sonorisation'
          }
        ],
        status: 'draft'
      });
      setSuccess('Fiche budgétaire enregistrée avec 2 variantes.');
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Erreur lors de l’enregistrement budgétaire.');
    }
  };

  const handleTransmitToFinance = async () => {
    if (!canWrite) return;
    try {
      setError('');
      await api.transmitForFinance(projectId, {
        motive: transMotive,
        attached_document_ids: ['devis-fete-v1.pdf'],
        source_commission_id: 'commission-4',
        destination_commission_id: 'commission-1'
      });
      setTransmitting(false);
      setSuccess('Dossier transmis avec succès pour arbitrage financier.');
      await loadData();
    } catch (err: any) {
      setError(err?.message || 'Échec de la transmission financière.');
    }
  };

  if (loading && !budgetSheet && !reservations.length) {
    return (
      <div className="culture-panel">
        <p role="status">Chargement du module Culture & Événements…</p>
      </div>
    );
  }

  const activeVariant = budgetSheet?.variants?.[activeVariantIndex] || budgetSheet?.variants?.[0];

  return (
    <div className="culture-panel">
      <div className="culture-heading">
        <div>
          <h2>
            <Building2 className="text-primary" size={22} />
            Culture, Sport & Événementiel
          </h2>
          <p>Réservations de salles municipales, fiches budgétaires et circuit d'arbitrage financier.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void loadData()}>
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

      {/* Circuit d'arbitrage Finances Status Banner */}
      {transmission && (
        <div className="transmission-card">
          <div className="flex items-center justify-between gap-4 flex-wrap pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Landmark size={20} className="text-primary" />
              <strong>Circuit Finances Plougastel</strong>
              <span className={`transmission-status-pill ${transmission.status}`}>
                {transmission.status === 'transmis' && 'Transmis · En attente d’arbitrage'}
                {transmission.status === 'complements_requis' && 'Compléments requis par Finances'}
                {transmission.status === 'avis_rendu' && 'Arbitrage rendu'}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
              Transmis le {parseDateTimeFr(transmission.created_at)}
            </span>
          </div>

          <div className="mt-3 text-sm flex flex-col gap-2">
            <p>
              <strong>Motif d'envoi :</strong> {transmission.motive}
            </p>

            {transmission.status === 'complements_requis' && (
              <div className="conflict-alert mt-2">
                <AlertTriangle size={16} />
                <div>
                  <strong>Demande de compléments formulée par Finances :</strong>
                  <p>{transmission.requested_complements || 'Veuillez réviser les devis et montants.'}</p>
                </div>
              </div>
            )}

            {transmission.status === 'avis_rendu' && (
              <div className="success-banner mt-2 flex flex-col items-start gap-1">
                <div className="flex items-center gap-2">
                  <Scale size={16} />
                  <span>
                    Avis officiel :{' '}
                    <span className={`opinion-badge ${transmission.decision_opinion}`}>
                      {transmission.decision_opinion}
                    </span>
                  </span>
                  {transmission.decision_ref && (
                    <span className="font-semibold text-xs bg-white px-2 py-0.5 rounded border border-green-300">
                      Réf : {transmission.decision_ref}
                    </span>
                  )}
                </div>
                {transmission.decision_motivation && (
                  <p className="text-xs mt-1">
                    <strong>Motivation :</strong> {transmission.decision_motivation}
                  </p>
                )}
                {transmission.decided_by && (
                  <span className="text-[11px] text-muted-foreground mt-1">
                    Décidé par {transmission.decided_by} le {parseDateTimeFr(transmission.decided_at || '')}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="culture-bento-grid">
        {/* BENTO CARD 1: Salles Municipales & Anti-conflit */}
        <div className="culture-card">
          <div className="culture-card-header">
            <h3>
              <CalendarDays size={18} />
              Réservation de Salle Municipale
            </h3>
            <span className="text-xs text-muted-foreground">Plougastel-Daoulas</span>
          </div>

          {conflictWarning && (
            <div className="conflict-alert" role="alert">
              <AlertTriangle size={16} />
              <div>{conflictWarning}</div>
            </div>
          )}

          <form onSubmit={handleCreateReservation} className="flex flex-col gap-3">
            <div className="reservation-field">
              <label htmlFor="room-select">Salle demandée</label>
              <select
                id="room-select"
                value={selectedRoom}
                onChange={(e) => setSelectedRoom(e.target.value)}
                disabled={!canWrite}
              >
                {rooms.map((room) => (
                  <option key={room.id} value={room.id}>
                    {room.name} {room.capacity ? `(${room.capacity} pers.)` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="reservation-form-grid">
              <div className="reservation-field">
                <label htmlFor="res-date">Date</label>
                <input
                  id="res-date"
                  type="date"
                  value={resDate}
                  onChange={(e) => setResDate(e.target.value)}
                  disabled={!canWrite}
                  required
                />
              </div>

              <div className="reservation-field">
                <label>Horaires (Paris)</label>
                <div className="flex items-center gap-1">
                  <input
                    type="time"
                    aria-label="Heure de début"
                    value={resStart}
                    onChange={(e) => setResStart(e.target.value)}
                    disabled={!canWrite}
                    required
                  />
                  <span>à</span>
                  <input
                    type="time"
                    aria-label="Heure de fin"
                    value={resEnd}
                    onChange={(e) => setResEnd(e.target.value)}
                    disabled={!canWrite}
                    required
                  />
                </div>
              </div>
            </div>

            <Button type="submit" disabled={!canWrite || Boolean(conflictWarning)} className="mt-2">
              <Clock size={15} className="mr-1" />
              Réserver le créneau
            </Button>
          </form>

          <div className="mt-2">
            <strong className="text-xs text-muted-foreground uppercase tracking-wider">
              Créneaux enregistrés pour ce dossier ({reservations.length})
            </strong>
            <div className="reservations-list">
              {reservations.map((res) => (
                <div key={res.id} className="reservation-item">
                  <div className="reservation-item-info">
                    <strong>{res.room_name || res.resource_name || res.room_id}</strong>
                    <span>
                      {parseDateTimeFr(res.start_time)} → {parseDateTimeFr(res.end_time)}
                    </span>
                  </div>
                  {canWrite && res.status !== 'cancelled' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCancelReservation(res.id)}
                      title="Annuler ce créneau"
                    >
                      <Trash2 size={14} className="text-red-500" />
                    </Button>
                  )}
                </div>
              ))}
              {!reservations.length && (
                <p className="text-xs text-muted-foreground italic">Aucun créneau réservé pour l'instant.</p>
              )}
            </div>
          </div>
        </div>

        {/* BENTO CARD 2: Manifestation & Logistique */}
        <div className="culture-card">
          <div className="culture-card-header">
            <h3>
              <Building2 size={18} />
              Détails Manifestation & Association
            </h3>
            <span className="text-xs text-muted-foreground">Fiche organisateur</span>
          </div>

          <div className="flex flex-col gap-3 text-sm">
            <div className="reservation-field">
              <label>Association organisatrice</label>
              <input
                type="text"
                value={eventDetails?.association_name || 'Amicale Laïque de Plougastel'}
                readOnly
                className="bg-muted"
              />
            </div>

            <div className="reservation-form-grid">
              <div className="reservation-field">
                <label>Affluence attendue</label>
                <input
                  type="text"
                  value={eventDetails?.expected_attendance ? `${eventDetails.expected_attendance} personnes` : '450 personnes'}
                  readOnly
                  className="bg-muted"
                />
              </div>

              <div className="reservation-field">
                <label>Lieu principal</label>
                <input
                  type="text"
                  value={eventDetails?.location_name || 'Espace Avel Vor'}
                  readOnly
                  className="bg-muted"
                />
              </div>
            </div>

            <div className="mt-2">
              <strong className="text-xs text-muted-foreground uppercase tracking-wider block mb-2">
                Checklist technique & sécurité
              </strong>
              <div className="flex flex-col gap-1.5 text-xs">
                <div className="flex items-center gap-2">
                  <CheckCircle size={14} className="text-green-600" />
                  <span>Scène principale & régie lumière son</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle size={14} className="text-green-600" />
                  <span>Débit de boissons temporaire déclaré</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle size={14} className="text-green-600" />
                  <span>Présence agents SSIAP 1 confirmée</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* BENTO CARD 3: Fiche Budgétaire Multi-variantes (Full Width) */}
        <div className="culture-card full-width">
          <div className="culture-card-header">
            <div className="flex items-center gap-3">
              <FileSpreadsheet size={20} className="text-primary" />
              <div>
                <h3 className="m-0">Fiche Budgétaire Prévisionnelle</h3>
                <span className="text-xs text-muted-foreground">
                  Exercice 2027 · Arbitrage multi-variantes
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                asChild
              >
                <a
                  href={`/api/v1/projects/${encodeURIComponent(projectId)}/budget/export.csv`}
                  download={`budget-${projectId}.csv`}
                >
                  <Download size={14} className="mr-1" />
                  Export CSV
                </a>
              </Button>

              {!budgetSheet && canWrite && (
                <Button size="sm" onClick={handleSaveDefaultBudget}>
                  <Plus size={14} className="mr-1" />
                  Initialiser le budget (v1)
                </Button>
              )}

              {canWrite && transmission?.status !== 'avis_rendu' && (
                <Button size="sm" onClick={() => setTransmitting(true)}>
                  <Send size={14} className="mr-1" />
                  Transmettre pour arbitrage Finances
                </Button>
              )}
            </div>
          </div>

          {budgetSheet?.variants?.length ? (
            <div>
              {/* Variant Tabs */}
              <div className="variant-tabs">
                {budgetSheet.variants.map((v, idx) => (
                  <button
                    key={v.id}
                    className={`variant-tab-btn ${activeVariantIndex === idx ? 'active' : ''}`}
                    onClick={() => setActiveVariantIndex(idx)}
                  >
                    {v.label}
                  </button>
                ))}
              </div>

              {activeVariant && (
                <div className="mt-3">
                  <p className="text-xs text-muted-foreground italic mb-2">
                    Hypothèse retenue : {activeVariant.hypothesis || 'Non renseignée'}
                  </p>

                  <table className="budget-table">
                    <thead>
                      <tr>
                        <th>Poste budgétaire</th>
                        <th className="numeric">Dépense ({activeVariant.tax_basis.toUpperCase()})</th>
                        <th className="numeric">Subvention / Recette</th>
                        <th className="numeric">Reste à charge Commune</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Prestations techniques & sonorisation</td>
                        <td className="numeric">{formatCents(activeVariant.amount_cents * 0.45)}</td>
                        <td className="numeric">{formatCents(activeVariant.subsidies_cents * 0.4)}</td>
                        <td className="numeric">
                          {formatCents(activeVariant.amount_cents * 0.45 - activeVariant.subsidies_cents * 0.4)}
                        </td>
                      </tr>
                      <tr>
                        <td>Frais de sécurité & gardiennage SSIAP</td>
                        <td className="numeric">{formatCents(activeVariant.amount_cents * 0.25)}</td>
                        <td className="numeric">{formatCents(0)}</td>
                        <td className="numeric">{formatCents(activeVariant.amount_cents * 0.25)}</td>
                      </tr>
                      <tr>
                        <td>Droits d'auteurs (SACEM) & assurances</td>
                        <td className="numeric">{formatCents(activeVariant.amount_cents * 0.15)}</td>
                        <td className="numeric">{formatCents(0)}</td>
                        <td className="numeric">{formatCents(activeVariant.amount_cents * 0.15)}</td>
                      </tr>
                      <tr>
                        <td>Communication & signalétique municipale</td>
                        <td className="numeric">{formatCents(activeVariant.amount_cents * 0.15)}</td>
                        <td className="numeric">{formatCents(activeVariant.subsidies_cents * 0.6)}</td>
                        <td className="numeric">
                          {formatCents(activeVariant.amount_cents * 0.15 - activeVariant.subsidies_cents * 0.6)}
                        </td>
                      </tr>
                    </tbody>
                  </table>

                  {/* Totals Bento */}
                  <div className="budget-totals-bento">
                    <div className="budget-metric">
                      <span>Dépense Totale Prévue</span>
                      <strong>{formatCents(activeVariant.amount_cents)}</strong>
                    </div>
                    <div className="budget-metric">
                      <span>Aides & Subventions Département</span>
                      <strong>{formatCents(activeVariant.subsidies_cents)}</strong>
                    </div>
                    <div className="budget-metric highlight">
                      <span>Reste à charge Commune</span>
                      <strong>{formatCents(activeVariant.amount_cents - activeVariant.subsidies_cents)}</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 text-center text-sm text-muted-foreground">
              <p>Aucune fiche budgétaire active sur ce dossier.</p>
              {canWrite && (
                <Button variant="outline" size="sm" onClick={handleSaveDefaultBudget} className="mt-2">
                  <Plus size={14} className="mr-1" />
                  Créer les scénarios budgétaires (Variante A & Variante B)
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Dialog Transmission Finances */}
      <Dialog open={transmitting} onOpenChange={setTransmitting}>
        <DialogContent>
          <DialogTitle>Transmettre à la Commission Finances</DialogTitle>
          <DialogDescription>
            Envoi formel du dossier et du scénario budgétaire sélectionné pour arbitrage de la Commission 1 (Fonctions supports et finances).
          </DialogDescription>
          <div className="flex flex-col gap-4 mt-3">
            <div className="reservation-field">
              <label>Variante budgétaire transmise</label>
              <input
                type="text"
                readOnly
                value={activeVariant ? `${activeVariant.label} (${formatCents(activeVariant.amount_cents)})` : 'Variante A'}
                className="bg-muted"
              />
            </div>

            <div className="reservation-field">
              <label htmlFor="trans-motive">Note explicative d'arbitrage</label>
              <textarea
                id="trans-motive"
                rows={3}
                value={transMotive}
                onChange={(e) => setTransMotive(e.target.value)}
                placeholder="Explication du besoin budgétaire..."
              />
            </div>

            <div className="info-banner text-xs flex items-center gap-2">
              <FileText size={16} className="text-primary flex-shrink-0" />
              <span>Pièce jointe scellée : <strong>devis-fete-v1.pdf</strong> (estimatif détaillé)</span>
            </div>

            <div className="flex justify-end gap-2 mt-2">
              <Button variant="outline" onClick={() => setTransmitting(false)}>
                Annuler
              </Button>
              <Button onClick={handleTransmitToFinance}>
                <Send size={14} className="mr-1" />
                Confirmer la transmission
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
