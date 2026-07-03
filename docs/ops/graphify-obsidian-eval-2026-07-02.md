# Evaluación Graphify + Obsidian para `umbral-agent-stack`

> **Versión:** UAS-GRAPHIFY-OBSIDIAN-EVAL-v0.2  
> **Fecha:** 2026-07-02  
> **Autor:** Cursor (responsable técnico, análisis read-only)  
> **Estado:** evaluación — **cero cambios de código, cero instalaciones, cero PR**  
> **Repo objetivo:** `Umbral-Bot/umbral-agent-stack` (clone auditado: `C:\GitHub\umbral-agent-stack-copilot`)  
> **Fuera de alcance:** `umbral-bot-2` (no evaluado, por instrucción)

---

## 0. Hechos verificados (base de la evaluación)

### 0.1 Graphify (verificado contra fuentes oficiales, 2026-07-02)

| Hecho | Detalle |
|-------|---------|
| Paquete | PyPI **`graphifyy`** (doble y); CLI **`graphify`**. Repo `safishamsi/graphify`, MIT, ~76k stars |
| Instalación recomendada | `uv tool install graphifyy` (entorno aislado, global por máquina). Evitar `pip install` plano en Windows |
| Arquitectura | 2 pasadas: (1) AST determinista tree-sitter para código — **sin LLM**; (2) extracción semántica de docs/imágenes/PDF vía LLM (usa la API key ya configurada del asistente; soporta backend **Azure OpenAI** vía `graphifyy[openai]` + `--backend azure`) |
| Outputs | `graphify-out/`: `graph.json` (grafo consultable), `GRAPH_REPORT.md` (resumen legible), `graph.html` (visualización), `cache/` (SHA256 incremental), `cost.json` (coste LLM, local-only) |
| Ignores | **Hereda `.gitignore` automáticamente** (merge); `.graphifyignore` gana en conflictos y **solo puede excluir más**, nunca re-incluir |
| Integración asistentes | `graphify install` **escribe `.cursor/rules/graphify.mdc` (alwaysApply) y modifica `AGENTS.md`**; en Claude Code instala hooks PreToolUse. Soporta OpenClaw (`--platform claw`) |
| Hooks git | `graphify hook install` (post-commit) — **no autorizado en esta evaluación** |
| Consulta | `graphify query "..."`, `graphify path "A" "B"`, `graphify explain "..."`; MCP server opcional: `graphifyy[mcp]` → `python -m graphify.serve graphify-out/graph.json` |
| Privacidad | Sin telemetría. La pasada semántica envía contenido de docs al modelo configurado (mismo trust class que usar Cursor/Codex sobre el repo, pero **en batch**) |

### 0.2 Repo (auditoría 2026-07-02)

| Hecho | Valor |
|-------|-------|
| Código Python | ~525 `.py`; `worker/tasks/` con **115 handlers** registrados en 36 módulos |
| Documentación | ~410 `.md` bajo `docs/` + ~266 tareas en `.agents/tasks/` + ~20 runbooks raíz + 5 en `docs/runbooks/` (**duplicación**) |
| Docs citados en el prompt | Los 6 existen: `docs/14`, `15`, `18`, `21`, `22`, `32` ✅ |
| TaskEnvelope | **Real**: `worker/models/__init__.py`, `worker/app.py`, `dispatcher/router.py`, `docs/07-worker-api-contract.md` |
| ModelRouter / TeamRouter | **Reales**: `worker/models/`, `config/teams*`, tests dedicados (`test_model_router.py`, `test_dispatcher_model_routing.py`) |
| LangGraph / ChromaDB / Langfuse | Presentes como dependencias/config (`pyproject.toml`, `worker/requirements.txt`, `.env.example`, README); RAG propio ya implementado en `worker/rag/` (`rag.index`, `rag.search`, `rag.query`) |
| Graphify previo | **0 referencias** — adopción greenfield; no existe `.graphifyignore` ni `graphify-out/` |
| Obsidian previo | **Ya diseñado**: `docs/ops/obsidian-context-vault.md` (vault externo, git privado, mirror VPS pull-only, carpetas `00_inbox/10_decisiones/20_reuniones/30_investigacion/40_runbooks/90_evals`) + `scripts/obsidian_context_check.py` + vars `OBSIDIAN_VAULT_PATH`/`OBSIDIAN_SYNC_MODE` en `.env.example` |
| Superficies sensibles en working tree | `.env` real en disco (gitignored), `scripts/manage_secrets.py`/`secrets_audit.py`, docs de setup de tokens, `docs/ops/evidence-imports/`, `.claude/settings.local.json`, fixtures de logs en tests |
| `.gitignore` | Ya cubre `.env`, `*.env`, `env.rick`, `openclaw/env`, `**/auth-profiles.json`, `**/sessions/`, logs, `.openclaw/`, `.agents/board.md`, snapshots — **Graphify hereda todo esto automáticamente** |

