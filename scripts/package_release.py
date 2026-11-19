"""Archive portable des sources et preuves, sans données ni environnement local."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from datetime import date
from zipfile import ZIP_DEFLATED, ZipFile


EXCLUDED_DIRECTORIES = {
    '.venv', 'data', '.local', 'local', '.private', 'private', '.git',
    '__pycache__', '.pytest_cache', '.ruff_cache', 'test-results',
    'node_modules', '.tools', 'secrets', '.secrets', '.ssh', '.saas-factory',
    'diagnostics', 'dist',
}
SECRET_FILENAMES = {
    'owner.json', 'credentials.json', 'secrets.json', 'bootstrap-material.json',
    'id_rsa', 'id_ed25519', 'id_ecdsa', 'id_dsa',
}
PRIVATE_SUFFIXES = {'.log', '.pyc', '.key', '.keys', '.pem', '.p12', '.pfx', '.jks', '.keystore'}


def indirect(path):
    """Do not follow a symlink, Windows junction or other reparse point."""
    info = path.lstat()
    return (path.is_symlink() or path.resolve() != path.absolute()
            or bool(getattr(info, 'st_file_attributes', 0)
                    & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)))


def load_verification(project):
    """Keep an unfinished latest review; never substitute an older green one."""
    selected = None
    selected_date = None
    for kind in ('production', 'professionnelle'):
        candidates = []
        for path in (project / 'docs').glob(f'verification-{kind}-*.json'):
            match = re.fullmatch(rf'verification-{kind}-(20\d{{2}}-\d{{2}}-\d{{2}})\.json', path.name)
            if match:
                candidates.append((date.fromisoformat(match.group(1)), path))
        if candidates:
            selected_date, selected = max(candidates)
            break
    selected = selected or project / 'docs/verification-native.json'
    if indirect(selected) or not stat.S_ISREG(selected.lstat().st_mode) or selected.stat().st_nlink != 1:
        raise ValueError('indirect_verification_file')
    content = json.loads(selected.read_text(encoding='utf-8'))
    if not isinstance(content, dict):
        raise ValueError('invalid_verification_report')
    if selected_date is not None and content.get('date') != selected_date.isoformat():
        raise ValueError('verification_date_mismatch')
    return selected, content


def source_files(project):
    """Prune private trees before walking; inspect metadata without opening them."""
    if indirect(project) or not project.is_dir():
        raise ValueError('indirect_project_directory')
    for folder, directories, filenames in os.walk(project, topdown=True, followlinks=False):
        folder = Path(folder)
        directories[:] = sorted(name for name in directories
                                if name.lower() not in EXCLUDED_DIRECTORIES
                                and not indirect(folder / name))
        for name in sorted(filenames):
            file = folder / name
            lowered = name.lower()
            if (indirect(file) or not stat.S_ISREG(file.lstat().st_mode)
                    or file.stat().st_nlink != 1):
                continue
            if ((lowered.startswith('.env') and lowered != '.env.example')
                    or lowered.endswith('.env') or lowered in SECRET_FILENAMES
                    or '.sqlite' in lowered or lowered.endswith(('.db', '.db-wal', '.db-shm', '.db-journal'))
                    or file.suffix.lower() in PRIVATE_SUFFIXES):
                continue
            yield file


def main():
    project = Path(__file__).resolve().parents[1]
    latest, verification = load_verification(project)
    target = project.parent / 'travaux-mairie-source.zip'
    count = 0
    with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
        for file in source_files(project):
            relative = file.relative_to(project)
            archive.write(file, Path('travaux-mairie') / relative)
            count += 1
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('archive_corrupted')
    report = {'archive': target.name, 'files': count, 'bytes': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'verification_source': latest.relative_to(project).as_posix(), 'verification': verification, 'real_municipal_data': False, 'municipal_connectors_connected': False, 'native_affine_engine_embedded': True}
    (project.parent / 'travaux-mairie-livraison.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
