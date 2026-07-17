# Prompts multi-IA — captura para diagnóstico total Umbral (2026-07-17)

Compañero de: `docs/plans/sys-diag-openclaw-worksystem-plan-2026-07-17.md`
Uso: David copia cada prompt en la IA indicada, en el orden de la sección "Orden de pegado" del plan (§5). Cada respuesta se guarda tal cual (archivo .md o pegada en la sesión de consolidación — prompt 9). **Ningún prompt debe ejecutar acciones: todos son de lectura/inventario.**

Reglas comunes ya embebidas en cada prompt: no inventar (UNKNOWN si no hay acceso), no secretos/PII, taxonomía `ACTIVE_HEALTHY|ACTIVE_DEGRADED|ACTIVE_NOISY|OBSOLETE|ORPHAN|DRIFT_REPO_VPS|NEVER_SHIPPED|DUPLICATE|SECURITY_RISK|COST_RISK|UNKNOWN`, y oportunidades ligadas al sistema de trabajo real (no wishlist).

---

## Prompt 1 — ChatGPT (web, modo Work, con conectores)

```text
ROL: Sos el auditor de mis flujos de trabajo personales (David, Umbral — BIM/AEC + docencia). Trabajás SOLO con lo que tus conectores y tu memoria ven de verdad: Gmail/correo, Google Drive (si está conectado), memoria de proyectos de ChatGPT, y mis custom GPTs. No tenés acceso a mi VPS, mis repos ni mi Notion: cualquier afirmación sobre eso es inventada y está prohibida. Si un conector no está activo, marcá la sección entera como UNKNOWN.

TAREA: Inventariá mi sistema de trabajo real desde tu punto de vista:
1. Flujos de email recurrentes (remitentes/temas que se repiten semanalmente, newsletters que respondo vs ignoro, hilos operativos vivos).
2. Compromisos y pendientes detectables (cosas que prometí por correo y siguen abiertas).
3. Automatizaciones que yo haya mencionado en conversaciones pasadas (memoria de proyectos): cuáles, para qué, y si parecen seguir vivas.
4. Custom GPTs míos: nombre, propósito, última vez que los usé (si lo sabés), etiqueta ACTIVE_HEALTHY/OBSOLETE/UNKNOWN.
5. Preferencias de trabajo que tengas registradas en memoria (idioma, formato, horarios, estilo de decisión).
6. Top 5 de cosas que hago A MANO repetidamente (según correos/conversaciones) que un sistema multi-agente podría absorber — ligadas a lo que viste, no genéricas.

FORMATO DE SALIDA (estricto, YAML):
fuentes_disponibles: [lista de conectores realmente activos]
flujos_email: [{tema, frecuencia, accion_mia_tipica, etiqueta}]
compromisos_abiertos: [{que, con_quien_rol, desde_cuando}]  # rol, no nombre completo de terceros
automatizaciones_mencionadas: [{nombre, proposito, ultima_senal, etiqueta}]
custom_gpts: [{nombre, proposito, etiqueta}]
preferencias_memoria: [lista]
oportunidades: [{que, evidencia, esfuerzo_estimado}]
unknowns: [lista de lo que no pudiste ver y por qué]

PROHIBIDO: inventar; pegar correos completos; incluir emails/teléfonos de terceros (usá rol o iniciales); recomendar herramientas nuevas que no salgan de la evidencia.
```

---

## Prompt 2 — Notion AI (pegar desde la página Gobernanza Notion o Control Room)

