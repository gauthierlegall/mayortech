import React, {useState, useEffect} from 'react';
import {
  FileText,
  Anchor,
  CheckCircle,
  AlertTriangle,
  Clock,
  Save,
  Plus,
  ExternalLink,
  ShieldAlert,
  Hammer,
  Ship,
  MapPin,
  CheckSquare,
  Square
} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog, DialogContent, DialogTitle, DialogDescription} from '@/components/ui/dialog';
import {useWorkspace} from '../workspace/context';
import {createNativeAction} from '../workspace/native-actions';
import './urbanisme.css';

interface ChecklistItem {
  id: string;
  label: string;
  required: boolean;
  checked: boolean;
}

const DEFAULT_CHECKLIST: ChecklistItem[] = [
  {id: 'pcmi1', label: 'PCMI1 — Plan de situation du terrain', required: true, checked: true},
  {id: 'pcmi2', label: 'PCMI2 — Plan de masse des constructions', required: true, checked: true},
  {id: 'pcmi3', label: 'PCMI3 — Plan en coupe du terrain et de la construction', required: true, checked: false},
  {id: 'pcmi4', label: 'PCMI4 — Notice descriptive du projet et matériaux', required: true, checked: false},
  {id: 'pcmi5', label: 'PCMI5 — Plan des façades et des toitures', required: false, checked: false},
  {id: 'loi_littoral', label: 'Conformité Loi Littoral (bande des 100m / espaces proches)', required: true, checked: true}
];

export interface PortInspection {
  id: string;
  project_id: string;
  port_name: string;
  ouvrage_type: string;
  inspector: string;
  inspection_date: string;
  condition_rating: 'bon' | 'moyen' | 'degrade' | 'urgent';
  observations: string;
  linked_action_id?: string;
  created_at: string;
}

