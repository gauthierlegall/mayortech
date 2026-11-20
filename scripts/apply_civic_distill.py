import re

def update_file(path, modifier_fn):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = modifier_fn(content)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {path}")
    else:
        print(f"No changes in {path}")

# ==============================================================================
# 1. commissionConfig.ts
# ==============================================================================
def mod_commission_config(content):
    # Add shortTitle to CommissionKpi interface
    content = content.replace(
        "export interface CommissionKpi {\n  id: string;",
        "export interface CommissionKpi {\n  id: string;\n  shortTitle?: string;"
    )
    # Add fullName to CommissionConfig interface
    content = content.replace(
        "export interface CommissionConfig {\n  id: string;",
        "export interface CommissionConfig {\n  id: string;\n  fullName?: string;"
    )
    # Add fullName & shortTitle to 'all'
    content = content.replace(
        "id: 'all',\n    number: 0,",
        "id: 'all',\n    number: 0,\n    fullName: 'Laurence Bernard',"
    )
    content = content.replace(
        "{ id: 'kpi-1', count: 3, title: 'Actes à signer'",
        "{ id: 'kpi-1', count: 3, title: 'Actes à signer', shortTitle: 'À signer'"
    )
    content = content.replace(
        "{ id: 'kpi-2', count: 1, title: 'Échéance sous 24h'",
        "{ id: 'kpi-2', count: 1, title: 'Échéance sous 24h', shortTitle: 'Urgences 24h'"
    )
    content = content.replace(
        "{ id: 'kpi-3', count: 2, title: 'Prochaines séances'",
        "{ id: 'kpi-3', count: 2, title: 'Prochaines séances', shortTitle: 'Séances'"
    )

    # Add fullName & shortTitle to 'commission-1'
    content = content.replace(
        "id: 'commission-1',\n    number: 1,",
        "id: 'commission-1',\n    number: 1,\n    fullName: 'Valérie Gestin',"
    )
    content = content.replace(
        "{ id: 'kpi-1', count: 2, title: 'Actes financiers à viser'",
        "{ id: 'kpi-1', count: 2, title: 'Actes financiers à viser', shortTitle: 'À viser'"
    )
    content = content.replace(
        "{ id: 'kpi-2', count: 1, title: 'Arbitrage M57 en attente'",
        "{ id: 'kpi-2', count: 1, title: 'Arbitrage M57 en attente', shortTitle: 'Arbitrages M57'"
    )
    content = content.replace(
        "{ id: 'kpi-3', count: 3, title: 'Marchés en cours'",
        "{ id: 'kpi-3', count: 3, title: 'Marchés en cours', shortTitle: 'Marchés'"
    )

    # Add fullName & shortTitle to 'commission-2'
    content = content.replace(
        "id: 'commission-2',\n    number: 2,",
        "id: 'commission-2',\n    number: 2,\n    fullName: 'Nolwenn Péron',"
    )
    content = content.replace(
        "{ id: 'kpi-1', count: 1, title: 'Dossier CCAS confidentiel'",
        "{ id: 'kpi-1', count: 1, title: 'Dossier CCAS confidentiel', shortTitle: 'Aides CCAS'"
    )
    content = content.replace(
        "{ id: 'kpi-2', count: 14, title: 'Inscriptions scolaires'",
        "{ id: 'kpi-2', count: 14, title: 'Inscriptions scolaires', shortTitle: 'Inscriptions'"
    )
    content = content.replace(
        "{ id: 'kpi-3', count: 8, title: 'Calculs QF à valider'",
        "{ id: 'kpi-3', count: 8, title: 'Calculs QF à valider', shortTitle: 'Calculs QF'"
    )

    # Add fullName & shortTitle to 'commission-3'
    content = content.replace(
        "id: 'commission-3',\n    number: 3,",
        "id: 'commission-3',\n    number: 3,\n    fullName: 'Loïc Kerbrat',"
    )
    content = content.replace(
        "{ id: 'kpi-1', count: 2, title: 'Arrêtés & Permis à viser'",
        "{ id: 'kpi-1', count: 2, title: 'Arrêtés & Permis à viser', shortTitle: 'À viser'"
    )
    content = content.replace(
        "{ id: 'kpi-2', count: 1, title: 'Échéance sous 24h'",
        "{ id: 'kpi-2', count: 1, title: 'Échéance sous 24h', shortTitle: 'Urgences 24h'"
    )
    content = content.replace(
        "{ id: 'kpi-3', count: 4, title: 'Chantiers actifs'",
        "{ id: 'kpi-3', count: 4, title: 'Chantiers actifs', shortTitle: 'Chantiers'"
    )

    # Add fullName & shortTitle to 'commission-4'
    content = content.replace(
        "id: 'commission-4',\n    number: 4,",
        "id: 'commission-4',\n    number: 4,\n    fullName: 'Jean-Luc Le Gall',"
    )
    content = content.replace(
        "{ id: 'kpi-1', count: 2, title: 'Séances du Conseil Municipal'",
        "{ id: 'kpi-1', count: 2, title: 'Séances du Conseil Municipal', shortTitle: 'Séances'"
    )
    content = content.replace(
        "{ id: 'kpi-2', count: 18, title: 'Délibérations à l’ordre du jour'",
        "{ id: 'kpi-2', count: 18, title: 'Délibérations à l’ordre du jour', shortTitle: 'Délibérations'"
    )
    content = content.replace(
        "{ id: 'kpi-3', count: 33, title: 'Conseillers & Pouvoirs enregistrés'",
        "{ id: 'kpi-3', count: 33, title: 'Conseillers & Pouvoirs enregistrés', shortTitle: 'Conseillers'"
    )

    return content