```text
ROL: Sos el auditor read-only de este workspace Notion (Umbral). SOLO inventariás lo que podés ver en este workspace. NO ejecutes ningún agente, NO dispares automatizaciones, NO edites páginas: una sola respuesta de auditoría.

TAREA — inventario en 6 tablas markdown:
1. AGENTES CUSTOM: nombre | qué hace (1 línea) | trigger (manual/programado/mención) | estado visible ON/OFF | modelo si es visible | última ejecución si es visible | etiqueta (ACTIVE_HEALTHY/ACTIVE_NOISY/OBSOLETE/UNKNOWN).
2. DATABASES CANÓNICAS: nombre | propósito | nº aprox de filas | última edición visible | quién la alimenta (humano/agente/ambos) | etiqueta. Incluí como mínimo: Control Room, Transcripciones Granola, Registro de Tareas, Bandeja(s) Rick, Publicaciones, Registro de Sesiones (V1?), y cualquier otra que veas con actividad.
3. VISTAS DE REVISIÓN / DASHBOARDS: página | para qué ritual sirve | ¿parece usarse? | etiqueta.
4. PÁGINAS DE AUTOMATIZACIÓN / instrucciones para agentes: página | a qué agente sirve | vigente o legacy.
5. LEGACY V1: cualquier superficie que parezca versión vieja duplicada por una V2 (ej. Registro de Sesiones V1, Esquemas mínimos) | evidencia de abandono | etiqueta OBSOLETE/DUPLICATE.
6. CRÉDITOS/USO: si tenés visibilidad del consumo de créditos Notion AI o ejecuciones de agentes, resumilo; si no, UNKNOWN.

Cierre: 5 oportunidades concretas de limpieza o consolidación LIGADAS a lo que viste (ej. "DB X duplica DB Y", "agente Z sin trigger"), y lista de UNKNOWNS.

PROHIBIDO: inventar contenido de páginas que no abriste; ejecutar agentes; citar contenido sensible de clientes (nombre de cliente → rol/iniciales).
```

---

## Prompt 3 — Cursor (agente Auto en el multi-root de David)

```text
ROL: Sos el auditor del entorno de desarrollo local (Cursor) de David. SOLO lectura del workspace multi-root actual y su configuración. No edites nada, no corras comandos que muten estado.

TAREA:
1. Reglas: listá todos los .cursor/rules, .cursorrules o AGENTS.md/CLAUDE.md que apliquen en los roots abiertos: path | resumen 1 línea | ¿contradice a otro? (marcá conflictos).
2. Multi-root: qué carpetas componen el workspace | cuáles tienen git dirty (git status --short) | cuáles parecen clones muertos o duplicados (etiqueta DUPLICATE/ORPHAN). Prestá atención a los clones notion-governance-* (cursor, antigravity, temp, rick-v1-draft) y worktrees _wt*.
3. Skills/comandos locales: .claude/skills, .agents/skills u otros paquetes de instrucciones por root: nombre | propósito | ¿duplicado entre roots? | etiqueta.
4. Hilos/tareas activas: si tenés visibilidad de chats o composer sessions recientes con trabajo a medio terminar, listalos (título + estado); si no, UNKNOWN.
5. Oportunidades: 3-5 limpiezas concretas del entorno local (borrar clones, unificar reglas, cerrar worktrees) con esfuerzo estimado.

FORMATO: YAML con claves reglas, roots, skills, hilos, oportunidades, unknowns. Taxonomía ACTIVE_HEALTHY/DUPLICATE/ORPHAN/OBSOLETE/UNKNOWN por ítem. PROHIBIDO inventar y pegar valores de .env.
```

---

## Prompt 4 — Codex (en el clone coordinador, p.ej. umbral-agent-stack-codex-coordinador)

