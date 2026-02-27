# ============================================================
# firewall-rule-8088.ps1
# ============================================================
# Crea una regla de firewall para permitir conexiones entrantes
# al puerto 8088 (worker FastAPI).
# Ejecutar como administrador.
# ============================================================

$ErrorActionPreference = "Stop"

$RuleName = "OpenClaw Worker 8088"

# --- Verificar si ya existe ---
$existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "La regla '$RuleName' ya existe." -ForegroundColor Yellow
    Write-Host "Estado: $($existing.Enabled)" -ForegroundColor Cyan
    exit 0
}

# --- Crear regla ---
Write-Host "Creando regla de firewall '$RuleName'..." -ForegroundColor Green

New-NetFirewallRule `
    -DisplayName $RuleName `
    -Direction Inbound `
    -LocalPort 8088 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private `
    -Description "Permite conexiones entrantes al worker FastAPI (Tailscale)"

Write-Host ""
Write-Host "Regla creada exitosamente." -ForegroundColor Green
Write-Host "Nota: La regla se aplica solo al perfil 'Private' (Tailscale)." -ForegroundColor Cyan