**Tres hallazgos que corrigen supuestos del prompt:**

1. **Obsidian ya tiene decisión y diseño en el repo** — no hay que crear el vault desde cero; hay que extender `obsidian-context-vault.md`, no competir con él.
2. **`.gitignore` ya hace la mitad del trabajo de seguridad** — Graphify lo hereda; `.graphifyignore` es defensa en profundidad + reducción de ruido, no la primera barrera.
3. **`graphify install` modifica `AGENTS.md` y `.cursor/rules/`** — choca con la restricción "no cambies reglas de agentes sin revisar compatibilidad". En el piloto se usa **solo consulta manual**, sin `install` ni hooks.

---

## 1. Resumen ejecutivo

Recomiendo **piloto controlado local** (Opción 5 híbrida), no implementación directa ni descarte. Graphify se instala **global** (`uv tool`), nunca como dependencia del repo; se genera `graphify-out/` localmente con un `.graphifyignore` creado **antes** de la primera pasada; nada de `graphify-out/` se commitea durante el piloto (el único archivo versionable desde el día 1 es `.graphifyignore`). Obsidian **no se crea nuevo**: se extiende el vault ya diseñado en `docs/ops/obsidian-context-vault.md` con una carpeta de material generado. La integración con Rick queda como **diseño futuro** (MCP read-only sobre `graph.json` filtrado), sin tocar VPS ni runtime. Go/no-go tras Fase 4 con un gold-set de 10 preguntas verificables y coste LLM medido en `cost.json`. El repo sí justifica el intento: 115 handlers, ~410 docs con duplicación y 266 tareas históricas hacen que el mapa estructural tenga valor real — pero exactamente esa masa documental es la que exige medir ruido y drift antes de convertir el grafo en artefacto compartido.

---

## 2. Diagnóstico técnico del repositorio

**Por qué sí se beneficia:**

- **Complejidad real multi-plane.** Control Plane (VPS) + Execution Plane (VM) + Rick + Dispatcher + Worker + Redis + Notion. Las relaciones entre módulos (`dispatcher/router.py` → `worker/app.py` → `worker/tasks/*` → `worker/models/`) no son visibles leyendo archivos sueltos; un call/import graph las expone directo.
- **Documentación masiva y fragmentada.** ~410 `.md` en `docs/` (numeradas 03–79 + `ops/` + `adr/` + `audits/` + `editorial-pipeline/` + `runbooks/` duplicados con `runbooks/` raíz). Hoy encontrar "qué doc describe el modo degradado" es grep + suerte; la pasada semántica de Graphify vincula doc↔código.
- **Coordinación multi-agente file-based que fuerza relectura.** Cada sesión de Cursor/Codex relee `board.md` (500+ líneas), `PROTOCOL.md` y tareas. Un `GRAPH_REPORT.md` de una página reduce la relectura de contexto estructural.
- **Trazabilidad exigida por diseño.** El stack ya opera con trace_id, gates y bitácoras; un grafo con nodos código+doc+runbook encaja culturalmente.
- **Análisis de impacto débil hoy.** "¿Qué toco si cambio Notion Bridge?" requiere conocer `docs/18`, `worker/tasks/notion.py` (1.609 líneas), `dispatcher/notion_poller.py` (665 líneas) y los schemas de `notion/`. Es el caso de uso estrella.

**Por qué con cautela:**

- **Drift estructural ya existente.** Runbooks duplicados, docs numeradas con solapes, 266 tareas históricas: el grafo fotografía el desorden además del orden. Sin ignores curados, el ruido puede superar la señal.
- **Frecuencia de cambios alta** (commits diarios multi-agente). El `cache/` incremental SHA256 mitiga el coste de regeneración, pero un `graph.json` versionado se desactualizaría en días → por eso no se versiona en piloto.
- **Solape parcial con capacidades existentes.** Cursor/Codex ya tienen grep/semantic search, y el repo ya tiene RAG propio (`worker/rag/`). El valor diferencial de Graphify está en **relaciones** (grafo de llamadas, dependencias, doc↔código, comunidades Leiden), no en búsqueda por keyword. Si el piloto solo replica grep, se descarta.

---

## 3. Casos de uso para desarrollo asistido por IA

Gold-set de preguntas para el piloto (todas verificables contra el repo real — la respuesta correcta se conoce de antemano):

