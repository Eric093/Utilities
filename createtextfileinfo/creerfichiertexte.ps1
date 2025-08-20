param (
    [string]$Path
)

if (-not $Path) {
    Write-Host "Chemin vide."
    exit 1
}

$baseName = [System.IO.Path]::GetFileNameWithoutExtension($Path)
$directory = [System.IO.Path]::GetDirectoryName($Path)

# Génère un nom unique
$index = 0
do {
    if ($index -eq 0) {
        $fileName = -join("$baseName", "_info.txt")
    } else {
        $fileName = -joiN("$baseName", "_info-", $index, ".txt")
    }
    $newFilePath = Join-Path $directory $fileName
    $index++
} while (Test-Path $newFilePath)

# Crée le fichier
New-Item -Path $newFilePath -ItemType File | Out-Null

# Ajoute la date et le nom original dans le contenu
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$originalName = [System.IO.Path]::GetFileName($Path)
$content = "Créé le $now depuis l'élément : $originalName"
Add-Content -Path $newFilePath -Value $content

# Ouvre dans le Bloc-notes
Start-Process notepad.exe $newFilePath
