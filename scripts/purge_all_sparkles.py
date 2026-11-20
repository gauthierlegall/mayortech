import re

files_and_changes = [
    ('frontend-lovable/src/features/municipal/MunicipalDirectoryView.tsx', [('Sparkles, ', '')]),
    ('frontend-lovable/src/features/municipal/PositionProfileDrawer.tsx', [(', Sparkles', '')]),
    ('frontend-lovable/src/features/seances/CouncilSessionView.tsx', [('Sparkles,', '')]),
    ('frontend-lovable/src/features/seances/SessionManager.tsx', [('Sparkles,', '')]),
    ('frontend-lovable/src/features/workflow/validation/MayorValidationInbox.tsx', [('Sparkles,', '')]),
    ('frontend-lovable/src/features/workflow/prompt/PromptWorkflowStudio.tsx', [('Sparkles', 'SlidersHorizontal')]),
    ('frontend-lovable/src/features/workspace/organization-modules-context.tsx', [("'Sparkles'", "'MessageSquare'")]),
    ('frontend-lovable/src/features/workspace/OrganizationCreationWizardModal.tsx', [('Sparkles,', '')]),
    ('frontend-lovable/src/features/workspace/OrganizationModulesSettings.tsx', [('Sparkles,', '')]),
    ('frontend-lovable/src/features/workspace/ProjectPanels.assistant.tsx', [(',Sparkles', '')]),
    ('frontend-lovable/src/features/workspace/commissionConfig.ts', [("'sparkles'", "'messages-square'")]),
]

for path, rep_list in files_and_changes:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for o, n in rep_list:
        content = content.replace(o, n)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Purged", path)

print("All remaining sparkles purged!")
