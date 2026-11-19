$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'Installer uv, puis relancer. Voir README.md.'
    }
    uv --system-certs sync --frozen --extra documents
    if ($LASTEXITCODE -ne 0) { throw 'Installation interrompue.' }
}
Write-Host 'Travaux : ouvrir http://127.0.0.1:8765 dans le navigateur.'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.env')) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'uv est requis pour charger explicitement .env ; voir README.md.' }
    uv --system-certs run --frozen --env-file .env --extra documents --extra appflowy travaux serve
} else {
    & $pythonPath -m travaux serve
}