```text
ROL: Sos el arqueólogo del repo umbral-agent-stack (y sus clones). SOLO lectura; no toques working trees.

TAREA — tabla markdown por sección, con evidencia path:línea o hash de commit:
1. ADRs (docs/adr/): número | decisión | ¿el código actual la respeta? | etiqueta (ACTIVE_HEALTHY/DRIFT_REPO_VPS/OBSOLETE).
2. DEUDA TÉCNICA: TODOs/FIXMEs/hacks relevantes en dispatcher/, worker/, scripts/ | riesgo real | esfuerzo.
3. HANDLERS/FEATURES NUNCA ACTIVADOS: código mergeado que ningún cron/config/flag invoca (buscá flags default-off, tasks sin caller, p.ej. en copilot_agent/, mission_control/, evals/) | etiqueta NEVER_SHIPPED.
4. PRs/RAMAS ABANDONADAS: ramas remotas sin merge > 30 días | qué contienen | KEEP/DELETE.
5. FOUNDRY/OAUTH: configs de Azure Foundry y OAuth Codex en el repo (docs/42, docs/43, env.example, gateway) | ¿el Worker puede heredar el OAuth del gateway hoy? | qué falta según el código.
6. CONSISTENCIA: contradicciones entre docs/ y código actual (docs que describen features retiradas).

Cierre: top 10 hallazgos ordenados por (impacto en el sistema de trabajo de David × facilidad), cada uno con recomendación KEEP/FIX/DISABLE/DELETE/IMPLEMENT/DEFER.
PROHIBIDO: inventar; declarar "verificado" sin evidencia; proponer refactors por estética.
```

---

## Prompt 5 — GitHub Copilot (chat, en Windows de David)

```text
ROL: Sos el auditor del entorno GitHub + Windows local de David para el stack Umbral. SOLO lectura.

TAREA — YAML estricto:
extensiones_vscode: [{nombre, ¿relacionada_a_umbral?, etiqueta}]  # solo las relevantes a agentes/IA/Azure
actions_workflows: [{repo, workflow, trigger, ultima_corrida_estado, etiqueta}]  # org Umbral-Bot y repos de David
entornos_github: [{repo, environments/secrets POR NOMBRE, etiqueta}]  # jamás valores
azure_vinculado: [{recurso, para_qué, ¿activo?, etiqueta}]  # subscripciones/recursos visibles desde acá; si no ves Azure, UNKNOWN
scripts_locales: [{path, propósito, última_modificación, etiqueta}]  # scripts sueltos en el Windows de David que toquen Umbral (tareas programadas de Windows incluidas: schtasks /query si podés)
oportunidades: [3-5 concretas ligadas a lo visto]
unknowns: [lista]

Taxonomía: ACTIVE_HEALTHY/ACTIVE_NOISY/OBSOLETE/ORPHAN/NEVER_SHIPPED/SECURITY_RISK/UNKNOWN.
PROHIBIDO: inventar; imprimir valores de secretos; disparar workflows.
```

---

## Prompt 6 — Copilot VPS / operador con shell en la VPS (GO MIN read-only)

```text
ROL: Operador read-only en la VPS Umbral (srv1431451, user rick). MANDATO GO MIN: solo comandos de lectura; PROHIBIDO restart/stop/deploy/editar archivos/escribir en Redis. Nunca imprimas VALORES de secretos: variables de entorno solo por NOMBRE (cut -d= -f1).

TAREA — devolvé YAML con bloques de evidencia (comando + salida sanitizada):
procesos: ps aux filtrado a poller|worker|openclaw|node|python|n8n → [{proceso, pid, desde, etiqueta}]
unidades: systemctl --user list-units --all + list-timers → [{unidad, estado, etiqueta}]
crons: crontab -l completo → por entrada: {línea, script_existe sí/no, última_corrida_si_hay_log, etiqueta}
disco_carga: df -h / ; uptime ; free -h
gateway: openclaw status --all ; openclaw models status → estado, agents, modelos con provider vivo vs solo-definido
worker: curl -fsS localhost:8088/health → familias de tasks y conteo
logs_48h: últimos errores de worker/poller/gateway (journalctl --user o logs/) sanitizados → [{origen, error, frecuencia}]
env_nombres: nombres presentes en ~/.config/openclaw/env y el env del worker → marcá presencia/ausencia de GOOGLE_API_KEY, ANTHROPIC_API_KEY, UMBRAL_DISABLE_CLAUDE, NOTION_POLLER_ENABLE_V2_CLASSIFY, AZURE_*, OPENAI_*
drift: cd ~/umbral-agent-stack && git log --oneline -3 ; git status --short → ¿producción corre main limpio?
skills_drift: diff -rq ~/.openclaw/workspace/skills ~/umbral-agent-stack/openclaw/workspace-templates/skills | head -40
redis_claves: redis-cli --scan --pattern '*cursor*' | head -20 (solo nombres; sin GET de contenido)
oportunidades: [3-5 retiros/arreglos concretos según lo observado]
unknowns: [lo que no pudiste ver]

Etiquetá cada ítem: ACTIVE_HEALTHY/ACTIVE_DEGRADED/ACTIVE_NOISY/ORPHAN/OBSOLETE/DRIFT_REPO_VPS/SECURITY_RISK/UNKNOWN.
```

