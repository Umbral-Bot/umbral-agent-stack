---
id: "2026-05-04-001"
title: "Copilot VPS — Investigar OpenClaw header refresh stale + Alertas del Supervisor (49d sin escribir)"
status: assigned
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026
created_at: 2026-05-04T00:00:00-03:00
updated_at: 2026-05-04T00:00:00-03:00
---

## Contexto previo (CRÍTICO leer primero)

Esta tarea fue creada por Copilot Chat trabajando en `notion-governance`. Antes de empezar:

1. **`git pull origin main`** en `umbral-agent-stack` (en la VPS, en `/home/rick/umbral-agent-stack`).
2. **Releer** `.github/copilot-instructions.md` — se acaba de añadir la sección **"VPS Reality Check Rule (CRITICAL — added 2026-05-04)"** (commit `fbc5dae`). Esta tarea es exactamente el caso de uso para esa regla. **No se puede cerrar esta tarea leyendo solo el repo.**
3. La regla en una línea: **el repo refleja intención; la VPS refleja realidad**. Cualquier afirmación sobre "el cron corre / no corre", "el writer escribe / no escribe", debe estar respaldada por `journalctl`/`systemctl`/`tail log`/`crontab -l` en la VPS.

## Objetivo

Investigar y reportar el estado real (en VPS) de dos componentes runtime que aparecen como "muertos" según evidencia observable en Notion:

### Subtarea A — OpenClaw header refresh cron stale

- **Síntoma:** un cron/job que debería refrescar headers de dashboards OpenClaw aparece desactualizado, mientras que el cron de OODA (sano) sí escribe.
- **Hipótesis a verificar/refutar:** el job está definido en repo pero el timer/cron real no está corriendo; o está corriendo pero falla silenciosamente; o el writer apunta a un destino equivocado.
- **No declarar nada como "fixed" hasta ver un journalctl/log que pruebe escritura exitosa post-fix.**

### Subtarea B — Alertas del Supervisor: writer muerto desde 2026-03-16

- **Síntoma:** la página/DB **Alertas del Supervisor** en Notion no recibe escrituras desde **2026-03-16** (49 días al 2026-05-04). Su contenido actual es literalmente `# Dashboard Rick` — placeholder o regresión.
- **Hipótesis a verificar/refutar:** el writer cron/agente que debería poblar esto fue desactivado, renombrado, o quedó apuntando al ID equivocado; la API key expiró; o el script falla y nadie lo detecta.

## Procedimiento mínimo (NO saltar pasos)

```bash
# 0. Sincronizar y leer la nueva regla
ssh rick@<vps>
cd ~/umbral-agent-stack && git pull origin main
cat .github/copilot-instructions.md | sed -n '/VPS Reality Check/,/Related Repositories/p'

# 1. Inventario de crons + timers
crontab -l
sudo crontab -l 2>/dev/null
systemctl list-timers --all --user
systemctl list-timers --all
ls ~/.config/systemd/user/ 2>/dev/null

# 2. Subtarea A — OpenClaw header refresh
# Identificar la unidad/script real (NO asumir nombre):
grep -rE "header.?refresh|openclaw.*refresh|refresh.*header" ~/umbral-agent-stack/scripts/ ~/umbral-agent-stack/runbooks/ 2>/dev/null
# Verificar journal de la unidad real encontrada:
sudo journalctl -u <unit-encontrada> --since '7 days ago' | tail -200
# Verificar logs de aplicación si los hay:
tail -300 ~/.config/umbral/ops_log.jsonl | jq 'select(.event | test("header|refresh"; "i"))'

# 3. Subtarea B — Alertas del Supervisor writer
# Buscar referencias en scripts/configs:
grep -rE "Alertas.?del.?Supervisor|alert.*supervisor|supervisor.*alert" ~/umbral-agent-stack/ 2>/dev/null | head -50
# Identificar el cron/timer que debería escribir y verificar journal:
sudo journalctl --since '2026-03-10' | grep -iE "supervisor|alertas" | tail -100
# Verificar el ops_log:
grep -i "supervisor\|alert" ~/.config/umbral/ops_log.jsonl | tail -50

# 4. Comparar repo (intención) vs VPS (realidad)
# Para cada componente, separar explícitamente en el reporte:
#   "Repo dice X" (cita el archivo + línea)
#   "VPS muestra Y" (cita el comando + output relevante)
```

## Criterios de aceptación

- [ ] Confirmaste haber leído la nueva sección "VPS Reality Check Rule" tras pulling main.
- [ ] **Subtarea A:** identificada la unidad/script REAL del header refresh, status del timer (`systemctl list-timers`), última ejecución exitosa según `journalctl`, y diagnóstico (¿está stale por timer apagado, por error en script, o por destino mal configurado?).
- [ ] **Subtarea B:** identificado el writer REAL que debería poblar Alertas del Supervisor, fecha de última escritura exitosa según logs (no según Notion), causa raíz de los 49 días sin actividad.
- [ ] Cada hallazgo separa **"Repo dice X"** vs **"VPS muestra Y"**.
- [ ] Si propones fix, NO lo aplicas todavía: dejas el plan en el Log de esta tarea para que David apruebe.
- [ ] Si hay bloqueos (falta de permisos, unidad no encontrada, ambigüedad de qué writer es el correcto), los listas explícitamente como `blocked` con la pregunta exacta para David.

## Antipatrones que esta tarea explícitamente prohíbe

- ❌ "Leí `scripts/openclaw-header-refresh.sh` y veo que está bien escrito, así que el problema es el script." → no es verificación, es hipótesis.
- ❌ "Asumo que el cron está activo porque está en `crontab.example`." → ejemplo ≠ realidad.
- ❌ "Notion muestra `# Dashboard Rick` desde marzo, así que el writer está roto." → eso es síntoma, falta confirmar QUÉ writer y POR QUÉ no escribe (writer apagado vs writer escribiendo a destino equivocado vs writer fallando silenciosamente vs página manualmente sobreescrita por humano).

## Reportar resultados

Actualiza este mismo archivo:

1. Cambiar `status: assigned` → `in_progress` al empezar, → `done` o `blocked` al cerrar.
2. Agregar bloque `### [copilot] 2026-05-04 HH:MM` en `## Log` con hallazgos.
3. Si necesitas escalar a David, ping en `.agents/board.md`.

## Log

### [copilot-chat-notion-governance] 2026-05-04
Tarea creada desde sesión de Copilot Chat en `notion-governance`. Trigger: David pidió delegar la investigación cron/writer a Copilot VPS aprovechando que tiene acceso SSH real y que se acaba de añadir la regla "VPS Reality Check" a las instrucciones (commit `fbc5dae` en `umbral-agent-stack`). La regla nació precisamente para evitar el patrón "leer repo y declarar fixed sin tocar la VPS".
