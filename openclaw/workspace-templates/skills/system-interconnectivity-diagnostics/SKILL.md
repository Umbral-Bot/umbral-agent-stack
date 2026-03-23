---
name: system-interconnectivity-diagnostics
description: >-
  Diagnosticar la interconectividad real del stack Umbral sin confundir
  conectividad base con sanidad operativa. Usar cuando David pida "diagnostico
  completo", "verifica el sistema", "revisa conexiones entre apps", "que esta
  roto", "que esta sano", "smoke post deploy" o "barrido cross-system".
metadata:
  openclaw:
    emoji: "\U0001F9ED"
    requires:
      env:
        - WORKER_URL
        - WORKER_TOKEN
        - REDIS_URL
---

# System Interconnectivity Diagnostics

Usa esta skill cuando haga falta comprobar el sistema completo de extremo a
extremo y dejar un diagnostico util para David. El objetivo no es "correr todo
porque si", sino distinguir:

- conectividad base;
- sanidad operativa real;
- drift entre repo, VPS y VM;
- fallos de integracion entre apps;
- y el siguiente slice concreto que conviene ejecutar.

## Flujo obligado

### 1. Delimitar el plano

Primero decide que estas auditando:

- `VPS / control plane`
- `VM Windows / execution plane`
- `codigo compartido`
- `integracion externa` como Notion, Linear, Google o search providers

No mezcles hallazgos de un plano con otro sin decirlo.

### 2. Empezar por el baseline

Corre primero el plano base y declaralo como tal:

```bash
PYTHONPATH=. python3 scripts/verify_stack_vps.py
```

Si el baseline falla, nombra exactamente que fallo y no declares "stack sano".

### 3. Validar enlaces criticos

Segun el caso, cubre como minimo:

- `Worker /health`
- `Dispatcher` y cola Redis
- `GET /providers/status`
- `GET /quota/status`
- `linear.list_teams`
- `google.calendar.list_events`
- `gmail.list_drafts`
- `research.web` o `scripts/research_web_smoke.py`
- `Dashboard Rick` y `OpenClaw` si el hallazgo toca paneles
- `VM 8088` y `8089` si el hallazgo toca execution plane

### 4. Separar evidencia de inferencia

Siempre entrega estos cuatro bloques:

1. `Probado en vivo`
2. `Inferencia razonable`
3. `No probado`
4. `Bloqueo o deuda real`

No uses "verificado" si solo leiste codigo o docs.

### 5. Priorizar hallazgos

Clasifica hallazgos por impacto:

- `P0`: caida operativa o riesgo alto de falso positivo/falso ok
- `P1`: integracion importante rota o degradada
- `P2`: deuda de observabilidad, copy, skill o ergonomia

### 6. Cerrar con siguiente accion

No cierres con resumen vacio. Deja siempre:

- si hace falta fix de codigo;
- si hace falta fix operativo o de env;
- si hace falta solo monitoreo;
- y cual es el siguiente slice mas util.

## Rutina corta recomendada

Cuando David pida un barrido serio pero no una auditoria desde cero, usa esta
secuencia:

```bash
PYTHONPATH=. python3 scripts/verify_stack_vps.py
PYTHONPATH=. python3 scripts/audit_traceability_check.py --format json
PYTHONPATH=. python3 scripts/governance_metrics_report.py --days 7 --format json
PYTHONPATH=. python3 scripts/skills_coverage_report.py
PYTHONPATH=. python3 scripts/secrets_audit.py
PYTHONPATH=. python3 scripts/research_web_smoke.py --query "BIM trends 2026"
```

Suma checks de VM o Notion solo si el frente los toca de verdad.

## Anti-patrones

- No declarar "todo ok" porque `verify_stack_vps.py` paso.
- No confundir `health 200` con operacion real.
- No decir que una integracion esta lista solo porque existe la env.
- No reauditar todo si el problema es un slice localizado.
- No cerrar sin decir que fue corrido en vivo y que no.

## Salida esperada

Un buen resultado con esta skill deja:

- evidencia fresca;
- hallazgos priorizados;
- siguiente accion concreta;
- y trazabilidad en task, issue o log cuando el caso lo amerite.
