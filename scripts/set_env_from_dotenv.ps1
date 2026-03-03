# Lee .env en la raiz del repo y define las variables en el entorno del usuario (persistente).
# Uso: desde la raiz del repo:  .\scripts\set_env_from_dotenv.ps1
# Requiere: archivo .env con KEY=valor (sin espacios alrededor del =).

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envPath = Join-Path $repoRoot ".env"

if (-not (Test-Path $envPath)) {
    Write-Host "No existe .env en $repoRoot" -ForegroundColor Red
    Write-Host "Copia .env.example a .env y rellena con tus claves." -ForegroundColor Yellow
    exit 1
}

$count = 0
Get-Content $envPath -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    if ($line -notmatch "^([A-Za-z_][A-Za-z0-9_]*)=(.*)$") { return }
    $name = $matches[1]
    $value = $matches[2].Trim().Trim('"').Trim("'")
    if ($value -match "^CHANGE_ME") { return }
    try {
        [Environment]::SetEnvironmentVariable($name, $value, "User")
        $count++
        Write-Host "  $name = ***" -ForegroundColor Green
    } catch {
        Write-Host "  $name : error $_" -ForegroundColor Red
    }
}

Write-Host "`n$count variables guardadas en entorno de usuario (Windows)." -ForegroundColor Cyan
Write-Host "Cierra y vuelve a abrir la terminal (o Cursor) para que las vean los programas." -ForegroundColor Yellow
