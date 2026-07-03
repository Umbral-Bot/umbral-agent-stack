# Plan piloto Graphify — umbral-agent-stack

> **Versión:** UAS-GRAPHIFY-PILOT-PLAN-v1  
> **Fecha:** 2026-07-02  
> **Base:** `docs/ops/graphify-obsidian-eval-2026-07-02.md` (UAS-GRAPHIFY-OBSIDIAN-EVAL-v0.2)  
> **Estado:** plan aprobable — nada ejecutado; arranca solo con firma G-GR-0 de David  
> **Task file:** `.agents/tasks/2026-07-02-002-graphify-pilot-f1-f4.md`

---

## 1. Encaje en el sistema de trabajo

| Rol | Responsabilidad en el piloto |
|-----|------------------------------|
| **David** | Firma gates (G-GR-0/G-GR-1); abre portal Azure Keys si F2 no tiene vars en sesión; valida spot-check scoring. Carga humana **< 1 h** |
| **Copilot Windows** | Ejecuta F1–F4 completo: sync repo, `.graphifyignore`, grafo, auditoría, gold-set A+B, decisión F4, PR. Modelo sesión: **Fable 5 · 1M** |
| **Cursor (lead)** | Bitácora/board; no ejecuta el piloto salvo desbloqueo |
| **Copilot-VPS** | **Fuera del piloto** (regla dura: nada en VPS — aunque vuelva a estar accesible) |
| **Codex** | Fuera de ejecución del piloto (supersedido por Copilot Windows 2026-07-02) |
| **Rick / OpenClaw** | **Fuera del piloto** (F8 es solo diseño) |

**Superficie:** workstation Windows de David, clone `C:\GitHub\umbral-agent-stack-copilot`, rama `copilot/graphify-pilot-f1-f4`.

**Gates de firma (análogo G-D1a):**

| Gate | Qué autoriza | Firma |
|------|-------------|-------|
| **G-GR-0** | Arrancar F1–F2 (instalar tool global + generar grafo local) | David pega el prompt de arranque (§7) |
| **G-GR-1** | Decisión F4: GO / GO parcial / NO-GO | David explícita, registrada en board |
| **G-GR-2** | Cualquier write post-piloto a `AGENTS.md`, `.cursor/rules/`, skill, versionado de artefactos | David por PR |
| **G-GR-3** | Exposición futura a Rick/MCP | David + ADR |

**Agenda:** el piloto no compite con el cutover Azure del 7-jul (programa umbral-bot). Recomendación: **no ejecutar F1–F2 el mismo día del cutover**; cualquier otro hueco sirve. Ventana de validez del piloto: **2 semanas desde G-GR-0**; si no se ejecuta, la tarea pasa a `blocked: no priorizado` (no dejar zombie).

---

## 2. Presupuestos y kill-switches (fijados de antemano)

| Límite | Valor | Al excederse |
|--------|-------|--------------|
| Tiempo humano David | ~1 h total | Recortar alcance, no extender |
| Sesiones de agente | 1 Copilot Windows (F1–F4 + gold-set A/B) | No añadir sesiones para "una prueba más" |
| Coste LLM primera pasada | Umbral lo fija David en F2 **antes** de correr (default sugerido: **USD 10**) | Directriz R2 (code-only) |
| Iteraciones de `.graphifyignore` | **Máximo 2** pasadas totales | Decisión forzada con lo que haya (R3) |
| Timebox calendario | 14 días desde G-GR-0 | Archivar como no priorizado |
| Fugas de secretos | **0 tolerancia** | R0 — STOP inmediato |

---

## 3. Fases detalladas F1–F4

### F1 — Instalación (David, ~10 min)

1. `uv tool install "graphifyy[openai]"` (si falta `uv`: instalarlo primero o usar `pipx`).
2. `graphify --version` responde.
3. **Prohibido:** `graphify install`, `graphify hook install`, tocar `pyproject.toml`.

**Salida:** CLI operativa. Si falla → directriz **R5**.

### F2 — Preparación + primera pasada (David ejecuta, Cursor prepara, ~20 min)

1. Cursor crea rama `cursor/graphify-pilot` + `.graphifyignore` (§9 de la evaluación) — **único archivo destinado a commit** en el piloto.
2. David fija el **umbral de coste** y exporta `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` en la sesión (no en archivos).
3. `graphify . --no-viz --backend azure`
4. Anotar: tamaño de `graph.json`, `cost.json`, duración.
5. **Auditoría de seguridad del grafo** (obligatoria antes de F3):

```powershell
# Valores con formato de secreto (nombres de vars desde .env.example son legítimos; VALORES no)
rg -i "sk-[a-z0-9]{20,}|ghp_[a-z0-9]{20,}|bearer [a-z0-9]{20,}|password.{0,4}[:=]" graphify-out\graph.json
# Paths que jamás deberían aparecer como nodos
rg -c "\\.env\"|sessions/|auth-profiles" graphify-out\graph.json
```

