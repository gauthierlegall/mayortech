import re

path = 'frontend-lovable/src/features/workflow/validation/MayorValidationInbox.tsx'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add ChevronDown and SlidersHorizontal to imports if not present
if 'SlidersHorizontal' not in code:
    code = code.replace("Pencil\n} from 'lucide-react';", "Pencil,\n  SlidersHorizontal,\n  ChevronDown\n} from 'lucide-react';")
    code = code.replace("Pencil\r\n} from 'lucide-react';", "Pencil,\n  SlidersHorizontal,\n  ChevronDown\n} from 'lucide-react';")

# 2. Add isMoreActionsOpen state
if 'isMoreActionsOpen' not in code:
    code = code.replace(
        "const [isParapheurModeOpen, setIsParapheurModeOpen] = useState(false);",
        "const [isParapheurModeOpen, setIsParapheurModeOpen] = useState(false);\n  const [isMoreActionsOpen, setIsMoreActionsOpen] = useState(false);"
    )

# 3. Replace Barre 2 filter tabs & 2nd search bar
pattern_filter = re.compile(
    r'\{\/\* Filter Tabs & Search Bar \*\/\}[\s\S]*?\{\/\* Main Directive Split View',
    re.MULTILINE
)

new_filter_bar = """{/* Barre 2 (Filtres compacts + Mode Parapheur sans 2e barre de recherche) */}
      <div className="bg-white border border-stone-200/90 rounded-xl p-2 sm:p-2.5 shadow-3xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
        {/* Pills */}
        <div className="flex items-center gap-1 overflow-x-auto text-xs py-0.5">
          {[
            { id: 'my_tasks', label: 'Mes validations', count: dossiers.filter(d => d.status === 'pending' && d.currentStepIndex === 2).length },
            { id: 'service_pool', label: 'Service / Pool', count: dossiers.filter(d => d.status === 'pending' && d.currentStepIndex < 2).length },
            { id: 'pending_dgs', label: 'En attente DGS', count: dossiers.filter(d => d.status === 'pending' && d.currentStepIndex >= 2).length },
            { id: 'history', label: 'Historique', count: dossiers.filter(d => d.status === 'signed' || d.status === 'rejected').length },
          ].map((tab) => {
            const isSelected = activeFilter === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveFilter(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold whitespace-nowrap transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#102A4C] text-white shadow-3xs'
                    : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                }`}
              >
                <span className={isSelected ? 'text-white' : ''}>{tab.label}</span>
                {tab.count > 0 && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                      isSelected ? 'bg-white/20 text-white' : 'bg-stone-200 text-stone-700'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Mode Parapheur Button */}
        <Button
          size="sm"
          onClick={() => {
            setParapheurIndex(0);
            setIsParapheurModeOpen(true);
          }}
          className="bg-[#102A4C] hover:bg-[#193D6B] text-white font-bold text-xs px-3.5 py-1.5 rounded-lg shadow-3xs flex items-center justify-center gap-1.5 shrink-0 cursor-pointer w-full sm:w-auto"
        >
          <Play className="w-3.5 h-3.5 fill-current text-white" />
          <span className="text-white">Mode Parapheur ({filteredDossiers.filter(d => d.status === 'pending').length})</span>
        </Button>
      </div>

      {/* Main Directive Split View"""

code = pattern_filter.sub(new_filter_bar, code, count=1)

# 4. Replace Filet tricolore with subtle continuous border
code = code.replace('<div className="filet-tricolore" />', '<div className="h-[2px] w-full bg-gradient-to-r from-[#102A4C] via-stone-200 to-[#9F1239]" />')

# 5. Replace Right Decision Panel Buttons with 2 visible + Autres actions dropdown
pattern_buttons = re.compile(
    r'\{\/\* Decision Action Buttons \*\/\}[\s\S]*?\{\/\* SLA Summary \*\/\}',
    re.MULTILINE
)

