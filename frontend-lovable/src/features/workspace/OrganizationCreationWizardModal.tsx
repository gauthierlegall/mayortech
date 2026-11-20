import React, { useState } from 'react';
import {
  X,
  Building2,
  Users,
  GitBranch,
  FileCheck2,
  Building,
  Anchor,
  HardHat,
  GraduationCap,
  Coins,
  Landmark,
  Mail,
  
  Send,
  ShieldCheck,
  Smartphone,
  Lock,
  Check,
  ChevronRight,
  ChevronLeft,
  UploadCloud,
  FileSpreadsheet,
  Link2,
  Sparkle,
  Layers,
  ArrowRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useOrganizationModules, ModuleItem } from './organization-modules-context';

const ICON_MAP: Record<string, React.ElementType> = {
  Users,
  GitBranch,
  FileCheck2,
  Building,
  Anchor,
  HardHat,
  GraduationCap,
  Coins,
  Landmark,
  Mail,
  
  Send,
  ShieldCheck,
  Smartphone,
};

interface OrganizationCreationWizardModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function OrganizationCreationWizardModal({ isOpen, onClose }: OrganizationCreationWizardModalProps) {
  const { catalog, presets, createOrganization } = useOrganizationModules();

  const [step, setStep] = useState<1 | 2 | 3>(2); // Start at Step 2 or allow 1->2->3 navigation
  const [name, setName] = useState('Ville de Plougastel-Daoulas');
  const [inseeCode, setInseeCode] = useState('29189');
  const [stratum, setStratum] = useState('3500-15000');
  const [emailDomain, setEmailDomain] = useState('plougastel.fr');
  
  // Selected modules set
  const [selectedModules, setSelectedModules] = useState<string[]>(() =>
    catalog.map((m) => m.key)
  );
  const [activePreset, setActivePreset] = useState<string>('commune_littorale');

  // Dynamic matching preset
  const currentActivePreset = React.useMemo(() => {
    const sorted = [...selectedModules].sort();
    for (const [id, pr] of Object.entries(presets)) {
      const sortedPr = [...pr.modules].sort();
      if (sorted.length === sortedPr.length && sorted.every((k, i) => k === sortedPr[i])) {
        return id;
      }
    }
    return activePreset;
  }, [selectedModules, presets, activePreset]);

