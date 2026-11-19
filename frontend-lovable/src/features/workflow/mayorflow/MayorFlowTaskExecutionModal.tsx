import React, { useState, useEffect } from 'react';
import { X, CheckCircle2, AlertTriangle, FileText, Upload, ShieldCheck, ArrowRight, CornerDownRight } from 'lucide-react';
import { toast } from 'sonner';

interface MayorFlowTaskExecutionModalProps {
  task: any | null;
  onClose: () => void;
  onCompleted: () => void;
}

export function MayorFlowTaskExecutionModal({ task, onClose, onCompleted }: MayorFlowTaskExecutionModalProps) {
  if (!task) return null;

  const [decision, setDecision] = useState<string>('approve');
  const [comment, setComment] = useState<string>('');
  const [piecesCompletes, setPiecesCompletes] = useState<boolean>(true);
  const [montantHt, setMontantHt] = useState<string>('35000');
  const [certified, setCertified] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const [formSchema, setFormSchema] = useState<any | null>(null);

  useEffect(() => {
    // Load custom dynamic JSON Schema if available
    const fetchForm = async () => {
      try {
        const res = await fetch(`/api/v1/workflows/definitions/${task.definition_id || 'urbanisme_ads'}/form/${task.node_id}`);
        if (res.ok) {
          const data = await res.json();
          setFormSchema(data.schema);
        }
      } catch (e) {
        // Fallback to default form
      }
    };
    fetchForm();
  }, [task]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!certified) {
      toast.error('Veuillez certifier sur l’honneur l’exactitude de l’instruction.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        form_data: {
          decision,
          comment,
          pieces_completes: piecesCompletes,
          montant_ht: parseFloat(montantHt) || 0,
          instructeur_certifie: true,
          date_visa: new Date().toISOString(),
        },
      };
      const res = await fetch(`/api/v1/workflows/tasks/${task.id}/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'Travaux',
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.message || 'Erreur lors de la validation.');
      }
      toast.success('Tâche validée avec succès ! Le jeton a progressé vers l’étape suivante.');
      onCompleted();
      onClose();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in font-sans">
      <div className="relative w-full max-w-4xl bg-white border border-slate-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-600">
              <FileText size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-blue-600 uppercase tracking-widest">
                  MayorFlow Play — Instruction Régalienne
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-50 text-blue-700 border border-blue-200 font-mono font-bold">
                  {task.business_key || 'DOSSIER-MUNICIPAL'}
                </span>
              </div>
              <h3 className="text-sm font-bold text-slate-900 tracking-tight">{task.node_name}</h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
            aria-label="Fermer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content: Split Panel */}
        <div className="grid grid-cols-1 md:grid-cols-12 flex-1 overflow-hidden">
          {/* Left Panel: Process Breadcrumb & Context */}
          <div className="md:col-span-5 bg-slate-50/80 border-r border-slate-200 p-5 overflow-y-auto space-y-5 text-xs text-slate-600">
            <div>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                Workflow Associé
              </span>
              <span className="font-bold text-slate-900 block text-sm">
                {task.workflow_name || 'Instruction Permis de Construire'}
              </span>
              <span className="text-slate-500 block text-[11px] mt-0.5">
                {task.instance_title || 'Demande initiale de réhabilitation'}
              </span>
            </div>

            {/* Stepper Breadcrumb */}
            <div className="space-y-3 pt-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Chaîne d'Instruction & Étapes
              </span>
              <div className="space-y-2 border-l-2 border-slate-200 ml-2 pl-3">
                <div className="flex items-center gap-2 text-emerald-600 font-medium">
                  <CheckCircle2 size={14} />
                  <span>Dépôt usager guichet</span>
                </div>
                <div className="flex items-center gap-2 text-blue-700 font-bold bg-blue-50 p-1.5 rounded border border-blue-200 -ml-2">
                  <ArrowRight size={14} className="shrink-0" />
                  <span>{task.node_name} (Étape Active)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-400">
                  <span className="w-3.5 h-3.5 rounded-full border border-slate-300 flex items-center justify-center text-[8px]">
                    3
                  </span>
                  <span>Passerelle Décisionnelle & Arbitrage</span>
                </div>
                <div className="flex items-center gap-2 text-slate-400">
                  <span className="w-3.5 h-3.5 rounded-full border border-slate-300 flex items-center justify-center text-[8px]">
                    4
                  </span>
                  <span>Scellement SHA-256 & Notification</span>
                </div>
              </div>
            </div>

            {/* SLA Alert */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-1">
              <div className="flex items-center gap-1.5 text-amber-700 font-bold text-[11px]">
                <AlertTriangle size={13} />
                <span>Délai Légal d'Instruction (SLA)</span>
              </div>
              <p className="text-[11px] text-amber-800">
                Échéance réglementaire : 48h ouvrées. Au-delà, escalade automatique à la Direction Générale des Services (DGS).
              </p>
            </div>
          </div>

          {/* Right Panel: Dynamic Form */}
          <form onSubmit={handleSubmit} className="md:col-span-7 p-6 overflow-y-auto space-y-4 text-xs">
            {/* Decision Select */}
            <div className="space-y-1.5">
              <label htmlFor="modal-decision-regalienne" className="font-semibold text-slate-700 block">
                Décision d'Instruction Régalienne <span className="text-rose-500">*</span>
              </label>
              <select
                id="modal-decision-regalienne"
                value={decision}
                onChange={(e) => setDecision(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-sans"
              >
                <option value="approve">Approuver / Émettre avis favorable</option>
                <option value="request_info">Demande de pièces complémentaires (suspend les délais)</option>
                <option value="reject">Rejeter le dossier pour non-conformité</option>
              </select>
            </div>

            {/* Checkboxes / Conditional inputs */}
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <label className="flex items-center gap-2 text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={piecesCompletes}
                  onChange={(e) => setPiecesCompletes(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="font-medium">Pièces 100% complètes</span>
              </label>

              <div className="space-y-1">
                <label htmlFor="modal-montant-estime" className="text-[10px] text-slate-400 uppercase tracking-wider block">
                  Montant Estimé (€ HT)
                </label>
                <input
                  id="modal-montant-estime"
                  type="number"
                  value={montantHt}
                  onChange={(e) => setMontantHt(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-slate-900 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Observations Textarea */}
            <div className="space-y-1.5">
              <label htmlFor="modal-motivations-visa" className="font-semibold text-slate-700 block">
                Motivations administratives & Prescriptions techniques
              </label>
              <textarea
                id="modal-motivations-visa"
                rows={4}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Renseignez les motifs réglementaires du visa ou les pièces manquantes requises..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-sans resize-none"
              />
            </div>

            {/* File Upload mock */}
            <div className="border border-dashed border-slate-200 rounded-xl p-3 text-center bg-slate-50 hover:bg-slate-100 transition cursor-pointer">
              <Upload size={18} className="mx-auto text-slate-400 mb-1" />
              <span className="text-[11px] text-slate-700 block font-medium">
                Joindre un rapport d'instruction ou arrêté complémentaire (PDF)
              </span>
              <span className="text-[9px] text-slate-400 block">Format PDF/A certifié jusqu'à 50 Mo</span>
            </div>

            {/* Honor Certification */}
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
              <label className="flex items-start gap-2.5 text-blue-900 cursor-pointer">
                <input
                  type="checkbox"
                  checked={certified}
                  onChange={(e) => setCertified(e.target.checked)}
                  className="mt-0.5 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-[11px] leading-relaxed">
                  Je certifie en qualité d'instructeur habilité de la Ville de Plougastel-Daoulas
                  l'exactitude des éléments visés et autorise le scellement cryptographique SHA-256 de cet acte.
                </span>
              </label>
            </div>

            {/* Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 transition font-medium"
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={submitting || !certified}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold transition active:scale-95 shadow-sm disabled:opacity-50"
              >
                <ShieldCheck size={16} />
                <span>{submitting ? 'Validation…' : 'Valider & Sceller la Tâche'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
