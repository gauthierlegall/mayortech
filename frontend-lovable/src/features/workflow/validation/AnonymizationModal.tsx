import React, { useState, useMemo } from 'react';
import {
  ShieldCheck,
  Eye,
  EyeOff,
  Check,
  X,
  FileText,
  AlertCircle,
  Hash,
  Download,
  Lock,
  CheckSquare,
  Square,
  Info,
} from 'lucide-react';
import { toast } from 'sonner';
import { ValidationDossier } from './validationData';

export interface AnonymizationEntity {
  id: string;
  category: 'name' | 'address' | 'phone' | 'email' | 'cadastre' | 'bank' | 'social';
  label: string;
  originalValue: string;
  suggestedReplacement: string;
  categoryColor: string;
}

interface AnonymizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  dossier: ValidationDossier;
  onSaveAnonymized: (updatedDossier: ValidationDossier) => void;
}

// Client-side deterministic detection regexes (matching backend src/travaux/anonymizer.py)
function detectEntitiesInText(text: string, applicant: string, address?: string): AnonymizationEntity[] {
  const detected: AnonymizationEntity[] = [];
  let counter = 1;

  // 1. Applicant name if available
  if (applicant && applicant.trim() && !applicant.toLowerCase().includes('commission')) {
    detected.push({
      id: `entity-${counter++}`,
      category: 'name',
      label: 'Identité du demandeur',
      originalValue: applicant,
      suggestedReplacement: '[NOM OCCULTÉ RGPD]',
      categoryColor: 'bg-rose-50 text-rose-800 border-rose-200',
    });
  }

  // 2. Applicant address if available
  if (address && address.trim()) {
    detected.push({
      id: `entity-${counter++}`,
      category: 'address',
      label: 'Adresse privée',
      originalValue: address,
      suggestedReplacement: '[ADRESSE OCCULTÉE RGPD]',
      categoryColor: 'bg-amber-50 text-amber-900 border-amber-200',
    });
  }

  // 3. Regex for civil titles & names inside act text
  const nameRegex = /(?:M\.\s*(?:&|et)\s*Mme|M\.|Mme|Monsieur|Madame)\s+[A-Za-zÀ-ÖØ-öø-ÿ'-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'-]+)+/gi;
  let match: RegExpExecArray | null;
  while ((match = nameRegex.exec(text)) !== null) {
    const val = match[0].trim();
    if (!detected.some((d) => d.originalValue.toLowerCase() === val.toLowerCase())) {
      detected.push({
        id: `entity-${counter++}`,
        category: 'name',
        label: 'Identité de particulier',
        originalValue: val,
        suggestedReplacement: '[NOM OCCULTÉ RGPD]',
        categoryColor: 'bg-rose-50 text-rose-800 border-rose-200',
      });
    }
  }

  // 4. Cadastral parcels
  const cadastreRegex = /(?:parcelle\s+(?:cadastrée\s+)?section\s+[A-Z]{1,2}\s*(?:n°|numéro)?\s*\d+|section\s+[A-Z]{1,2}\s*n°\s*\d+)/gi;
  while ((match = cadastreRegex.exec(text)) !== null) {
    const val = match[0].trim();
    if (!detected.some((d) => d.originalValue.toLowerCase() === val.toLowerCase())) {
      detected.push({
        id: `entity-${counter++}`,
        category: 'cadastre',
        label: 'Parcelle cadastrale nominative',
        originalValue: val,
        suggestedReplacement: '[PARCELLE OCCULTÉE RGPD]',
        categoryColor: 'bg-blue-50 text-blue-900 border-blue-200',
      });
    }
  }

  // 5. Emails
  const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/gi;
  while ((match = emailRegex.exec(text)) !== null) {
    const val = match[0].trim();
    if (!detected.some((d) => d.originalValue.toLowerCase() === val.toLowerCase())) {
      detected.push({
        id: `entity-${counter++}`,
        category: 'email',
        label: 'Courriel privé',
        originalValue: val,
        suggestedReplacement: '[COURRIEL OCCULTÉ RGPD]',
        categoryColor: 'bg-purple-50 text-purple-900 border-purple-200',
      });
    }
  }

  // 6. Phones
  const phoneRegex = /(?:(?:\+|00)33|0)[ \t]*[1-9](?:[ \t.-]*\d{2}){4}\b/g;
  while ((match = phoneRegex.exec(text)) !== null) {
    const val = match[0].trim();
    if (!detected.some((d) => d.originalValue === val)) {
      detected.push({
        id: `entity-${counter++}`,
        category: 'phone',
        label: 'Téléphone personnel',
        originalValue: val,
        suggestedReplacement: '[TÉLÉPHONE OCCULTÉ RGPD]',
        categoryColor: 'bg-emerald-50 text-emerald-900 border-emerald-200',
      });
    }
  }

  // 7. IBAN
  const ibanRegex = /\bFR\d{2}[ \t]?(?:\d{4}[ \t]?){5}\d{3}\b/gi;
  while ((match = ibanRegex.exec(text)) !== null) {
    const val = match[0].trim();
    if (!detected.some((d) => d.originalValue === val)) {
      detected.push({
        id: `entity-${counter++}`,
        category: 'bank',
        label: 'IBAN bancaire',
        originalValue: val,
        suggestedReplacement: '[IBAN OCCULTÉ RGPD]',
        categoryColor: 'bg-stone-100 text-stone-800 border-stone-300',
      });
    }
  }

  // 8. Social / CCAS Sensitive
  if (text.includes('Famille B.') || text.includes('Réf #7412')) {
    detected.push({
      id: `entity-${counter++}`,
      category: 'social',
      label: 'Dossier social CCAS',
      originalValue: 'Famille B. (Dossier Anonymisé Réf #7412)',
      suggestedReplacement: '[DOSSIER SOCIAL OCCULTÉ RGPD]',
      categoryColor: 'bg-rose-50 text-rose-800 border-rose-200',
    });
  }

  return detected;
}

