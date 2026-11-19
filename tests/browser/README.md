# Recette documentaire et chat avec les vraies API locales

La recette indépendante des séparateurs de messagerie est décrite dans [MAIL_SPLITTER.md](MAIL_SPLITTER.md).

`document_chat_server.py` lance une application de recette sur **127.0.0.1:18806** avec une base SQLite dédiée dans `.local/document-chat-browser-qa`. Le dépôt de PDF, son analyse textuelle, les propositions en base, la confirmation humaine et la page Yjs sont réels. Les réponses des modèles passent exclusivement par `httpx.MockTransport` ; l’URL du modèle est `https://model.invalid/chat`, sans appel à un fournisseur. Les réglages `TRAVAUX_*` hérités du processus sont écartés pour ce serveur de recette.

`document_chat_real_api.py` ouvre Chrome sans interface, crée un nouveau dossier fictif, dépose un PDF généré en mémoire, vérifie les octets téléchargés et le RAG, confirme un changement de statut puis une action, et vérifie la persistance Yjs après rechargement. Les captures sont en Full HD et sur mobile. Le client refuse toute origine de fixture différente de `http://127.0.0.1:18806`.

Le scénario porté dans ce répertoire a été exécuté sur le paquet final : **12 contrôles réussis**, aucune exception JavaScript et aucune requête échouée. Les serveurs de recette ont ensuite été arrêtés et le port vérifié libre. Le mode est une démonstration locale sans authentification : **cette recette ne qualifie ni une identité professionnelle, ni une inscription, ni une 2FA, ni un fournisseur LLM réel**.

## Préparation

Depuis la racine du projet contenant `pyproject.toml`, utiliser son environnement `.venv`, les dépendances de développement/documentaires et Chrome avec Playwright déjà installés. Les deux interfaces doivent être construites :

```powershell
npm --prefix frontend-lovable run build
.venv/Scripts/python.exe scripts/package_frontend.py
npm --prefix native-editor run build
```

Les résultats sont écrits dans `test-results/document-chat-integration` : `fixture.json`, `checks.json`, `model-routing.json` et les captures PNG. Le serveur réutilise uniquement sa base de recette dédiée ; chaque passage du scénario crée un nouveau dossier fictif. Ne pas utiliser de documents ni de comptes réels.

## Exécuter et arrêter explicitement le serveur

Ce bloc PowerShell refuse d’occuper un port déjà utilisé. Il conserve le PID du seul serveur qu’il a lancé et l’arrête dans `finally`, y compris si le scénario échoue. Il ne faut pas l’exécuter tant que le port 18806 appartient à une autre recette.

```powershell
$qaRoot = (Get-Location).Path
$qaPython = (Resolve-Path .venv/Scripts/python.exe).Path
$qaOut = Join-Path $qaRoot 'test-results/document-chat-integration'
if (Get-NetTCPConnection -LocalPort 18806 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Le port local 18806 est déjà occupé. Terminez cette recette avant de continuer.'
}
New-Item -ItemType Directory -Path $qaOut -Force | Out-Null
$qaServer = Start-Process -FilePath $qaPython `
    -ArgumentList @('tests/browser/document_chat_server.py') `
    -WorkingDirectory $qaRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $qaOut 'server.stdout.log') `
    -RedirectStandardError (Join-Path $qaOut 'server.stderr.log')
try {
    $qaReady = $false
    for ($qaAttempt = 0; $qaAttempt -lt 30; $qaAttempt++) {
        if ($qaServer.HasExited) { throw 'Le serveur de recette a quitté avant son démarrage.' }
        try {
            Invoke-RestMethod 'http://127.0.0.1:18806/api/v1/session' -TimeoutSec 1 | Out-Null
            $qaReady = $true
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $qaReady) { throw 'Le serveur de recette local ne répond pas.' }
    & $qaPython tests/browser/document_chat_real_api.py
    if ($LASTEXITCODE -ne 0) { throw 'La recette a échoué ; consulter checks.json et les captures.' }
} finally {
    if (-not $qaServer.HasExited) {
        Stop-Process -Id $qaServer.Id
        $qaServer.WaitForExit()
    }
}
```

Le navigateur est fermé par le scénario. Le bloc ci-dessus arrête explicitement le processus serveur ; il ne supprime ni les preuves ni la base fictive. Pour une exécution manuelle dans deux terminaux, lancer le serveur au premier plan, exécuter le client dans le second, puis revenir au premier et envoyer **Ctrl+C**.
