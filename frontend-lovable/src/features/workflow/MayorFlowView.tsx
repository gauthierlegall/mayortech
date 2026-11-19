import React, { useState } from 'react';
import {
  Inbox,
  Sparkles,
  Plus,
  GitFork,
  CheckCircle2
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

  const navItems: { id: MayorFlowMainTab; label: string; badge?: number }[] = [
    {
      id: 'validation',
      label: 'À valider',
      badge: pendingCount,
    },
    {
      id: 'suivi',
      label: 'Suivi du circuit',
    },
    {
      id: 'concepteur',
      label: 'Concepteur',
    },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto space-y-3 font-sans text-stone-900 pb-10">
      {/* Barre 1 (En-tête unifié de vue) : Titre à gauche, les 3 onglets centrés/alignés sur la même ligne, et le bouton + Nouvelle validation en #102A4C text-white à droite */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-stone-200 pb-3">
        <h1 className="text-xl sm:text-2xl font-bold text-stone-900 tracking-tight shrink-0">
          Circuits de validation
        </h1>

        {/* 3-Tab Rail */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs py-0.5">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-bold transition-all shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-[#102A4C] text-white shadow-3xs'
                    : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                }`}
              >
                {item.id === 'validation' && <Inbox size={15} className={isActive ? 'text-white' : 'text-[#102A4C]'} />}
                {item.id === 'suivi' && <GitFork size={15} className={isActive ? 'text-white' : 'text-emerald-600'} />}
                {item.id === 'concepteur' && <Sparkles size={15} className={isActive ? 'text-white' : 'text-purple-600'} />}
                <span className={isActive ? 'text-white' : ''}>{item.label}</span>
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

        {/* Primary Action Button: + Nouvelle validation */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            onClick={() => setIsLaunchModalOpen(true)}
            className="bg-[#102A4C] hover:bg-[#193D6B] text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow-3xs transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 text-white" />
            <span className="text-white font-semibold">+ Nouvelle validation</span>
          </Button>
        </div>
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