| # | Pregunta | Respuesta esperada (verificación) |
|---|----------|-----------------------------------|
| 1 | ¿Qué archivos participan en el flujo TaskEnvelope? | `worker/models/__init__.py`, `worker/app.py`, `dispatcher/router.py`, `docs/07-worker-api-contract.md` |
| 2 | ¿Dónde se conecta Dispatcher con Worker? | `dispatcher/service.py`/`router.py` → HTTP `worker/app.py` :8088 (Bearer `WORKER_TOKEN`) |
| 3 | ¿Qué módulos dependen de Redis? | `dispatcher/` (cola/estado), quota, rate limiting; ver `docs/15-model-quota-policy.md` |
| 4 | ¿Qué documentación describe el modo degradado / dual worker? | `docs/21-vps-autosufficient-dual-worker.md`, `docs/32-vps-vm-dual-session-control.md` |
| 5 | ¿Qué archivos reviso antes de cambiar Notion Bridge? | `docs/18-notion-enlace-rick-convention.md`, `worker/tasks/notion.py`, `dispatcher/notion_poller.py`, `notion/schemas/` |
| 6 | ¿Qué relaciones hay entre Rick, ModelRouter y TeamRouter? | `worker/tasks/rick_orchestrator.py`, `worker/models/`, `config/teams*.yaml`, tests de routing |
| 7 | ¿Qué handlers del worker tocan el pipeline editorial? | `editorial_publish.py` (publish/unpublish), granola, notion |
| 8 | ¿Dónde está definida la política de cuotas de modelos? | `docs/15-model-quota-policy.md` + config + quota-guard |
| 9 | ¿Qué runbook aplico si el gateway OpenClaw cae? | runbooks raíz + skill `openclaw-vps-operator` |
| 10 | ¿Qué scripts publican al blog editorial de Azure? | `functions/editorial-publish/`, `scripts/smoke-*-editorial-post.ps1`, `worker/tasks/editorial_publish.py` |

Ganancia esperada por tipo de tarea: **debugging** (mapa de dependencias antes de tocar), **onboarding** (GRAPH_REPORT como primer contexto en vez de leer 20 docs), **análisis de impacto** (`graphify path "notion_poller" "editorial_publish"`), **reducción de contexto** (subgrafo scoped en vez de dump de archivos completos al LLM).

---

## 4. Casos de uso para navegación humana con Obsidian

**Hallazgo clave:** el repo ya decidió esto en `docs/ops/obsidian-context-vault.md` — vault **externo**, repo git privado, mirror VPS pull-only, y regla explícita "complementary context vault, not source of truth". La propuesta correcta no es crear `Umbral Knowledge/` desde cero sino **extender el vault existente**:

```text
<vault existente (obsidian-context-vault.md)>/
├─ 00_inbox/                      # ya definido
├─ 10_decisiones/                 # ya definido — MOCs curados a mano
├─ 20_reuniones/                  # ya definido
├─ 30_investigacion/              # ya definido
├─ 35_generated/                  # ← NUEVO (esta evaluación)
│  └─ graphify-umbral-agent-stack/
│     ├─ GRAPH_REPORT.md          # copiado por script tras cada regeneración
│     ├─ moc-arquitectura.md      # generado desde el grafo, no editado a mano
│     └─ freshness.md             # SHA de main + fecha de generación
├─ 40_runbooks/                   # ya definido — enlaces al repo, no copias
└─ 90_evals/                      # ya definido
```

**Generado automáticamente (no se edita a mano):** todo lo de `35_generated/` — se sobrescribe en cada regeneración; drift imposible por definición.

**Curado manualmente:** MOCs en `10_decisiones/` y `30_investigacion/` que **enlazan** a rutas del repo y a páginas Notion — nunca copian contenido. Regla dura anti-duplicación (alineada con la gobernanza `notion-governance`): *Notion sigue siendo el runtime humano canónico; el vault es grafo de contexto técnico privado; nada en el vault es fuente de verdad*.

**Qué NO hacer con Obsidian:** meter el vault dentro del repo, copiar docs del repo al vault (drift garantizado), duplicar dashboards Notion, o indexar el vault con Graphify en el piloto (el vault puede contener notas privadas de David).

---

## 5. Casos de uso futuros para Rick

**Solo diseño — nada de esto se implementa ahora.**

