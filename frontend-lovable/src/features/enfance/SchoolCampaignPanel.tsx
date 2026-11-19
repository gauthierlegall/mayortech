import React, {useState, useEffect} from 'react';
import {
  GraduationCap,
  Calendar,
  RotateCw,
  Plus,
  Calculator,
  CheckCircle,
  Clock,
  Check,
  AlertCircle,
  School,
  FileCheck,
  Bell
} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog, DialogContent, DialogTitle, DialogDescription} from '@/components/ui/dialog';
import {useWorkspace} from '../workspace/context';
import './school.css';

export interface SocialCampaign {
  id: string;
  campaign_type: string;
  title: string;
  school_year: string;
  start_date: string;
  end_date: string;
  status: string;
  config: Record<string, any>;
  created_at: string;
}

export interface CampaignDossier {
  id: string;
  campaign_id: string;
  family_ref: string;
  beneficiary_name: string;
  child_name: string;
  school_name: string;
  quotient_familial: number;
  rate_bracket: string;
  status: string;
  details: Record<string, any>;
  created_at: string;
}

export interface SocialReminder {
  id: string;
  campaign_id?: string;
  title: string;
  due_date: string;
  reminder_type: string;
  is_dismissed: boolean;
  created_at: string;
}

export const CANTEEN_BRACKETS_INFO: Record<string, {label: string; rate: string; subsidy: string; css: string}> = {
  T1: {label: 'Tranche 1 (QF ≤ 450 €) - Tarif solidaire', rate: '1,00 €', subsidy: 'Commune : 3,95 €', css: 't1'},
  T2: {label: 'Tranche 2 (451 € à 750 €)', rate: '2,15 €', subsidy: 'Commune : 2,80 €', css: 't2'},
  T3: {label: 'Tranche 3 (751 € à 1 100 €)', rate: '3,20 €', subsidy: 'Commune : 1,75 €', css: 't3'},
  T4: {label: 'Tranche 4 (1 101 € à 1 600 €)', rate: '4,10 €', subsidy: 'Commune : 0,85 €', css: 't4'},
  T5: {label: 'Tranche 5 (> 1 600 €) - Tarif plein', rate: '4,95 €', subsidy: 'Sans subvention', css: 't5'},
};

export function getBracketForQF(qf: number): string {
  if (qf <= 450) return 'T1';
  if (qf <= 750) return 'T2';
  if (qf <= 1100) return 'T3';
  if (qf <= 1600) return 'T4';
  return 'T5';
}

