# 34 — Windows FS tools (sin PAD)

## Objetivo
Permitir operaciones simples de archivos/carpetas en la VM (ej. `G:\\Mi unidad\\Rick-David`) sin depender de Power Automate Desktop.

**Tras mergear** el PR que añade estas tareas: en la VM ejecutar `git pull origin main`, `nssm restart openclaw-worker`, y comprobar que `GET http://localhost:8088/health` incluye en `tasks_registered` las tareas `windows.fs.*`. Ver runbook: [runbook-vm-worker-setup.md](../runbooks/runbook-vm-worker-setup.md) sección "Actualizar Worker tras merge".

## Seguridad
Se restringe por allowlist en `config/tool_policy.yaml`:

```yaml
tools:
  fs:
    allowed_base_paths:
      - G:\\Mi unidad\\Rick-David
      - C:\\Windows\\Temp
```

El Worker valida que cualquier `path` esté **dentro** de alguno de esos prefijos.

**Acceso a G:\ (Google Drive):** Si el Worker corre como servicio con cuenta LocalSystem, no verá unidades montadas por usuario (ej. `G:\`). Para que `windows.fs.*` funcione en `G:\Mi unidad\...`, el servicio NSSM debe ejecutarse con el usuario que tiene Drive montado. Ver [runbook-vm-worker-setup.md](../runbooks/runbook-vm-worker-setup.md) sección "Worker como usuario (acceso a G:\)".

## Tareas
- `windows.fs.ensure_dirs` — crea árbol de directorios
- `windows.fs.list` — lista entradas
- `windows.fs.read_text` — lee archivo texto UTF-8 (limitado)
- `windows.fs.write_text` — escribe archivo texto UTF-8 (limitado)

## Ejemplos

```json
{ "task": "windows.fs.ensure_dirs", "input": {"path": "G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas\\informes"} }
```

```json
{ "task": "windows.fs.list", "input": {"path": "G:\\Mi unidad\\Rick-David", "limit": 200} }
```

**Ruta de reportes (2026-03-08):** Los informes están en `G:\Mi unidad\Rick-David\Perfil de David Moreira\Reportes_Mercado` (bulk_market_report.md, competitor_report.md). La carpeta `Proyecto-Embudo-Ventas` está vacía.

## Transferencia de binarios (opcional)
- `windows.fs.write_bytes_b64`: escribir un archivo binario desde base64 (limitado por `tools.fs.max_bytes_b64`).