update_file('frontend-lovable/src/features/workspace/commissionConfig.ts', mod_commission_config)

# ==============================================================================
# 2. Shell.tsx
# ==============================================================================
def mod_shell(content):
    # Brand link: wrap MayorTech in span.brand-title
    old_brand = '<Link to="/" className="brand !p-0 !text-xl !gap-2 mb-1">\n    <span className="brand-mark bg-[#102A4C] text-white shrink-0"><Landmark size={18}/></span>\n    {!railCollapsed && <>MayorTech<span className="brand-dot text-[#102A4C]">.</span></>}\n   </Link>'
    new_brand = '<Link to="/" className={`brand !p-0 !text-xl !gap-2 mb-1 ${railCollapsed ? "justify-center" : ""}`}>\n    <span className="brand-mark bg-[#102A4C] text-white shrink-0"><Landmark size={18}/></span>\n    {!railCollapsed && <span className="brand-title">MayorTech<span className="brand-dot text-[#102A4C]">.</span></span>}\n   </Link>'
    content = content.replace(old_brand, new_brand)

    # User profile name at bottom of sidebar: use fullName without parentheses or pole repetition
    old_user_name = '<strong className="text-xs font-semibold text-stone-900 block truncate">{commissionCfg.greetingName} ({commissionCfg.shortName})</strong>'
    new_user_name = '<strong className="text-xs font-semibold text-stone-900 block truncate">{commissionCfg.fullName || commissionCfg.greetingName}</strong>'
    content = content.replace(old_user_name, new_user_name)

    return content

update_file('frontend-lovable/src/features/workspace/Shell.tsx', mod_shell)

# ==============================================================================
# 3. styles.css
# ==============================================================================
def mod_styles(content):
    # Hide .brand-title and center brand when .nav-rail is active
    if '.workspace.nav-rail .brand-title' not in content:
        content += "\n.workspace.nav-rail .brand-title { display: none !important; }\n"
        content += ".workspace.nav-rail .brand { justify-content: center !important; text-align: center !important; }\n"
    return content

update_file('frontend-lovable/src/styles.css', mod_styles)