**Salida esperada (veredicto):** `GRAPHIFY_PILOT_READY | nodes=N | cost=$X | leaks=0`  
Si la auditoría encuentra algo → **R0**. Si coste > umbral → **R2**.

### F3 — Gold-set A/B (agentes, sin David)

Gold-set: las **10 preguntas con respuesta verificada** de la evaluación §3 (no se duplican aquí).

- **Brazo A (Cursor, graph-first):** responder usando primero `graphify query` / `path` / `explain`; máximo 2 lecturas de archivo por pregunta para verificar. Registrar por pregunta: respuesta, nº de queries, nº de archivos leídos, tiempo aproximado.
- **Brazo B (Copilot Windows, baseline):** mismas preguntas con grep/glob/read normales, sin grafo ni `graphify query`. Mismos registros en la misma sesión, después del brazo A.

**Scoring (Cursor puntúa, David spot-checkea 2–3):** 1 = correcta y completa · 0.5 = parcial · 0 = incorrecta, contra la tabla verificada de la evaluación.

### F4 — Evaluación y decisión (Cursor propone, David firma G-GR-1)

Se calculan las 5 variables de resultado y se aplica la matriz de §4. La decisión queda en el board con veredicto estándar:

```
GRAPHIFY_PILOT_GO         | goldset=X/10 | cost=$Y | leaks=0 | escenario=S1
GRAPHIFY_PILOT_GO_PARTIAL | goldset=X/10 | motivo=...
GRAPHIFY_PILOT_NOGO       | motivo=...
GRAPHIFY_PILOT_BLOCKED    | motivo=...
```

---

## 4. Variables de resultado y matriz de escenarios

### Variables (medidas en F2–F3)

| Var | Qué mide | Niveles |
|-----|----------|---------|
| **P** | Precisión gold-set brazo A | alta ≥ 8/10 · media 6–7 · baja ≤ 5 |
| **C** | Coste primera pasada vs umbral David | ok · alto |
| **S** | Seguridad (auditoría F2 + revisión F3) | limpio · fuga |
| **U** | Utilidad diferencial vs brazo B | positiva (A lee menos archivos y tarda menos que B) · nula/negativa |
| **O** | Fricción operativa (regen incremental) | ligera < 5 min · pesada |

### Directrices predefinidas (se ejecutan sin re-consultar, salvo donde se indica firma)

