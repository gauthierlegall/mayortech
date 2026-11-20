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

# 1. Shell.tsx
def mod_shell(content):
    # Remove activeCommission div under select
    p = r'\{activeCommission&&<div className="flex items-center gap-1\.5 mt-1\.5 text-\[11px\]">.*?</div>\}'
    content = re.sub(p, '', content)
    # Replace Sparkles on Focus Elu
    content = content.replace('<Sparkles size={13} className="text-amber-500"/>', '<Eye size={14} className="text-stone-700"/>')
    # Replace Sparkles on Assistant
    content = content.replace('<Sparkles size={13} className="text-[#102A4C]"/>', '<MessageSquare size={14} className="text-[#102A4C]"/>')
    return content

update_file('frontend-lovable/src/features/workspace/Shell.tsx', mod_shell)

# 2. CommandPaletteModal.tsx
def mod_palette(content):
    # Remove recherche instantanée < 50 ms
    content = re.sub(r'\s*<span className="text-\[10px\] text-slate-400">Recherche instantan[ée]e &lt; 50 ms</span>', '', content)
    return content

update_file('frontend-lovable/src/features/workspace/CommandPaletteModal.tsx', mod_palette)

# 3. TodayDashboardView.tsx
def mod_today(content):
    # Remove role & organization duplicate line
    p_org = r'<div className="text-xs font-semibold text-stone-500 flex items-center gap-1\.5">\s*<span>\{commissionCfg\.roleTitle\}</span>\s*<span>·</span>\s*<span>\{organization\?\.name \|\| \'Ville de Plougastel-Daoulas\'\}</span>\s*</div>'
    content = re.sub(p_org, '', content)
    
    # Remove filler phrase in Focus Elu
    p_filler = r'<span className="text-xs text-stone-500 font-medium">\s*V[ée]rifiez les visas puis signez d’un clic\s*</span>'
    content = re.sub(p_filler, '', content)
    
    # Priorités à traiter - remove Inbox icon
    content = content.replace('<Inbox className="w-4 h-4 text-[#102A4C]" />\n                  ', '')
    content = content.replace('<Inbox className="w-4 h-4 text-[#102A4C]" />', '')
    
    # Activité récente - remove ShieldCheck icon and rename title and remove Temps réel
    content = content.replace('<ShieldCheck className="w-4 h-4 text-emerald-600" />\n                  ', '')
    content = content.replace('<ShieldCheck className="w-4 h-4 text-emerald-600" />', '')
    content = content.replace('Activité récente des services', 'Activité récente')
    content = re.sub(r'\s*<span className="text-\[11px\] text-stone-400 font-medium">Temps r[ée]el</span>', '', content)
    
    # Prochaines échéances - remove Calendar icon and rename title
    content = content.replace('<Calendar className="w-4 h-4 text-[#102A4C]" />\n                ', '')
    content = content.replace('<Calendar className="w-4 h-4 text-[#102A4C]" />', '')
    content = content.replace('Prochaines échéances & Séances', 'Échéances & Séances')
    
    return content

update_file('frontend-lovable/src/features/workspace/TodayDashboardView.tsx', mod_today)

# 4. ConnectorsSettings.tsx
def mod_connectors(content):
    p_latency = r'\{c\.latency !== undefined && \(\s*<div className="flex items-center justify-between text-stone-500 pt-0\.5">.*?</div>\s*\)\}'
    content = re.sub(p_latency, '', content, flags=re.DOTALL)
    content = content.replace('(`Connexion réussie (${latency} ms) : ${message}`)', '(`Connexion réussie : ${message}`)')
    content = content.replace('(`Connexion réussie (${latency} ms) : Bac à sable certifié.`)', '(`Connexion réussie : Bac à sable certifié.`)')
    return content

update_file('frontend-lovable/src/features/workspace/ConnectorsSettings.tsx', mod_connectors)

# 5. MayorFlowView.tsx
def mod_flow(content):
    content = content.replace('Sparkles,', 'SlidersHorizontal,')
    content = content.replace('<Sparkles size={15}', '<SlidersHorizontal size={15}')
    return content

update_file('frontend-lovable/src/features/workflow/MayorFlowView.tsx', mod_flow)