  // Step 3 fields
  const [mayorName, setMayorName] = useState('Dominique CAP');
  const [dgsName, setDgsName] = useState('Marie ROLLAND');
  const [enrollmentMode, setEnrollmentMode] = useState<'invite_links' | 'import_file'>('invite_links');
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleToggleModule = (key: string) => {
    const item = catalog.find((m) => m.key === key);
    if (item?.locked) return;

    setActivePreset(''); // Unset preset when customized
    setSelectedModules((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleApplyPreset = (presetId: string) => {
    const p = presets[presetId];
    if (!p) return;
    setActivePreset(presetId);
    setSelectedModules(p.modules);
  };

  // Circuit templates count calculation
  const readyCircuitsCount = selectedModules.reduce((acc, k) => {
    const item = catalog.find((m) => m.key === k);
    return acc + (item ? item.circuits.length : 0);
  }, 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createOrganization({
        name,
        insee_code: inseeCode,
        stratum,
        email_domain: emailDomain,
        enabled_modules: selectedModules,
      });
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-4xl bg-white border border-slate-200 rounded-2xl shadow-xl flex flex-col max-h-[92vh] overflow-hidden font-sans"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200/80 flex items-center justify-center text-blue-600 shadow-2xs">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">
                  Assistant d’Enrôlement & Déploiement Collectivité
                </h2>
                <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                  MayorTech v3.0
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Configuration sur-mesure du périmètre modulaire et amorçage souverain
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

        {/* Step Progression Bar */}
        <div className="grid grid-cols-3 border-b border-slate-100 bg-white text-xs font-semibold shrink-0">
          <button
            type="button"
            onClick={() => setStep(1)}
            className={`py-2.5 px-4 flex items-center justify-center gap-2 border-b-2 transition-all ${
              step === 1
                ? 'border-blue-600 text-blue-700 bg-blue-50/30 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span className={`w-5 h-5 rounded-full text-[11px] flex items-center justify-center ${step === 1 ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
              1
            </span>
            <span>Identité Mairie</span>
          </button>

          <button
            type="button"
            onClick={() => setStep(2)}
            className={`py-2.5 px-4 flex items-center justify-center gap-2 border-b-2 transition-all ${
              step === 2
                ? 'border-blue-600 text-blue-700 bg-blue-50/30 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span className={`w-5 h-5 rounded-full text-[11px] flex items-center justify-center ${step === 2 ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
              2
            </span>
            <span>Modules & Périmètre</span>
          </button>

          <button
            type="button"
            onClick={() => setStep(3)}
            className={`py-2.5 px-4 flex items-center justify-center gap-2 border-b-2 transition-all ${
              step === 3
                ? 'border-blue-600 text-blue-700 bg-blue-50/30 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <span className={`w-5 h-5 rounded-full text-[11px] flex items-center justify-center ${step === 3 ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
              3
            </span>
            <span>Têtes de pont & Équipes</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* STEP 1: Identité */}
          {step === 1 && (
            <div className="space-y-5 max-w-2xl mx-auto py-2">
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900">1. Identité et Référencement de la Collectivité</h3>
                <p className="text-xs text-slate-500">
                  Renseignez les données officielles de la commune pour le scellement et les arrêtés municipaux.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="sm:col-span-2 space-y-1">
                  <label className="font-semibold text-slate-700">Nom officiel de la Mairie / Collectivité *</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    placeholder="ex. Ville de Plougastel-Daoulas"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Code INSEE / Département *</label>
                  <input
                    type="text"
                    value={inseeCode}
                    onChange={(e) => setInseeCode(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none font-mono"
                    placeholder="ex. 29189"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-700">Domaine email professionnel autorisé</label>
                  <input
                    type="text"
                    value={emailDomain}
                    onChange={(e) => setEmailDomain(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-1 focus:ring-blue-500 focus:outline-none font-mono"
                    placeholder="ex. plougastel.fr"
                  />
                </div>

                <div className="sm:col-span-2 space-y-1.5">
                  <label className="font-semibold text-slate-700">Strate démographique</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'less-3500', label: '< 3 500 hab.', sub: 'Petite commune rurale' },
                      { id: '3500-15000', label: '3 500 – 15 000 hab.', sub: 'Ville moyenne (ex. Plougastel)' },
                      { id: 'more-15000', label: '> 15 000 hab.', sub: 'Agglomération & Métropole' },
                    ].map((st) => (
                      <button
                        key={st.id}
                        type="button"
                        onClick={() => setStratum(st.id)}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          stratum === st.id
                            ? 'bg-blue-50/50 border-blue-500 ring-1 ring-blue-500/20'
                            : 'bg-white border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <div className="font-bold text-slate-900">{st.label}</div>
                        <div className="text-[10px] text-slate-500">{st.sub}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Bento Grid Modules Selection (Cœur de la demande) */}
          {step === 2 && (
            <div className="space-y-6">
              {/* Presets Bar */}
              <div className="p-3 bg-slate-50/80 border border-slate-200/90 rounded-2xl flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Sparkle className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Profils pré-configurés en 1 clic :
                  </span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap text-xs">
                  {Object.values(presets).map((pr) => {
                    const isSelected = currentActivePreset === pr.id;
                    return (
                      <button
                        key={pr.id}
                        type="button"
                        onClick={() => handleApplyPreset(pr.id)}
                        className={`px-3 py-1.5 rounded-xl border font-semibold text-xs transition-all cursor-pointer shadow-2xs ${
                          isSelected
                            ? 'bg-blue-600 text-white border-blue-600 shadow-sm font-bold'
                            : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100/70'
                        }`}
                      >
                        {pr.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Bento Grid: 3 Categories (Compact padding to fit Section 3) */}
              <div className="space-y-3.5">
                {/* 1. Socle Obligatoire */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      1. Socle Régalien Obligatoire (Inclus d’office)
                    </span>
                    <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      Verrouillé · 3 modules
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    {catalog
                      .filter((m) => m.category === 'socle')
                      .map((mod) => {
                        const Icon = ICON_MAP[mod.icon] || Layers;
                        return (
                          <div
                            key={mod.key}
                            className="bg-white border border-slate-200 rounded-xl p-2.5 shadow-2xs space-y-1.5 relative"
                          >
                            <div className="flex items-start justify-between">
                              <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600">
                                <Icon className="w-3.5 h-3.5" />
                              </div>
                              <span className="inline-flex items-center gap-1 text-[9px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
                                <Lock className="w-2.5 h-2.5" />
                                <span>Inclus</span>
                              </span>
                            </div>
                            <div>
                              <h4 className="text-xs font-bold text-slate-900">{mod.name}</h4>
                              <p className="text-[10.5px] text-slate-500 leading-snug mt-0.5">
                                {mod.description}
                              </p>
                            </div>
                            <div className="pt-0.5 flex items-center gap-1 flex-wrap">
                              {mod.circuits.map((c, i) => (
                                <span key={i} className="text-[9px] font-mono text-blue-700 bg-blue-50 px-1.5 py-0.2 rounded border border-blue-100">
                                  {c}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* 2. Modules Métiers */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      2. Modules Métiers à la Carte
                    </span>
                    <span className="text-[10px] text-slate-500">
                      Cochez selon les compétences de votre collectivité
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                    {catalog
                      .filter((m) => m.category === 'metier')
                      .map((mod) => {
                        const isChecked = selectedModules.includes(mod.key);
                        const Icon = ICON_MAP[mod.icon] || Layers;
                        return (
                          <div
                            key={mod.key}
                            onClick={() => handleToggleModule(mod.key)}
                            className={`rounded-xl p-2.5 border transition-all cursor-pointer relative shadow-2xs space-y-1.5 ${
                              isChecked
                                ? 'bg-white border-blue-500 ring-2 ring-blue-500/10'
                                : 'bg-slate-50/60 border-slate-200 opacity-70 hover:opacity-100'
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className={`w-7 h-7 rounded-lg flex items-center justify-center border ${isChecked ? 'bg-blue-50 text-blue-600 border-blue-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                                <Icon className="w-3.5 h-3.5" />
                              </div>

                              {/* Toggle switch */}
                              <div
                                className={`w-8 h-4 rounded-full p-0.5 transition-colors duration-200 ease-in-out ${
                                  isChecked ? 'bg-blue-600' : 'bg-slate-300'
                                }`}
                              >
                                <div
                                  className={`w-3 h-3 rounded-full bg-white shadow-xs transform transition-transform duration-200 ease-in-out ${
                                    isChecked ? 'translate-x-4' : 'translate-x-0'
                                  }`}
                                />
                              </div>
                            </div>

                            <div>
                              <h4 className="text-xs font-bold text-slate-900">{mod.name}</h4>
                              <p className="text-[10.5px] text-slate-500 leading-snug mt-0.5 line-clamp-2">
                                {mod.description}
                              </p>
                            </div>

                            <div className="pt-0.5 flex items-center gap-1 flex-wrap">
                              {mod.circuits.map((c, i) => (
                                <span key={i} className="text-[9px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200 truncate max-w-full">
                                  {c}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* 3. Options & Connecteurs */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      3. Options & Connecteurs Souverains (Désactivables pour charte sobre / zéro IA)
                    </span>
                    <span className="text-[10px] text-slate-500">
                      Conforme ANSSI & DINUM
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
                    {catalog
                      .filter((m) => m.category === 'options')
                      .map((mod) => {
                        const isChecked = selectedModules.includes(mod.key);
                        const Icon = ICON_MAP[mod.icon] || Layers;
                        return (
                          <div
                            key={mod.key}
                            onClick={() => handleToggleModule(mod.key)}
                            className={`rounded-xl p-2.5 border transition-all cursor-pointer relative shadow-2xs space-y-1.5 ${
                              isChecked
                                ? 'bg-white border-blue-500 ring-2 ring-blue-500/10'
                                : 'bg-slate-50/60 border-slate-200 opacity-60 hover:opacity-100'
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className={`w-6 h-6 rounded-lg flex items-center justify-center border ${isChecked ? 'bg-blue-50 text-blue-600 border-blue-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                                <Icon className="w-3 h-3" />
                              </div>

                              <div
                                className={`w-7 h-3.5 rounded-full p-0.5 transition-colors duration-200 ease-in-out ${
                                  isChecked ? 'bg-blue-600' : 'bg-slate-300'
                                }`}
                              >
                                <div
                                  className={`w-2.5 h-2.5 rounded-full bg-white shadow-xs transform transition-transform duration-200 ease-in-out ${
                                    isChecked ? 'translate-x-3.5' : 'translate-x-0'
                                  }`}
                                />
                              </div>
                            </div>

                            <div>
                              <h4 className="text-[11px] font-bold text-slate-900">{mod.name}</h4>
                              <p className="text-[9.5px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                                {mod.description}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* Clear Scroll / Configuration Notice */}
                <div className="p-2 rounded-xl bg-blue-50/40 border border-blue-200/60 text-center text-[10.5px] text-blue-800 flex items-center justify-center gap-1.5 font-medium">
                  <Sparkle className="w-3 h-3 text-blue-600 shrink-0" />
                  <span>Tous les modules ci-dessus peuvent être réactivés ou désactivés à chaud dans Paramètres &gt; Modules & Périmètre.</span>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Têtes de pont & Enrôlement */}
          {step === 3 && (
            <div className="space-y-6 max-w-2xl mx-auto py-2">
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900">3. Têtes de Pont & Déploiement des Équipes</h3>
                <p className="text-xs text-slate-500">
                  Définissez les signataires régaliens et choisissez le mode d’intégration des agents municipaux.
                </p>
              </div>

              {/* Têtes de pont */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                  <div className="flex items-center gap-2">
                    <Landmark className="w-4 h-4 text-purple-600" />
                    <span className="font-bold text-slate-900">Maire / Exécutif Municipal</span>
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600">Nom & Prénom</label>
                    <input
                      type="text"
                      value={mayorName}
                      onChange={(e) => setMayorName(e.target.value)}
                      className="w-full mt-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs"
                      placeholder="ex. Dominique CAP"
                    />
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-blue-600" />
                    <span className="font-bold text-slate-900">Direction Générale des Services (DGS)</span>
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-600">Nom & Prénom</label>
                    <input
                      type="text"
                      value={dgsName}
                      onChange={(e) => setDgsName(e.target.value)}
                      className="w-full mt-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs"
                      placeholder="ex. Marie ROLLAND"
                    />
                  </div>
                </div>
              </div>

              {/* Mode d'enrôlement */}
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-800">Mode de déploiement des agents municipaux</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <button
                    type="button"
                    onClick={() => setEnrollmentMode('invite_links')}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      enrollmentMode === 'invite_links'
                        ? 'bg-blue-50/50 border-blue-500 ring-1 ring-blue-500/20'
                        : 'bg-white border-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-blue-600 font-bold mb-1">
                      <Link2 className="w-4 h-4" />
                      <span>Liens sécurisés par pôle (Recommandé)</span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Génère des invitations `/join/poleToken` avec approbation directe dans l’onglet « À valider » des chefs de service.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setEnrollmentMode('import_file')}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      enrollmentMode === 'import_file'
                        ? 'bg-blue-50/50 border-blue-500 ring-1 ring-blue-500/20'
                        : 'bg-white border-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-emerald-600 font-bold mb-1">
                      <FileSpreadsheet className="w-4 h-4" />
                      <span>Import Organigramme (CSV / PDF)</span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Glisser-déposer de votre organigramme municipal existant pour constitution instantanée de l’arbre hiérarchique.
                    </p>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Dynamic Sticky Footer */}
        <div className="px-6 py-3.5 border-t border-slate-100 bg-slate-50 flex items-center justify-between shrink-0 text-xs">
          {/* Dynamic Counter */}
          <div className="flex items-center gap-2 font-medium text-slate-600">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>
              <strong className="text-slate-900">{selectedModules.length}</strong> modules actifs
            </span>
            <span className="text-slate-300">·</span>
            <span className="text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full font-semibold border border-blue-100">
              {readyCircuitsCount} modèles de circuits prêts
            </span>
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center gap-2">
            {step > 1 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setStep((s) => (s - 1) as any)}
                className="text-xs flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Précédent</span>
              </Button>
            )}

            {step < 3 ? (
              <Button
                type="button"
                size="sm"
                onClick={() => setStep((s) => (s + 1) as any)}
                className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 flex items-center gap-1 shadow-xs"
              >
                <span>Continuer</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            ) : (
              <Button
                type="button"
                disabled={submitting}
                onClick={handleSubmit}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 flex items-center gap-1.5 shadow-xs"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{submitting ? 'Initialisation…' : 'Créer l’organisation & activer'}</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