| Vía | Cómo sería | Pro | Contra |
|-----|-----------|-----|--------|
| **MCP (preferida)** | `graphifyy[mcp]` sirve `graph.json` read-only; OpenClaw ya está soportado por Graphify (`--platform claw`) | Sin código nuevo; scoped queries; read-only por diseño | Expone rutas internas y nombres de módulos al agente; requiere revisión de contenido del grafo |
| ChromaDB (RAG existente) | Chunks de `GRAPH_REPORT.md` + descripciones de nodos indexados vía `rag.index` | Reusa `worker/rag/`; búsqueda híbrida grafo+vector | Duplica memoria; hay que definir refresh |
| Notion | Publicar un resumen del GRAPH_REPORT como system card | Visible para David | No consultable programáticamente en detalle |
| LangGraph tool | Tool `repo.graph_query` en el runtime | Integración nativa | Acopla runtime a un artefacto de dev — exactamente lo que queremos evitar en v0 |

**Separación de memorias (obligatoria antes de exponer nada a Rick):**

- **Memoria técnica de repo** = `graph.json` (código + docs) — candidata a exponerse filtrada.
- **Memoria declarativa** = Notion — ya existe, no se toca.
- **Memoria operativa** = Redis + ops_log — no entra al grafo.
- **Memoria conversacional** = sesiones OpenClaw (`**/sessions/`) — **jamás** se indexa (ya excluida por gitignore heredado).

**Gates previos a cualquier exposición a Rick:** (1) piloto aprobado; (2) revisión humana del contenido de `graph.json` buscando rutas/nombres sensibles; (3) decisión explícita de David registrada en `.agents/board.md`; (4) el MCP corre local o en VPS con el mismo trust boundary que el worker — nunca público.

---

## 6. Comparativa de opciones

| Opción | Descripción | Beneficios | Riesgos | Esfuerzo | Impacto esperado | Recomendación |
|--------|-------------|------------|---------|----------|------------------|---------------|
| 1. Solo desarrollo local | Global via `uv tool`; cada agente genera su grafo; nada se commitea; Obsidian manual externo | Riesgo mínimo; cero fricción de repo; validación real | Cada máquina paga su coste LLM de indexación; grafos divergentes entre agentes; sin beneficio compartido | Bajo | Medio (solo quien lo ejecuta) | ✅ **Como fase inicial** |
| 2. Artefacto compartido | Se versionan `graph.json` y/o `GRAPH_REPORT.md`; cache/cost/html ignorados | Un solo coste de generación; mapa común Cursor/Codex/Claude/Copilot; onboarding instantáneo | Drift (repo cambia a diario); merges ruidosos de JSON; peso del repo; "mapa viejo" peor que sin mapa | Medio | Alto si se mantiene fresco | ⏸ Solo post-piloto, empezando por `GRAPH_REPORT.md` (no `graph.json`) |
| 3. Vault Obsidian central | Vault externo con export de Graphify + MOCs curados | Navegación humana para David; ya hay diseño previo en el repo; separación generado/curado | Tercera superficie de memoria → riesgo de duplicar Notion; mantenimiento manual de MOCs | Bajo-medio | Medio (humano, no agentes) | ✅ Extender vault existente, carpeta `35_generated/` |
| 4. Integración futura Rick | `graph.json` consultable vía MCP/ChromaDB por agentes | Rick respondería arquitectura/módulos/runbooks con fuente estructural | Exposición de información interna; acoplar runtime a artefacto dev; seguridad sin resolver | Alto | Alto (si el piloto valida calidad) | 📋 Solo diseño ahora; gates de seguridad primero |
| 5. **Híbrida (recomendada)** | 1 → 3 → 2 → 4 en fases con go/no-go | Captura valor incremental; cada fase valida la siguiente; reversible en todo punto | Requiere disciplina de fases (no saltarse el piloto) | Incremental | Alto acumulado | ✅ **Adoptar** |

---

## 7. Recomendación principal

**Opción 5 — estrategia híbrida por fases con go/no-go explícito:**

1. **Fase inicial (ahora, 1–2 semanas):** piloto local en la workstation Windows de David. `uv tool install graphifyy`, `.graphifyignore` primero, `graphify . --no-viz`, gold-set de 10 preguntas, coste medido. **Sin `graphify install`, sin hooks, sin commits de artefactos.**
2. **Fase secundaria:** si el gold-set pasa (≥7/10), export a la carpeta `35_generated/` del vault Obsidian ya diseñado + 2–3 MOCs curados.
3. **Fase posterior:** decidir versionado — el candidato es **solo `GRAPH_REPORT.md`** con freshness stamp (SHA de main embebido), regenerado manualmente por Cursor en cada cierre de frente; `graph.json` se queda local/regenerable (drift y peso lo descartan como artefacto git en este repo de cambio diario).
4. **Fase futura:** diseño de seguridad para exponer el grafo a Rick vía MCP read-only, con revisión de contenido y firma de David.