export function SchoolCampaignPanel() {
  const {api, bootstrap} = useWorkspace();
  const canWrite = bootstrap?.permissions?.workspace?.write !== false;

  const [campaigns, setCampaigns] = useState<SocialCampaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<SocialCampaign | null>(null);
  const [dossiers, setDossiers] = useState<CampaignDossier[]>([]);
  const [reminders, setReminders] = useState<SocialReminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Simulator state
  const [simQF, setSimQF] = useState<number>(550);

  // Renewal dialog state
  const [renewOpen, setRenewOpen] = useState(false);
  const [renewYear, setRenewYear] = useState('2027-2028');
  const [carryDossiers, setCarryDossiers] = useState(true);
  const [carryReminders, setCarryReminders] = useState(true);
  const [renewing, setRenewing] = useState(false);

  // New dossier dialog state
  const [newDossierOpen, setNewDossierOpen] = useState(false);
  const [dFamilyRef, setDFamilyRef] = useState('FAM-29470-');
  const [dBeneficiary, setDBeneficiary] = useState('');
  const [dChild, setDChild] = useState('');
  const [dSchool, setDSchool] = useState('École des Alizés');
  const [dQf, setDQf] = useState<number>(450);
  const [creatingDossier, setCreatingDossier] = useState(false);

  // Load campaigns
  useEffect(() => {
    let alive = true;
    async function loadData() {
      try {
        setLoading(true);
        const res = await (api as any).socialCampaigns({campaign_type: 'rentree_scolaire'});
        if (!alive) return;
        const list = res?.items || [];
        setCampaigns(list);
        if (list.length > 0) {
          setSelectedCampaign(list[0]);
        }
      } catch (err: any) {
        if (alive) setError(err.message || 'Impossible de charger les campagnes.');
      } finally {
        if (alive) setLoading(false);
      }
    }
    loadData();
    return () => {
      alive = false;
    };
  }, [api]);

  // Load dossiers & reminders for selected campaign
  useEffect(() => {
    if (!selectedCampaign) return;
    const camp = selectedCampaign;
    let alive = true;
    async function loadDetails() {
      try {
        const [dosRes, remRes] = await Promise.all([
          (api as any).campaignDossiers(camp.id),
          (api as any).socialReminders({campaign_id: camp.id}),
        ]);
        if (!alive) return;
        setDossiers(dosRes?.items || []);
        setReminders(remRes?.items || []);
      } catch (err: any) {
        if (alive) setError(err.message || 'Erreur lors du chargement des détails.');
      }
    }
    loadDetails();
    return () => {
      alive = false;
    };
  }, [api, selectedCampaign]);

  // Handle renewal
  async function handleRenewal() {
    if (!selectedCampaign) return;
    try {
      setRenewing(true);
      setError('');
      const res = await (api as any).renewSocialCampaign(selectedCampaign.id, {
        target_school_year: renewYear,
        carry_over_dossiers: carryDossiers,
        carry_over_reminders: carryReminders,
      });
      const newCamp = res?.target_campaign;
      if (newCamp) {
        setCampaigns(prev => [newCamp, ...prev]);
        setSelectedCampaign(newCamp);
      }
      setSuccess(`Campagne reconduite avec succès pour ${renewYear} (${res.dossiers_renewed_count} dossiers, ${res.reminders_carried_count} rappels).`);
      setRenewOpen(false);
    } catch (err: any) {
      setError(err.message || 'Échec de la reconduction.');
    } finally {
      setRenewing(false);
    }
  }

  // Handle new dossier creation
  async function handleCreateDossier() {
    if (!selectedCampaign) return;
    try {
      setCreatingDossier(true);
      setError('');
      const created = await (api as any).createCampaignDossier(selectedCampaign.id, {
        family_ref: dFamilyRef,
        beneficiary_name: dBeneficiary,
        child_name: dChild,
        school_name: dSchool,
        quotient_familial: dQf,
        details: {canteen_registered: true},
      });
      setDossiers(prev => [created, ...prev]);
      setSuccess(`Dossier famille ${dFamilyRef} enregistré en Tranche ${created.rate_bracket}.`);
      setNewDossierOpen(false);
      setDBeneficiary('');
      setDChild('');
    } catch (err: any) {
      setError(err.message || 'Échec de la création du dossier.');
    } finally {
      setCreatingDossier(false);
    }
  }

  // Handle dismiss reminder
  async function handleDismissReminder(reminderId: string) {
    try {
      await (api as any).dismissSocialReminder(reminderId);
      setReminders(prev => prev.filter(r => r.id !== reminderId));
    } catch (err: any) {
      setError(err.message || 'Impossible d’acquitter le rappel.');
    }
  }

  const currentBracket = getBracketForQF(simQF);
  const currentBracketInfo = CANTEEN_BRACKETS_INFO[currentBracket];

  return (
    <div className="school-panel">
      {/* Header */}
      <div className="school-panel-header">
        <div className="school-title-group">
          <h2>
            <GraduationCap className="text-blue-600" size={28} />
            Campagne Scolaire & Périscolaire
          </h2>
          <p>Commission 2 · Solidarités, CCAS, enfance, jeunesse et vie scolaire de Plougastel-Daoulas</p>
        </div>
        <div className="school-actions">
          {campaigns.length > 1 && (
            <select
              aria-label="Sélectionner la campagne"
              value={selectedCampaign?.id || ''}
              onChange={e => {
                const c = campaigns.find(x => x.id === e.target.value);
                if (c) setSelectedCampaign(c);
              }}
              className="p-2 border rounded text-sm bg-white"
            >
              {campaigns.map(c => (
                <option key={c.id} value={c.id}>
                  {c.title} ({c.school_year})
                </option>
              ))}
            </select>
          )}
          {canWrite && selectedCampaign && (
            <Button
              variant="outline"
              onClick={() => {
                const nextY = selectedCampaign.school_year === '2026-2027' ? '2027-2028' : '2028-2029';
                setRenewYear(nextY);
                setRenewOpen(true);
              }}
              className="border-blue-600 text-blue-600 hover:bg-blue-50"
            >
              <RotateCw size={15} className="mr-1" />
              Reconduire pour l’année suivante
            </Button>
          )}
          {canWrite && selectedCampaign && (
            <Button onClick={() => setNewDossierOpen(true)}>
              <Plus size={16} className="mr-1" />
              Nouveau dossier famille
            </Button>
          )}
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

      {/* Selected Campaign Hero */}
      {selectedCampaign ? (
        <div className="campaign-hero">
          <div className="campaign-hero-info">
            <h3>
              <School size={20} />
              {selectedCampaign.title}
            </h3>
            <div className="campaign-hero-meta">
              <span>
                <Calendar size={14} />
                Année scolaire : <strong>{selectedCampaign.school_year}</strong>
              </span>
              <span>
                <Clock size={14} />
                Période : {selectedCampaign.start_date} au {selectedCampaign.end_date}
              </span>
              <span>
                <FileCheck size={14} />
                Statut : <span className="uppercase font-semibold text-emerald-700">{selectedCampaign.status}</span>
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4 bg-gray-50 border rounded text-center text-gray-500">
          Aucune campagne active. Cliquez pour initialiser la première rentrée scolaire.
        </div>
      )}

      {/* Jalonnement annuel (Timeline Milestones) */}
      <section className="timeline-section">
        <h3>
          <Calendar size={18} />
          Calendrier et Jalons de la Campagne Scolaire
        </h3>
        <div className="milestones-grid">
          <div className="milestone-item done">
            <div className="milestone-step">Jalon 1</div>
            <div className="milestone-title">Ouverture des inscriptions</div>
            <div className="milestone-date">
              <Check size={13} className="text-green-600" />
              01 mai
            </div>
          </div>
          <div className="milestone-item active">
            <div className="milestone-step">Jalon 2</div>
            <div className="milestone-title">Clôture dossiers cantine & QF</div>
            <div className="milestone-date">
              <Clock size={13} className="text-blue-600" />
              15 juillet
            </div>
          </div>
          <div className="milestone-item">
            <div className="milestone-step">Jalon 3</div>
            <div className="milestone-title">Arbitrage dérogations scolaires</div>
            <div className="milestone-date">28 juillet</div>
          </div>
          <div className="milestone-item">
            <div className="milestone-step">Jalon 4</div>
            <div className="milestone-title">Rentrée scolaire des élèves</div>
            <div className="milestone-date">02 septembre</div>
          </div>
        </div>
      </section>

      {/* Quick Quotient Familial Simulator */}
      <section className="simulator-card">
        <div className="simulator-header">
          <h3>
            <Calculator size={18} className="text-blue-600" />
            Simulateur Tarification Sociale Cantine Plougastel
          </h3>
          <span className="text-xs text-muted-foreground">Barème voté par le Conseil Municipal</span>
        </div>
        <div className="simulator-body">
          <div className="qf-input-group">
            <label htmlFor="sim-qf-input">Quotient Familial CAF (€) :</label>
            <input
              id="sim-qf-input"
              type="number"
              min="0"
              max="9999"
              step="10"
              value={simQF}
              onChange={e => setSimQF(Math.max(0, parseInt(e.target.value || '0', 10)))}
            />
            <span className="text-xs text-gray-500">Ex : 380 € (Tranche 1), 600 € (Tranche 2), 1250 € (Tranche 4)</span>
          </div>

          <div className={`bracket-result-banner ${currentBracketInfo.css}`}>
            <div>
              <div className="bracket-name">{currentBracketInfo.label}</div>
              <div className="bracket-subsidy">{currentBracketInfo.subsidy}</div>
            </div>
            <div className="text-right">
              <span className="text-xs text-muted-foreground block">Prix du repas :</span>
              <span className="bracket-price">{currentBracketInfo.rate}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Dossiers Table */}
      <section>
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-bold flex items-center gap-2">
            <FileCheck size={18} />
            Dossiers d’inscriptions scolaires ({dossiers.length})
          </h3>
        </div>
        <div className="dossier-table-container">
          <table className="dossier-table">
            <thead>
              <tr>
                <th>RÉF. FAMILLE</th>
                <th>BÉNÉFICIAIRE / PARENT</th>
                <th>ENFANT</th>
                <th>ÉCOLE</th>
                <th>QUOTIENT (CAF)</th>
                <th>TRANCHE TARIF</th>
                <th>STATUT</th>
              </tr>
            </thead>
            <tbody>
              {dossiers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-6 text-muted-foreground">
                    Aucun dossier inscrit dans cette campagne. Cliquez sur "Nouveau dossier famille" pour en ajouter un.
                  </td>
                </tr>
              ) : (
                dossiers.map(d => (
                  <tr key={d.id} className="dossier-row">
                    <td className="font-mono text-xs font-semibold">{d.family_ref}</td>
                    <td className="font-semibold">{d.beneficiary_name}</td>
                    <td>{d.child_name || '—'}</td>
                    <td>{d.school_name || 'École des Alizés'}</td>
                    <td>{d.quotient_familial} €</td>
                    <td>
                      <span className={`badge-bracket ${d.rate_bracket}`}>
                        {d.rate_bracket} ({CANTEEN_BRACKETS_INFO[d.rate_bracket]?.rate || 'Tarif plein'})
                      </span>
                    </td>
                    <td>
                      <span className={`badge-status ${d.status}`}>
                        {d.status === 'reconduit'
                          ? 'Reconduit'
                          : d.status === 'valide'
                          ? 'Validé'
                          : 'En instruction'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Reminders Section */}
      {reminders.length > 0 && (
        <section className="reminders-section">
          <h3 className="text-base font-bold flex items-center gap-2 text-amber-700">
            <Bell size={18} />
            Rappels et échéances critiques ({reminders.length})
          </h3>
          <div className="reminders-list">
            {reminders.map(r => (
              <div key={r.id} className="reminder-item">
                <div className="reminder-info">
                  <strong>{r.title}</strong>
                  <small>Échéance : {r.due_date} · Type : {r.reminder_type}</small>
                </div>
                {canWrite && (
                  <Button size="sm" variant="ghost" onClick={() => handleDismissReminder(r.id)}>
                    <Check size={14} className="mr-1" />
                    Acquitter
                  </Button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Dialog: Annual Campaign Renewal */}
      <Dialog open={renewOpen} onOpenChange={setRenewOpen}>
        <DialogContent className="max-w-md">
          <DialogTitle>Reconduire la campagne pour l’année suivante</DialogTitle>
          <DialogDescription>
            Duplication intelligente des règles, des échéances (+1 an) et des dossiers actifs.
          </DialogDescription>
          <div className="space-y-4 pt-2">
            <div>
              <label className="text-xs font-semibold block mb-1">Année scolaire cible :</label>
              <input
                type="text"
                className="w-full p-2 border rounded font-mono"
                value={renewYear}
                onChange={e => setRenewYear(e.target.value)}
                placeholder="2027-2028"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="carry-dos"
                checked={carryDossiers}
                onChange={e => setCarryDossiers(e.target.checked)}
              />
              <label htmlFor="carry-dos" className="text-sm">
                Reconduire les dossiers valides (statut 'Reconduit')
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="carry-rem"
                checked={carryReminders}
                onChange={e => setCarryReminders(e.target.checked)}
              />
              <label htmlFor="carry-rem" className="text-sm">
                Décaler les échéances de rappel (+1 an)
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-3">
              <Button variant="ghost" onClick={() => setRenewOpen(false)}>
                Annuler
              </Button>
              <Button onClick={handleRenewal} disabled={renewing}>
                <RotateCw size={15} className={`mr-1 ${renewing ? 'animate-spin' : ''}`} />
                {renewing ? 'Reconduction en cours…' : 'Exécuter la reconduction'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog: New Dossier */}
      <Dialog open={newDossierOpen} onOpenChange={setNewDossierOpen}>
        <DialogContent className="max-w-md">
          <DialogTitle>Nouveau dossier famille</DialogTitle>
          <DialogDescription>
            Inscription scolaire et calcul automatique du tarif de restauration municipale.
          </DialogDescription>
          <div className="space-y-3 pt-2">
            <div>
              <label className="text-xs font-semibold block mb-1">Référence CAF / Famille :</label>
              <input
                type="text"
                className="w-full p-2 border rounded font-mono text-sm"
                value={dFamilyRef}
                onChange={e => setDFamilyRef(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Nom du responsable légal :</label>
              <input
                type="text"
                className="w-full p-2 border rounded text-sm"
                value={dBeneficiary}
                onChange={e => setDBeneficiary(e.target.value)}
                placeholder="Mme ou M. Dupont"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Prénom de l’enfant :</label>
              <input
                type="text"
                className="w-full p-2 border rounded text-sm"
                value={dChild}
                onChange={e => setDChild(e.target.value)}
                placeholder="Yann"
              />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Établissement scolaire :</label>
              <select
                className="w-full p-2 border rounded text-sm bg-white"
                value={dSchool}
                onChange={e => setDSchool(e.target.value)}
              >
                <option>École des Alizés</option>
                <option>École du Goëland</option>
                <option>École Saint-Pierre</option>
                <option>Collège Champ de la Rive</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Quotient Familial CAF (€) :</label>
              <input
                type="number"
                min="0"
                step="10"
                className="w-full p-2 border rounded text-sm"
                value={dQf}
                onChange={e => setDQf(Math.max(0, parseInt(e.target.value || '0', 10)))}
              />
              <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-900">
                Tranche calculée : <strong>{getBracketForQF(dQf)}</strong> (Repas à{' '}
                {CANTEEN_BRACKETS_INFO[getBracketForQF(dQf)]?.rate})
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3">
              <Button variant="ghost" onClick={() => setNewDossierOpen(false)}>
                Annuler
              </Button>
              <Button onClick={handleCreateDossier} disabled={creatingDossier || !dBeneficiary}>
                <Plus size={15} className="mr-1" />
                {creatingDossier ? 'Enregistrement…' : 'Enregistrer le dossier'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
