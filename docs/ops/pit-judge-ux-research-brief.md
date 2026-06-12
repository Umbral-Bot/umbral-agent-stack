# PIT judge UX — research brief (P5.2b, Fase A)

- **Status:** RESEARCH — 2026-06-12. Insumo de la implementación `/pit/judge` (P5.2b).
- **Contexto:** David usó el dashboard `/pit` v1 (P5.2) contra el piloto real
  `pit-salud-mental-pilot` y le resultó difícil de leer: tabla densa de 8+ columnas,
  monospace, fulfillment empatado en 1.00 en las 3 lanes, sin desempate visual,
  y `__PASTE_TOKEN__` roto en browser ("preview: Failed to fetch").
- **Método:** revisión de docs públicas de productos de experimentación (Statsig,
  LaunchDarkly, Optimizely), guías de research UX (Nielsen Norman Group, Baymard),
  visualización de KPIs (Stephen Few) y dashboards internos dark-mode (Grafana,
  Linear, Notion gallery). No se copia UI de terceros: se adaptan patrones al
  judge de producto PIT (read-only, ADR-009).

Convención: **[E]** = evidencia con fuente · **[R]** = recomendación propia derivada.

---

## 1. Patrones aplicables

### P1 — Scorecard "columna por variante" con winner highlighting