**Justificación:** el repo tiene la complejidad y la masa documental que justifican un grafo (115 handlers, 410 docs, arquitectura multi-plane), pero también las dos condiciones que matan grafos versionados: cambio diario y duplicación documental previa. La única forma honesta de decidir es medir con preguntas verificables antes de comprometer artefactos compartidos o runtime. Además, el backend LLM debe ser **Azure OpenAI del tenant Umbral** (`--backend azure`), manteniendo la extracción semántica dentro del mismo trust boundary que ya usa el stack.

---

## 8. Plan piloto propuesto

| Fase | Qué | Owner | Gate de salida |
|------|-----|-------|----------------|
| **F0 — Revisión previa** | Hecho en esta evaluación: README, AGENTS.md, `.gitignore`, docs 14/15/18/21/22/32, estructura, superficies sensibles | Cursor | ✅ Este documento |
| **F1 — Instalación local** | `uv tool install "graphifyy[openai]"` en workstation Windows (NO en VPS, NO en pyproject). Verificar `graphify --version` | David | CLI responde |
| **F2 — Generación local** | Crear `.graphifyignore` (§9) **antes** de la primera pasada. `graphify . --no-viz --backend azure`. Revisar `cost.json` y tamaño de `graph.json`. Nada se commitea | David + Cursor | Grafo generado; coste anotado; spot-check de que ningún nodo contiene material sensible |
| **F3 — Preguntas reales** | Gold-set §3 (10 preguntas) vía `graphify query` / `graphify path`. Registrar aciertos y tiempo vs baseline grep | Cursor | Resultados registrados |
| **F4 — Evaluación de calidad** | Métricas §12. **Go/no-go:** ≥7/10 gold-set + coste de regeneración aceptable + cero fugas sensibles en el grafo | David | Decisión escrita en `.agents/board.md` |
| **F5 — Integración Cursor/Codex** | Si GO: redactar guidance **manualmente** en `AGENTS.md` (patrón: "el grafo orienta, el archivo manda" — análogo a VPS Reality Check). **No** ejecutar `graphify install` automático; **no** hooks | Cursor | PR revisado por David |
| **F6 — Obsidian** | Export de `GRAPH_REPORT.md` + MOC generado a `35_generated/` del vault existente. MOCs curados solo con enlaces | David | Vault navegable; cero copias de contenido |
| **F7 — Versionado** | Decidir con datos: `.graphifyignore` ya versionado; evaluar commitear solo `GRAPH_REPORT.md` + script de regeneración; `graph.json`/`cache/`/`cost.json`/`graph.html` nunca | Cursor + David | Decisión en board + ADR corto si se versiona |
| **F8 — Diseño Rick** | Documento de diseño MCP read-only (sin implementar): superficie, filtrado, trust boundary, gates | Cursor | ADR de diseño, sin código |

---

## 9. `.graphifyignore` recomendado

Contexto: Graphify **hereda `.gitignore`** (que ya excluye `.env`, `*.env`, `env.rick`, `openclaw/env`, `**/auth-profiles.json`, `**/sessions/`, logs, `.openclaw/`, `.agents/board.md`, snapshots). Este archivo añade defensa en profundidad y control de ruido:

```gitignore
# ============================================================
# .graphifyignore — umbral-agent-stack (piloto v0, 2026-07)
# Graphify hereda .gitignore (merge; este archivo gana y solo
# puede excluir más). Capa 1 = .gitignore; capa 2 = esto.
# ============================================================

# --- OBLIGATORIO: secretos (redundante con .gitignore a propósito:
# --- protege clones con .gitignore alterado o archivos ya trackeados)
.env
*.env
env.rick
openclaw/env
**/auth-profiles.json
**/sessions/
**/*.pem
**/*.key
**/token*.json

# --- OBLIGATORIO: estado local de asistentes IDE/agentes
.claude/
.cursor/
.codex/
.openclaw/
.vscode/
.idea/

# --- OBLIGATORIO: salida de graphify (no auto-indexarse) y cachés
graphify-out/
__pycache__/
.pytest_cache/
.venv/
venv/
node_modules/
dist/
build/
*.egg-info/
.cache/
.coverage

# --- OBLIGATORIO: logs, evidencia, reportes generados, snapshots
*.log
logs/
reports/
artifacts/
mission_control/snapshots/
docs/ops/evidence-imports/
docs/audits/*.json

# --- OPCIONAL (recomendado en v0; revisar en F4 si quitan señal útil)
.agents/tasks/          # 266 tareas históricas = ruido dominante
.agents/prompts-*       # series de prompts Codex archivadas
docs/external-context/  # dumps externos (n8n-llms-full.txt, etc.)
tests/fixtures/         # fixtures binarias/logs de test
*.png
*.pdf
*.zip
*.pptx
```