export function AnonymizationModal({
  isOpen,
  onClose,
  dossier,
  onSaveAnonymized,
}: AnonymizationModalProps) {
  const fullText = useMemo(() => {
    return `Vu la demande déposée par ${dossier.applicant}${
      dossier.applicantAddress ? `, demeurant ${dossier.applicantAddress}` : ''
    } ;\n\n${dossier.previewArticle}`;
  }, [dossier]);

  const initialEntities = useMemo(() => {
    return detectEntitiesInText(fullText, dossier.applicant, dossier.applicantAddress);
  }, [fullText, dossier.applicant, dossier.applicantAddress]);

  // Set of selected entity IDs (all checked by default)
  const [selectedEntityIds, setSelectedEntityIds] = useState<Set<string>>(() => {
    return new Set(initialEntities.map((e) => e.id));
  });

  // Re-sync if dossier changes
  React.useEffect(() => {
    setSelectedEntityIds(new Set(initialEntities.map((e) => e.id)));
  }, [initialEntities]);

  const toggleEntity = (id: string) => {
    setSelectedEntityIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelectedEntityIds(new Set(initialEntities.map((e) => e.id)));
  };

  const deselectAll = () => {
    setSelectedEntityIds(new Set());
  };

  // Compute live anonymized text
  const anonymizedText = useMemo(() => {
    let text = fullText;
    // Replace selected entities
    initialEntities.forEach((entity) => {
      if (selectedEntityIds.has(entity.id)) {
        // Safe regex escape
        const escaped = entity.originalValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const reg = new RegExp(escaped, 'g');
        text = text.replace(reg, entity.suggestedReplacement);
      }
    });
    return text;
  }, [fullText, initialEntities, selectedEntityIds]);

  // Deterministic short hash computation for display
  const originalSha = useMemo(() => {
    return dossier.auditTrail?.[0]?.sha256 || '9f86d081884c7d659a2feaa0';
  }, [dossier]);

  const anonymizedSha = useMemo(() => {
    // Generate a pseudo-random stable hash for the anonymized version
    let hash = 0;
    for (let i = 0; i < anonymizedText.length; i++) {
      hash = (hash << 5) - hash + anonymizedText.charCodeAt(i);
      hash |= 0;
    }
    const hex = Math.abs(hash).toString(16).padStart(8, '0');
    return `c3a4e15b7d90f28e${hex}`.slice(0, 24);
  }, [anonymizedText]);

  const handleConfirmAnonymization = () => {
    const updatedDocuments = [
      ...dossier.documents.filter((d) => !d.name.includes('Version_Publiable_RGPD')),
      {
        name: `${dossier.id}_Version_Publiable_RGPD.pdf`,
        size: '540 Ko',
        type: 'Acte Anonymisé Publiable (PDF/A-2b)',
        badge: 'Publiable RGPD',
      },
    ];

    const now = new Date();
    const formattedDate = `${String(now.getDate()).padStart(2, '0')}/${String(
      now.getMonth() + 1
    ).padStart(2, '0')}/${now.getFullYear()} · ${String(now.getHours()).padStart(2, '0')}:${String(
      now.getMinutes()
    ).padStart(2, '0')}`;

    const newAuditEntry = {
      timestamp: formattedDate,
      author: 'Marie ROLLAND (DGS)',
      role: 'Direction Générale (DGS)',
      action: 'scellement' as const,
      stepName: 'Anonymisation légale avant affichage',
      comment: `Version publiable conforme Ordonnance 2021-1310 scellée (${selectedEntityIds.size} mentions sensibles occultées). Original conservé au coffre.`,
      sha256: anonymizedSha,
    };

    const updated: ValidationDossier = {
      ...dossier,
      anonymizedArticle: anonymizedText,
      anonymizedSha256: anonymizedSha,
      isAnonymizedForPublish: true,
      documents: updatedDocuments,
      auditTrail: [newAuditEntry, ...dossier.auditTrail],
    };

    onSaveAnonymized(updated);
    toast.success('Version publiable (RGPD) scellée et prête pour affichage légal (Ordonnance 2021-1310).');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rgpd-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div className="bg-[#F7F7F5] border border-stone-300 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-150 text-stone-900">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-stone-200 bg-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#102A4C]/10 text-[#102A4C] flex items-center justify-center border border-[#102A4C]/20">
              <EyeOff className="w-4 h-4 text-[#102A4C]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 id="rgpd-modal-title" className="text-sm font-bold text-[#102A4C] leading-snug">
                  Préparation de la version publiable (Conformité RGPD)
                </h3>
                <span className="font-mono text-[10px] text-stone-500 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
                  {dossier.id}
                </span>
              </div>
              <p className="text-xs text-stone-500">
                Ordonnance n° 2021-1310 du 7 octobre 2021 · Publicité et entrée en vigueur des actes locaux
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer la modale"
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Legal Frame Callout Banner */}
        <div className="px-5 py-2.5 bg-amber-50/70 border-b border-amber-200/80 text-xs text-amber-950 flex items-start gap-2 shrink-0">
          <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <div className="space-y-0.5 leading-relaxed text-[11px]">
            <p className="font-semibold text-amber-900">
              Obligation d’occultation des données personnelles avant mise en ligne (Art. L. 2131-1 CGCT)
            </p>
            <p className="text-amber-900/90">
              L’original complet reste archivé inaltérable dans le coffre numérique municipal sous son empreinte SHA-256 initiale. La version générée ci-dessous sera publiée sur le panneau d’affichage numérique et le portail communal.
            </p>
          </div>
        </div>

        {/* Modal Body: 2 Columns Split Layout */}
        <div className="flex-1 overflow-y-auto p-5 grid grid-cols-1 md:grid-cols-12 gap-5 min-h-0">
          {/* Left Column (5 cols): Entities checklist */}
          <div className="md:col-span-5 space-y-3 flex flex-col min-h-0">
            <div className="flex items-center justify-between pb-1 border-b border-stone-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-stone-700 flex items-center gap-1.5">
                <span>Mentions sensibles</span>
                <span className="font-mono text-[10px] text-[#102A4C] bg-stone-100 px-1.5 py-0.2 rounded font-semibold">
                  {selectedEntityIds.size} / {initialEntities.length}
                </span>
              </h4>
              <div className="flex items-center gap-2 text-[11px]">
                <button
                  type="button"
                  onClick={selectAll}
                  className="text-[#102A4C] hover:underline font-semibold cursor-pointer"
                >
                  Tout cocher
                </button>
                <span className="text-stone-300">·</span>
                <button
                  type="button"
                  onClick={deselectAll}
                  className="text-stone-500 hover:text-stone-800 hover:underline cursor-pointer"
                >
                  Tout décocher
                </button>
              </div>
            </div>

            <div className="space-y-2 overflow-y-auto pr-1 flex-1">
              {initialEntities.length === 0 ? (
                <div className="p-4 rounded-xl bg-white border border-stone-200 text-center text-xs text-stone-500">
                  Aucune mention sensible détectée dans cet acte.
                </div>
              ) : (
                initialEntities.map((entity) => {
                  const isChecked = selectedEntityIds.has(entity.id);
                  return (
                    <div
                      key={entity.id}
                      onClick={() => toggleEntity(entity.id)}
                      className={`p-3 rounded-xl border transition-all cursor-pointer select-none space-y-1.5 ${
                        isChecked
                          ? 'bg-white border-[#102A4C]/40 shadow-3xs ring-1 ring-[#102A4C]/10'
                          : 'bg-stone-50/70 border-stone-200 opacity-70 hover:opacity-100 hover:bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleEntity(entity.id)}
                            className="w-3.5 h-3.5 rounded text-[#102A4C] border-stone-300 focus:ring-[#102A4C] cursor-pointer"
                          />
                          <span
                            className={`text-[9.5px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${entity.categoryColor}`}
                          >
                            {entity.label}
                          </span>
                        </div>
                        <span className="font-mono text-[9px] text-stone-400">{entity.id}</span>
                      </div>

                      <div className="pl-5 space-y-0.5 text-xs">
                        <p className="font-semibold text-stone-900 leading-snug line-clamp-2">
                          « {entity.originalValue} »
                        </p>
                        <div className="flex items-center gap-1 text-[10px] text-stone-500 font-mono">
                          <span>Remplacé par :</span>
                          <span className="font-bold text-[#0F766E] bg-emerald-50 px-1 rounded">
                            {entity.suggestedReplacement}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Column (7 cols): Live Anonymized Letterhead Preview */}
          <div className="md:col-span-7 flex flex-col space-y-2 min-h-0">
            <div className="flex items-center justify-between pb-1 border-b border-stone-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-stone-700 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-[#102A4C]" />
                <span>Aperçu en direct · Version publiable</span>
              </h4>
              <span className="text-[10px] text-emerald-800 bg-emerald-50 border border-emerald-200 font-semibold px-2 py-0.5 rounded-full">
                Prêt pour affichage
              </span>
            </div>

            {/* Simulated Public Letterhead */}
            <div className="bg-white border border-stone-200/90 rounded-xl p-4 sm:p-5 shadow-3xs overflow-y-auto flex-1 font-sans space-y-3">
              <div className="text-center border-b border-stone-200/70 pb-3">
                <p className="text-[9.5px] font-bold tracking-widest uppercase text-stone-500">
                  RÉPUBLIQUE FRANÇAISE
                </p>
                <h5 className="text-xs font-bold text-stone-900 mt-0.5">
                  VILLE DE PLOUGASTEL-DAOULAS
                </h5>
                <p className="text-[9.5px] text-stone-400">
                  Publication d'acte légal en ligne · Certifiée conforme
                </p>
              </div>

              <div className="font-bold text-stone-900 text-xs">
                {dossier.title}
              </div>

              {/* Rendered Body with subtle redacted badges */}
              <div className="font-serif text-xs text-stone-800 leading-relaxed whitespace-pre-line space-y-2.5">
                {anonymizedText.split('\n\n').map((paragraph, idx) => {
                  return (
                    <p key={idx} className="leading-relaxed">
                      {paragraph.split(/(\[[A-ZÀ-ÖØ-öø-ÿ\s]+OCCULTÉ RGPD\])/g).map((chunk, cIdx) => {
                        if (chunk.startsWith('[') && chunk.endsWith('RGPD]')) {
                          return (
                            <span
                              key={cIdx}
                              className="font-mono text-[10px] font-bold bg-stone-100 text-[#102A4C] border border-stone-300 px-1 py-0.5 rounded mx-0.5 inline-flex items-center gap-1 shadow-3xs"
                              title="Mention occultée en application du RGPD et de l'Ordonnance 2021-1310"
                            >
                              <Lock className="w-2.5 h-2.5 text-stone-500" />
                              <span>{chunk}</span>
                            </span>
                          );
                        }
                        return <React.Fragment key={cIdx}>{chunk}</React.Fragment>;
                      })}
                    </p>
                  );
                })}
              </div>

              {/* Double SHA-256 Stamp */}
              <div className="pt-3 border-t border-stone-200/70 space-y-1.5 text-[9.5px] font-mono">
                <div className="flex items-center justify-between text-stone-500">
                  <span className="flex items-center gap-1">
                    <Hash className="w-3 h-3 text-stone-400" />
                    <span>Original au coffre (Intégral) :</span>
                  </span>
                  <span className="text-stone-700 font-semibold">{originalSha}...</span>
                </div>
                <div className="flex items-center justify-between text-emerald-900 bg-emerald-50/70 p-1.5 rounded border border-emerald-200/80">
                  <span className="flex items-center gap-1 font-sans font-semibold">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                    <span>Version publiable (SHA-256) :</span>
                  </span>
                  <span className="font-bold font-mono text-emerald-950">{anonymizedSha}...</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer (Civic Distill: 1 Single Filled Primary CTA) */}
        <div className="px-5 py-3.5 border-t border-stone-200 bg-white flex items-center justify-between gap-3 shrink-0">
          <p className="text-[11px] text-stone-500 font-medium hidden sm:block">
            {selectedEntityIds.size} mention(s) seront occultées sur le document publié.
          </p>
          <div className="flex items-center gap-2.5 ml-auto">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-xl border border-stone-300 bg-white hover:bg-stone-50 text-stone-700 text-xs font-semibold cursor-pointer transition-colors shadow-3xs"
            >
              Annuler
            </button>
            <button
              type="button"
              onClick={handleConfirmAnonymization}
              className="px-4 py-2 rounded-xl bg-[#0F766E] hover:bg-[#0D655E] text-white text-xs font-bold cursor-pointer transition-colors shadow-xs flex items-center gap-1.5"
            >
              <Check className="w-3.5 h-3.5 text-white" />
              <span>Générer & sceller la version publiable</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