---

## Prompt 7 — Microsoft Copilot 365 / Graph (si David lo usa para AEC/docencia)

*(David decide si pegarlo: solo aplica si el tenant M365 está activo en su flujo.)*

```text
ROL: Auditor read-only de mi entorno Microsoft 365 (calendario, Teams, SharePoint/OneDrive) en lo relativo a mi trabajo AEC/BIM y docencia. Solo lo que Graph te deja ver; nada de inventar.

TAREA — tablas markdown:
1. CALENDARIO (últimas 4 semanas + próximas 2): patrones recurrentes | tipo (docencia/cliente/interno) | carga horaria semanal aproximada por tipo.
2. TEAMS: equipos/canales con actividad real el último mes | propósito | etiqueta ACTIVE_HEALTHY/OBSOLETE.
3. SHAREPOINT/ONEDRIVE: bibliotecas/carpetas con ediciones recientes relacionadas a proyectos AEC o cursos | ¿duplican algo que ya vive en Notion/Drive? (marcá DUPLICATE si lo sabés).
4. AUTOMATIZACIONES: flujos de Power Automate visibles para mí | trigger | última corrida | etiqueta.
5. OPORTUNIDADES: 3 concretas para reducir fricción entre M365 y mi sistema Notion-céntrico (basadas en lo visto).
UNKNOWN explícito por sección sin acceso. PROHIBIDO: citar contenido de correos/documentos de terceros (solo títulos/patrones), inventar flujos.
```

---

## Prompt 8 — Perplexity Pro (research externo puro)

```text
ROL: Investigador de mejores prácticas 2025-2026, con citas. NO sabés nada de mi infraestructura y NO debés especular sobre ella: tu output es research externo puro.

TAREA — informe markdown con fuentes citadas por sección:
1. Gobernanza multi-agente personal/PYME 2026: patrones recomendados para orquestar varios agentes (gateway + workers + supervisor humano) sin drift: registro de agentes, contratos de superficie, kill-switches, auditoría. ¿Qué frameworks/estándares emergieron (p.ej. MCP, A2A) y qué prácticas se consideran ya antipatrón?
2. Higiene de créditos Notion AI / agentes Notion 2026: cómo limitan equipos pequeños el gasto de agentes Notion (triggers, batch, modelos), errores comunes de facturación, y prácticas de "credit budget" documentadas.
3. Patrones poller + worker sobre APIs SaaS (Notion/Slack): mejores prácticas actuales de cursors/checkpoints, idempotencia, backoff, y cuándo migrar de polling a webhooks; riesgos de rate-limit documentados por Notion API.
4. Riesgos de gateways self-hosted tipo OpenClaw/computer-use (2025-2026): superficies de ataque conocidas (prompt injection vía canales, exposición de Control UI, tokens en env), incidentes públicos si los hay, y mitigaciones estándar.
5. Síntesis: checklist de 10 puntos "estado del arte 2026" contra el que un sistema como el descrito genéricamente en 1-4 debería medirse.
PROHIBIDO: afirmar cualquier cosa sobre MI stack concreto; fuentes de baja calidad sin marcar; respuestas sin fecha de publicación de la fuente.
```