# ==============================================================================
# 4. MayorFlowView.tsx
# ==============================================================================
def mod_mayor_flow_view(content):
    # Button + Nouvelle validation -> sober light button (bg-white border text-stone-800)
    old_btn = '''          <Button
            onClick={() => setIsLaunchModalOpen(true)}
            className="bg-[#102A4C] hover:bg-[#193D6B] text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow-3xs transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 text-white" />
            <span className="text-white font-semibold">+ Nouvelle validation</span>
          </Button>'''
    new_btn = '''          <Button
            variant="outline"
            onClick={() => setIsLaunchModalOpen(true)}
            className="bg-white border border-stone-200 hover:border-stone-400 text-stone-800 font-medium text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow-3xs transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 text-stone-600" />
            <span>Nouvelle validation</span>
          </Button>'''
    content = content.replace(old_btn, new_btn)
    return content

update_file('frontend-lovable/src/features/workflow/MayorFlowView.tsx', mod_mayor_flow_view)

# ==============================================================================
# 5. MayorValidationInbox.tsx
# ==============================================================================
def mod_inbox(content):
    # 1. Mode Parapheur Button -> sober light button
    old_parapheur = '''        <Button
          size="sm"
          onClick={() => {
            setParapheurIndex(0);
            setIsParapheurModeOpen(true);
          }}
          className="bg-[#102A4C] hover:bg-[#193D6B] text-white font-bold text-xs px-3.5 py-1.5 rounded-lg shadow-3xs flex items-center justify-center gap-1.5 shrink-0 cursor-pointer w-full sm:w-auto"
        >
          <Play className="w-3.5 h-3.5 fill-current text-white" />
          <span className="text-white">Mode Parapheur ({filteredDossiers.filter(d => d.status === 'pending').length})</span>
        </Button>'''
    new_parapheur = '''        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setParapheurIndex(0);
            setIsParapheurModeOpen(true);
          }}
          className="bg-white border border-stone-200 hover:border-stone-400 text-stone-800 font-medium text-xs px-3.5 py-1.5 rounded-lg shadow-3xs flex items-center justify-center gap-1.5 shrink-0 cursor-pointer w-full sm:w-auto"
        >
          <Play className="w-3.5 h-3.5 text-stone-600" />
          <span>Mode Parapheur ({filteredDossiers.filter(d => d.status === 'pending').length})</span>
        </Button>'''
    content = content.replace(old_parapheur, new_parapheur)

    # 2. Add isObservationOpen state
    if "const [isObservationOpen, setIsObservationOpen] = useState(false);" not in content:
        content = content.replace(
            "const [decisionComment, setDecisionComment] = useState('');",
            "const [decisionComment, setDecisionComment] = useState('');\n  const [isObservationOpen, setIsObservationOpen] = useState(false);"
        )

    # 3. Observation / Motif Textarea -> Progressive Disclosure (+ Ajouter une observation)
    old_obs = '''                      {/* Observation / Motif Textarea */}
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
                          className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 bg-slate-50/50 hover:bg-white focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#102A4C]/20 focus:border-[#102A4C] text-xs shadow-2xs font-medium resize-none transition-colors"
                        />
                      </div>'''
    new_obs = '''                      {/* Observation / Motif Textarea - Divulgation Progressive */}
                      <div>
                        {(!isObservationOpen && !decisionComment) ? (
                          <button
                            type="button"
                            onClick={() => setIsObservationOpen(true)}
                            className="text-xs text-stone-500 hover:text-[#102A4C] font-medium flex items-center gap-1.5 py-1 cursor-pointer transition-colors"
                          >
                            <Plus className="w-3.5 h-3.5 text-stone-400" />
                            <span>Ajouter une observation (facultatif)</span>
                          </button>
                        ) : (
                          <div className="space-y-1.5 animate-in fade-in duration-100">
                            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 flex items-center justify-between">
                              <span>Observation / Motif du visa</span>
                              <button
                                type="button"
                                onClick={() => { setIsObservationOpen(false); setDecisionComment(''); }}
                                className="text-[10px] text-stone-400 hover:text-stone-600"
                              >
                                Masquer
                              </button>
                            </label>
                            <textarea
                              rows={3}
                              value={decisionComment}
                              onChange={(e) => setDecisionComment(e.target.value)}
                              placeholder="Indiquez vos motifs, réserves ou remarques de validation..."
                              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 bg-slate-50/50 hover:bg-white focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#102A4C]/20 focus:border-[#102A4C] text-xs shadow-2xs font-medium resize-none transition-colors"
                            />
                          </div>
                        )}
                      </div>'''
    content = content.replace(old_obs, new_obs)

    # When clicking Renvoyer, open observation automatically
    content = content.replace(
        "onClick={() => setIsRollbackModalOpen(true)}",
        "onClick={() => { setIsObservationOpen(true); setIsRollbackModalOpen(true); }}"
    )

    # 4. Remove permanent 'Corriger une coquille' button and keep only PDF/A
    old_typo_btn = '''                      {!isEditingArticle && (
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => {
                              setEditedArticleText(selectedDossier.previewArticle);
                              setIsEditingArticle(true);
                            }}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 hover:border-stone-300 bg-slate-50 hover:bg-stone-100 text-slate-700 hover:text-[#102A4C] text-xs font-semibold transition-colors shadow-3xs cursor-pointer ml-1"
                            title="Corriger directement une faute ou un numéro sans renvoyer le dossier"
                          >
                            <Pencil className="w-3.5 h-3.5 text-[#102A4C]" />
                            <span>Corriger une coquille</span>
                          </button>
                          <button
                            type="button"
                            onClick={handleDownloadPdf}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 hover:border-stone-300 bg-slate-50 hover:bg-stone-100 text-slate-700 hover:text-[#102A4C] text-xs font-semibold transition-colors shadow-3xs cursor-pointer"
                            title="Télécharger l'acte certifié au format officiel PDF/A-2b"
                          >
                            <Download className="w-3.5 h-3.5 text-[#102A4C]" />
                            <span>PDF/A</span>
                          </button>
                        </div>
                      )}'''
    new_typo_btn = '''                      {!isEditingArticle && (
                        <button
                          type="button"
                          onClick={handleDownloadPdf}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 hover:border-stone-300 bg-slate-50 hover:bg-stone-100 text-slate-700 hover:text-[#102A4C] text-xs font-semibold transition-colors shadow-3xs cursor-pointer"
                          title="Télécharger l'acte certifié au format officiel PDF/A-2b"
                        >
                          <Download className="w-3.5 h-3.5 text-[#102A4C]" />
                          <span>PDF/A</span>
                        </button>
                      )}'''
    content = content.replace(old_typo_btn, new_typo_btn)

    # 5. Make article text directly clickable to edit
    old_article_display = '''                          <div className="font-serif-act text-xs text-stone-800 leading-relaxed space-y-2 whitespace-pre-line">'''
    new_article_display = '''                          <div
                            onClick={() => {
                              setEditedArticleText(selectedDossier.previewArticle);
                              setIsEditingArticle(true);
                            }}
                            className="font-serif-act text-xs text-stone-800 leading-relaxed space-y-2 whitespace-pre-line group/act cursor-pointer relative p-2 rounded-lg hover:bg-stone-50/80 border border-transparent hover:border-stone-200/60 transition-colors"
                            title="Cliquer directement sur le texte pour corriger une coquille"
                          >
                            <div className="absolute top-1 right-1 opacity-0 group-hover/act:opacity-100 transition-opacity flex items-center gap-1 text-[10px] text-stone-500 font-sans font-medium bg-white border border-stone-200 px-1.5 py-0.5 rounded shadow-3xs">
                              <Pencil className="w-3 h-3 text-[#102A4C]" />
                              <span>Cliquer pour corriger</span>
                            </div>'''
    content = content.replace(old_article_display, new_article_display)

    # 6. Semicolon after applicant: prevent newline before semicolon
    content = content.replace(
        "Vu la demande déposée le {selectedDossier.createdAt} par {selectedDossier.applicant} ;<br />",
        "Vu la demande déposée le {selectedDossier.createdAt} par {selectedDossier.applicant}&nbsp;;<br />"
    )

    # 7. Stamp: Replace 'VISÉ & SCELLÉ · HORODATAGE eIDAS' with 'Intégrité SHA-256 vérifiée · En attente de signature' if not approved
    old_stamp = '''                          {/* Tampon VISÉ & SCELLÉ */}
                          <div className="pt-3 border-t border-stone-200/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded border border-emerald-600/40 bg-emerald-50/70 text-emerald-800 text-[10px] font-mono font-bold tracking-wider">
                              <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                              <span>VISÉ & SCELLÉ · HORODATAGE eIDAS</span>
                            </div>
                            <div className="text-[9.5px] font-mono text-stone-500 tabular-nums">
                              SHA-256 : <span className="text-stone-700 font-semibold">{selectedDossier.auditTrail?.[0]?.sha256?.slice(0, 24) || '9f86d081884c7d659a2feaa0'}...</span>
                            </div>
                          </div>'''
    new_stamp = '''                          {/* Tampon Juridique Strict */}
                          <div className="pt-3 border-t border-stone-200/70 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            {selectedDossier.status === 'approved' ? (
                              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded border border-emerald-600/40 bg-emerald-50/70 text-emerald-800 text-[10px] font-mono font-bold tracking-wider">
                                <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                                <span>VISÉ & SCELLÉ · HORODATAGE eIDAS</span>
                              </div>
                            ) : (
                              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded border border-stone-200 bg-stone-100 text-stone-700 text-[10px] font-mono font-semibold tracking-wider">
                                <ShieldCheck className="w-3.5 h-3.5 text-stone-500" />
                                <span>Intégrité SHA-256 vérifiée · En attente de signature</span>
                              </div>
                            )}
                            <div className="text-[9.5px] font-mono text-stone-500 tabular-nums">
                              SHA-256 : <span className="text-stone-700 font-semibold">{selectedDossier.auditTrail?.[0]?.sha256?.slice(0, 24) || '9f86d081884c7d659a2feaa0'}...</span>
                            </div>
                          </div>'''
    content = content.replace(old_stamp, new_stamp)

    return content

