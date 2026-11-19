import React, { useState } from 'react';
import { 
  X, 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  Clock, 
  Building2, 
  Layers, 
  ShieldCheck,
  Send
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ValidationDossier } from './validationData';
import { useOrganizationModules } from '@/features/workspace/organization-modules-context';

interface MayorValidationLaunchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLaunch: (newDossier: ValidationDossier) => void;
}

export function MayorValidationLaunchModal({ isOpen, onClose, onLaunch }: MayorValidationLaunchModalProps) {
  const { hasModule } = useOrganizationModules();

  const allCircuits = [
    { id: 'arrete', label: 'Arrêté de Voirie', icon: Building2, module: 'travaux_terrain' },
    { id: 'permis', label: 'Permis Construire', icon: FileText, module: 'urbanisme_ads' },
    { id: 'marche', label: 'Marché Public', icon: ShieldCheck, module: 'finances_m57' },
    { id: 'deliberation', label: 'Délibération', icon: Layers, module: 'conseil_seances' },
  ];

  const circuitsToDisplay = allCircuits.filter(c => !c.module || hasModule(c.module));
  const activeCircuits = circuitsToDisplay.length > 0 ? circuitsToDisplay : [
    { id: 'arrete', label: 'Circuit Standard', icon: Layers, module: '' }
  ];

  const [circuitType, setCircuitType] = useState<'arrete' | 'permis' | 'marche' | 'deliberation'>(() => {
    return (activeCircuits[0]?.id as any) || 'arrete';
  });
  const [title, setTitle] = useState('Arrêté municipal · Travaux voirie Rue des Ajoncs');
  const [applicant, setApplicant] = useState('Entreprise Ouest Réseaux · Brest');
  const [priority, setPriority] = useState<'normal' | 'urgent'>('urgent');
  const [fileName, setFileName] = useState('Projet_Arrete_Ajoncs_2026.pdf');
  const [fileSize, setFileSize] = useState('1.4 Mo');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    const circuitLabels: Record<string, string> = {
      arrete: 'Arrêté de Voirie & Police',
      permis: 'Permis de Construire (ADS)',
      marche: 'Marché Public (CAO)',
      deliberation: 'Délibération du Conseil',
      standard: 'Circuit de Validation Standard',
    };

    const newDossier: ValidationDossier = {
      id: `${circuitType.toUpperCase().slice(0, 3)}-2026-${Math.floor(100 + Math.random() * 900)}`,
      title: title.trim(),
      circuitType,
      circuitLabel: circuitLabels[circuitType] || 'Arrêté Municipal',
      applicant: applicant.trim() || 'Collectivité de Plougastel',
      applicantAddress: 'Mairie de Plougastel-Daoulas',
      createdAt: 'Aujourd’hui à l’instant',
      slaDeadline: priority === 'urgent' ? 'Sous 24h' : 'Sous 72h',
      slaStatus: priority === 'urgent' ? 'warning' : 'ok',
      priority,
      currentStepIndex: 0, // Starts at Agent
      status: 'pending',
      steps: [
        {
          id: 'step-agent',
          label: 'Agent instructeur',
          role: 'Instructeur Référent',
          actor: 'Gwenn LE BIHAN',
          status: 'active',
        },
        {
          id: 'step-ctm',
          label: 'Chef Services Techniques',
          role: 'Responsable CTM & Voirie',
          actor: 'Erwan KERVRAN',
          status: 'upcoming',
        },
        {
          id: 'step-dgs',
          label: 'Direction Générale (DGS)',
          role: 'Contrôle Légalité',
          actor: 'Marie ROLLAND (DGS)',
          status: 'upcoming',
        },
        {
          id: 'step-maire',
          label: 'Maire de Plougastel',
          role: 'Signature Arrêté',
          actor: 'Dominique CAP (Maire)',
          status: 'upcoming',
        },
      ],
      documents: [
        { name: fileName, size: fileSize, type: 'Document PDF officiel', badge: 'Prêt pour visa' },
      ],
      auditTrail: [
        {
          timestamp: 'Aujourd’hui · À l’instant',
          author: 'Initiateur du circuit',
          role: 'Agent de saisie',
          action: 'depot',
          stepName: 'Création du circuit',
          comment: `Lancement du circuit de validation directive pour « ${title.trim()} ».`,
        },
      ],
      previewArticle: `ARTICLE 1ER : La présente décision prend effet à compter de sa signature par l’autorité municipale.\n\nARTICLE 2 : Monsieur le Directeur Général des Services est chargé de l’exécution du présent arrêté.`,
    };

    onLaunch(newDossier);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150 font-sans">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden animate-in zoom-in-95 duration-150 text-slate-900">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 leading-snug">
                Lancer un nouveau circuit de validation
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Validation municipale directive · Agent ➔ CTM ➔ DGS ➔ Maire
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            title="Fermer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {/* Circuit Type Selection */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Modèle de circuit municipal
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {activeCircuits.map((c) => {
                const isSelected = circuitType === c.id;
                const Icon = c.icon;
                return (
                  <button
                    type="button"
                    key={c.id}
                    onClick={() => setCircuitType(c.id as any)}
                    className={`p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50/40 text-blue-900 ring-2 ring-blue-500/20 font-bold shadow-xs'
                        : 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                    }`}
                  >
                    <Icon className={`w-4 h-4 mb-1.5 ${isSelected ? 'text-blue-600' : 'text-slate-400'}`} />
                    <span className="text-[11px] leading-tight">{c.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Document Title */}
          <div className="space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Titre officiel du document
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Arrêté municipal portant autorisation de voirie..."
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs shadow-2xs font-medium"
            />
          </div>

          {/* Applicant & Priority Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Demandeur / Pétitionnaire
              </label>
              <input
                type="text"
                value={applicant}
                onChange={(e) => setApplicant(e.target.value)}
                placeholder="Ex: Entreprise Colas, M. Dupont..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs shadow-2xs font-medium"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Délai réglementaire SLA
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPriority('urgent')}
                  className={`flex-1 py-2 px-2 rounded-xl border text-center font-semibold transition-all ${
                    priority === 'urgent'
                      ? 'border-amber-400 bg-amber-50 text-amber-800 ring-2 ring-amber-400/20 shadow-2xs'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Urgent (24h)
                </button>
                <button
                  type="button"
                  onClick={() => setPriority('normal')}
                  className={`flex-1 py-2 px-2 rounded-xl border text-center font-semibold transition-all ${
                    priority === 'normal'
                      ? 'border-blue-400 bg-blue-50 text-blue-800 ring-2 ring-blue-400/20 shadow-2xs'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Standard (72h)
                </button>
              </div>
            </div>
          </div>

          {/* PDF Dropzone */}
          <div className="space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Document officiel à soumettre (PDF)
            </label>
            <div className="border border-dashed border-slate-200 hover:border-blue-400 rounded-xl p-4 bg-slate-50/50 flex flex-col items-center justify-center text-center gap-1.5 transition-colors cursor-pointer">
              <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-blue-600">
                <UploadCloud className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-800">
                  {fileName}
                </p>
                <p className="text-[10px] text-slate-400">
                  Document joint certifié ({fileSize}) · Cliquez pour remplacer le fichier
                </p>
              </div>
            </div>
          </div>

          {/* Stepper Preview */}
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-[11px] font-medium text-slate-600">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
              <span>Circuit configuré :</span>
            </div>
            <div className="font-mono text-[10px] text-slate-500">
              Agent ➔ Chef CTM ➔ DGS ➔ Maire
            </div>
          </div>

          {/* Actions */}
          <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="text-xs"
            >
              Annuler
            </Button>
            <Button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 flex items-center gap-1.5 shadow-xs"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Démarrer immédiatement la validation</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
