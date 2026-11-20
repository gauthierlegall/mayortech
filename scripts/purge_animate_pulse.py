from pathlib import Path

files_to_clean = [
    'frontend-lovable/src/components/ui/skeleton.tsx',
    'frontend-lovable/src/features/municipal/EnrollmentApprovalQueue.tsx',
    'frontend-lovable/src/features/municipal/MunicipalOrganigramCanvas.tsx',
    'frontend-lovable/src/features/workflow/mayorflow/MayorFlowStudioCanvas.tsx',
    'frontend-lovable/src/features/workflow/pixelflow/BpmnTaskNode.tsx',
    'frontend-lovable/src/features/workflow/pixelflow/PixelFlowCanvas.tsx',
]

for p in files_to_clean:
    path = Path(p)
    if path.exists():
        content = path.read_text(encoding='utf-8')
        new_content = content.replace('animate-pulse', '')
        if new_content != content:
            path.write_text(new_content, encoding='utf-8')
            print(f"Purged animate-pulse from {p}")

print("Clean completed.")
