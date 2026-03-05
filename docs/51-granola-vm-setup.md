# Guía de instalación — Granola Watcher en VM

> Configura el watcher que monitorea automáticamente la carpeta de exports de Granola y envía las transcripciones al Worker para procesarlas en Notion.

## Requisitos previos

- Python 3.11+ instalado en la VM Windows
- Worker corriendo en `localhost:8088`
- Granola instalado en la VM
- Repositorio clonado en `C:\GitHub\umbral-agent-stack`

## Instalación rápida (5 pasos)

1. Abrir PowerShell como usuario normal (NO admin)
2. Navegar al repo:
   ```powershell
   cd C:\GitHub\umbral-agent-stack
   ```
3. Ejecutar el instalador:
   ```powershell
   .\scripts\vm\setup_granola_watcher.ps1
   ```
4. Ingresar el `WORKER_TOKEN` cuando se solicite (mismo token que usa el Worker)
5. Verificar con:
   ```powershell
   .\scripts\vm\test_granola_watcher.ps1
   ```

## Flujo de trabajo diario

1. Terminar reunión en Granola
2. En Granola: **File → Export / Copy** (o usar `granola-to-markdown` para batch)
3. Guardar el `.md` en `C:\Granola\exports\`
4. Rick detecta automáticamente el archivo en ~5 segundos
5. Rick sube la transcripción a Notion y notifica por Telegram

```
Reunión termina → Export .md → Carpeta exports/ → Watcher detecta
    → POST al Worker → Notion page + Action items + Notificación
```

## Variables de entorno

Las variables se guardan en `C:\Granola\.env` (el instalador las configura automáticamente).

| Variable | Descripción | Default |
|----------|-------------|---------|
| `GRANOLA_EXPORT_DIR` | Carpeta monitoreada | `C:\Granola\exports` |
| `GRANOLA_WORKER_URL` | URL del Worker | `http://localhost:8088` |
| `GRANOLA_WORKER_TOKEN` | Token de autenticación | (requerido) |
| `GRANOLA_NOTION_DATABASE_ID` | ID de DB Notion para transcripciones | (opcional) |
| `GRANOLA_POLL_INTERVAL` | Segundos entre checks | `5` |
| `GRANOLA_LOG_FILE` | Ruta del archivo de log | `C:\Granola\watcher.log` |

## Estructura de archivos

```
C:\Granola\
├── .env                    # Configuración del watcher
├── watcher.log             # Log del watcher (rotación manual)
└── exports\
    ├── meeting-2026-03-04.md   # ← archivos nuevos aquí
    └── processed\
        └── meeting-2026-03-04.md   # ← movidos después de procesar
```

## Ejecución manual

```powershell
# Modo continuo (polling cada N segundos)
python scripts\vm\granola_watcher.py --poll

# Procesar archivos pendientes y salir
python scripts\vm\granola_watcher.py --once

# Modo watchdog (requiere pip install watchdog)
python scripts\vm\granola_watcher.py
```

## Task Scheduler

El instalador registra automáticamente la tarea `GranolaWatcher` con `schtasks`:

- **Trigger:** Al hacer login del usuario (`/SC ONLOGON`)
- **No requiere privilegios de admin**
- **Se ejecuta bajo el usuario actual**

Para verificar el estado:
```powershell
schtasks /Query /TN "GranolaWatcher"
```

Para ejecutar manualmente:
```powershell
schtasks /Run /TN "GranolaWatcher"
```

## Logs

El watcher escribe logs tanto a `stdout` como a `C:\Granola\watcher.log`.

```powershell
# Ver las últimas líneas del log
Get-Content C:\Granola\watcher.log -Tail 20

# Seguir el log en tiempo real
Get-Content C:\Granola\watcher.log -Wait
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `GRANOLA_EXPORT_DIR not set` | Verificar que `C:\Granola\.env` existe y tiene la variable |
| `WORKER_TOKEN not set` | Agregar el token en `C:\Granola\.env` |
| `Connection refused` | Verificar que el Worker está corriendo: `curl http://localhost:8088/health` |
| El archivo no se mueve a `processed/` | Verificar permisos de escritura en la carpeta |
| El watcher no inicia al hacer login | Verificar: `schtasks /Query /TN "GranolaWatcher"` |

## Desinstalar

```powershell
.\scripts\vm\uninstall_granola_watcher.ps1
```

Esto elimina la tarea del Task Scheduler y opcionalmente limpia `C:\Granola\.env` y el log.
