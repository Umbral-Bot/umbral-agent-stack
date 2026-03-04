# Task R12 — Cloud 2: Granola VM Service Installer

**Fecha:** 2026-03-04  
**Ronda:** 12  
**Agente:** Cursor Agent Cloud 2  
**Branch:** `feat/granola-vm-service`

---

## Contexto

El script `scripts/vm/granola_watcher.py` fue creado en R11 (Cloud 7). Es un watcher de carpeta que detecta archivos `.md` exportados desde Granola y los envía al Worker local. Sin embargo, **no existe ningún instalador** para configurarlo como servicio automático en la VM Windows. El pipeline no funciona hasta que el watcher esté corriendo.

**Archivos de referencia:**
- `scripts/vm/granola_watcher.py` — el watcher ya implementado
- `docs/50-granola-notion-pipeline.md` — arquitectura elegida (Opción D: Watcher en VM)
- `worker/config.py` — patrón de variables de entorno
- `.env.example` — variables a agregar
- `scripts/vm/` — carpeta donde van los scripts de VM

**Arquitectura elegida (leer el doc):** El watcher corre en la VM Windows, monitorea `GRANOLA_EXPORT_DIR`, y hace POST al Worker local (`:8088`).

---

## Tareas requeridas

### 1. `scripts/vm/setup_granola_watcher.ps1`

Script PowerShell para instalación completa del servicio en Windows. Debe:

```powershell
# Estructura esperada del script:
# 1. Verificar que Python está instalado
# 2. Instalar dependencias (watchdog si se usa, o solo stdlib)
# 3. Crear la carpeta GRANOLA_EXPORT_DIR si no existe (default: C:\Granola\exports)
# 4. Crear el archivo .env para el watcher (pide valores interactivamente o usa defaults)
# 5. Registrar el watcher como tarea en Windows Task Scheduler (schtasks)
# 6. Mostrar resumen de lo instalado
```

**Detalles de la tarea Task Scheduler:**
```powershell
schtasks /Create /TN "GranolaWatcher" `
  /TR "python C:\GitHub\umbral-agent-stack\scripts\vm\granola_watcher.py" `
  /SC ONLOGON /RU $env:USERNAME /F
```

El flag `/SC ONLOGON` hace que inicie con el login del usuario (no requiere privilegios de sistema).

**Variables de entorno que debe configurar:**
```
GRANOLA_EXPORT_DIR=C:\Granola\exports
GRANOLA_WORKER_URL=http://localhost:8088
GRANOLA_WORKER_TOKEN=<pedir al usuario>
GRANOLA_NOTION_DATABASE_ID=<pedir al usuario o dejar vacío>
GRANOLA_POLL_INTERVAL=5
```

El script debe guardar estas variables en `C:\Granola\.env` y cargarlas al iniciar el watcher.

---

### 2. `scripts/vm/granola_watcher_env_loader.py`

Módulo pequeño para que `granola_watcher.py` cargue variables desde `C:\Granola\.env` si `python-dotenv` no está disponible:

```python
def load_env(path: str = r"C:\Granola\.env") -> None:
    """Carga variables de entorno desde archivo .env simple (KEY=VALUE)."""
    ...
```

Importarlo al inicio de `granola_watcher.py` (verificar si ya tiene carga de env; si no, agregar).

---

### 3. `scripts/vm/uninstall_granola_watcher.ps1`

Script para desinstalar/detener el servicio:
```powershell
schtasks /Delete /TN "GranolaWatcher" /F
Write-Host "GranolaWatcher eliminado del Task Scheduler."
```

---

### 4. `scripts/vm/test_granola_watcher.ps1`

Script de verificación rápida (smoke test):
```powershell
# 1. Crear archivo .md de prueba en GRANOLA_EXPORT_DIR
# 2. Esperar 10 segundos
# 3. Verificar que el archivo fue procesado (movido a _processed/)
# 4. Verificar que el Worker respondió con 200
# Muestra OK/FAIL en cada paso
```

---

### 5. `docs/51-granola-vm-setup.md`

Guía paso a paso para David (en español):