**Obligatorias:** secretos, estado de asistentes, `graphify-out/`, cachés, logs/evidencia/reportes. Sin esto no se ejecuta la primera pasada.  
**Opcionales:** el bloque final. Recomiendo empezar **con** ellas (grafo limpio) y en F4 probar una pasada incluyendo `.agents/tasks/` para medir si las tareas históricas aportan trazabilidad o solo ruido.  
**Se queda dentro del grafo (deliberado):** `.env.example` y `env.template` (documentan configuración, sin valores), `tests/` (documentan comportamiento), `runbooks/`, `docs/` operativas, `.agents/PROTOCOL.md` y `.agents/skills/`.

---

## 10. Archivos a versionar / ignorar

| Archivo / carpeta | ¿Versionar? | Motivo |
|-------------------|-------------|--------|
| `.graphifyignore` | **Sí, desde el día 1** | Contrato de seguridad del indexado; barato; útil aunque el piloto falle |
| `graphify-out/graph.json` | **No** (revisar en F7, tendencia: no) | Cambia con cada commit del repo; pesado; diffs JSON inútiles; regenerable con `cache/` |
| `graphify-out/GRAPH_REPORT.md` | **No en piloto** → candidato sí en F7 | Legible, diffable, útil para todos los agentes; solo con freshness stamp (SHA main) y cadencia de regeneración definida |
| `graphify-out/graph.html` | **No, nunca** | Visualización pesada, regenerable |
| `graphify-out/cache/` | **No, nunca** | Caché local SHA256 |
| `graphify-out/cost.json` | **No, nunca** | Dato local de coste (el propio README lo marca local-only) |
| `.codex/` | **No** | No existe hoy; los hooks que `graphify install` crearía no están autorizados |
| `.cursor/rules/graphify.mdc` | **No en piloto** | Lo escribiría `graphify install`; requiere revisión de compatibilidad con `agent-coordination.mdc` antes de considerar versionarlo (F5) |
| `.agents/skills/graphify/` | **Sí, post-piloto** | Skill curada a mano con guidance de uso (query-first, verificar en archivo real) — mejor vehículo que tocar AGENTS.md agresivamente |
| Notas Obsidian exportadas | **No en este repo** | Van al vault externo (git privado propio, ya diseñado) |
| Vault Obsidian completo | **No, nunca en este repo** | Superficie personal de David; mezclaría memorias |

---

## 11. Riesgos y mitigaciones

| # | Riesgo | Mitigación |
|---|--------|------------|
| 1 | Indexación accidental de secretos | Doble capa `.gitignore` heredado + `.graphifyignore` redundante; correr `scripts/secrets_audit.py` antes de F2; spot-check manual de `graph.json` en F2; skill `secret-output-guard` vigente |
| 2 | Exfiltración semántica a LLM externo (pasada 2 envía contenido de docs) | Backend `--backend azure` con Azure OpenAI del tenant Umbral (mismo trust boundary del stack); si no está disponible, limitar pasada semántica o aceptar mismo trust class que Cursor/Codex ya tienen |
| 3 | Exposición de rutas internas / nombres de infra en el grafo | Aceptable mientras el grafo sea local/privado; gate de revisión de contenido antes de exponer a Rick (F8) o versionar (F7) |
| 4 | Ruido por archivos generados y tareas históricas | Bloque opcional del `.graphifyignore` (tasks/, prompts-*, fixtures, external-context) |
| 5 | Drift entre grafo y repo | No versionar `graph.json`; freshness stamp en todo artefacto compartido; regeneración manual con cadencia definida (cierre de frente); `cache/` hace la regen barata |
| 6 | Dependencia excesiva de Graphify | Regla escrita en la skill: "el grafo orienta, el archivo manda" — toda respuesta crítica se verifica contra el archivo real (análogo a VPS Reality Check Rule) |
| 7 | Conflictos con `AGENTS.md` / reglas de agentes | **No ejecutar `graphify install`** en piloto; integración manual revisada en F5; los hooks PreToolUse quedan prohibidos hasta decisión explícita |
| 8 | Aumento de peso del repo | Solo `.graphifyignore` (+ eventualmente `GRAPH_REPORT.md`, texto plano) se versiona |
| 9 | Artefactos obsoletos engañando a agentes ("mapa viejo") | Freshness stamp + instrucción en skill: si SHA del grafo ≠ HEAD, tratar el grafo como orientativo |
| 10 | Confusión memoria dev vs memoria runtime | Separación explícita §5; el grafo jamás entra a Redis/Notion/ChromaDB en piloto; ADR requerido para cambiarlo |
| 11 | Filtración de información sensible a agentes vía MCP futuro | F8 con gates: revisión de contenido, filtrado de nodos, trust boundary = worker, firma de David |
| 12 | Coste LLM de indexar ~410 docs | F2 mide `cost.json` en la primera pasada; si excede presupuesto, indexar código-only (pasada AST es gratis) + subset de docs core (docs numeradas + adr + runbooks) |
| 13 | Duplicar el diseño Obsidian existente | Esta evaluación adopta `obsidian-context-vault.md` como base; cualquier cambio de estructura del vault se hace ahí, no en un vault paralelo |