update_file('frontend-lovable/src/features/workflow/validation/MayorValidationInbox.tsx', mod_inbox)

# ==============================================================================
# 6. TodayDashboardView.tsx
# ==============================================================================
def mod_today(content):
    # 1. Geographic consistency: replace e-Bourgogne with Mégalis Bretagne
    content = content.replace(
        "timeAgo: 'Hier 15:10 · Transmission scellée e-Bourgogne'",
        "timeAgo: 'Hier 15:10 · Transmission scellée Mégalis Bretagne'"
    )

    # 2. Header mobile padding: px-4 sm:px-0, date below greeting
    old_greeting = '''        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
          <div className="flex items-baseline gap-2.5 flex-wrap">
            <h1 className="text-2xl font-bold text-stone-900 tracking-tight">
              Bonjour {commissionCfg.greetingName}
            </h1>
            <span className="text-xs text-stone-500 font-medium">· {capitalizedDate}</span>
          </div>
          
        </div>'''
    new_greeting = '''        <div className="px-4 sm:px-0 space-y-0.5">
          <h1 className="text-2xl sm:text-3xl font-bold text-stone-900 tracking-tight">
            Bonjour {commissionCfg.greetingName}
          </h1>
          <p className="text-xs text-stone-500 font-medium">{capitalizedDate}</p>
        </div>'''
    content = content.replace(old_greeting, new_greeting)

    # 3. Short KPI titles for mobile
    old_kpi_title = '<p className="text-[10px] sm:text-[11px] font-semibold text-stone-500 uppercase tracking-wider truncate">{kpi.title}</p>'
    new_kpi_title = '<p className="text-[10px] sm:text-[11px] font-semibold text-stone-500 uppercase tracking-wider truncate"><span className="sm:hidden">{kpi.shortTitle || kpi.title}</span><span className="hidden sm:inline">{kpi.title}</span></p>'
    content = content.replace(old_kpi_title, new_kpi_title)

    # 4. Mode Focus Elu: clean continuous paper reading
    # Remove double unicode arrows
    content = content.replace("Masquer l'acte complet ▴", "Masquer l'acte complet")
    content = content.replace("Lire l'acte complet ▾", "Lire l'acte complet")

    # Remove interior boxes around Vu and article
    old_focus_act = '''                        <div className="text-stone-600 text-xs italic font-serif leading-relaxed bg-stone-50/60 p-3 rounded-lg border border-stone-200/80">
                          <p>Vu le Code Général des Collectivités Territoriales ;</p>
                          <p>Vu la demande déposée par {d.applicant} ({d.id}) ;</p>
                          <p>Vu les avis techniques préalables favorables répertoriés au circuit d’instruction ;</p>
                        </div>
                        <div className="p-3.5 bg-stone-50/70 rounded-lg text-xs text-stone-800 leading-relaxed font-serif-act border border-stone-200/80 whitespace-pre-line">
                          {d.previewArticle}
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-stone-500 bg-stone-50/60 p-2.5 rounded-lg border border-stone-200/80">
                          <span className="flex items-center gap-1.5 font-semibold text-emerald-800">
                            <ShieldCheck className="w-4 h-4 text-emerald-700" />
                            <span>Certifié conforme eIDAS · Scellement SHA-256</span>
                          </span>
                          <span className="font-mono text-[10px] text-stone-400">Horodatage officiel RGS**</span>
                        </div>'''
    new_focus_act = '''                        <div className="text-stone-600 text-xs italic font-serif leading-relaxed py-1 space-y-0.5">
                          <p>Vu le Code Général des Collectivités Territoriales ;</p>
                          <p>Vu la demande déposée par {d.applicant} ({d.id}) ;</p>
                          <p>Vu les avis techniques préalables favorables répertoriés au circuit d’instruction ;</p>
                        </div>
                        <div className="py-2 text-xs text-stone-900 leading-relaxed font-serif-act whitespace-pre-line">
                          {d.previewArticle}
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-stone-600 pt-2 border-t border-stone-200/60">
                          <span className="flex items-center gap-1.5 font-semibold text-stone-700">
                            <ShieldCheck className="w-3.5 h-3.5 text-stone-500" />
                            <span>Intégrité SHA-256 · Prêt pour signature</span>
                          </span>
                          <span className="font-mono text-[10px] text-stone-400">En attente de signature</span>
                        </div>'''
    content = content.replace(old_focus_act, new_focus_act)

    # 5. Priorités à traiter: Flat typography, divide-y divide-stone-200, no buttons, references plain text, deadline plain text
    old_priorities_block = '''            {/* Priorités à traiter (1 seul bouton par ligne, texte blanc garanti, badge collé au titre) */}
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-stone-900 tracking-tight">
                    Priorités à traiter
                  </h2>
                  <span className="text-[11px] font-bold bg-stone-100 text-[#102A4C] border border-stone-200 px-2 py-0.5 rounded-full font-mono tabular-nums">
                    {pendingDossiers.length}
                  </span>
                </div>
                <a
                  href="#/workflows"
                  className="text-xs font-semibold text-[#102A4C] hover:text-[#193D6B] flex items-center gap-1"
                >
                  <span>Tous les circuits</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="space-y-3">
                {pendingDossiers.slice(0, 4).map((d) => (
                  <div
                    key={d.id}
                    onClick={() => {
                      window.location.hash = `/workflows?dossier=${d.id}`;
                    }}
                    className="p-4 rounded-xl border border-stone-200/90 bg-white hover:bg-stone-50/80 hover:border-stone-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-3xs cursor-pointer group"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      {/* Ligne 1: Identifiant + Titre complet (sans troncature) + Badge éventuel */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold text-[#102A4C] bg-stone-100 border border-stone-200 px-2 py-0.5 rounded shadow-3xs shrink-0">
                          {d.id}
                        </span>
                        <span className="text-xs font-bold text-stone-900 group-hover:text-[#102A4C] transition-colors">
                          {d.title}
                        </span>
                        {d.isConfidentialCCAS && (
                          <span className="text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200 px-2 py-0.5 rounded-full shrink-0">
                            {d.confidentialBadge || 'Accès restreint · Secret professionnel CCAS'}
                          </span>
                        )}
                      </div>
                      {/* Ligne 2: Métadonnées alignées proprement sans séparateur flottant */}
                      <div className="flex items-center gap-2.5 text-[11px] text-stone-500 font-medium">
                        <span>{d.circuitLabel}</span>
                        <span className="text-stone-300">/</span>
                        <span>{d.applicant}</span>
                      </div>
                    </div>

                    {/* Échéance + Unique bouton Traiter calés à droite */}
                    <div className="flex flex-row sm:flex-row items-center justify-between sm:justify-end gap-2.5 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-stone-100">
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border flex items-center justify-center gap-1 ${
                          d.slaStatus === 'warning'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-stone-100 text-stone-800 border-stone-200'
                        }`}
                      >
                        <Clock className="w-2.5 h-2.5" />
                        <span>{d.slaDeadline}</span>
                      </span>

                      {/* Unique Bouton d'action Traiter avec texte blanc strict */}
                      <a
                        href={`#/workflows?dossier=${d.id}&action=sign`}
                        onClick={(e) => e.stopPropagation()}
                        style={{ color: '#ffffff' }}
                        className="px-4 py-1.5 rounded-lg bg-[#102A4C] hover:bg-[#193D6B] !text-white font-semibold text-xs shadow-3xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer shrink-0"
                      >
                        <Check className="w-3.5 h-3.5 text-white" />
                        <span className="text-white font-semibold">Traiter</span>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>'''

    new_priorities_block = '''            {/* Priorités à traiter (Design épuré Civic Distill: Surface unique, divide-y, zéro bouton plein, lignes cliquables) */}
            <div className="bg-white border border-stone-200/90 rounded-2xl shadow-[0_1px_2px_rgba(16,42,76,0.04)] overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-stone-100">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-stone-900 tracking-tight">
                    Priorités à traiter
                  </h2>
                  <span className="text-[11px] font-semibold text-stone-500 font-mono tabular-nums">
                    ({pendingDossiers.length})
                  </span>
                </div>
                <a
                  href="#/workflows"
                  className="text-xs font-semibold text-[#102A4C] hover:text-[#193D6B] flex items-center gap-1 transition-colors"
                >
                  <span>Tous les circuits</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="divide-y divide-stone-200/70">
                {pendingDossiers.slice(0, 4).map((d) => (
                  <div
                    key={d.id}
                    onClick={() => {
                      window.location.hash = `/workflows?dossier=${d.id}`;
                    }}
                    className="px-5 py-3.5 hover:bg-stone-50/90 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer group"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      {/* Ligne 1: Référence en texte brut sans cadre + Titre complet + Badge critique éventuel */}
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-mono text-xs text-stone-500 shrink-0">
                          {d.id}
                        </span>
                        <span className="text-xs font-bold text-stone-900 group-hover:text-[#102A4C] transition-colors">
                          {d.title}
                        </span>
                        {d.isConfidentialCCAS && (
                          <span className="text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200 px-2 py-0.5 rounded-full shrink-0">
                            {d.confidentialBadge || 'Secret professionnel CCAS'}
                          </span>
                        )}
                      </div>
                      {/* Ligne 2: Métadonnées discrètes */}
                      <div className="flex items-center gap-2 text-[11px] text-stone-500 font-medium">
                        <span>{d.circuitLabel}</span>
                        <span className="text-stone-300">·</span>
                        <span>{d.applicant}</span>
                      </div>
                    </div>

                    {/* Échéance en texte sobre (sans pilule) + Flèche discrète alignée à droite */}
                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      <span
                        className={`text-xs ${
                          d.slaStatus === 'warning'
                            ? 'text-amber-700 font-semibold'
                            : 'text-stone-500 font-medium'
                        }`}
                      >
                        {d.slaDeadline}
                      </span>
                      <ArrowRight className="w-4 h-4 text-stone-300 group-hover:text-[#102A4C] group-hover:translate-x-0.5 transition-all" />
                    </div>
                  </div>
                ))}
              </div>
            </div>'''
    content = content.replace(old_priorities_block, new_priorities_block)

    # 6. Activité récente: Surface unique avec divide-y (No card-in-card)
    old_activity_block = '''            {/* Activité récente (Scoping strict 100% sans fuite) */}
            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center justify-between border-b border-stone-100 pb-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                    Activité récente
                  </h3>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                {recentActivities.map((act, actIdx) => (
                  <div key={actIdx} className="flex items-start gap-3 p-3 rounded-xl bg-stone-50/70 border border-stone-100">
                    <div className={`w-7 h-7 rounded-lg ${act.tagBg} ${act.tagColor} flex items-center justify-center shrink-0 font-bold text-xs mt-0.5`}>
                      {act.tag}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-stone-800 font-medium">
                        {act.htmlText}
                      </p>
                      <p className="text-[10px] text-stone-400 mt-0.5">{act.timeAgo}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>'''

    new_activity_block = '''            {/* Activité récente (Surface épurée sans cartes imbriquées) */}
            <div className="bg-white border border-stone-200/90 rounded-2xl shadow-[0_1px_2px_rgba(16,42,76,0.04)] overflow-hidden">
              <div className="px-5 py-4 border-b border-stone-100">
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Activité récente
                </h3>
              </div>

              <div className="divide-y divide-stone-100 text-xs">
                {recentActivities.map((act, actIdx) => (
                  <div key={actIdx} className="flex items-start gap-3 px-5 py-3 hover:bg-stone-50/60 transition-colors">
                    <div className={`w-6 h-6 rounded-md ${act.tagBg} ${act.tagColor} flex items-center justify-center shrink-0 font-bold text-[10px] mt-0.5`}>
                      {act.tag}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-stone-800 font-medium">
                        {act.htmlText}
                      </p>
                      <p className="text-[10px] text-stone-400 mt-0.5">{act.timeAgo}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>'''
    content = content.replace(old_activity_block, new_activity_block)

    # 7. Échéances & Séances: Surface unique avec divide-y (No card-in-card)
    old_sched_block = '''            <div className="bg-white border border-stone-200/90 rounded-2xl p-5 shadow-[0_1px_2px_rgba(16,42,76,0.04)] space-y-4">
              <div className="flex items-center gap-2 border-b border-stone-100 pb-3">
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Échéances & Séances
                </h3>
              </div>

              <div className="space-y-3 text-xs">
                {scheduleEvents.map((evt, evtIdx) => (
                  <div key={evtIdx} className="p-3.5 rounded-xl bg-stone-50/70 border border-stone-200/80 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-stone-900">{evt.title}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${evt.badgeColor}`}>
                        {evt.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-stone-600 font-medium">{evt.datetime}</p>
                    <p className="text-[10px] text-stone-400">{evt.description}</p>
                  </div>
                ))}
              </div>
            </div>'''

    new_sched_block = '''            <div className="bg-white border border-stone-200/90 rounded-2xl shadow-[0_1px_2px_rgba(16,42,76,0.04)] overflow-hidden">
              <div className="px-5 py-4 border-b border-stone-100">
                <h3 className="text-sm font-bold text-stone-900 tracking-tight">
                  Échéances & Séances
                </h3>
              </div>

              <div className="divide-y divide-stone-100 text-xs">
                {scheduleEvents.map((evt, evtIdx) => (
                  <div key={evtIdx} className="px-5 py-3 hover:bg-stone-50/60 transition-colors space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-stone-900">{evt.title}</span>
                      <span className={`text-[10px] font-medium text-stone-500`}>
                        {evt.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-stone-600 font-medium">{evt.datetime}</p>
                    <p className="text-[10px] text-stone-400">{evt.description}</p>
                  </div>
                ))}
              </div>
            </div>'''
    content = content.replace(old_sched_block, new_sched_block)

    return content

update_file('frontend-lovable/src/features/workspace/TodayDashboardView.tsx', mod_today)