new_decision_buttons = """{/* Decision Action Buttons : Exactly 2 prominent buttons + Collapsible "Autres actions ▾" */}
                      <div className="space-y-2 pt-1">
                        {/* 1. Action Primaire: Vert Sceau #0F766E text-white */}
                        <button
                          type="button"
                          onClick={handleValidateAndSign}
                          className="w-full py-2.5 px-4 rounded-xl bg-[#0F766E] hover:bg-[#0D655E] text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition-colors cursor-pointer"
                        >
                          <CheckCircle2 className="w-4 h-4 text-white" />
                          <span className="text-white">{dynamicPrimaryCta}</span>
                        </button>

                        {/* 2. Action Secondaire: Contour sobre */}
                        <button
                          type="button"
                          onClick={() => setIsRollbackModalOpen(true)}
                          className="w-full py-2 px-4 rounded-xl border border-stone-300 bg-white hover:bg-stone-50 text-stone-800 font-bold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-3xs"
                        >
                          <RotateCcw className="w-4 h-4 text-stone-600" />
                          <span>{dynamicRollbackCta}</span>
                        </button>

                        {/* Collapsible / Dropdown "Autres actions ▾" */}
                        <div className="pt-1">
                          <button
                            type="button"
                            onClick={() => setIsMoreActionsOpen(!isMoreActionsOpen)}
                            className="w-full py-1.5 px-3 rounded-lg border border-dashed border-stone-200 hover:border-stone-300 bg-stone-50/50 hover:bg-stone-100/70 text-stone-600 hover:text-stone-900 font-semibold text-xs flex items-center justify-between transition-colors cursor-pointer"
                          >
                            <span className="flex items-center gap-1.5">
                              <SlidersHorizontal className="w-3.5 h-3.5 text-stone-500" />
                              <span>Autres actions</span>
                            </span>
                            <ChevronDown size={14} className={`text-stone-400 transition-transform ${isMoreActionsOpen ? 'rotate-180' : ''}`} />
                          </button>

                          {isMoreActionsOpen && (
                            <div className="mt-1.5 p-1.5 bg-stone-50 border border-stone-200 rounded-xl space-y-1 text-xs shadow-3xs animate-in fade-in duration-100">
                              {/* Action: Pousser vers i-Parapheur */}
                              <button
                                type="button"
                                onClick={() => {
                                  handleValidateAndSign();
                                  toast.success('Dossier télétransmis sur i-Parapheur pour signature eIDAS RGS**.');
                                }}
                                className="w-full p-2 rounded-lg hover:bg-white text-stone-700 hover:text-[#102A4C] font-semibold flex items-center gap-2 text-left transition-colors cursor-pointer"
                              >
                                <Cpu className="w-3.5 h-3.5 text-[#102A4C] shrink-0" />
                                <span>Pousser vers i-Parapheur (eIDAS)</span>
                              </button>

                              {/* Action: Lien rapide Élu */}
                              <button
                                type="button"
                                onClick={() => {
                                  const token = `${selectedDossier.id}.1763789000.9f86d081884c7d65`;
                                  const url = `${window.location.origin}/#/quick-sign/${token}`;
                                  navigator.clipboard?.writeText(url);
                                  toast.success("Lien d'émargement rapide Élu copié ! Prêt pour smartphone (validité 72h).");
                                }}
                                className="w-full p-2 rounded-lg hover:bg-white text-stone-700 hover:text-[#102A4C] font-semibold flex items-center gap-2 text-left transition-colors cursor-pointer"
                              >
                                <Smartphone className="w-3.5 h-3.5 text-[#102A4C] shrink-0" />
                                <span>Lien rapide Élu (Smartphone)</span>
                              </button>

                              {/* Action: Refuser */}
                              <button
                                type="button"
                                onClick={handleReject}
                                className="w-full p-2 rounded-lg hover:bg-rose-50 text-stone-600 hover:text-rose-700 font-semibold flex items-center gap-2 text-left transition-colors cursor-pointer border-t border-stone-200/60"
                              >
                                <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                                <span>Refuser le dossier</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                  {/* SLA Summary */}"""

code = pattern_buttons.sub(new_decision_buttons, code, count=1)

# 6. Replace residual blue classes with Civic Craft tokens
replacements = [
    ("bg-blue-50 border border-blue-200 rounded-xl", "bg-stone-100 border border-stone-200 rounded-xl"),
    ("text-blue-900", "text-stone-900"),
    ("text-blue-600", "text-[#102A4C]"),
    ("text-blue-700", "text-[#102A4C]"),
    ("text-blue-500", "text-[#102A4C]"),
    ("text-blue-800", "text-stone-800"),
    ("bg-blue-600", "bg-[#102A4C]"),
    ("bg-blue-500", "bg-[#102A4C]"),
    ("bg-blue-100", "bg-stone-200"),
    ("bg-blue-50/10", "bg-stone-50/50"),
    ("bg-blue-50/30", "bg-stone-100/60"),
    ("bg-blue-50/40", "bg-stone-100/60"),
    ("bg-blue-50/50", "bg-stone-100"),
    ("bg-blue-50/60", "bg-stone-50"),
    ("bg-blue-50/70", "bg-stone-100"),
    ("bg-blue-50", "bg-stone-100"),
    ("border-blue-500", "border-[#102A4C]"),
    ("border-blue-400", "border-[#102A4C]/50"),
    ("border-blue-200", "border-stone-200"),
    ("border-blue-300", "border-stone-300"),
    ("ring-blue-500/20", "ring-[#102A4C]/20"),
    ("ring-blue-500/10", "ring-[#102A4C]/10"),
    ("ring-blue-500/30", "ring-[#102A4C]/30"),
    ("hover:border-blue-300", "hover:border-stone-400"),
    ("hover:bg-blue-50/50", "hover:bg-stone-100"),
    ("hover:bg-blue-100", "hover:bg-stone-200"),
    ("hover:bg-blue-700", "hover:bg-[#193D6B]"),
    ("hover:text-blue-700", "hover:text-[#102A4C]"),
    ("hover:text-blue-600", "hover:text-[#102A4C]"),
]

for old, new in replacements:
    code = code.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated MayorValidationInbox.tsx successfully!")
