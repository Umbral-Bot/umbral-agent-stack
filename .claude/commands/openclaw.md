# OpenClaw — Umbral Agent Stack

Configuración y operación de OpenClaw/Rick en este repositorio.
OpenClaw es el gateway Telegram + Control UI que corre en el VPS.

## Estructura en el repo

```
openclaw/
├── extensions/
│   └── umbral-worker/
│       └── index.ts        ← extension que conecta OpenClaw con el Worker
├── workspace-templates/
│   ├── AGENTS.md           ← instrucciones del agente Rick
│   ├── SOUL.md             ← 20 reglas de comportamiento de Rick
│   └── skills/             ← 90+ skills disponibles para Rick
│       ├── notion-workflow/
│       ├── linear/
│       ├── research/
│       └── ...
```

**Config en VPS:** `~/.openclaw/openclaw.json`
**Config local referencia:** no hay openclaw.json en el repo (es personal del VPS)

## Ver config actual de Rick en VPS
```bash
ssh $VPS_USER@$VPS_HOST "cat ~/.openclaw/openclaw.json"
```

## Verificar que OpenClaw está corriendo
```bash
ssh $VPS_USER@$VPS_HOST "systemctl status openclaw"
ssh $VPS_USER@$VPS_HOST "bash ~/umbral-agent-stack/scripts/vps/verify-openclaw.sh"
```

## Reiniciar OpenClaw
```bash
ssh $VPS_USER@$VPS_HOST "systemctl restart openclaw"
ssh $VPS_USER@$VPS_HOST "journalctl -u openclaw -n 50 --no-pager"
```

## Trabajar con skills de Rick

### Ver skills disponibles
```bash
ls openclaw/workspace-templates/skills/
```

### Estructura de una skill
```
skills/<nombre>/
├── SKILL.md        ← descripción, trigger, workflow (OBLIGATORIO)
└── references/     ← documentos de referencia opcionales
    └── *.md
```

### Agregar/editar una skill
1. Crear o editar `openclaw/workspace-templates/skills/<nombre>/SKILL.md`
2. Seguir el formato de skills existentes (ver `skills/linear/SKILL.md` como referencia)
3. Commitear y pushear al repo
4. En VPS: `git pull && systemctl restart openclaw`

### Formato mínimo de SKILL.md
```markdown
---
name: nombre-skill
description: Una línea clara de cuándo usar esta skill. Incluir palabras clave de trigger.
---

# Nombre Skill

## Objetivo
Qué hace esta skill.

## Flujo rápido
1. Paso 1
2. Paso 2

## Reglas
- Regla operativa importante
```

## Sincronizar skills al VPS
```bash
ssh $VPS_USER@$VPS_HOST "cd ~/umbral-agent-stack && git pull origin main"
# No requiere restart si solo cambian skills (OpenClaw las lee en runtime)
```

## Extensión umbral-worker

Conecta OpenClaw con el Worker FastAPI. Código en `openclaw/extensions/umbral-worker/index.ts`.

Para modificar y deployar:
```bash
cd openclaw/extensions/umbral-worker
npm install
npm run build
# Copiar al VPS
scp -r . $VPS_USER@$VPS_HOST:~/umbral-agent-stack/openclaw/extensions/umbral-worker/
ssh $VPS_USER@$VPS_HOST "systemctl restart openclaw"
```

## SOUL.md — Reglas de Rick

El archivo `openclaw/workspace-templates/SOUL.md` define el comportamiento de Rick.
20 reglas. Las más importantes para el trabajo diario:

- Regla 4: Todo proyecto debe tener un issue Linear
- Regla 6: Subagentes → esperar resultado y retomar turno
- Regla 13: Benchmark = artefacto + issue + Notion (no solo respuesta en chat)
- Regla 18: "Verificado" solo con evidencia observable
- Regla 20: Páginas sueltas → convertir a entregables con `notion.upsert_deliverable`

## Archivos de referencia
- `openclaw/workspace-templates/SOUL.md` — reglas completas de Rick
- `openclaw/workspace-templates/AGENTS.md` — instrucciones de coordinación
- `docs/03-setup-vps-openclaw.md` — setup inicial
- `docs/19-openclaw-claude-quota.md` — prevención de freeze de cuota Claude