# 6. MayorWorkflowDesigner.tsx
def mod_designer(content):
    content = content.replace('Sparkles,', 'SlidersHorizontal,')
    content = content.replace('<Sparkles className="w-3.5 h-3.5" />', '<SlidersHorizontal className="w-3.5 h-3.5" />')
    return content

update_file('frontend-lovable/src/features/workflow/designer/MayorWorkflowDesigner.tsx', mod_designer)

# 7. AssistantWidget.tsx
def mod_assistant(content):
    content = content.replace('Sparkles,', '')
    content = content.replace('<Sparkles size={18}/>', '<MessageSquare size={18}/>')
    return content

update_file('frontend-lovable/src/features/workspace/AssistantWidget.tsx', mod_assistant)

# 8. Conversation.tsx
def mod_conversation(content):
    content = content.replace('Sparkles,', '')
    content = content.replace('<Sparkles size={17}/>', '<MessageSquare size={17}/>')
    return content

update_file('frontend-lovable/src/features/workspace/Conversation.tsx', mod_conversation)

# 9. Mail.tsx
def mod_mail(content):
    content = content.replace('Sparkles,', '')
    content = content.replace('<Sparkles size={15}/>', '<FileEdit size={15}/>')
    return content

update_file('frontend-lovable/src/features/workspace/Mail.tsx', mod_mail)

# 10. MayorValidationInbox.tsx
def mod_validation_inbox(content):
    content = content.replace('animate-pulse', '')
    return content

update_file('frontend-lovable/src/features/workflow/validation/MayorValidationInbox.tsx', mod_validation_inbox)

# 11. MayorValidationLaunchModal.tsx
def mod_launch_modal(content):
    content = content.replace('<span className="w-2 h-2 rounded-full bg-[#102A4C] animate-ping" />\n              ', '')
    content = content.replace('<span className="w-2 h-2 rounded-full bg-[#102A4C] animate-ping" />', '')
    return content

update_file('frontend-lovable/src/features/workflow/validation/MayorValidationLaunchModal.tsx', mod_launch_modal)

# 12. StructureEnrolementSettings.tsx
def mod_structure(content):
    content = content.replace('Sparkles,\n  ', '')
    content = content.replace('Sparkles,', '')
    return content

update_file('frontend-lovable/src/features/workspace/StructureEnrolementSettings.tsx', mod_structure)

# 13. OrganizationCreationWizardModal.tsx
def mod_wizard(content):
    content = content.replace('<span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />', '<span className="w-2 h-2 rounded-full bg-emerald-500" />')
    return content

update_file('frontend-lovable/src/features/workspace/OrganizationCreationWizardModal.tsx', mod_wizard)

# 14. SimulationControlBar.tsx
def mod_sim(content):
    content = content.replace('animate-pulse', '')
    return content

update_file('frontend-lovable/src/features/workflow/pixelflow/SimulationControlBar.tsx', mod_sim)

# Clean remaining Sparkles
def mod_project_detail(content):
    content = content.replace('Sparkles,', '')
    content = content.replace('<Sparkles/>Assistant', '<MessageSquare size={15}/>Assistant')
    content = content.replace('<Sparkles/>Préparer un', '<FileText size={15}/>Préparer un')
    content = content.replace('<Sparkles/>Pr\xe9parer un', '<FileText size={15}/>Préparer un')
    return content

update_file('frontend-lovable/src/features/workspace/ProjectDetail.tsx', mod_project_detail)

def mod_project_panels_assistant(content):
    content = content.replace('Sparkles,', '')
    content = content.replace('<Sparkles className="inline mr-2" size={20}/>', '<MessageSquare className="inline mr-2" size={20}/>')
    content = content.replace('<Sparkles/>{busy', '<MessageSquare size={15}/>{busy')
    return content

update_file('frontend-lovable/src/features/workspace/ProjectPanels.assistant.tsx', mod_project_panels_assistant)

def mod_project_panels(content):
    content = content.replace(',Sparkles', '')
    content = content.replace('<Sparkles size={15}/>', '<FileText size={15}/>')
    return content

update_file('frontend-lovable/src/features/workspace/ProjectPanels.tsx', mod_project_panels)
