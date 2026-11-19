import React, { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCcw,
  XCircle,
  FileText,
  Building2,
  ShieldCheck,
  Search,
  Filter,
  ExternalLink,
  ChevronRight,
  GitFork,
  ArrowLeft,
  Calendar,
  User,
  Paperclip,
  Eye,
  Check,
  Hash,
  AlertCircle,
  Sparkles,
  Cpu,
  Smartphone,
  CheckSquare,
  Square,
  Play,
  X,
  UserCheck,
  Pencil
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { ValidationDossier, ValidationStep } from './validationData';

interface MayorValidationInboxProps {
  dossiers: ValidationDossier[];
  onUpdateDossier: (updated: ValidationDossier) => void;
  onViewBpmn: (dossierId: string) => void;
}

export function MayorValidationInbox({
  dossiers,
  onUpdateDossier,
  onViewBpmn,
}: MayorValidationInboxProps) {
  const [activeFilter, setActiveFilter] = useState<'my_tasks' | 'service_pool' | 'pending_dgs' | 'history'>('my_tasks');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDossierId, setSelectedDossierId] = useState<string>(
    dossiers[0]?.id || 'PC-2026-042'
  );

  // Decision state
  const [decisionComment, setDecisionComment] = useState('');
  const [isRollbackModalOpen, setIsRollbackModalOpen] = useState(false);
  const [rollbackTargetStep, setRollbackTargetStep] = useState<string>('step-ctm');
  const [isDirectRollbackException, setIsDirectRollbackException] = useState(true);
  const [rollbackReason, setRollbackReason] = useState('Précisions requises sur les servitudes de recul et l’altimétrie du faîtage.');

  // Parapheur en rafale & validation par lot
  const [selectedBatchIds, setSelectedBatchIds] = useState<string[]>([]);
  const [isParapheurModeOpen, setIsParapheurModeOpen] = useState(false);
  const [parapheurIndex, setParapheurIndex] = useState(0);

  // Delegation
  const [delegationInfo] = useState<{ active: boolean; delegate: string } | null>(() => {
    try {
      const s = localStorage.getItem('mayortech_absence_delegation');
      return s ? JSON.parse(s) : null;
    } catch {
      return null;
    }
  });

  // Current selected dossier
  const selectedDossier = dossiers.find((d) => d.id === selectedDossierId) || dossiers[0];
  const pendingDossiers = dossiers.filter((d) => d.status === 'pending');

  // Inline Typo Correction & Change Highlight
  const [isEditingArticle, setIsEditingArticle] = useState(false);
  const [editedArticleText, setEditedArticleText] = useState(selectedDossier?.previewArticle || '');
  const [isHighlightingChanges, setIsHighlightingChanges] = useState(Boolean(selectedDossier?.returnFeedback));

  React.useEffect(() => {
    if (selectedDossier) {
      setEditedArticleText(selectedDossier.previewArticle);
      setIsEditingArticle(false);
      setIsHighlightingChanges(Boolean(selectedDossier.returnFeedback));
    }
  }, [selectedDossierId]);

  // Handle URL hash parameters (e.g. #/workflows?dossier=PC-2026-042 or ?parapheur=1)
  React.useEffect(() => {
    const updateFromHash = () => {
      const hash = window.location.hash;
      const queryIdx = hash.indexOf('?');
      if (queryIdx === -1) return;
      const params = new URLSearchParams(hash.substring(queryIdx));
      const dId = params.get('dossier');
      if (dId && dossiers.some((d) => d.id === dId)) {
        setSelectedDossierId(dId);
        const target = dossiers.find((d) => d.id === dId);
        if (target) {
          if (target.currentStepIndex < 2) setActiveFilter('service_pool');
          else if (target.status === 'signed') setActiveFilter('history');
          else setActiveFilter('pending_dgs');
        }
      }
      if (params.get('parapheur') === '1') {
        setIsParapheurModeOpen(true);
      }
    };

    updateFromHash();
    window.addEventListener('hashchange', updateFromHash);
    return () => window.removeEventListener('hashchange', updateFromHash);
  }, [dossiers]);

  const handleSaveTypoFix = () => {
    if (!selectedDossier) return;
    const now = new Date();
    const formattedDate = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()} · ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    const newAuditEntry = {
      timestamp: formattedDate,
      author: 'Laurence GUIVARC’H (DGS)',
      role: 'Direction Générale (DGS)',
      action: 'visa' as const,
      stepName: 'Modification de coquille en relecture',
      comment: 'Modification mineure par DGS (Mme Laurence Guivarc’h) · Version v1.1 · Empreinte SHA-256 mise à jour',
      sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    };

    const updated: ValidationDossier = {
      ...selectedDossier,
      previewArticle: editedArticleText,
      isEditedInReview: true,
      editVersion: 'v1.1',
      auditTrail: [newAuditEntry, ...selectedDossier.auditTrail],
    };

    onUpdateDossier(updated);
    setIsEditingArticle(false);
    toast.success('Modification enregistrée. Version v1.1 scellée dans le journal d’audit.');
  };

  // Keyboard shortcuts for Mode Parapheur
  React.useEffect(() => {
    if (!isParapheurModeOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsParapheurModeOpen(false);
      } else if (e.key === 'v' || e.key === 'V') {
        if (parapheurIndex < pendingDossiers.length) {
          const cur = pendingDossiers[parapheurIndex];
          onUpdateDossier({
            ...cur,
            status: 'signed',
            currentStepIndex: cur.steps.length - 1
          });
          toast.success(`Dossier ${cur.id} visé et transmis !`);
          setParapheurIndex(prev => prev + 1);
        }
      } else if (e.key === 'ArrowRight') {
        setParapheurIndex(prev => Math.min(pendingDossiers.length - 1, prev + 1));
      } else if (e.key === 'r' || e.key === 'R') {
        if (parapheurIndex < pendingDossiers.length) {
          setSelectedDossierId(pendingDossiers[parapheurIndex].id);
          setIsParapheurModeOpen(false);
          setIsRollbackModalOpen(true);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isParapheurModeOpen, parapheurIndex, pendingDossiers, onUpdateDossier]);

  // Filtering dossiers
  const filteredDossiers = dossiers.filter((d) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = d.id.toLowerCase().includes(q);
      const matchTitle = d.title.toLowerCase().includes(q);
      const matchApplicant = d.applicant.toLowerCase().includes(q);
      if (!matchId && !matchTitle && !matchApplicant) return false;
    }

    if (activeFilter === 'my_tasks') {
      return d.status === 'pending' && d.currentStepIndex === 2; // DGS tasks
    }
    if (activeFilter === 'service_pool') {
      return d.status === 'pending' && d.currentStepIndex < 2; // Earlier service steps
    }
    if (activeFilter === 'pending_dgs') {
      return d.status === 'pending' && d.currentStepIndex >= 2;
    }
    if (activeFilter === 'history') {
      return d.status === 'signed' || d.status === 'rejected' || d.status === 'returned';
    }
    return true;
  });

  // Action: Valider & Signer
  const handleValidateAndSign = () => {
    if (!selectedDossier) return;

    const currentIdx = selectedDossier.currentStepIndex;
    const currentStep = selectedDossier.steps[currentIdx];
    const nextIdx = Math.min(currentIdx + 1, selectedDossier.steps.length - 1);
    const isFinal = currentIdx >= selectedDossier.steps.length - 1;

    const newSha256 = Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10);
    const nowStr = new Date().toLocaleDateString('fr-FR') + ' à ' + new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

    const updatedSteps = selectedDossier.steps.map((st, idx) => {
      if (idx === currentIdx) {
        return {
          ...st,
          status: 'completed' as const,
          signedAt: nowStr,
          comment: decisionComment.trim() || 'Visa légal favorable accordé sans réserve.',
          sha256: newSha256,
        };
      }
      if (idx === nextIdx && !isFinal) {
        return {
          ...st,
          status: 'active' as const,
        };
      }
      return st;
    });

    const updatedAudit = [
      ...selectedDossier.auditTrail,
      {
        timestamp: nowStr,
        author: 'Marie ROLLAND (DGS)',
        role: 'Direction Générale des Services',
        action: 'visa' as const,
        stepName: currentStep?.label || 'Visa DGS',
        comment: decisionComment.trim() || 'Visa légal et financier favorable accordé.',
        sha256: newSha256,
      },
    ];

    const updatedDossier: ValidationDossier = {
      ...selectedDossier,
      currentStepIndex: isFinal ? currentIdx : nextIdx,
      status: isFinal ? 'signed' : 'pending',
      steps: updatedSteps,
      auditTrail: updatedAudit,
    };

    onUpdateDossier(updatedDossier);
    setDecisionComment('');
    toast.success(`Dossier ${selectedDossier.id} validé et signé avec succès ! Transmis à l’étape suivante.`);
  };

  // Action: Renvoyer à une étape
  const handleConfirmRollback = () => {
    if (!selectedDossier) return;
    if (!rollbackReason.trim()) {
      toast.error('Le motif du renvoi est strictement obligatoire.');
      return;
    }

    const targetIdx = selectedDossier.steps.findIndex((s) => s.id === rollbackTargetStep);
    if (targetIdx < 0) return;

    const targetStep = selectedDossier.steps[targetIdx];
    const nowStr = new Date().toLocaleDateString('fr-FR') + ' à ' + new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

    const updatedSteps = selectedDossier.steps.map((st, idx) => {
      if (idx === targetIdx) {
        return {
          ...st,
          status: 'returned' as const,
        };
      }
      if (idx > targetIdx) {
        return {
          ...st,
          status: 'upcoming' as const,
          signedAt: undefined,
          sha256: undefined,
        };
      }
      return st;
    });

    const updatedAudit = [
      ...selectedDossier.auditTrail,
      {
        timestamp: nowStr,
        author: 'Marie ROLLAND (DGS)',
        role: 'Direction Générale',
        action: 'renvoi' as const,
        stepName: `Renvoi vers ${targetStep.label}`,
        comment: `Dossier renvoyé pour réexamen : ${rollbackReason.trim()}${isDirectRollbackException ? ' [Renvoi direct exceptionnel]' : ''}`,
      },
    ];

    const updatedDossier: ValidationDossier = {
      ...selectedDossier,
      currentStepIndex: targetIdx,
      status: 'pending',
      steps: updatedSteps,
      auditTrail: updatedAudit,
    };

    onUpdateDossier(updatedDossier);
    setIsRollbackModalOpen(false);
    toast.warning(`Dossier ${selectedDossier.id} renvoyé à l’étape : ${targetStep.label}`);
  };

  // Action: Refuser
  const handleReject = () => {
    if (!selectedDossier) return;
    const motif = prompt('Veuillez indiquer le motif de rejet / clôture motivée du dossier :');
    if (!motif || !motif.trim()) return;

    const nowStr = new Date().toLocaleDateString('fr-FR') + ' à ' + new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    const currentIdx = selectedDossier.currentStepIndex;

    const updatedSteps = selectedDossier.steps.map((st, idx) => {
      if (idx === currentIdx) {
        return {
          ...st,
          status: 'rejected' as const,
          signedAt: nowStr,
          comment: motif.trim(),
        };
      }
      return st;
    });

    const updatedAudit = [
      ...selectedDossier.auditTrail,
      {
        timestamp: nowStr,
        author: 'Marie ROLLAND (DGS)',
        role: 'Direction Générale',
        action: 'refus' as const,
        stepName: 'Notification de rejet motivé',
        comment: motif.trim(),
      },
    ];

    const updatedDossier: ValidationDossier = {
      ...selectedDossier,
      status: 'rejected',
      steps: updatedSteps,
      auditTrail: updatedAudit,
    };

    onUpdateDossier(updatedDossier);
    toast.error(`Dossier ${selectedDossier.id} rejeté. Clôture administrative notifiée.`);
  };

  return (
    <div className="space-y-4 font-sans text-slate-900">
      {/* Filter Tabs & Search Bar */}
      <div className="bg-white border border-slate-200 rounded-2xl p-3 sm:p-4 shadow-2xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 text-xs">
          {[
            { id: 'my_tasks', label: 'Mes validations', count: dossiers.filter(d => d.status === 'pending' && d.currentStepIndex === 2).length },
            { id: 'service_pool', label: 'Service / Pool', count: dossiers.filter(d => d.status === 'pending' && d.currentStepIndex < 2).length },
            { id: 'pending_dgs', label: 'En attente DGS / Maire', count: dossiers.filter(d => d.status === 'pending' && d.currentStepIndex >= 2).length },
            { id: 'history', label: 'Historique / Signés', count: dossiers.filter(d => d.status === 'signed' || d.status === 'rejected').length },
          ].map((tab) => {
            const isSelected = activeFilter === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveFilter(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold whitespace-nowrap transition-all ${
                  isSelected
                    ? 'bg-[#102A4C] text-white shadow-2xs'
                    : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                }`}
              >
                <span>{tab.label}</span>
                {tab.count > 0 && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                      isSelected ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Mode Parapheur Button & Search Input */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => {
              setParapheurIndex(0);
              setIsParapheurModeOpen(true);
            }}
            className="bg-[#102A4C] hover:bg-[#193D6B] text-white font-bold text-xs px-3.5 py-1.5 rounded-md shadow-xs flex items-center gap-1.5 shrink-0 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Mode Parapheur ({filteredDossiers.filter(d => d.status === 'pending').length})</span>
          </Button>

          <div className="relative w-full md:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Rechercher un dossier..."
              className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs text-slate-800 font-medium transition-colors"
            />
          </div>
        </div>
      </div>

      {/* Main Directive Split View: Dossier List (Left/Top) + Directive Treatment Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Dossiers Selection Column (Desktop: 4 cols, Mobile: full) */}
        <div className="lg:col-span-4 space-y-2.5">
          {/* Floating/Sticky Batch Action Bar */}
          {selectedBatchIds.length > 0 && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl shadow-sm flex items-center justify-between gap-2 text-xs animate-in fade-in duration-150">
              <div className="flex items-center gap-1.5 font-bold text-blue-900">
                <CheckSquare className="w-4 h-4 text-blue-600" />
                <span>{selectedBatchIds.length} sélectionné(s)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setSelectedBatchIds([])}
                  className="px-2 py-1 text-slate-600 hover:text-slate-900 text-[11px] font-semibold cursor-pointer"
                >
                  Annuler
                </button>
                <button
                  onClick={() => {
                    selectedBatchIds.forEach((id) => {
                      const d = dossiers.find((item) => item.id === id);
                      if (d) {
                        onUpdateDossier({
                          ...d,
                          status: 'signed',
                          currentStepIndex: d.steps.length - 1
                        });
                      }
                    });
                    toast.success(`${selectedBatchIds.length} dossiers visés et signés par lot !`);
                    setSelectedBatchIds([]);
                  }}
                  className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-2xs cursor-pointer flex items-center gap-1"
                >
                  <Check className="w-3 h-3" />
                  <span>Viser la sélection ({selectedBatchIds.length})</span>
                </button>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Dossiers ({filteredDossiers.length})
            </span>
            <span className="text-[11px] text-slate-500">
              Trié par échéance SLA
            </span>
          </div>

          <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
            {filteredDossiers.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-xs">
                Aucun dossier ne correspond aux critères sélectionnés.
              </div>
            ) : (
              filteredDossiers.map((d) => {
                const isSelected = selectedDossier?.id === d.id;
                const isChecked = selectedBatchIds.includes(d.id);
                const currentStep = d.steps[d.currentStepIndex];

                return (
                  <div
                    key={d.id}
                    onClick={() => setSelectedDossierId(d.id)}
                    className={`bg-white rounded-xl border p-3.5 cursor-pointer transition-all duration-150 relative shadow-2xs ${
                      isSelected
                        ? 'border-blue-500 ring-2 ring-blue-500/20 shadow-md bg-blue-50/10'
                        : 'border-slate-200 hover:border-slate-300 hover:shadow-xs'
                    }`}
                  >
                    {/* Header line: Checkbox + ID + SLA badge */}
                    <div className="flex items-center justify-between gap-1.5 mb-1.5">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedBatchIds(prev => prev.includes(d.id) ? prev.filter(x => x !== d.id) : [...prev, d.id]);
                          }}
                          className="p-0.5 text-slate-400 hover:text-blue-600 cursor-pointer"
                          title="Sélectionner pour visa par lot"
                        >
                          {isChecked ? (
                            <CheckSquare className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-300 hover:text-slate-500" />
                          )}
                        </button>
                        <span className="font-mono text-[11px] font-bold text-[#102A4C] bg-stone-100 px-2 py-0.5 rounded border border-stone-200 whitespace-nowrap shrink-0">
                          {d.id}
                        </span>
                        {d.confidentialBadge && (
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-rose-50 text-rose-800 border border-rose-200 whitespace-nowrap shrink-0">
                            {d.confidentialBadge}
                          </span>
                        )}
                      </div>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold flex items-center gap-1 whitespace-nowrap shrink-0 ${
                          d.slaStatus === 'warning'
                            ? 'bg-amber-50 text-amber-800 border border-amber-200'
                            : d.status === 'signed'
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : 'bg-stone-100 text-stone-600 border border-stone-200'
                        }`}
                      >
                        <Clock className="w-2.5 h-2.5" />
                        <span>{d.slaDeadline}</span>
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="text-xs font-bold text-slate-900 leading-snug line-clamp-2">
                      {d.title}
                    </h3>

                    {/* Delegation tag if active */}
                    {delegationInfo?.active && d.status === 'pending' && (
                      <div className="mt-1.5 flex items-center gap-1 text-[10px] font-semibold text-amber-800 bg-amber-50 border border-amber-200/70 px-2 py-0.5 rounded-md">
                        <UserCheck className="w-3 h-3 text-amber-600 shrink-0" />
                        <span className="truncate">Délégation : {delegationInfo.delegate.split('·')[0].trim()}</span>
                      </div>
                    )}

                    {/* Applicant & Step info */}
                    <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                      <span className="truncate max-w-[160px]" title={d.applicant}>
                        {d.applicant}
                      </span>
                      <span className="font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
                        {currentStep?.label || 'Clôturé'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Directive Treatment Panel (Desktop: 8 cols) */}
        {selectedDossier ? (
          <div className="lg:col-span-8 space-y-4">
            {/* Upper Banner: Horizontal Circuit Stepper */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-2xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs font-bold text-[#102A4C] bg-stone-100 border border-stone-200 px-2.5 py-1 rounded-md whitespace-nowrap shrink-0">
                    {selectedDossier.id}
                  </span>
                  {selectedDossier.confidentialBadge && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 whitespace-nowrap shrink-0">
                      {selectedDossier.confidentialBadge}
                    </span>
                  )}
                  <span className="text-xs font-bold text-slate-900">
                    {selectedDossier.circuitLabel}
                  </span>
                  <span className="text-xs text-slate-400">·</span>
                  <span className="text-xs text-slate-500 font-medium">
                    {selectedDossier.applicant}
                  </span>
                </div>

                {/* Button Voir le circuit */}
                <button
                  onClick={() => onViewBpmn(selectedDossier.id)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stone-200 bg-white text-stone-700 hover:bg-stone-50 text-xs font-semibold transition-colors shrink-0 shadow-3xs cursor-pointer"
                  title="Voir la position du dossier sur le circuit interactif"
                >
                  <GitFork className="w-3.5 h-3.5" />
                  <span>Voir le circuit</span>
                </button>
              </div>

              {/* Stepper of Actors */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                {selectedDossier.steps.map((st, idx) => {
                  const isCompleted = st.status === 'completed';
                  const isActive = st.status === 'active';
                  const isReturned = st.status === 'returned';

                  return (
                    <div
                      key={st.id}
                      className={`p-2.5 rounded-xl border flex flex-col justify-between transition-all ${
                        isActive
                          ? 'border-blue-500 bg-blue-50/30 ring-2 ring-blue-500/20 shadow-xs'
                          : isCompleted
                          ? 'border-emerald-200 bg-emerald-50/20'
                          : isReturned
                          ? 'border-amber-300 bg-amber-50/30'
                          : 'border-slate-200 bg-slate-50/50 opacity-75'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono text-slate-500 font-bold">
                          0{idx + 1}
                        </span>
                        {isCompleted ? (
                          <span className="flex items-center gap-0.5 text-[9px] font-bold text-emerald-700 bg-emerald-100/70 px-1.5 py-0.2 rounded-full">
                            <Check className="w-2.5 h-2.5" />
                            <span>Signé</span>
                          </span>
                        ) : isActive ? (
                          <span className="flex items-center gap-1 text-[9px] font-bold text-blue-700 bg-blue-100 px-1.5 py-0.2 rounded-full animate-pulse">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                            <span>En cours</span>
                          </span>
                        ) : isReturned ? (
                          <span className="text-[9px] font-bold text-amber-800 bg-amber-100 px-1.5 py-0.2 rounded-full">
                            Renvoyé
                          </span>
                        ) : (
                          <span className="text-[9px] text-slate-400">À venir</span>
                        )}
                      </div>
                      <h4 className="text-xs font-bold text-slate-900 leading-snug">
                        {st.label}
                      </h4>
                      <p className="text-[10px] text-slate-500 truncate mt-0.5" title={st.actor}>
                        {st.actor}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Split Grid: Left Document Zone + Right Sticky Decision Panel */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
              {/* Left Zone: Document Preview & Audit Trail (7 cols) */}
              <div className="md:col-span-7 space-y-4">
                {/* Document Preview Card */}
                <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3 flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-600" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                        Projet d’Acte Municipal
                      </h3>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        Réf: {selectedDossier.id}
                      </span>
                      {selectedDossier.isEditedInReview && (
                        <span className="text-[10px] font-mono font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full flex items-center gap-1 shadow-3xs">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                          <span>Modifié en relecture ({selectedDossier.editVersion || 'v1.1'})</span>
                        </span>
                      )}
                      {!isEditingArticle && (
                        <button
                          type="button"
                          onClick={() => {
                            setEditedArticleText(selectedDossier.previewArticle);
                            setIsEditingArticle(true);
                          }}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 hover:border-blue-300 bg-slate-50 hover:bg-blue-50/50 text-slate-700 hover:text-blue-700 text-xs font-semibold transition-colors shadow-3xs cursor-pointer ml-1"
                          title="Corriger directement une faute ou un numéro sans renvoyer le dossier"
                        >
                          <Pencil className="w-3.5 h-3.5 text-blue-600" />
                          <span>Corriger une coquille</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Bandeau « Ce qui a changé » lors d'un retour après renvoi */}
                  {selectedDossier.returnFeedback && (
                    <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-300 text-xs space-y-2 animate-in fade-in duration-150">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-amber-950 font-bold">
                          <RotateCcw className="w-3.5 h-3.5 text-amber-600" />
                          <span>Suite à votre demande de correction</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => setIsHighlightingChanges(!isHighlightingChanges)}
                          className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1 border transition-colors cursor-pointer ${
                            isHighlightingChanges
                              ? 'bg-emerald-600 text-white border-emerald-600 shadow-3xs'
                              : 'bg-white text-emerald-800 border-emerald-300 hover:bg-emerald-50'
                          }`}
                        >
                          <Eye className="w-3 h-3" />
                          <span>{isHighlightingChanges ? 'Masquer le surlignage' : 'Voir les modifications'}</span>
                        </button>
                      </div>
                      <div className="space-y-1 text-slate-700">
                        <p className="text-[11px] text-amber-950">
                          <strong className="text-amber-900">Motif initial du renvoi :</strong> « {selectedDossier.returnFeedback.initialReason} »
                        </p>
                        <p className="text-[11px] text-emerald-900">
                          <strong className="text-emerald-800">Correction apportée :</strong> {selectedDossier.returnFeedback.agentResponse}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Official Letterhead Preview */}
                  <div className="rounded-xl bg-[#FFFEFC] border border-stone-200/90 shadow-[0_1px_2px_rgba(16,42,76,0.04)] overflow-hidden">
                    <div className="filet-tricolore" />
                    <div className="p-4 sm:p-5 space-y-3.5">
                      <div className="text-center border-b border-stone-200/70 pb-3 font-sans">
                        <p className="text-[10px] font-bold tracking-widest uppercase text-stone-500">
                          RÉPUBLIQUE FRANÇAISE
                        </p>
                        <h4 className="text-sm font-bold text-stone-900 mt-0.5">
                          VILLE DE PLOUGASTEL-DAOULAS
                        </h4>
                        <p className="text-[10px] text-stone-500">
                          Direction Générale des Services · Pôle Aménagement
                        </p>
                      </div>

                      <p className="font-bold text-stone-900 font-sans text-xs">
                        {selectedDossier.title}
                      </p>

                      <p className="text-stone-600 text-[11px] italic font-serif leading-relaxed">
                        Vu le Code Général des Collectivités Territoriales et le Code de l’Urbanisme ;<br />
                        Vu la demande déposée le {selectedDossier.createdAt} par {selectedDossier.applicant} ;<br />
                        Vu les avis favorables recueillis lors de l’instruction technique préalable ;
                      </p>

                      {isEditingArticle ? (
                        <div className="space-y-2 font-sans pt-1">
                          <div className="flex items-center justify-between text-[11px] text-blue-700 font-semibold">
                            <span>Édition en direct du texte de l'acte (tracée) :</span>
                            <span className="text-stone-400 font-normal">Version v1.1 en préparation</span>
                          </div>
                          <textarea
                            value={editedArticleText}
                            onChange={(e) => setEditedArticleText(e.target.value)}
                            rows={6}
                            className="w-full p-3 font-sans text-xs text-stone-800 leading-relaxed border-2 border-blue-400 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                          />
                          <div className="flex items-center justify-end gap-2 pt-1">
                            <button
                              type="button"
                              onClick={() => setIsEditingArticle(false)}
                              className="px-3 py-1.5 rounded-xl border border-stone-200 text-stone-600 hover:bg-stone-100 text-xs font-semibold cursor-pointer"
                            >
                              Annuler
                            </button>
                            <button
                              type="button"
                              onClick={handleSaveTypoFix}
                              className="px-3.5 py-1.5 rounded-xl bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs font-bold shadow-xs flex items-center gap-1.5 cursor-pointer"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Enregistrer la modification (tracé)</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {selectedDossier.isConfidentialCCAS && (
                            <div className="p-2.5 rounded bg-rose-50 border border-rose-200 text-rose-900 text-xs font-semibold flex items-center gap-2">
                              <ShieldCheck className="w-4 h-4 text-rose-700 shrink-0" />
                              <span>Accès restreint · Secret professionnel CCAS (Art. L.226-13 du Code Pénal)</span>
                            </div>
                          )}
                          <div className="font-serif-act text-xs text-stone-800 leading-relaxed space-y-2 whitespace-pre-line">
                            {selectedDossier.previewArticle.split('\n\n').map((para, idx) => {
                              const isHighlighted = isHighlightingChanges && (
                                para.includes('28 novembre 2026') ||
                                (selectedDossier.returnFeedback?.changedParagraph &&
                                 para.includes(selectedDossier.returnFeedback.changedParagraph.slice(0, 30)))
                              );
                              return (
                                <p
                                  key={idx}
                                  className={`transition-colors ${
                                    isHighlighted
                                      ? 'bg-emerald-50 border-l-4 border-emerald-500 pl-3 py-1.5 rounded-r-md text-emerald-950 font-medium shadow-3xs'
                                      : ''
                                  }`}
                                >
                                  {para}
                                </p>
                              );
                            })}
                          </div>

                          {/* Tampon VISÉ & SCELLÉ */}
                          <div className="pt-3 border-t border-stone-200/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded border border-emerald-600/40 bg-emerald-50/70 text-emerald-800 text-[10px] font-mono font-bold tracking-wider">
                              <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                              <span>VISÉ & SCELLÉ · HORODATAGE eIDAS</span>
                            </div>
                            <div className="text-[9.5px] font-mono text-stone-500 tabular-nums">
                              SHA-256 : <span className="text-stone-700 font-semibold">{selectedDossier.auditTrail?.[0]?.sha256?.slice(0, 24) || '9f86d081884c7d659a2feaa0'}...</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Documents & Attached Cerfa Pieces */}
                  <div className="space-y-2">
                    <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <Paperclip className="w-3.5 h-3.5 text-slate-500" />
                      <span>Pièces Justificatives Associées ({selectedDossier.documents.length})</span>
                    </h4>
                    <div className="space-y-1.5">
                      {selectedDossier.documents.map((doc, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 hover:bg-slate-100/60 text-xs transition-colors"
                        >
                          <div className="flex items-center gap-2 truncate">
                            <FileText className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                            <span className="font-medium text-slate-800 truncate">{doc.name}</span>
                            <span className="text-[10px] text-slate-400 font-mono">({doc.size})</span>
                          </div>
                          {doc.badge && (
                            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full shrink-0">
                              {doc.badge}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Historique des visas certifiés */}
                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Historique des visas certifiés (eIDAS)</span>
                      </span>
                      <span className="text-[9.5px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-semibold">
                        2 visas apposés
                      </span>
                    </h4>
                    <div className="space-y-1.5 text-[11px]">
                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">Étape 01 · Guichetier ADS</span>
                          <span className="text-[10px] text-slate-500 font-mono">14/11/2026 à 09:15</span>
                        </div>
                        <p className="text-[10.5px] text-slate-600">M. Ronan LE GALL · Récépissé Cerfa délivré</p>
                        <p className="text-[9.5px] font-mono text-slate-500 truncate" title="SHA-256: 3a9f14b8c7e2d19f5a04e672b1d9c3f8e4a7b2c5d6e1f0a9b8c7d6e5f4a3b2c1">
                          <span className="text-slate-400 font-sans">Empreinte SHA-256 :</span> 3a9f14b8c7e2d19f...b2c1
                        </p>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">Étape 02 · Instructeur ADS</span>
                          <span className="text-[10px] text-slate-500 font-mono">16/11/2026 à 14:30</span>
                        </div>
                        <p className="text-[10.5px] text-slate-600">Mme Gwenn LE BIHAN · Complétude & Conformité PLU validées</p>
                        <p className="text-[9.5px] font-mono text-slate-500 truncate" title="SHA-256: 7d2e9a1c8f4b5e6a0d3f2b1c8e7a6d5f4e3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a">
                          <span className="text-slate-400 font-sans">Empreinte SHA-256 :</span> 7d2e9a1c8f4b5e6a...0b9a
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Audit Trail Card */}
                <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                        Journal d’Audit des Visas & Scellements
                      </h3>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Norme ISO/IEC 19510
                    </span>
                  </div>

                  <div className="space-y-3 pt-1">
                    {selectedDossier.auditTrail.map((entry, idx) => (
                      <div key={idx} className="flex items-start gap-3 text-xs">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                        <div className="flex-1 space-y-0.5">
                          <div className="flex items-center justify-between gap-1 flex-wrap">
                            <span className="font-bold text-slate-900">
                              {entry.author}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {entry.timestamp}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 font-medium">
                            {entry.stepName} · {entry.role}
                          </p>
                          <p className="text-xs text-slate-700 bg-slate-50 p-2 rounded-lg border border-slate-100 mt-1">
                            « {entry.comment} »
                          </p>
                          {entry.sha256 && (
                            <div className="flex items-center gap-1 text-[10px] font-mono text-slate-400 mt-0.5">
                              <Hash className="w-2.5 h-2.5 text-blue-500" />
                              <span>Empreinte cryptographique : {entry.sha256}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Zone: Sticky Directive Decision Panel (5 cols) */}
              {(() => {
                const currentStep = selectedDossier.steps[selectedDossier.currentStepIndex] || selectedDossier.steps[0];
                const isStepCtm = currentStep.id === 'step-ctm' || currentStep.label.toLowerCase().includes('ctm') || currentStep.label.toLowerCase().includes('technique');
                const isStepMaire = currentStep.label.toLowerCase().includes('maire') || currentStep.role.toLowerCase().includes('maire');
                const isStepSocial = Boolean(selectedDossier.isConfidentialCCAS) || currentStep.label.toLowerCase().includes('social') || currentStep.id.includes('ccas');

                const dynamicDecisionTitle = isStepCtm
                  ? 'Avis Technique · Étape CTM'
                  : isStepMaire
                  ? 'Signature Finale Régitime · Étape Maire'
                  : isStepSocial
                  ? 'Évaluation Sociale · Étape CCAS'
                  : 'Visa Régalien · Étape DGS';

                const dynamicDecisionSubtitle = isStepCtm
                  ? 'Votre avis technique est requis pour instruire le dossier et le transmettre à la Direction Générale.'
                  : isStepMaire
                  ? 'Apposition de la signature exécutoire et télétransmission en Préfecture (@CTES).'
                  : isStepSocial
                  ? 'Instruction confidentielle soumise au secret professionnel (Art. L.226-13 du Code Pénal).'
                  : 'Votre visa est requis pour transmettre ce document à la signature finale du Maire.';

                const dynamicPrimaryCta = isStepCtm
                  ? 'Valider et transmettre à la DGS'
                  : isStepMaire
                  ? 'Signer et sceller l’acte régalien'
                  : isStepSocial
                  ? 'Valider et transmettre au Président du CCAS'
                  : 'Signer et transmettre au Maire';

                const dynamicRollbackCta = isStepCtm
                  ? 'Renvoyer à l’Agent instructeur'
                  : isStepMaire
                  ? 'Renvoyer à la Direction Générale (DGS)'
                  : isStepSocial
                  ? 'Renvoyer pour pièces complémentaires'
                  : 'Renvoyer au Chef CTM';

                return (
                  <div className="md:col-span-5">
                    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 sticky top-4">
                      <div className="border-b border-slate-100 pb-3">
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                            Panneau de Décision
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-slate-900">
                          {dynamicDecisionTitle}
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5 font-medium">
                          {dynamicDecisionSubtitle}
                        </p>
                      </div>

                      {/* Observation / Motif Textarea */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 flex items-center justify-between">
                          <span>Observation / Motif du visa</span>
                          <span className="text-[10px] text-slate-400 font-normal">Facultatif</span>
                        </label>
                        <textarea
                          rows={3}
                          value={decisionComment}
                          onChange={(e) => setDecisionComment(e.target.value)}
                          placeholder="Indiquez vos motifs, réserves ou remarques de validation..."
                          className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 bg-slate-50/50 hover:bg-white focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs shadow-2xs font-medium resize-none transition-colors"
                        />
                      </div>

                      {/* Decision Action Buttons */}
                      <div className="space-y-2 pt-1">
                        {/* Primary Button */}
                        <button
                          onClick={handleValidateAndSign}
                          className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition-colors cursor-pointer"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          <span>{dynamicPrimaryCta}</span>
                        </button>

                        {/* Parapheur External Push Button */}
                        <button
                          onClick={() => {
                            handleValidateAndSign();
                            toast.success('Dossier télétransmis sur i-Parapheur pour signature eIDAS RGS**.');
                          }}
                          className="w-full py-2 px-3 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 font-bold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-2xs"
                        >
                          <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                          <span>Viser et pousser vers i-Parapheur</span>
                        </button>

                        {/* Secondary Button */}
                        <button
                          onClick={() => setIsRollbackModalOpen(true)}
                          className="w-full py-2.5 px-4 rounded-xl border border-amber-300 bg-amber-50/70 hover:bg-amber-100 text-amber-900 font-bold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-2xs"
                        >
                          <RotateCcw className="w-4 h-4 text-amber-700" />
                          <span>{dynamicRollbackCta}</span>
                        </button>

                        {/* Mobile Quick Sign Magic Link Button */}
                        <button
                          onClick={() => {
                            const token = `${selectedDossier.id}.1763789000.9f86d081884c7d65`;
                            const url = `${window.location.origin}/#/quick-sign/${token}`;
                            navigator.clipboard?.writeText(url);
                            toast.success(`Lien d'émargement rapide Élu copié ! Prêt pour smartphone (validité 72h).`);
                          }}
                          className="w-full py-2 px-3 rounded-xl border border-blue-200 bg-blue-50/70 hover:bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
                          title="Copier le lien direct pour signature sur smartphone sans mot de passe"
                        >
                          <Smartphone className="w-3.5 h-3.5 text-blue-600" />
                          <span>Lien rapide Élu (Smartphone)</span>
                        </button>

                        {/* Tertiary Button: Refuser */}
                        <button
                          onClick={handleReject}
                          className="w-full py-1.5 px-3 rounded-xl border border-slate-200 hover:border-rose-300 text-slate-500 hover:text-rose-700 hover:bg-rose-50/50 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Refuser le dossier</span>
                        </button>
                      </div>

                  {/* SLA Summary */}
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-700">Échéance réglementaire :</span>
                      <span className="font-mono font-bold text-slate-900">{selectedDossier.slaDeadline}</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <span>Délégation :</span>
                      <span>Arrêté DGS-2026/04</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}
            </div>
          </div>
        ) : null}
      </div>

      {/* Rollback Directive Modal (Renvoyer à une étape) */}
      {isRollbackModalOpen && selectedDossier && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-150 text-slate-900">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-amber-50/50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center border border-amber-300">
                  <RotateCcw className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 leading-snug">
                    Renvoyer le dossier à une étape
                  </h3>
                  <p className="text-xs text-slate-500">
                    Dossier {selectedDossier.id} · {selectedDossier.circuitLabel}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsRollbackModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <XCircle className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4 text-xs">
              {/* Upstream Steps Radios */}
              <div className="space-y-2">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Sélectionnez l’étape de renvoi
                </label>
                <div className="space-y-2">
                  {[
                    { id: 'step-ctm', label: 'Chef des Services Techniques (CTM)', actor: 'Erwan KERVRAN · Services Techniques', desc: 'Réexamen technique réseaux & voirie' },
                    { id: 'step-agent', label: 'Agent instructeur / Guichet (ADS)', actor: 'Gwenn LE BIHAN · Instructrice', desc: 'Demande de pièces complémentaires Cerfa au pétitionnaire' },
                  ].map((step) => {
                    const isSelected = rollbackTargetStep === step.id;
                    return (
                      <div
                        key={step.id}
                        onClick={() => setRollbackTargetStep(step.id)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                          isSelected
                            ? 'border-amber-500 bg-amber-50/40 ring-2 ring-amber-400/20 shadow-xs'
                            : 'border-slate-200 bg-white hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">{step.label}</span>
                          <input
                            type="radio"
                            name="rollbackStep"
                            checked={isSelected}
                            onChange={() => setRollbackTargetStep(step.id)}
                            className="text-amber-600 focus:ring-amber-500"
                          />
                        </div>
                        <p className="text-[11px] text-slate-600 mt-0.5">{step.actor}</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">{step.desc}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Direct Rollback Exception Checkbox */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isDirectRollbackException}
                    onChange={(e) => setIsDirectRollbackException(e.target.checked)}
                    className="mt-0.5 text-amber-600 rounded focus:ring-amber-500"
                  />
                  <div className="text-xs">
                    <span className="font-bold text-slate-800">
                      Renvoi direct (exception hors boucle BPMN)
                    </span>
                    <p className="text-[11px] text-slate-500">
                      Autorise le recul immédiat du dossier sans exiger de transition cyclique prédéfinie dans le circuit standard.
                    </p>
                  </div>
                </label>
              </div>

              {/* Mandatory Reason */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1">
                  <span>Motif obligatoire du renvoi</span>
                  <span className="text-rose-600 font-bold">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  value={rollbackReason}
                  onChange={(e) => setRollbackReason(e.target.value)}
                  placeholder="Expliquez précisément les pièces ou corrections attendues..."
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 text-xs shadow-2xs font-medium resize-none"
                />
              </div>

              {/* Actions */}
              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsRollbackModalOpen(false)}
                  className="text-xs"
                >
                  Annuler
                </Button>
                <Button
                  type="button"
                  onClick={handleConfirmRollback}
                  className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-4 flex items-center gap-1.5 shadow-xs"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Confirmer le renvoi</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Mode Parapheur (Traitement en rafale) */}
      {isParapheurModeOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex flex-col justify-between p-3 sm:p-6 animate-in fade-in duration-150">
          <div className="w-full max-w-5xl mx-auto bg-white border border-slate-200 rounded-3xl shadow-2xl flex flex-col overflow-hidden max-h-[92vh] text-slate-900">
            {/* Parapheur Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-xs shadow-2xs">
                  <Play className="w-4 h-4 fill-current" />
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm sm:text-base font-bold text-slate-900">
                      Mode Parapheur · Traitement en rafale
                    </h2>
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-800">
                      Dossier {Math.min(parapheurIndex + 1, pendingDossiers.length)} sur {pendingDossiers.length}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Raccourcis clavier : [V] Viser · [R] Renvoyer · [&rarr;] Suivant · [Échap] Quitter
                  </p>
                </div>
              </div>

              <button
                onClick={() => setIsParapheurModeOpen(false)}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Fermer le mode parapheur"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Parapheur Content */}
            {pendingDossiers.length === 0 || parapheurIndex >= pendingDossiers.length ? (
              <div className="p-12 text-center space-y-3">
                <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 mx-auto flex items-center justify-center border-2 border-emerald-200">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">
                  Tous les dossiers ont été visés !
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Votre file d’approbation régalienne est à jour. Les actes ont été télétransmis et scellés.
                </p>
                <Button
                  onClick={() => setIsParapheurModeOpen(false)}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-xl shadow-xs"
                >
                  Revenir à la liste
                </Button>
              </div>
            ) : (
              (() => {
                const cur = pendingDossiers[parapheurIndex];
                return (
                  <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    {/* Upper row: ID, title, applicant */}
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                            {cur.id}
                          </span>
                          <span className="text-xs font-bold text-slate-900">{cur.circuitLabel}</span>
                          <span className="text-xs text-slate-400">·</span>
                          <span className="text-xs text-slate-600 font-medium">{cur.applicant}</span>
                        </div>
                        <h3 className="text-sm font-bold text-slate-900 leading-snug">{cur.title}</h3>
                      </div>
                      <div className="shrink-0 flex items-center gap-1.5 font-mono text-xs font-bold text-amber-800 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-xl">
                        <Clock className="w-3.5 h-3.5" />
                        <span>{cur.slaDeadline}</span>
                      </div>
                    </div>

                    {/* Document Preview & Text */}
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                      <div className="md:col-span-8 p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-2">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                          Extrait officiel de l’acte municipal
                        </span>
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-800 font-sans leading-relaxed max-h-64 overflow-y-auto whitespace-pre-line">
                          {cur.documentExcerpt || cur.previewArticle || "ARTICLE 1ER : La circulation des véhicules sera temporairement alternée par feux tricolores du 24 au 28 novembre 2026, au droit du chantier Rue des Ajoncs.\n\nARTICLE 2 : La vitesse maximale autorisée est abaissée à 30 km/h aux abords directs de la zone de travaux.\n\nARTICLE 3 : Le présent arrêté sera télétransmis en Préfecture du Finistère (@CTES) et affiché en mairie."}
                        </div>
                      </div>

                      <div className="md:col-span-4 space-y-3">
                        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                            Pièces jointes
                          </span>
                          {cur.documents.map((doc, idx) => (
                            <div key={idx} className="p-2 rounded-xl bg-white border border-slate-200 text-xs flex items-center justify-between">
                              <span className="truncate font-semibold text-slate-800 text-[11px]">{doc.name}</span>
                              <span className="text-[10px] text-slate-400">{doc.size}</span>
                            </div>
                          ))}
                        </div>

                        <div className="p-3.5 rounded-2xl bg-blue-50/60 border border-blue-200 text-[11px] text-blue-900 space-y-1">
                          <span className="font-bold block">Conformité réglementaire</span>
                          <p className="text-[10px] text-blue-800 leading-relaxed">
                            Contrôle préalable conforme aux articles L.2212-2 du CGCT. Visa prêt pour télétransmission @CTES.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setParapheurIndex(prev => Math.max(0, prev - 1))}
                          disabled={parapheurIndex === 0}
                          className="text-xs"
                        >
                          Précédent
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setParapheurIndex(prev => Math.min(pendingDossiers.length - 1, prev + 1))}
                          disabled={parapheurIndex >= pendingDossiers.length - 1}
                          className="text-xs"
                        >
                          Dossier suivant [&rarr;]
                        </Button>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedDossierId(cur.id);
                            setIsParapheurModeOpen(false);
                            setIsRollbackModalOpen(true);
                          }}
                          className="border-amber-300 text-amber-800 hover:bg-amber-50 text-xs font-bold"
                        >
                          <RotateCcw className="w-3.5 h-3.5 mr-1" />
                          <span>Renvoyer [R]</span>
                        </Button>

                        <Button
                          size="sm"
                          onClick={() => {
                            onUpdateDossier({
                              ...cur,
                              status: 'signed',
                              currentStepIndex: cur.steps.length - 1
                            });
                            toast.success(`Dossier ${cur.id} visé et transmis !`);
                            setParapheurIndex(prev => prev + 1);
                          }}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs px-4 shadow-xs"
                        >
                          <CheckCircle2 className="w-4 h-4 mr-1.5" />
                          <span>Signer & Passer au suivant [V]</span>
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })()
            )}
          </div>
        </div>
      )}
    </div>
  );
}
