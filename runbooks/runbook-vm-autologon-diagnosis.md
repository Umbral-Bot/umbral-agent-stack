# Runbook: Diagnóstico de auto-logon en la VM (para Codex)

> Ejecutar este runbook **dentro de la VM** (OpenClaw / pcrick) con Codex. El objetivo es identificar por qué el inicio de sesión automático (DefaultUserName, DefaultPassword, AutoAdminLogon) no funciona tras reiniciar.

## Contexto

- Usuario esperado: `pcrick\rick` (salida de `whoami`).
- Registro configurado en `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`: DefaultDomainName, DefaultUserName, DefaultPassword, AutoAdminLogon.
- Tras reiniciar, Windows sigue mostrando la pantalla de contraseña en lugar de iniciar sesión automáticamente.

## Checklist para Codex (ejecutar en la VM)

### 1. Verificar valores del registro Winlogon

En PowerShell **ejecutado como Administrador**:

```powershell
$path = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Get-ItemProperty -Path $path | Select-Object DefaultDomainName, DefaultUserName, AutoAdminLogon | Format-List
# DefaultPassword no se muestra por seguridad; verificar que existe:
(Get-ItemProperty -Path $path).PSObject.Properties.Name -match "Default"
```

Anotar: ¿DefaultDomainName = pcrick? ¿DefaultUserName = rick? ¿AutoAdminLogon existe y es "1"? ¿Existe la propiedad DefaultPassword?

### 2. Tipo de cuenta (local vs Microsoft)

```powershell
# Ver si la cuenta rick es local o vinculada a Microsoft
Get-LocalUser -Name "rick" -ErrorAction SilentlyContinue | Select-Object Name, Enabled, Description
# Si hay cuenta Microsoft, el auto-logon por registro suele fallar
```

### 3. Directivas de seguridad que podrían bloquear auto-logon

```powershell
# Requerir Ctrl+Alt+Supr (si está habilitado, puede interferir)
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "DisableCAD" -ErrorAction SilentlyContinue | Select-Object DisableCAD
# DisableCAD = 0 → se requiere Ctrl+Alt+Supr (puede afectar). 1 = no requerido.
```

### 4. Visor de eventos: errores de inicio de sesión

```powershell
# Últimos fallos de logon (últimas 24 h)
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625; StartTime=(Get-Date).AddHours(-24)} -MaxEvents 5 -ErrorAction SilentlyContinue | Format-List TimeCreated, Message
# Id 4625 = logon failure. Revisar si hay muchos fallos tras reinicio.
```

### 5. Comprobar que el SID del usuario coincide con AutoLogonSID (si existe)

```powershell
$u = Get-LocalUser -Name "rick" -ErrorAction SilentlyContinue
if ($u) { $u.SID.Value }
# Comparar con el valor de AutoLogonSID en Winlogon (si existe).
```

### 6. Recomendación según hallazgos

- Si **DefaultUserName** o **DefaultDomainName** están mal o **DefaultPassword** no existe → corregir registro.
- Si la cuenta es **Microsoft** → indicar que el auto-logon por registro suele no funcionar; usar cuenta local o herramienta Autologon de Sysinternals.
- Si **DisableCAD = 0** → probar crear `DisableCAD` = 1 en `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System` (requiere reinicio).
- Si hay muchos **eventos 4625** tras reinicio → la contraseña podría ser incorrecta o la cuenta bloqueada temporalmente.

Al final, Codex debe dejar un resumen en este runbook o en un comentario de tarea con: valores actuales del registro, tipo de cuenta, resultado de DisableCAD y eventos 4625, y recomendación concreta (qué cambiar o qué herramienta usar).
