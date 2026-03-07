# Agregar clave SSH pública a la VM (PCRick) para acceso sin contraseña.
# Ejecutar UNA VEZ; te pedirá la contraseña de Rick en la VM.
# Uso: .\scripts\setup-ssh-vm.ps1

$vmUser = "rick"
$vmHost = "100.109.16.40"
$keyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"

if (-not (Test-Path $keyPath)) {
    Write-Error "No se encontró $keyPath"
    exit 1
}

$key = (Get-Content $keyPath -Raw).Trim()
# Escapar para paso seguro: base64
$keyB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($key))

$remoteCmd = "`$k=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$keyB64')); New-Item -ItemType Directory -Path `$env:USERPROFILE\.ssh -Force | Out-Null; Add-Content -Path `$env:USERPROFILE\.ssh\authorized_keys -Value `$k; Write-Host 'Clave agregada.'"

Write-Host "Conectando a ${vmUser}@${vmHost}... (ingresá la contraseña cuando la pida)"
& ssh "${vmUser}@${vmHost}" "powershell -NoProfile -Command `"$remoteCmd`""
