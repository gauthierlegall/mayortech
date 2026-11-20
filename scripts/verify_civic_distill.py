from pathlib import Path

patterns = ['< 50 ms', 'Temps réel', 'animate-pulse', 'Sparkles', 'e-Bourgogne', '+ + ']
root = Path('frontend-lovable/src')
results = {p: [] for p in patterns}

for f in root.rglob('*.ts*'):
    try:
        content = f.read_text(encoding='utf-8')
    except Exception:
        continue
    for p in patterns:
        if p in content:
            results[p].append(str(f))

all_clear = True
for p, files in results.items():
    print(f"'{p}': {len(files)} matches -> {files}")
    if len(files) > 0:
        all_clear = False

if all_clear:
    print("\nPROVED: 0 occurrences of forbidden patterns!")
else:
    print("\nWARNING: Some patterns were found!")
