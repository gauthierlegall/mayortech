import React, { useState, useEffect } from 'react';
import { 
  X, 
  UploadCloud, 
  FileText, 
  Building2, 
  Layers, 
  ShieldCheck,
  Send,
  Eye,
  SlidersHorizontal,
  ChevronDown,
  Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ValidationDossier } from './validationData';
import { useOrganizationModules } from '@/features/workspace/organization-modules-context';
import { 
  ACT_TEMPLATES, 
  renderTemplateText, 
  evaluateFinancialThreshold,
  ActTemplate 
} from './actTemplates';

interface MayorValidationLaunchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLaunch: (newDossier: ValidationDossier) => void;
  initialData?: {
    title?: string;
    applicant?: string;
    fileName?: string;
    priority?: 'normal' | 'urgent';
    circuitType?: 'arrete' | 'permis' | 'marche' | 'deliberation';
    variables?: Record<string, string>;
  };
}

export function MayorValidationLaunchModal({ isOpen, onClose, onLaunch, initialData }: MayorValidationLaunchModalProps) {
  const { hasModule } = useOrganizationModules();

  const allCircuits = [
    { id: 'arrete', label: 'Arrêté de Voirie', icon: Building2, module: 'travaux_terrain' },
    { id: 'permis', label: 'Permis Construire', icon: FileText, module: 'urbanisme_ads' },
    { id: 'marche', label: 'Marché Public', icon: ShieldCheck, module: 'finances_m57' },
    { id: 'deliberation', label: 'Délibération M57', icon: Layers, module: 'conseil_seances' },
  ];

  const circuitsToDisplay = allCircuits.filter(c => !c.module || hasModule(c.module));
  const activeCircuits = circuitsToDisplay.length > 0 ? circuitsToDisplay : [
    { id: 'arrete', label: 'Circuit Standard', icon: Layers, module: '' }
  ];

  const [circuitType, setCircuitType] = useState<'arrete' | 'permis' | 'marche' | 'deliberation'>(() => {
    return initialData?.circuitType || (activeCircuits[0]?.id as any) || 'arrete';
  });

  const [title, setTitle] = useState(initialData?.title || '');
  const [applicant, setApplicant] = useState(initialData?.applicant || '');
  const [priority, setPriority] = useState<'normal' | 'urgent'>(initialData?.priority || 'normal');
  const [fileName, setFileName] = useState(initialData?.fileName || 'Acte_Projet_Officiel.pdf');
  const [fileSize, setFileSize] = useState('1.4 Mo');
  const [showLivePreview, setShowLivePreview] = useState(true);

  // Template variables state
  const currentTemplate: ActTemplate = ACT_TEMPLATES[circuitType] || ACT_TEMPLATES.arrete;
  const [variables, setVariables] = useState<Record<string, string>>(() => {
    const initVars: Record<string, string> = {};
    currentTemplate.variables.forEach(v => {
      initVars[v.key] = v.defaultValue;
    });
    return { ...initVars, ...(initialData?.variables || {}) };
  });

  // Re-sync variables when circuitType changes
  useEffect(() => {
    const tmpl = ACT_TEMPLATES[circuitType] || ACT_TEMPLATES.arrete;
    const nextVars: Record<string, string> = {};
    tmpl.variables.forEach(v => {
      nextVars[v.key] = v.defaultValue;
    });
    if (initialData?.variables) {
      Object.assign(nextVars, initialData.variables);
    }
    setVariables(nextVars);

    // Auto title if empty or default
    if (!initialData?.title) {
      if (circuitType === 'arrete') setTitle('Arrêté municipal · Travaux voirie Rue de Pen ar Men');
      if (circuitType === 'permis') setTitle('Permis de Construire · Extension Ty-Ar-Braz');
      if (circuitType === 'marche') setTitle('Attribution Marché Public · Restauration Avel-Vor');
      if (circuitType === 'deliberation') setTitle('Délibération budgétaire M57 · Affectation du résultat');
    }
    if (!initialData?.applicant) {
      if (circuitType === 'arrete') setApplicant('Entreprise Ouest Réseaux · Brest');
      if (circuitType === 'permis') setApplicant('M. & Mme Jean-Luc QUÉRÉ');
      if (circuitType === 'marche') setApplicant('SAS Ouest Charpentes & Énergie');
      if (circuitType === 'deliberation') setApplicant('Direction des Finances');
    }
  }, [circuitType]);

  // Keep title/applicant synced if passed in initialData
  useEffect(() => {
    if (initialData?.title) setTitle(initialData.title);
    if (initialData?.applicant) setApplicant(initialData.applicant);
    if (initialData?.fileName) setFileName(initialData.fileName);
    if (initialData?.priority) setPriority(initialData.priority);
    if (initialData?.circuitType) setCircuitType(initialData.circuitType);
  }, [initialData]);

  if (!isOpen) return null;

  // Financial Threshold Evaluation
  const amountHtValue = variables.montant_ht ? parseFloat(variables.montant_ht) : undefined;
  const thresholdEval = evaluateFinancialThreshold(circuitType, amountHtValue);

  // Rendered preview text
  const renderedActeText = renderTemplateText(currentTemplate.bodyTemplate, variables);

  const handleVariableChange = (key: string, val: string) => {
    setVariables(prev => {
      const updated = { ...prev, [key]: val };
      // Sync demandeur to applicant
      if (key === 'demandeur' || key === 'titulaire') {
        setApplicant(val);
      }
      return updated;
    });
  };

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

    const newDossierId = `${circuitType.toUpperCase().slice(0, 3)}-2026-${Math.floor(100 + Math.random() * 900)}`;

    const newDossier: ValidationDossier = {
      id: newDossierId,
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
          comment: `Lancement du circuit de validation directive pour « ${title.trim()} ». Modèle appliqué : ${currentTemplate.title}. ${thresholdEval.ruleLabel}`,
        },
      ],
      previewArticle: renderedActeText,
    };

    // Attach financial / delegation details
    (newDossier as any).amountHt = amountHtValue;
    (newDossier as any).delegationRuleApplied = thresholdEval.ruleLabel;
    (newDossier as any).templateVariables = variables;

    onLaunch(newDossier);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-xs animate-in fade-in duration-150 font-sans">
      <div className="bg-[#F7F7F5] border border-stone-200 rounded-2xl shadow-xl w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-150 text-stone-900">
        
        {/* Header : Sobre Civic Craft */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-stone-100 border border-stone-200 text-[#102A4C] flex items-center justify-center font-bold">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#102A4C] leading-snug">
                Nouveau circuit de validation directive
              </h2>
              <p className="text-xs text-stone-500 font-medium">
                Gabarits officiels à variables & seuil de délégation · Ville de Plougastel-Daoulas
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors"
            title="Fermer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5 text-xs divide-y divide-stone-200/80">
          
          {/* Section 1 : Choix du Gabarit Juridique */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold uppercase tracking-wider text-stone-600">
              Modèle d'acte officiel
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
                    className={`p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all cursor-pointer ${
                      isSelected
                        ? 'border-[#102A4C] bg-white text-[#102A4C] ring-2 ring-[#102A4C]/15 font-bold shadow-xs'
                        : 'border-stone-200 bg-white/60 hover:border-stone-300 text-stone-700'
                    }`}
                  >
                    <Icon className={`w-4 h-4 mb-1.5 ${isSelected ? 'text-[#102A4C]' : 'text-stone-400'}`} />
                    <span className="text-[11px] leading-tight">{c.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 2 : Variables dynamiques du gabarit */}
          <div className="pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold uppercase tracking-wider text-stone-600">
                Variables de l'acte · {currentTemplate.title}
              </label>
              <span className="text-[11px] text-stone-500 font-mono">
                Remplacement dynamique sans ressaisie
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {currentTemplate.variables.map((variable) => (
                <div key={variable.key} className="space-y-1">
                  <label className="text-[10px] font-semibold text-stone-600">
                    {variable.label}
                  </label>
                  <input
                    type={variable.type === 'number' ? 'number' : 'text'}
                    value={variables[variable.key] || ''}
                    onChange={(e) => handleVariableChange(variable.key, e.target.value)}
                    placeholder={variable.placeholder}
                    className="w-full px-3 py-1.5 rounded-lg border border-stone-200 bg-white text-stone-900 text-xs focus:outline-none focus:ring-1 focus:ring-[#102A4C] focus:border-[#102A4C]"
                  />
                </div>
              ))}
            </div>

            {/* Moteur de délégation & seuil financier (10 000 € HT) */}
            {currentTemplate.hasFinancialThreshold && (
              <div className="mt-2 p-2.5 rounded-xl border border-stone-200 bg-white flex items-start gap-2.5 text-xs">
                <Info className="w-4 h-4 text-stone-500 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="font-semibold text-stone-900">
                    Règle de délégation active :
                  </p>
                  <p className={`font-mono text-[11px] ${thresholdEval.isOverThreshold ? 'text-amber-800 font-bold' : 'text-stone-600'}`}>
                    {thresholdEval.ruleLabel}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Section 3 : Métadonnées du circuit (Titre & Priorité) */}
          <div className="pt-4 space-y-3">
            <div className="space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-stone-600">
                Titre officiel pour le parapheur
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex: Arrêté municipal..."
                className="w-full px-3 py-2 rounded-lg border border-stone-200 bg-white text-stone-900 font-medium text-xs focus:outline-none focus:ring-1 focus:ring-[#102A4C] focus:border-[#102A4C]"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-stone-600">
                  Demandeur / Attributaire
                </label>
                <input
                  type="text"
                  value={applicant}
                  onChange={(e) => setApplicant(e.target.value)}
                  placeholder="Ex: Entreprise..."
                  className="w-full px-3 py-1.5 rounded-lg border border-stone-200 bg-white text-stone-900 text-xs focus:outline-none focus:ring-1 focus:ring-[#102A4C] focus:border-[#102A4C]"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold uppercase tracking-wider text-stone-600">
                  Délai réglementaire SLA
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPriority('urgent')}
                    className={`flex-1 py-1.5 px-2 rounded-lg border text-center font-semibold transition-all cursor-pointer ${
                      priority === 'urgent'
                        ? 'border-amber-400 bg-amber-50 text-amber-800 ring-1 ring-amber-400/40'
                        : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50'
                    }`}
                  >
                    Urgent (24h)
                  </button>
                  <button
                    type="button"
                    onClick={() => setPriority('normal')}
                    className={`flex-1 py-1.5 px-2 rounded-lg border text-center font-semibold transition-all cursor-pointer ${
                      priority === 'normal'
                        ? 'border-stone-400 bg-stone-100 text-[#102A4C] ring-1 ring-[#102A4C]/30'
                        : 'border-stone-200 bg-white text-stone-600 hover:bg-stone-50'
                    }`}
                  >
                    Standard (72h)
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section 4 : Aperçu éditorial direct (Source Serif 4 / Georgia) */}
          <div className="pt-4 space-y-2">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setShowLivePreview(!showLivePreview)}
                className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-stone-600 hover:text-stone-900 cursor-pointer"
              >
                <Eye className="w-3.5 h-3.5 text-stone-500" />
                <span>Aperçu de l'acte officiel généré</span>
                <ChevronDown className={`w-3.5 h-3.5 text-stone-400 transition-transform ${showLivePreview ? 'rotate-180' : ''}`} />
              </button>
              <span className="text-[10px] text-stone-500 italic">Typographie officielle République Française</span>
            </div>

            {showLivePreview && (
              <div className="p-4 rounded-xl border border-stone-200 bg-white shadow-2xs font-serif text-stone-800 space-y-3">
                {/* Micro-filet tricolore officiel */}
                <div className="flex h-1 w-20 rounded-full overflow-hidden mx-auto mb-2">
                  <div className="w-1/3 bg-blue-600" />
                  <div className="w-1/3 bg-white border-y border-stone-200" />
                  <div className="w-1/3 bg-red-600" />
                </div>
                
                <div className="text-center border-b border-stone-200 pb-2">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-[#102A4C]">RÉPUBLIQUE FRANÇAISE</p>
                  <p className="text-[10px] text-stone-500">Ville de Plougastel-Daoulas · Arrondissement de Brest</p>
                </div>

                <div className="text-[12px] leading-relaxed whitespace-pre-wrap font-serif text-stone-800">
                  {renderedActeText}
                </div>

                <div className="pt-2 border-t border-stone-200 text-right text-[11px] text-stone-600 font-sans">
                  <p className="font-semibold text-stone-900">Pour le Maire de Plougastel-Daoulas,</p>
                  <p className="text-[10px] text-stone-500 mt-0.5">Le Caractère exécutoire sera certifié à l'émargement final.</p>
                </div>
              </div>
            )}
          </div>

          {/* Section 5 : Document PDF joint */}
          <div className="pt-4 space-y-1.5">
            <div className="border border-dashed border-stone-300 hover:border-stone-400 rounded-xl p-3 bg-white/70 flex items-center justify-between transition-colors">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-stone-100 flex items-center justify-center text-[#102A4C]">
                  <UploadCloud className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-stone-900">{fileName}</p>
                  <p className="text-[10px] text-stone-500">Document joint certifié ({fileSize})</p>
                </div>
              </div>
              <span className="text-[10px] font-mono text-stone-500">Prêt pour visa</span>
            </div>
          </div>

        </form>

        {/* Footer : Exactly 1 Primary Full Button */}
        <div className="px-6 py-3.5 bg-white border-t border-stone-200 flex items-center justify-between shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-semibold text-stone-600 hover:text-stone-900 px-3 py-1.5 rounded-lg hover:bg-stone-100 transition-colors cursor-pointer"
          >
            Annuler
          </button>
          <Button
            type="button"
            onClick={handleSubmit}
            className="bg-[#102A4C] hover:bg-[#193D6B] text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 shadow-2xs cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Démarrer immédiatement la validation</span>
          </Button>
        </div>

      </div>
    </div>
  );
}