---

## 12. Métricas de éxito

Baseline: medir 1 semana de trabajo normal **antes** del piloto (o estimar con sesiones recientes).

| Métrica | Cómo se mide | Target piloto |
|---------|--------------|---------------|
| Tiempo para localizar archivos relevantes a una pregunta | Cronometrar gold-set con grep vs con `graphify query` | −50 % |
| Archivos leídos antes de responder | Conteo de reads por pregunta del gold-set | ≤3 con grafo (vs 6–10 típico) |
| Precisión en preguntas de arquitectura | Gold-set §3 contra respuestas verificadas | ≥7/10 |
| Reducción de búsquedas manuales (grep/glob) | Conteo por sesión de agente | −30 % |
| Reducción de tokens/contexto | Tokens de contexto por respuesta arquitectural | −20 % |
| Calidad de análisis de impacto | "¿Qué toco si cambio X?" — completitud vs lista real de dependencias | 0 dependencias críticas omitidas en 3 casos |
| Onboarding | Tiempo para que un agente nuevo responda las 10 preguntas | <30 min con GRAPH_REPORT |
| Errores por desconocimiento del repo | Incidencias en PRs por dependencia no vista | Tendencia a 0 |
| Utilidad percibida Cursor/Codex | Registro cualitativo por sesión (¿el grafo cambió la ruta de trabajo?) | Positiva en ≥60 % de usos |
| Frescura del grafo | `HEAD` vs SHA embebido en el artefacto | ≤7 días o regen en cierre de frente |
| **Coste** (añadida) | `cost.json` por regeneración completa e incremental | Umbral fijado por David en F2 |

---

## 13. Comandos de prueba sugeridos

**Windows PowerShell (workstation David — piloto):**

```powershell
# F1 — instalación global aislada (NO en pyproject, NO en VPS)
uv tool install "graphifyy[openai]"
# si 'graphify' no aparece: uv tool update-shell y abrir nueva terminal
graphify --version

# F2 — preparar repo (rama solo para el .graphifyignore; artefactos NO se commitean)
cd C:\GitHub\umbral-agent-stack-copilot
git checkout -b codex/graphify-obsidian-eval
# crear .graphifyignore (§9) ANTES de la primera pasada
graphify . --no-viz --backend azure   # requiere AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT en la sesión
# revisar coste y tamaño:
Get-Item graphify-out\graph.json | Select-Object Length
Get-Content graphify-out\cost.json

# F3 — gold-set
graphify query "explica la arquitectura Control Plane y Execution Plane"
graphify query "qué archivos participan en el flujo TaskEnvelope"
graphify query "cómo se conecta Dispatcher con Worker"
graphify query "qué módulos usan Redis"
graphify query "qué documentación explica Notion Bridge"
graphify query "qué archivos debo revisar antes de cambiar el Worker"
graphify query "qué handlers publican o despublican posts del blog editorial"
graphify path "dispatcher/notion_poller.py" "worker/tasks/editorial_publish.py"
graphify explain "worker/models"

# higiene — confirmar que nada generado quedó staged
git status
git diff
```

**Linux/WSL (solo si el piloto Windows pasa y se quiere replicar; NUNCA en la VPS de producción en piloto):**

```bash
uv tool install "graphifyy[openai]"
cd ~/umbral-agent-stack && graphify . --no-viz --backend azure
```

**Referencia futura (F8, no ejecutar ahora):** `python -m graphify.serve graphify-out/graph.json` — MCP server read-only para agentes.

**Explícitamente NO ejecutar en piloto:** `graphify install` (modifica `AGENTS.md` y `.cursor/rules/`), `graphify hook install` (hook post-commit), cualquier ejecución en VPS.

---

## Anexo A — Respuestas directas a las 20 preguntas

