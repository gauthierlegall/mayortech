from pathlib import Path
import os

healthy = False
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        command = path.read_bytes().rstrip(b'\0').split(b'\0')
    except OSError:
        continue
    if path.parent.name != str(os.getpid()) and len(command) == 4 and command[1:] == [b'-m', b'travaux', b'worker']:
        healthy = True
        break
raise SystemExit(0 if healthy else 1)
