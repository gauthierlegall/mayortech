import React, { useState } from 'react';
import {
  Inbox,
  SlidersHorizontal,
  Plus,
  GitFork,
  CheckCircle2,
  UploadCloud
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
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [dropInitialData, setDropInitialData] = useState<any>(null);

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

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    // Only unset if leaving the container
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDraggingOver(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      const fileName = file.name;
      const cleanTitle = fileName.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
      const lower = fileName.toLowerCase();
      let cType: 'arrete' | 'permis' | 'marche' | 'deliberation' = 'arrete';
      if (lower.includes('permis') || lower.includes('ads') || lower.includes('pc')) cType = 'permis';
      else if (lower.includes('marche') || lower.includes('cao') || lower.includes('mp')) cType = 'marche';
      else if (lower.includes('delib') || lower.includes('m57') || lower.includes('conseil')) cType = 'deliberation';

      setDropInitialData({
        title: `Arrêté municipal · ${cleanTitle}`,
        applicant: 'Entreprise pétitionnaire (Déposé)',
        fileName: file.name,
        priority: 'urgent',
        circuitType: cType,
      });
      setIsLaunchModalOpen(true);
      toast.success(`Document « ${file.name} » ingéré · Modèle ${cType} pré-rempli.`);
    }
  };

  return (
    <div 
      className="w-full max-w-7xl mx-auto space-y-3 font-sans text-stone-900 pb-10 relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Glisser-déposer Overlay Sobre */}
      {isDraggingOver && (
        <div className="absolute inset-0 bg-[#F7F7F5]/90 border-2 border-dashed border-[#102A4C] rounded-2xl flex flex-col items-center justify-center gap-2.5 z-50 backdrop-blur-xs animate-in fade-in duration-100">
          <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center text-[#102A4C] shadow-2xs">
            <UploadCloud className="w-6 h-6" />
          </div>
          <p className="text-sm font-bold text-[#102A4C]">Déposer le document PDF pour lancer un circuit</p>
          <p className="text-xs text-stone-500">Ingestion instantanée zéro ressaisie · Détection automatique du modèle</p>
        </div>
      )}

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
                {item.id === 'concepteur' && <SlidersHorizontal size={15} className={isActive ? 'text-white' : 'text-purple-600'} />}
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
            variant="outline"
            onClick={() => {
              setDropInitialData(null);
              setIsLaunchModalOpen(true);
            }}
            className="bg-white border border-stone-200 hover:border-stone-400 text-stone-800 font-medium text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow-3xs transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 text-stone-600" />
            <span>Nouvelle validation</span>
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
        onClose={() => {
          setIsLaunchModalOpen(false);
          setDropInitialData(null);
        }}
        onLaunch={handleLaunchNewDossier}
        initialData={dropInitialData || undefined}
      />
    </div>
  );
}