**[E]** Statsig, LaunchDarkly y Optimizely presentan resultados de experimentos como
una grilla con **una columna por variante** y métricas como filas; la variante
ganadora se resalta (highlight verde / badge), y distinguen *leading* (va ganando,
sin significancia) de *winning* (ganadora confirmada).
Fuentes: [Statsig — Reading experiment results](https://docs.statsig.com/experiments/interpreting-results/read-results) ·
[LaunchDarkly — Shipping the winning variation](https://launchdarkly.com/docs/home/experimentation/winning) ·
[Optimizely — Experiment Results page](https://support.optimizely.com/hc/en-us/articles/38994840559501-Optimizely-Experiment-Results-page).

**[R]** PIT judge: una **card-columna por lane** (3 en el piloto), mismas "filas"
internas en idéntico orden. PIT no tiene intervalos de confianza ni stat-sig:
el equivalente honesto es el badge relativo por métrica ("Mejor check-in") y el
badge **"empate"** cuando el fulfillment no discrimina.

### P2 — Tabla comparativa para decisiones compensatorias en sets chicos (2–7)

**[E]** NN/g: cuando hay ≤5–7 alternativas el usuario decide de forma
*compensatoria* (pesa pros y contras por atributo); eso se sirve con comparación
columna-por-ítem / fila-por-atributo, no con páginas de detalle sueltas.
Cards funcionan mejor cuando los atributos clave son pocos (~2–4) y el foco es
un ítem por vez; las tablas, cuando se necesita cross-scan preciso de muchos
atributos. Fuente: [NN/g — Comparison Tables](https://www.nngroup.com/articles/comparison-tables/).

**[R]** PIT judge con 3 lanes × ~6 atributos clave queda en el medio → **híbrido**:
grid de 3 cards **alineadas por fila interna** (semántica de tabla, peso visual
de card). El ojo puede saltar horizontalmente porque cada card presenta
fulfillment / KPIs / hipótesis / acciones en el mismo orden y altura.

### P3 — Resaltar solo la diferencia que importa (con moderación)

**[E]** NN/g y Baymard: en comparadores, marcar visualmente el valor
diferenciador (bold, check, color de fondo) y **no** decorar todas las celdas;
el exceso de highlights anula el beneficio. Fuentes:
[NN/g — Comparison Tables](https://www.nngroup.com/articles/comparison-tables/) ·
[Baymard — Comparison Table UX](https://baymard.com/blog/comparison-tables-ux).

**[R]** PIT judge: **máximo un badge por métrica** en todo el torneo
("Mejor check-in" en una sola lane). Empate estricto en una métrica → ningún
badge para esa métrica (un "mejor" repartido no informa nada).

### P4 — Bullet graph: logrado vs objetivo en una barra compacta

**[E]** Stephen Few: el bullet graph (barra lineal + marca de target +
contexto cualitativo) comunica "KPI vs objetivo" en una fracción del espacio de
un gauge, y los gauges/donuts desperdician espacio y dificultan la lectura
cuantitativa. Fuente: [Few — Bullet Graph Design Specification (PDF)](https://www.perceptualedge.com/articles/misc/Bullet_Graph_Design_Spec.pdf).

**[R]** PIT judge: cada KPI del spec se muestra como **barra de cumplimiento
vs objetivo** (ratio direction-aware: `achieved/expected` si `increase`,
`expected/achieved` si `decrease`), con el valor logrado en número grande y el
objetivo del spec como texto de contexto ("objetivo ≥ 60 %"). Nada de gauges.

### P5 — Sparkline para la trayectoria, no para el valor

**[E]** Few/Tufte: los sparklines (gráficos del tamaño de una palabra) muestran
tendencia inline sin consumir layout; ideales para "cómo llegó hasta acá"
junto al número final. Fuente: Few, *Information Dashboard Design*;
[NN/g — Data visualization study guide](https://www.nngroup.com/articles/data-visualization-study-guide/).

**[R]** PIT judge: **sparkline SVG inline del fulfillment iteración 1→5** por
lane, al lado del fulfillment final. Responde "¿la lane convergió o rebotó?"
sin abrir ningún kpi_pack.

### P6 — Stat panel: un número héroe por card, colores semánticos, dark theme sobrio

**[E]** Grafana (best practices de dashboards): un KPI dominante por panel en
fuente grande, umbrales con colores consistentes (verde/ámbar/rojo) de alto
contraste sobre fondo oscuro, texto off-white, mínimo de tinta no-data.
Fuente: [Grafana — Dashboard best practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/).

**[R]** PIT judge: el **fulfillment es el único número héroe** de cada card
(20→40 px), el resto jerarquía menor. Mantener paleta dark GitHub ya usada en
MC v1, pero tipografía **sans (system-ui) para prosa** y mono solo para ids y
números — el monospace integral de v1 penaliza el escaneo.

### P7 — Rúbrica de jurado: criterios idénticos, en el mismo orden, por entrada

**[E]** Los scorecards de hackathon / design critique comparan **por criterio**
(filas = criterios, columnas = entradas, headers pegajosos), nunca con layouts
distintos por entrada; el juez evalúa un criterio a la vez a través de todas
las entradas. (Patrón estándar de scorecards de jurado, p. ej.
[Devpost — judging](https://help.devpost.com/hc/en-us/articles/360021906012-How-to-judge-a-hackathon)).

**[R]** PIT judge: las 3 cards comparten plantilla estricta (orden y altura de
secciones); el panel "Qué mirar" arriba cumple el rol del brief del jurado:
3 bullets **derivados de datos** que orientan el criterio antes de mirar cards.

### P8 — Guardrails y salud del experimento como banner aparte, no footnote

**[E]** LaunchDarkly/Optimizely separan métricas guardrail y alertas de salud
(p. ej. SRM) del resultado primario, con warnings visibles que frenan una
lectura ingenua del "winner". Fuentes:
[LaunchDarkly — Bayesian decision making](https://launchdarkly.com/docs/home/experimentation/bayesian) ·
[Optimizely — Experiment Results page](https://support.optimizely.com/hc/en-us/articles/38994840559501-Optimizely-Experiment-Results-page).

**[R]** PIT judge: banner amarillo persistente cuando las señales son 100 %
sintéticas: *"KPIs sintéticos — comparar prototipo e hipótesis, no adopción
real"*. Es la alerta de salud del torneo piloto; no va escondida en una celda.

---

## 2. Qué evitar (antipatrones observados o documentados)

| Antipatrón | Por qué | Evidencia |
|---|---|---|
| Tabla plana única de 8–12 columnas por lane (v1 actual) | sin jerarquía: el judge no encuentra ni el winner ni el porqué; NN/g: demasiados atributos sin agrupar saturan | [E] NN/g comparison tables; pit.html v1 |
| Jerga KPI cruda (`checkin_completion`, `kpi_id`, unit suelta) sin lenguaje humano | el judge piensa en "¿qué probó esta lane?", no en ids de schema | [E] LaunchDarkly muestra hipótesis y takeaways en lenguaje natural |
| Empate de fulfillment sin desempate visual | con 1.00 en todas las lanes la pantalla v1 "no dice nada"; el dato discriminante (KPIs relativos) queda enterrado en `<details>` | [E] piloto real: 3× fulfillment 1.0 |
| Badge "mejor" repartido en empates | un highlight que aparece en todas las columnas no discrimina | [E] NN/g: highlight selectivo |
| Gauges/donuts por KPI | desperdician espacio y dificultan comparación cuantitativa | [E] Few, Bullet Graph spec |
| Monospace para toda la prosa | legibilidad de lectura corrida pobre; mono solo para datos | [R] derivado de Grafana/Linear (sans para UI, mono para valores) |
| `__PASTE_TOKEN__` editado a mano + HTML guardado como `file://` | rompe fetch (CORS/origen nulo) y filtra el token a archivos sueltos | [E] bug reproducido por David (P5.2/P5.3) |
| Polling / auto-refresh sobre el vault | prohibido por diseño (ADR-009, sin acciones ni carga de fondo) | [E] ADR-009 D1 |

---

## 3. Wireframe propuesto — `/pit/judge/{pit_id}`

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ PIT judge · pit-salud-mental-pilot            [judge_pending] [⟳ refresh]    │
│ Micro-herramienta de chequeo de carga mental para equipos AECO               │
│ Semilla: "la fricción percibida (tiempo+taps) es la variable clave…"         │
│ runner: PIT_RUN_PASS · 3 lanes · 5 iteraciones · budget $200                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⚠ KPIs 100 % sintéticos — comparar prototipo e hipótesis, no adopción real.  │
├──────────────────────────────────────────────────────────────────────────────┤
│ QUÉ MIRAR                                                                    │
│ • Fulfillment empatado en 1.00 en las 3 lanes — desempatá por KPIs.          │
│ • lane-nudges lidera check-ins (83.3 %); lane-friccion lidera tiempo (9 s).  │
│ • 3/3 lanes validaron su hipótesis final.                                    │
├──────────────────────────┬──────────────────────────┬────────────────────────┤
│ lane-friccion            │ lane-nudges              │ lane-semaforo          │
│ "fricción percibida:     │ "nudges contextuales     │ "semáforo agregado     │
│  taps hasta completar"   │  con framing privacidad" │  por equipo"           │
│                          │                          │                        │
│ FULFILLMENT  1.00 [emp.] │ FULFILLMENT  1.00 [emp.] │ FULFILLMENT 1.00 [emp.]│
│ iter 1→5  ▁▃▅▇█          │ iter 1→5  ▂▄▆▇█          │ iter 1→5  ▁▂▅▆█        │
│                          │                          │                        │
│ Check-ins   74 %         │ Check-ins   83.3 %       │ Check-ins   68 %       │
│ ███████████▌· obj ≥60 %  │ █████████████ [Mejor]    │ ██████████ · obj ≥60 % │
│ Tiempo      9 s [Mejor]  │ Tiempo      17 s         │ Tiempo      18.2 s     │
│ █████████████ · obj ≤30s │ ███████████▌· obj ≤30 s  │ ███████████ · obj ≤30s │
│ Opt-in      7 usuarios   │ Opt-in      6 usuarios   │ Opt-in      7 usuarios │
│ █████████████ · obj ≥5   │ ███████████▌· obj ≥5     │ █████████████ · obj ≥5 │
│ (empate 7 ↔ semaforo: sin badge opt-in)                                      │
│                          │                          │                        │
│ Hipótesis ✓ validada     │ Hipótesis ✓ validada     │ Hipótesis ∅ inconclusa │
│ "si bajo taps, sube      │ "si encuadro privacidad, │ "si agrego señal de    │
│  checkin_completion"     │  sube opt_in_signals"    │  equipo, sube checkin" │
│                          │                          │                        │
│ [► Ver prototipo]        │ [► Ver prototipo]        │ [► Ver prototipo]      │
│ [Detalle KPI ▾]          │ [Detalle KPI ▾]          │ [Detalle KPI ▾]        │
├──────────────────────────┴──────────────────────────┴────────────────────────┤
│ judge pendiente — decidí winner y pedile a Rick el outcome report.           │
│ read-only ADR-009 · sin acciones de ejecución · datos: GET /pit/tournaments/…│
└──────────────────────────────────────────────────────────────────────────────┘
```

Flujo de acceso (sin ModHeader): `/pit/access` (form pegar token → sessionStorage
→ valida contra `/pit/tournaments`) → redirect a `/pit/judge/{pit_id}`.
`[Detalle KPI ▾]` expande la tabla por iteración (fetch on-demand del kpi_pack,
sin polling). `[► Ver prototipo]` pide `preview-link` firmado con el bearer de
sessionStorage y abre tab nueva (P5.3 intacto).

---

## 4. Decisiones UX para PIT judge (resumen ejecutivo)

1. **Card-columna por lane, plantilla idéntica** (P1, P2, P7): 3 columnas en
   desktop; el orden interno (tagline → fulfillment+sparkline → KPIs → hipótesis
   → acciones) es fijo para permitir cross-scan.
2. **Fulfillment = número héroe; badge "empate"** cuando max−min < 0.005 entre
   lanes con score (P1, P6) — el empate del piloto se declara, no se oculta.
3. **Desempate visible: un badge "Mejor <kpi>" por métrica**, direction-aware,
   ninguno si hay empate estricto (P3).
4. **Barras KPI vs objetivo del spec** estilo bullet (ratio direction-aware,
   color por cumplimiento), nunca gauges (P4).
5. **Sparkline fulfillment 1→5** por lane, SVG inline sin librerías (P5).
6. **Panel "Qué mirar" con 3 bullets generados desde datos** (empate/líder de
   fulfillment, líderes por KPI, validación de hipótesis, señal sintética) —
   texto plantillado en el adapter, testeable, sin opinión del agente (P7, P8).
7. **Banner amarillo sintético** persistente cuando `synthetic_share = 1.0` en
   todas las lanes con datos (P8).
8. **Hipótesis en lenguaje humano**: variable + statement del kpi_pack final con
   ✓/✗/∅, no solo `kpi_id` (anti-jerga).
9. **Auth sin ModHeader**: `/pit/access` + sessionStorage + fetch bearer en JS;
   shells HTML sin datos del vault y sin bearer; cero `__PASTE_TOKEN__`; errores
   humanos (túnel caído / token faltante / no usar `file://`).
10. **Read-only estricto** (ADR-009): sin botones de acción, sin polling,
    refresh manual; tipografía sans para prosa + mono para datos; desktop-first.

---

*Fuentes citadas inline. Este brief es evidencia de la Fase A de P5.2b; la
implementación vive en `mission_control/templates/pit_judge.html`,
`pit_access.html` y `mission_control/adapters/pit_vault.py` (helpers derivados).*