---

## Prompt 9 — Claude Code / Fable (sesión de consolidación, cuando David tenga las respuestas)

```text
SYNC
cd C:\GitHub\umbral-agent-stack
git fetch origin && git checkout claude/plan-sys-diag-openclaw-worksystem-2026-07-17 && git pull

ROL: Sos el consolidador del diagnóstico total Umbral. Insumos: (1) docs/plans/sys-diag-openclaw-worksystem-plan-2026-07-17.md; (2) docs/audits/sys-diag-openclaw-inventory-draft-2026-07-17.md (inventario propio con evidencia VPS/repo); (3) las respuestas multi-IA que pego a continuación de este prompt (ChatGPT, Notion AI, Cursor, Codex, GitHub Copilot, Copilot VPS, M365 si aplica, Perplexity).

TAREA:
1. Validación cruzada: donde una IA contradiga la evidencia VPS/repo del inventario, gana la evidencia observable; anotá el conflicto.
2. Fusioná todo en la matriz de consolidación (Fuente → Hallazgo → Etiqueta → Impacto en sistema de trabajo → Recomendación KEEP/FIX/DISABLE/DELETE/IMPLEMENT/DEFER → Esfuerzo → Dependencias → Riesgo), deduplicando por superficie.
3. Actualizá el inventario draft a FINAL: docs/audits/sys-diag-openclaw-inventory-final-<fecha>.md, con las oportunidades re-priorizadas (quick wins / apalancamiento / retiros / nuevas / anti-recomendaciones).
4. Proponeme un plan de ejecución por tandas (cada tanda ≤1 sesión, reversible, con gate humano), SIN implementar nada todavía.
5. Commit docs-only en la misma rama; preguntame antes de abrir PR.
REGLAS: sin fixes de código; sin deploy; sin gastar créditos Notion; taxonomía y etiquetas de evidencia del plan §2-§3; español.
```

---

## Prompt 10 — Opcional: n8n / Make / Linear vía MCP

*(Captura 2026-07-17: **n8n SÍ corre en la VPS** — systemd user `n8n.service` activo desde 2026-06-23 — y el repo tiene 0 workflows exportados, así que la parte n8n de este prompt SÍ hace falta (vía MCP n8n o UI). Make: sin señal viva (sim-to-make roto por env ausente) — David decide. Linear: integración congelada desde marzo — David decide.)*

```text
ROL: Auditor read-only de [n8n | Make | Linear] vía tus conectores. Solo inventario; no actives, no edites, no ejecutes workflows/escenarios.

TAREA — tabla markdown:
[n8n/Make] workflows/escenarios: nombre | trigger | ¿activo? | última ejecución y resultado | qué sistemas toca | etiqueta ACTIVE_HEALTHY/ACTIVE_NOISY/OBSOLETE/ORPHAN | recomendación KEEP/DISABLE/DELETE.
[Linear] equipos/proyectos: nombre | issues abiertas | última actividad | ¿duplica el board .agents o Notion? | etiqueta.
Cierre: ¿qué debería migrar al stack determinista (worker/poller) y qué debería morir? 3 líneas máximo.
PROHIBIDO: inventar, ejecutar, exponer API keys.
```

---

## Registro de devoluciones

| # | Destinatario | Pegado | Respuesta guardada en |
|---|-------------|--------|----------------------|
| 1 | ChatGPT | ☐ | |
| 2 | Notion AI | ☐ | |
| 3 | Cursor | ☐ | |
| 4 | Codex | ☐ | |
| 5 | GitHub Copilot | ☐ | |
| 6 | Copilot VPS | ☐ | |
| 7 | M365 Copilot | ☐ (opcional) | |
| 8 | Perplexity | ☐ | |
| 9 | Claude Code (consolidación) | ☐ (al final) | |
| 10 | n8n/Make/Linear MCP | ☐ (opcional) | |
