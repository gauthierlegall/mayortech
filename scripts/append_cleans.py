with open('scripts/apply_zero_gadget.py', 'a', encoding='utf-8') as f:
    f.write('''
# Clean remaining Sparkles
def mod_project_detail(content):
    content = content.replace('Sparkles,', '')
    content = content.replace('<Sparkles/>Assistant', '<MessageSquare size={15}/>Assistant')
    content = content.replace('<Sparkles/>Préparer un', '<FileText size={15}/>Préparer un')
    content = content.replace('<Sparkles/>Pr\\xe9parer un', '<FileText size={15}/>Préparer un')
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
''')