```markdown
# Guía de instalación — Granola Watcher en VM

## Requisitos previos
- Python 3.11+ instalado en la VM
- Worker corriendo en localhost:8088
- Granola instalado en la VM

## Instalación rápida (5 pasos)

1. Abrir PowerShell como usuario normal (NO admin)
2. Navegar al repo: `cd C:\GitHub\umbral-agent-stack`
3. Ejecutar: `.\scripts\vm\setup_granola_watcher.ps1`
4. Ingresar el WORKER_TOKEN cuando se solicite
5. Verificar con: `.\scripts\vm\test_granola_watcher.ps1`

## Flujo de trabajo diario

1. Terminar reunión en Granola
2. En Granola: File → Export / Copy (o usar granola-to-markdown)
3. Guardar el .md en `C:\Granola\exports\`
4. Rick detecta automáticamente el archivo en ~5 segundos
5. Rick sube la transcripción a Notion y notifica por Telegram

## Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| GRANOLA_EXPORT_DIR | Carpeta monitoreada | C:\Granola\exports |
| GRANOLA_WORKER_URL | URL del Worker | http://localhost:8088 |
| GRANOLA_WORKER_TOKEN | Token de autenticación | (requerido) |
| GRANOLA_NOTION_DATABASE_ID | ID de DB Notion | (opcional) |
| GRANOLA_POLL_INTERVAL | Segundos entre checks | 5 |

## Desinstalar

`.\scripts\vm\uninstall_granola_watcher.ps1`
```

---

### 6. Actualizar `granola_watcher.py` si es necesario

Revisar `scripts/vm/granola_watcher.py` y verificar:
- [ ] Carga variables desde `C:\Granola\.env` o variables de entorno
- [ ] Maneja errores de conexión al Worker (retry con backoff)
- [ ] Mueve archivos procesados a `_processed/` subdirectorio
- [ ] Log a archivo `C:\Granola\watcher.log` además de stdout
- Si alguna de estas cosas falta, agregarlas.

---

### 7. Actualizar `.env.example`

Agregar sección si no existe:
```dotenv
# Granola Watcher (VM Windows — en C:\Granola\.env, no en VPS)
GRANOLA_EXPORT_DIR=C:\Granola\exports
GRANOLA_WORKER_URL=http://localhost:8088
GRANOLA_WORKER_TOKEN=CHANGE_ME_SAME_AS_WORKER_TOKEN
GRANOLA_NOTION_DATABASE_ID=CHANGE_ME_NOTION_DATABASE_ID
GRANOLA_POLL_INTERVAL=5
```

---

### 8. Tests

Crear `tests/test_granola_watcher.py` con al menos 10 tests:

- `test_env_loader_reads_file`
- `test_env_loader_missing_file_no_crash`
- `test_env_loader_skips_comments`
- `test_watcher_processes_md_file` (mock Worker HTTP)
- `test_watcher_skips_non_md_files`
- `test_watcher_moves_processed_to_subdir`
- `test_watcher_retry_on_connection_error`
- `test_watcher_skips_already_processed`
- `test_watcher_log_to_file`
- `test_smoke_test_script_exists` (verifica que el .ps1 existe)

---

## Convenciones del proyecto

- **PowerShell:** compatibilidad con Windows 10+, sin requerir módulos adicionales
- **Python:** stdlib only (no watchdog requerido; usar `os.listdir` poll simple)
- **Task Scheduler:** `/SC ONLOGON` (no SYSTEM, no admin required)
- **Rama:** crear `feat/granola-vm-service` y abrir PR a `main`

## Criterios de éxito

- [ ] `scripts/vm/setup_granola_watcher.ps1` — instalador completo
- [ ] `scripts/vm/uninstall_granola_watcher.ps1` — desinstalador
- [ ] `scripts/vm/test_granola_watcher.ps1` — smoke test
- [ ] `scripts/vm/granola_watcher_env_loader.py` — cargador de .env
- [ ] `docs/51-granola-vm-setup.md` — guía en español
- [ ] `granola_watcher.py` actualizado con logging a archivo y retry
- [ ] `.env.example` actualizado
- [ ] `tests/test_granola_watcher.py` con 10+ tests
- [ ] PR abierto a `main`
