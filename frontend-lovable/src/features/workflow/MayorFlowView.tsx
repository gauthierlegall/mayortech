import React, { useState } from 'react';
import {
  Inbox,
  PenTool,
  Sparkles,
  Layers,
  Plus,
  GitFork,
  CheckCircle2,
  Send
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

import { ValidationDossier, INITIAL_DOSSIERS } from './validation/validationData';
import { MayorValidationInbox } from './validation/MayorValidationInbox';
import { MayorValidationLaunchModal } from './validation/MayorValidationLaunchModal';
import { PixelFlowCanvas } from './pixelflow/PixelFlowCanvas';
import { MayorWorkflowDesigner } from './designer/MayorWorkflowDesigner';

import { useWorkspace } from '../workspace/context';
import { getCommissionConfig } from '../workspace/commissionConfig';

export type MayorFlowMainTab = 'validation' | 'suivi' | 'concepteur';

export function MayorFlowView() {
  const [activeTab, setActiveTab] = useState<MayorFlowMainTab>('validation');
  const [dossiers, setDossiers] = useState<ValidationDossier[]>(INITIAL_DOSSIERS);
  const [selectedDossierId, setSelectedDossierId] = useState<string>(INITIAL_DOSSIERS[0].id);
  const [isLaunchModalOpen, setIsLaunchModalOpen] = useState(false);

  const { activeCommissionId } = useWorkspace();
  const commissionCfg = getCommissionConfig(activeCommissionId);
  const allowedDossiers = dossiers.filter((d) => commissionCfg.allowedDossierIds.includes(d.id));
  const effectiveDossiers = allowedDossiers.length > 0 ? allowedDossiers : dossiers;

  // Counter of active pending validation tasks for the active commission
  const pendingCount = effectiveDossiers.filter((d) => d.status === 'pending').length;

  const handleUpdateDossier = (updated: ValidationDossier) => {
    setDossiers((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  };

  const handleLaunchNewDossier = (newDossier: ValidationDossier) => {
    setDossiers((prev) => [newDossier, ...prev]);
    setSelectedDossierId(newDossier.id);
    setActiveTab('validation');
    toast.success(`Circuit « ${newDossier.title} » initié et disponible dans votre file !`);
  };

  const navItems: { id: MayorFlowMainTab; label: string; icon: React.ReactNode; badge?: number }[] = [
    {
      id: 'validation',
      label: 'À valider',
      icon: <Inbox size={15} className="text-[#102A4C]" />,
      badge: pendingCount,
    },
    {
      id: 'suivi',
      label: 'Suivi du circuit',
      icon: <GitFork size={15} className="text-emerald-600" />,
    },
    {
      id: 'concepteur',
      label: 'Concepteur',
      icon: <Sparkles size={15} className="text-purple-600" />,
    },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto space-y-3 font-sans text-slate-900 pb-10">
      {/* Hide floating assistant FAB on mobile view and keep it under drawer on desktop */}
      <style>{`
        @media (max-width: 768px) {
          .assistant-widget {
            display: none !important;
          }
        }
        .assistant-widget {
          z-index: 20 !important;
        }
      `}</style>

      {/* Header: Circuits de validation + Ville de Plougastel-Daoulas + Button + Lancer une validation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Circuits de validation
          </h1>
          <span className="text-xs text-slate-500 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-md font-medium">
            Ville de Plougastel-Daoulas
          </span>
        </div>

        {/* Primary Action Button: + Lancer une validation */}
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setIsLaunchModalOpen(true)}
            className="bg-[#102A4C] hover:bg-[#193D6B] text-white font-semibold text-xs px-3.5 py-2 rounded-md flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Lancer une validation</span>
          </Button>
        </div>
      </div>

      {/* Directive 3-Tab Rail */}
      <div className="flex items-center gap-2 border-b border-stone-200/80 pb-2 text-xs">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-md font-bold transition-all duration-150 shrink-0 ${
                isActive
                  ? 'bg-[#102A4C] text-white shadow-xs'
                  : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                    isActive ? 'bg-white/20 text-white' : 'bg-stone-100 text-[#102A4C]'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Views */}
      <div className="pt-1">
        {activeTab === 'validation' && (
          <MayorValidationInbox
            dossiers={effectiveDossiers}
            onUpdateDossier={handleUpdateDossier}
            onViewBpmn={(dossierId) => {
              setSelectedDossierId(dossierId);
              setActiveTab('suivi');
            }}
          />
        )}

        {activeTab === 'suivi' && (
          <PixelFlowCanvas
            dossiers={effectiveDossiers}
            selectedDossierId={effectiveDossiers.some(d => d.id === selectedDossierId) ? selectedDossierId : effectiveDossiers[0]?.id || dossiers[0]?.id}
            onSelectDossierId={setSelectedDossierId}
            onOpenDecision={() => setActiveTab('validation')}
            onOpenValidation={(dossierId) => {
              if (dossierId) {
                setSelectedDossierId(dossierId);
              }
              setActiveTab('validation');
            }}
            onOpenStudio={() => setActiveTab('concepteur')}
          />
        )}

        {activeTab === 'concepteur' && (
          <MayorWorkflowDesigner
            onLaunchSimulation={() => setActiveTab('suivi')}
          />
        )}
      </div>

      {/* Modal: + Lancer une validation */}
      <MayorValidationLaunchModal
        isOpen={isLaunchModalOpen}
        onClose={() => setIsLaunchModalOpen(false)}
        onLaunch={handleLaunchNewDossier}
      />
    </div>
  );
}