export function UrbanismePortsPanel({projectId}: {projectId: string}) {
  const {api, bootstrap} = useWorkspace();
  const canWrite = bootstrap?.permissions?.workspace?.write !== false;

  const [loading, setLoading] = useState(true);
  const [savingUrbanisme, setSavingUrbanisme] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Urbanisme state
  const [parcelRef, setParcelRef] = useState('Parcelle Exemple A-12');
  const [requestType, setRequestType] = useState('permis_construire');
  const [regulationSource, setRegulationSource] = useState('PLU Plougastel — Zone Ub (Centre-Bourg)');
  const [adviceStatus, setAdviceStatus] = useState('en_cours');
  const [followUpDate, setFollowUpDate] = useState('2027-02-15');
  const [checklist, setChecklist] = useState<ChecklistItem[]>(DEFAULT_CHECKLIST);

  // Port Inspections state
  const [inspections, setInspections] = useState<PortInspection[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newPortName, setNewPortName] = useState('Port du Tinduff');
  const [newOuvrageType, setNewOuvrageType] = useState('Ponton plaisance');
  const [newInspector, setNewInspector] = useState('Service Maritime Plougastel');
  const [newInspectionDate, setNewInspectionDate] = useState(new Date().toISOString().split('T')[0]);
  const [newConditionRating, setNewConditionRating] = useState<'bon' | 'moyen' | 'degrade' | 'urgent'>('moyen');
  const [newObservations, setNewObservations] = useState('');
  const [submittingInspection, setSubmittingInspection] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');

  useEffect(() => {
    let alive = true;
    async function loadData() {
      if (!api) return;
      try {
        setLoading(true);
        setError('');
        const [urbRes, inspRes] = await Promise.allSettled([
          api.projectUrbanisme ? api.projectUrbanisme(projectId) : Promise.resolve(null),
          api.portInspections ? api.portInspections(projectId) : Promise.resolve({items: []})
        ]);

        if (alive) {
          if (urbRes.status === 'fulfilled' && urbRes.value?.dossier) {
            const d = urbRes.value.dossier;
            if (d.parcel_ref) setParcelRef(d.parcel_ref);
            if (d.request_type) setRequestType(d.request_type);
            if (d.regulation_source) setRegulationSource(d.regulation_source);
            if (d.advice_status) setAdviceStatus(d.advice_status);
            if (d.follow_up_date) setFollowUpDate(d.follow_up_date);
            if (Array.isArray(d.checklist) && d.checklist.length > 0) setChecklist(d.checklist);
          }

          if (inspRes.status === 'fulfilled' && Array.isArray(inspRes.value?.items)) {
            setInspections(inspRes.value.items);
          }
        }
      } catch (err: any) {
        if (alive) setError(err?.message || 'Erreur lors du chargement');
      } finally {
        if (alive) setLoading(false);
      }
    }
    loadData();
    return () => {
      alive = false;
    };
  }, [api, projectId]);

  const toggleChecklist = (id: string) => {
    if (!canWrite) return;
    setChecklist(prev => prev.map(item => (item.id === id ? {...item, checked: !item.checked} : item)));
  };

  const handleSaveUrbanisme = async () => {
    if (!canWrite || !api?.saveProjectUrbanisme) return;
    try {
      setSavingUrbanisme(true);
      setError('');
      setSuccess('');
      await api.saveProjectUrbanisme(projectId, {
        parcel_ref: parcelRef,
        request_type: requestType,
        regulation_source: regulationSource,
        checklist,
        advice_status: adviceStatus,
        follow_up_date: followUpDate
      });
      setSuccess('Dossier d’urbanisme enregistré avec succès.');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: any) {
      setError(err?.message || 'Erreur lors de l’enregistrement');
    } finally {
      setSavingUrbanisme(false);
    }
  };

  const handleCreateInspection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canWrite || !api?.createPortInspection) return;
    try {
      setSubmittingInspection(true);
      setError('');
      const created = await api.createPortInspection(projectId, {
        port_name: newPortName,
        ouvrage_type: newOuvrageType,
        inspector: newInspector,
        inspection_date: newInspectionDate,
        condition_rating: newConditionRating,
        observations: newObservations
      });
      setInspections(prev => [created, ...prev]);
      setDialogOpen(false);
      setNewObservations('');
      setSuccess('Rapport d’inspection enregistré.');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: any) {
      setError(err?.message || 'Erreur lors de l’enregistrement de l’inspection');
    } finally {
      setSubmittingInspection(false);
    }
  };

  const handleCreateMaintenanceAction = async (insp: PortInspection) => {
    if (!canWrite) return;
    try {
      setActionSuccess('');
      const actionTitle = `[Maintenance] ${insp.ouvrage_type} — ${insp.port_name}`;
      const actionDesc = `Action préventive/curative issue du constat (${insp.condition_rating.toUpperCase()}) du ${insp.inspection_date} par ${insp.inspector} : ${insp.observations}`;
      const priority = insp.condition_rating === 'urgent' ? 'Haute' : 'Normale';
      const due = new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0];

      await createNativeAction(api, projectId, {
        Intitulé: actionTitle,
        Description: actionDesc,
        Statut: 'À faire',
        Priorité: priority,
        Échéance: due
      });

      setActionSuccess(`Action de maintenance créée dans le suivi du chantier : "${actionTitle}"`);
      setTimeout(() => setActionSuccess(''), 6000);
    } catch (err: any) {
      setError(err?.message || 'Impossible de créer l’action de maintenance');
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Chargement du dossier Urbanisme & Ports…</div>;
  }

  const completedChecklistCount = checklist.filter(c => c.checked).length;

  return (
    <div className="urbanisme-panel">
      <div className="urbanisme-header">
        <div>
          <h2>
            <MapPin className="text-sky-500" />
            Urbanisme, Travaux & Ports — Plougastel-Daoulas
          </h2>
          <p>
            Instruction réglementaire des sols, cadastre et suivi des infrastructures maritimes littorales.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {success && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-sm flex items-center gap-2">
          <CheckCircle size={16} />
          {success}
        </div>
      )}

      {actionSuccess && (
        <div className="p-3 bg-sky-50 border border-sky-200 text-sky-800 rounded-lg text-sm flex items-center gap-2">
          <Hammer size={16} />
          {actionSuccess}
        </div>
      )}

      <div className="urbanisme-bento-grid">
        {/* Section 1: Urbanisme & Droits du Sol */}
        <div className="urbanisme-card">
          <div className="urbanisme-card-title">
            <span>
              <FileText size={18} className="text-emerald-500" />
              Instruction Droits du Sol & Cadastre
            </span>
            <span
              className={`badge-status ${
                adviceStatus === 'favorable'
                  ? 'favorable'
                  : adviceStatus === 'defavorable'
                  ? 'defavorable'
                  : adviceStatus === 'reserve'
                  ? 'reserve'
                  : 'en_cours'
              }`}
            >
              {adviceStatus === 'favorable'
                ? 'Avis Favorable'
                : adviceStatus === 'defavorable'
                ? 'Avis Défavorable'
                : adviceStatus === 'reserve'
                ? 'Favorable avec Réserves'
                : 'En cours d\'instruction'}
            </span>
          </div>

          <div className="urbanisme-form-grid">
            <div className="urbanisme-form-field">
              <label>Référence Parcelle Cadastrale</label>
              <input
                type="text"
                value={parcelRef}
                onChange={e => setParcelRef(e.target.value)}
                disabled={!canWrite}
                placeholder="Ex. Section A, Parcelle 12"
              />
            </div>

            <div className="urbanisme-form-field">
              <label>Type de Demande</label>
              <select
                value={requestType}
                onChange={e => setRequestType(e.target.value)}
                disabled={!canWrite}
              >
                <option value="permis_construire">Permis de construire (PC)</option>
                <option value="declaration_prealable">Déclaration préalable (DP)</option>
                <option value="certificat_urbanisme">Certificat d'urbanisme (CU)</option>
                <option value="autre">Autre autorisation</option>
              </select>
            </div>

            <div className="urbanisme-form-field full">
              <label>Source Réglementaire / Zone PLU</label>
              <div className="flex gap-2 items-center">
                <input
                  type="text"
                  className="w-full"
                  value={regulationSource}
                  onChange={e => setRegulationSource(e.target.value)}
                  disabled={!canWrite}
                  placeholder="Ex. PLU Plougastel Zone Ub / Loi Littoral"
                />
                <a
                  href="https://www.geoportail-urbanisme.gouv.fr"
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-sky-600 hover:underline flex items-center gap-1 whitespace-nowrap p-2 border border-slate-200 rounded"
                  title="Consulter le Géoportail de l'Urbanisme"
                >
                  <ExternalLink size={13} /> Géoportail
                </a>
              </div>
            </div>

            <div className="urbanisme-form-field">
              <label>Avis Préfectoral / Municipal</label>
              <select
                value={adviceStatus}
                onChange={e => setAdviceStatus(e.target.value)}
                disabled={!canWrite}
              >
                <option value="en_cours">En cours d'instruction</option>
                <option value="favorable">Favorable</option>
                <option value="reserve">Favorable avec réserves</option>
                <option value="defavorable">Défavorable</option>
              </select>
            </div>

            <div className="urbanisme-form-field">
              <label>Date Limite d'Instruction</label>
              <input
                type="date"
                value={followUpDate}
                onChange={e => setFollowUpDate(e.target.value)}
                disabled={!canWrite}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Pièces Réglementaires du Dossier ({completedChecklistCount}/{checklist.length})
              </label>
            </div>

            <div className="urbanisme-checklist" role="list">
              {checklist.map(item => (
                <div
                  key={item.id}
                  className="checklist-item"
                  onClick={() => toggleChecklist(item.id)}
                  role="checkbox"
                  aria-checked={item.checked}
                  tabIndex={0}
                  onKeyDown={e => {
                    if (e.key === ' ' || e.key === 'Enter') {
                      e.preventDefault();
                      toggleChecklist(item.id);
                    }
                  }}
                >
                  <div className="checklist-item-left">
                    {item.checked ? (
                      <CheckSquare size={17} className="text-emerald-600" />
                    ) : (
                      <Square size={17} className="text-slate-400" />
                    )}
                    <span className={item.checked ? 'text-slate-900 font-medium' : 'text-slate-600'}>
                      {item.label}
                    </span>
                  </div>
                  {item.required && (
                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">Obligatoire</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {canWrite && (
            <div className="pt-2 flex justify-end">
              <Button onClick={handleSaveUrbanisme} disabled={savingUrbanisme}>
                <Save size={15} className="mr-1" />
                {savingUrbanisme ? 'Enregistrement…' : 'Enregistrer le dossier urbanisme'}
              </Button>
            </div>
          )}
        </div>

        {/* Section 2: Ports & Ouvrages Maritimes */}
        <div className="urbanisme-card">
          <div className="urbanisme-card-title">
            <span>
              <Anchor size={18} className="text-sky-500" />
              Ouvrages Portuaires & Littoral
            </span>
            {canWrite && (
              <Button size="sm" variant="outline" onClick={() => setDialogOpen(true)}>
                <Plus size={14} className="mr-1" /> Nouvelle inspection
              </Button>
            )}
          </div>

          <div className="text-sm text-slate-600">
            Suivi périodique de l'état structurel des pontons, cales de mise à l'eau, digues et chaînes d'amarrage
            (Ports du Tinduff, du Passage et de l'Auberlac'h).
          </div>

          <div className="inspections-list">
            {inspections.length === 0 ? (
              <div className="p-6 text-center text-slate-400 border border-dashed rounded-lg">
                <Ship size={28} className="mx-auto mb-2 opacity-40" />
                <p>Aucun rapport d'inspection enregistré pour ce site.</p>
                {canWrite && (
                  <Button size="sm" variant="ghost" className="mt-2" onClick={() => setDialogOpen(true)}>
                    Créer la première inspection
                  </Button>
                )}
              </div>
            ) : (
              inspections.map(insp => (
                <div key={insp.id} className="inspection-entry">
                  <div className="inspection-entry-header">
                    <div>
                      <strong>{insp.port_name}</strong> · <span>{insp.ouvrage_type}</span>
                    </div>
                    <span
                      className={`badge-condition ${
                        insp.condition_rating === 'bon'
                          ? 'bon'
                          : insp.condition_rating === 'moyen'
                          ? 'moyen'
                          : insp.condition_rating === 'degrade'
                          ? 'degrade'
                          : 'urgent'
                      }`}
                    >
                      {insp.condition_rating}
                    </span>
                  </div>

                  <div className="inspection-entry-obs">{insp.observations}</div>

                  <div className="inspection-entry-footer">
                    <span className="text-slate-500 text-xs">
                      Inspecté le {insp.inspection_date} par {insp.inspector}
                    </span>

                    {canWrite && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-xs text-sky-700 hover:text-sky-900"
                        onClick={() => handleCreateMaintenanceAction(insp)}
                        title="Créer une action de maintenance issue de ce constat"
                      >
                        <Hammer size={12} className="mr-1" /> Maintenance
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Dialog: Nouvelle Inspection Portuaire */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogTitle>Enregistrer une inspection portuaire</DialogTitle>
          <DialogDescription>
            Rapport de visite périodique des équipements portuaires et maritimes de Plougastel.
          </DialogDescription>

          <form className="space-y-4 pt-2" onSubmit={handleCreateInspection}>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Port</label>
              <select
                className="w-full border rounded p-2 text-sm"
                value={newPortName}
                onChange={e => setNewPortName(e.target.value)}
              >
                <option value="Port du Tinduff">Port du Tinduff</option>
                <option value="Port du Passage">Port du Passage</option>
                <option value="Port de l'Auberlac'h">Port de l'Auberlac'h</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Ouvrage inspecté</label>
              <input
                type="text"
                className="w-full border rounded p-2 text-sm"
                value={newOuvrageType}
                onChange={e => setNewOuvrageType(e.target.value)}
                placeholder="Ex. Ponton plaisance, Cale ouest, Digue"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Inspecteur / Technicien</label>
                <input
                  type="text"
                  className="w-full border rounded p-2 text-sm"
                  value={newInspector}
                  onChange={e => setNewInspector(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Date d'inspection</label>
                <input
                  type="date"
                  className="w-full border rounded p-2 text-sm"
                  value={newInspectionDate}
                  onChange={e => setNewInspectionDate(e.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">État constaté</label>
              <select
                className="w-full border rounded p-2 text-sm"
                value={newConditionRating}
                onChange={e => setNewConditionRating(e.target.value as any)}
              >
                <option value="bon">BON — Aucune anomalie détectée</option>
                <option value="moyen">MOYEN — Usure normale, à surveiller</option>
                <option value="degrade">DÉGRADÉ — Réparation recommandée</option>
                <option value="urgent">URGENT — Risque d'avarie ou sécurité</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Observations détaillées</label>
              <textarea
                className="w-full border rounded p-2 text-sm min-h-[90px]"
                value={newObservations}
                onChange={e => setNewObservations(e.target.value)}
                placeholder="Description des désordres, usure des chaînes, fissures ou corrosion constatée…"
                required
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" disabled={submittingInspection}>
                {submittingInspection ? 'Enregistrement…' : 'Valider l’inspection'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
