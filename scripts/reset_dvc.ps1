<#
Script PowerShell pour reconstruire DVC proprement dans le projet Lybrary_DIT.
Usage :
  .\scripts\reset_dvc.ps1 -GDriveFolderId "<FOLDER_ID>" -ServiceAccountPath "C:\path\to\service-account.json"

Le script :
  - supprime en sécurité l'état DVC ancien
  - crée la structure de dossier attendue
  - installe les dépendances DVC
  - réinitialise DVC proprement
  - prépare un remote Google Drive si les paramètres sont fournis
#>
Param(
    [string]$GDriveRemoteName = "gdrive",
    [string]$GDriveFolderId = "",
    [string]$ServiceAccountPath = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Push-Location $projectRoot

$paths = @(
    ".dvc",
    "dvc.lock",
    ".dvc/config.local",
    ".dvc/cache",
    ".dvc/tmp"
)

foreach ($path in $paths) {
    if (Test-Path $path) {
        Write-Host "Suppression sécurisée : $path"
        Remove-Item -Recurse -Force $path
    }
    else {
        Write-Host "Absent : $path"
    }
}

Write-Host "Création des dossiers de données attendus..."
New-Item -ItemType Directory -Force -Path data\raw, data\processed, models, metrics | Out-Null

$python = "python"
if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
    throw "Python introuvable. Activez l'environnement virtuel ou utilisez le chemin complet vers Python."
}

Write-Host "Installation des dépendances DVC..."
& $python -m pip install -r requirements-dvc.txt

Write-Host "Initialisation de DVC..."
& $python -m dvc init --force

if ($GDriveFolderId -and $ServiceAccountPath) {
    Write-Host "Configuration du remote Google Drive..."
    & $python -m dvc remote add -d $GDriveRemoteName "gdrive://$GDriveFolderId"
    & $python -m dvc remote modify $GDriveRemoteName gdrive_use_service_account true
    & $python -m dvc remote modify $GDriveRemoteName gdrive_service_account_json_file_path $ServiceAccountPath --local
    Write-Host "Remote $GDriveRemoteName configuré dans .dvc/config.local."
}
else {
    Write-Host "Remote Google Drive non configuré."
    Write-Host "Utilisez : .\scripts\reset_dvc.ps1 -GDriveFolderId '<id>' -ServiceAccountPath 'C:\path\to\service-account.json'"
}

Write-Host "Le reset DVC est terminé."
Write-Host "Ensuite : python -m dvc status ; python -m dvc repro"
Pop-Location
