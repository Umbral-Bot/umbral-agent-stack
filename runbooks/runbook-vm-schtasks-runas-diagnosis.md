# Runbook: Diagnóstico schtasks /ru en VM (Codex)

## Objetivo

Ejecutar en la VM (PCRick) pruebas de `schtasks /create /ru` para determinar qué formato de cuenta funciona y devolver input útil al agente principal (Cursor).

## Contexto

- La VPS envía tareas al Worker de la VM. Autenticación OK.
- La tarea `windows.open_notepad` crea una tarea programada con `schtasks` y `/ru` para que se ejecute en la sesión del usuario.
- Actualmente falla: "No se efectuó ninguna asignación entre los nombres de cuenta y los identificadores de seguridad".
- Necesitamos saber qué formato de cuenta acepta `schtasks` en esta VM.

## Prerrequisitos

- Codex corriendo dentro de la VM (o con acceso a la VM).
- PowerShell como Administrador.

## Pruebas a ejecutar

### 1. Identidad actual

```powershell
whoami
whoami /user
```

### 2. Probar schtasks con distintos formatos de /ru

Usa la contraseña real del usuario Rick. Sustituye `PASSWORD` por la contraseña.

**A) Formato .\rick**
```powershell
schtasks /create /tn TestNotepadA /tr "notepad.exe" /sc onlogon /ru ".\rick" /rp "PASSWORD" /f
```
Si OK: `schtasks /query /tn TestNotepadA` debe mostrar la tarea.
Luego: `schtasks /delete /tn TestNotepadA /f`

**B) Formato pcrick\rick**
```powershell
schtasks /create /tn TestNotepadB /tr "notepad.exe" /sc onlogon /ru "pcrick\rick" /rp "PASSWORD" /f
```
Si OK: `schtasks /query /tn TestNotepadB`
Luego: `schtasks /delete /tn TestNotepadB /f`

**C) Formato solo rick**
```powershell
schtasks /create /tn TestNotepadC /tr "notepad.exe" /sc onlogon /ru "rick" /rp "PASSWORD" /f
```
Si OK: `schtasks /query /tn TestNotepadC`
Luego: `schtasks /delete /tn TestNotepadC /f`

### 3. Valor actual de OPENCLAW en NSSM

```powershell
nssm get openclaw-worker AppEnvironmentExtra
```

Extrae la línea OPENCLAW_NOTEPAD_RUN_AS_USER (o similar) si existe.
**No incluyas contraseñas en el output.**

### 4. Nombre del equipo

```powershell
$env:COMPUTERNAME
hostname
```

## Qué reportar

Al final, devuelve al agente principal (Cursor) un resumen con:

1. Salida de `whoami` y `whoami /user`.
2. Para cada prueba A, B, C: si la tarea se creó OK o el mensaje de error exacto.
3. Valor de OPENCLAW_NOTEPAD_RUN_AS_USER (sin contraseña).
4. Nombre del equipo (COMPUTERNAME).

Con esto el agente podrá ajustar el código del Worker para usar el formato correcto.