| Regla | Condición | Acción automática |
|-------|-----------|-------------------|
| **R0 — kill-switch seguridad** | S = fuga en cualquier momento | **STOP.** Purgar `graphify-out\` completo, corregir `.graphifyignore`, re-auditar. Máx **1 reintento**; si reincide → `NOGO` por seguridad sin excepción. Reportar a David siempre (el purge no espera firma; el reintento sí) |
| **R1 — GO pleno** | P alta + C ok + S limpio + U positiva | Cursor propone GO; David firma G-GR-1; pasar a post-piloto rama GO (§5) |
| **R2 — recorte de alcance por coste** | C alto (o `cost.json` roto/ilegible → tratar como alto) | Repetir pasada **code-only + docs core** (`docs/[0-9]*.md`, `docs/adr/`, `runbooks/`; excluir resto de docs). La pasada AST es gratis; solo se recorta la semántica. Cuenta como iteración 2 de ignores |
| **R3 — precisión media** | P media | **1 iteración** de `.graphifyignore` (ajustar bloque opcional según fallos observados) + re-run solo de las preguntas falladas. Si sigue media: U positiva → GO parcial; U nula → NOGO |
| **R4 — precisión baja** | P baja | **NOGO directo.** No iterar más (anti rabbit hole). Escribir cierre y alternativas (§5 rama NO-GO) |
| **R5 — fallo técnico** | Instalación/ejecución falla en Windows | **1 reintento** en WSL. Si falla → `BLOCKED`, issue upstream si aplica, re-evaluar en la siguiente release de `graphifyy`. No hackear workarounds |
| **R6 — utilidad nula con precisión alta** | P alta pero U nula/negativa (el grafo acierta pero no ahorra nada vs grep) | GO parcial como techo: uso opcional por agente, **sin** artefactos compartidos ni skill |
| **R7 — frontera de firma** | Cualquier acción que toque `AGENTS.md`, `.cursor/rules/`, skill, versionado, VPS o Rick | **Siempre** gate David (G-GR-2/G-GR-3), en todos los escenarios, sin excepción |

### Escenarios compuestos → resultado

| Escenario | Combinación | Directriz | Resultado |
|-----------|-------------|-----------|-----------|
| **S1** | P alta · C ok · S limpio · U positiva | R1 | **GO pleno** → post-piloto completa |
| **S2** | P alta · C alto | R2 → re-medir | GO con alcance code-only+docs core si la re-pasada queda en umbral |
| **S3** | P media (ruido de docs/tasks) | R3 | GO parcial o NOGO según segunda medición |
| **S4** | Fuga en grafo | R0 | STOP → 1 reintento → GO/NOGO según re-auditoría |
| **S5** | P baja | R4 | **NOGO** + capitalización |
| **S6** | Fallo técnico Windows | R5 | BLOCKED / posponer |
| **S7** | P alta · U nula | R6 | **GO parcial** (uso personal opcional, sin compartir) |
| **S8** | O pesada (regen > 5 min incremental) con P alta | — | GO pero **sin** compromiso de frescura compartida: el grafo es estrictamente local y bajo demanda; F7 (versionado) se descarta de antemano |

**Precedencia si aplican varias:** R0 > R5 > R4 > R2 > R3 > R6 > R1. (Seguridad y fallo técnico dominan; el coste se resuelve antes de juzgar precisión final.)

---

## 5. Post-piloto — siguientes pasos (solo en general)

### Rama GO pleno (S1, S2 ok)

Orden fijo, cada paso con su gate:

1. **F5 — Integración agentes:** skill `.agents/skills/graphify/` (query-first, "el grafo orienta, el archivo manda", freshness check) + párrafo manual en `AGENTS.md`. Vía PR, firma G-GR-2. Nunca `graphify install` automático.
2. **F6 — Obsidian:** export de `GRAPH_REPORT.md` + MOC generado a `35_generated/` del vault existente (`docs/ops/obsidian-context-vault.md`). Curaduría de David: solo enlaces, cero copias.
3. **F7 — Versionado:** tras **2 semanas de uso real**, decidir si se versiona `GRAPH_REPORT.md` con freshness stamp y cadencia de regeneración (cierre de frente). `graph.json` no se versiona (confirmado salvo evidencia nueva). ADR corto si se versiona.
4. **F8 — Diseño Rick:** ADR de diseño MCP read-only (superficie, filtrado de nodos, trust boundary = worker). Solo papel; implementación requiere G-GR-3.

### Rama GO parcial (S3 favorable, S7)

- Uso **opcional por agente** en local; sin skill, sin AGENTS.md, sin artefactos compartidos, sin Obsidian obligatorio.
- Revisión a **30 días**: si hubo uso real y valioso (registro cualitativo en board), reabrir F5–F7; si no hubo uso → degradar a NOGO silencioso (desinstalar opcional).

### Rama NO-GO (S4 reincidente, S5)

1. Doc de cierre corto en `docs/ops/` (qué se midió, por qué falló) — capitalización obligatoria, mismo patrón que torneos descartados.
2. Alternativas **anotadas como candidatas en board, ninguna se arranca automáticamente**:
   - índice manual curado de `docs/` (un `docs/00-index.md` mantenido por Cursor);
   - reutilizar `worker/rag/` para contexto de desarrollo (ya existe);
   - re-evaluar `graphifyy` en 1–2 releases (es un proyecto muy activo).
3. `.graphifyignore` **se conserva versionado** aunque haya NOGO: documenta la política de indexación para cualquier herramienta futura.

### Rama BLOCKED (S6)

- Registrar en board con motivo técnico; recordatorio de re-intento en la siguiente release del paquete; no consume más presupuesto.

---

## 6. Registro y bitácora (obligatorio en cada fase)

- **Task file:** `.agents/tasks/2026-07-02-002-graphify-pilot-f1-f4.md` — status y Log por fase.
- **Board:** línea en Trabajo vivo al arrancar (G-GR-0); veredicto final al cerrar (G-GR-1).
- **Evidencia local:** `C:\coord-ag-evidence\graphify-pilot\` (cost.json copiado, scoring A/B, salida de auditoría). No entra al repo.
- **Commits permitidos durante el piloto:** `.graphifyignore` + docs de plan/cierre. Nada de `graphify-out/`.

---

## 7. Prompt de arranque (G-GR-0 — David lo pega en **Copilot Windows**)

Archivo canónico: `docs/ops/MEGAPROMPT-copilot-windows-graphify-pilot-f1-f4.txt`  
Índice sprint (Graphify + Rick voz): `docs/ops/sprint-2026-07-02-prompts-index.md`

Atajo de arranque:

```text
Autorizo G-GR-0. Ejecutá el piloto Graphify F1–F4 completo según
docs/ops/MEGAPROMPT-copilot-windows-graphify-pilot-f1-f4.txt

Clone: C:\GitHub\umbral-agent-stack-copilot
Rama: copilot/graphify-pilot-f1-f4
Modelo: Fable 5 · 1M tokens
Umbral coste: USD 10
Superficie: Copilot Windows ONLY — NO Copilot-VPS

Antes de F2: git pull --ff-only origin main y verificar docs del piloto.
Reglas: nada en VPS, nada de graphify install/hooks, solo commit de
.graphifyignore + results doc. Ante fuga: R0. Decisión F4 la firmo yo (G-GR-1).
NO mergear PR.
```