| # | Pregunta | Respuesta corta |
|---|----------|-----------------|
| 1 | ¿Global o dependencia del repo? | **Global** (`uv tool install graphifyy`), en workstation Windows (+ opcional WSL/VM dev). Jamás en `pyproject.toml`: no es runtime del stack |
| 2 | ¿Dev, doc o runtime? | **Herramienta de desarrollo.** Sus outputs son documentación derivada regenerable. Runtime: solo diseño futuro con gates (F8) |
| 3 | ¿Generar `graph.json`? | **Sí**, localmente en piloto |
| 4 | ¿Versionar `graph.json`? | **No** en piloto; tendencia a **no** también en F7 (drift diario + peso + diffs inútiles); compartir vía regeneración con cache |
| 5 | ¿Versionar `GRAPH_REPORT.md`? | No en piloto; **candidato sí** en F7 con freshness stamp y cadencia de regeneración |
| 6 | ¿Qué ignorar de `graphify-out/`? | Todo por defecto (`graphify-out/` completo en `.gitignore`); si F7 aprueba, allowlist solo `GRAPH_REPORT.md` |
| 7 | ¿Artefacto compartido entre agentes? | Sí **después** del piloto, empezando por GRAPH_REPORT; con regla "grafo orienta, archivo manda" |
| 8 | ¿Exportar a Obsidian? | Sí, opcional, en F6 |
| 9 | ¿Obsidian en repo o externo? | **Externo** — ya está decidido en `docs/ops/obsidian-context-vault.md`; se extiende, no se duplica |
| 10 | ¿Qué excluir en `.graphifyignore`? | §9 — secretos, estado de asistentes, generated/cachés, logs/evidencia (obligatorio); tasks históricos/fixtures/dumps externos (opcional) |
| 11 | ¿Cómo evitar indexar secretos? | Herencia automática de `.gitignore` + `.graphifyignore` redundante + `secrets_audit.py` pre-pasada + spot-check de `graph.json` + backend Azure propio |
| 12 | ¿Impacto en AGENTS.md / .agents / reglas? | Nulo en piloto (prohibido `graphify install`). Post-piloto: skill `.agents/skills/graphify/` + párrafo manual en AGENTS.md revisado por David |
| 13 | ¿Beneficios para Control/Execution Plane, Rick, Dispatcher, Worker? | Mapa de dependencias entre planes; ruta Dispatcher→Worker→handlers visible; análisis de impacto antes de tocar `worker/app.py` (115 handlers) |
| 14 | ¿Beneficios para Notion Bridge, Redis, LangGraph, ChromaDB, Langfuse? | Vincula doc↔código (docs/18 ↔ notion.py de 1.609 líneas ↔ poller); expone qué módulos consumen Redis; muestra qué es dependencia real vs aspiracional |
| 15 | ¿Beneficios para TaskEnvelope, ModelRouter, TeamRouter? | Son los nodos más conectados del grafo (contrato central + routing); cambios ahí son los de mayor blast radius — el grafo lista consumidores exactos antes de editar |
| 16 | ¿Riesgos producción/seguridad/privacidad/consistencia? | §11 — los críticos: exfiltración semántica (mitigada con backend Azure), secretos (doble capa), drift (no versionar), doble memoria (gobernanza) |
| 17 | ¿Cómo medir eficiencia? | §12 — gold-set 10 preguntas + tiempo + archivos leídos + tokens + coste |
| 18 | ¿Plan piloto? | §8 — F0 a F8 con go/no-go en F4 |
| 19 | ¿Cambios mínimos al repo? | **Uno solo ahora:** `.graphifyignore` (+ este doc de evaluación). Post-piloto: skill graphify + párrafo AGENTS.md + posible GRAPH_REPORT versionado |
| 20 | ¿Qué NO hacer todavía? | Anexo B |

## Anexo B — Qué NO hacer todavía

1. **No** ejecutar `graphify install` ni `graphify hook install` (modifican `AGENTS.md`, `.cursor/rules/`, hooks git).
2. **No** commitear `graphify-out/` (nada de graph.json/html/cache/cost).
3. **No** instalar Graphify en la VPS ni exponerlo a Rick/OpenClaw (F8 es diseño, no implementación).
4. **No** crear un vault Obsidian nuevo ni meterlo al repo — extender el existente.
5. **No** indexar `**/sessions/`, logs, dumps, evidencia, `.env` ni el vault de David.
6. **No** reemplazar RAG (`worker/rag/`), Notion, Redis ni Langfuse — Graphify es capa de orientación, no de estado.
7. **No** convertir el grafo en fuente de verdad: ante conflicto grafo vs archivo, gana el archivo; ante conflicto doc vs código, se flaggea (regla de gobernanza existente).
8. **No** añadir `graphifyy` a `pyproject.toml` ni a `worker/requirements.txt`.
