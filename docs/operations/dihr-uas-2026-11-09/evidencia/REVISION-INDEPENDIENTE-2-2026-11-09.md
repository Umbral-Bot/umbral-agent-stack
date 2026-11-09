<!-- Informe íntegro del subagente revisor, segunda pasada (instrucción: refutar) sobre el delta del PR 712 no cubierto por la primera revisión. Sesión coordinadora local_815b91f1, 2026-11-09 ~17:00Z. Correcciones aplicadas anotadas al final. -->

# Revisión independiente (2.ª pasada) — PR #712 `docs/operations/dihr-uas-2026-11-09/`

Comprobaciones propias (solo lectura): `gh` sobre PR 711/712; hash del acta (`85c9e86f…` coincide); ledger del coordinador (`ledger-stack-roadmap-diag.jsonl`: 237 líneas no vacías, única inválida la 112, `Invalid \escape` char 322: D13 confirmada); script del canario en `49404b9` (`kind:"canary_inference"`, clave `agent:main:canario`); `release-deploy.sh --rollback/--status` existen; el nombre público del VPS resuelve en DNS.

## 1. Hallazgos

| ID | Sev. | Archivo | Afirmación | Por qué falla | Corrección |
|---|---|---|---|---|---|
| A1 | Alta | Integral A.1-1; decisiones D2; ledger `DIHR-DECISION-A` | «Opción A de David (~15:2xZ), ejecutada (VPS-05, 15:06–15:50Z)» | GitHub: PR 711 ready 15:04:56Z, merge 15:05:17Z; VPS-05 arranca 15:06:22Z; el ledger escribe la decisión a 15:06:08Z citando «~15:2xZ». La autorización queda fechada después del merge y del inicio de la ejecución. | Hora real de la decisión (≤15:04Z) con fuente. |
| A2 | Alta | ESTADO cp.2–5; cabeceras REPORT VPS-03/PCRick-03; decisiones; pruebas; ledger | Eje temporal del corte 2–3 | Ledger y ventanas de los emisores sitúan VPS-03/PCRick-03 en 06:34–06:44Z; ESTADO/cabeceras los ponen ~70 min después. Cp.5 «~08:40Z» dice VPS-04 emitido y PR 711 con checks pendientes, pero commit a66ad62 = 14:28:26Z, PR = 14:28:33Z, VPS-04 = 14:29:06Z; `DIHR-DECISION-B` ts 14:28:57Z cita «~08:25Z». | Un solo reloj (UTC del ledger); corregir checkpoints y cabeceras. |
| A3 | Alta | Integral («sin commit»); decisiones D8 («PR en borrador, sin merge»); ESTADO; ledger | Estado del entregable | Commit 238cac4 (15:54:11Z) y PR 712 abierto con `isDraft=false`; el ledger de la copia del PR termina 15:51:04Z sin evento D8. | Evento ledger con la autorización y el commit; pasar el PR a borrador o corregir el texto. |
| A4 | Alta | Integral cabecera, A.2, F, I, K | «ningún sistema productivo fue modificado», «Nada de lo anterior se ejecutó» | Contradice H (cortes 2 y 4) y D1/D2 APLICADO. A.2-D1 con `MemoryHigh=6G/MemoryMax=6800M` (aplicado 5000M/5500M), A.2-D2 con «rama `rick/`» y `--session-key canary`; F-R0 pendiente y «paso 2 solo si R0.2 no corta el ciclo», pero el paso 2 se aplicó sin el paso 1; I «D1–D10», K «D1–D11», archivo D1–D13. | Cabecera con ventana real y cambios; A.2 con valores aplicados; F actualizada; anotar que la inversión paso 2→1 invalida G1b como discriminador. |
| A5 | Alta | COMPARATIVA-01; inventario-TARRO; integral B.1/B.5 | «Barrido… sin ids reservados del juez ciego» | Expuestos: carpeta de coordinación privada `1CXIBz_TA4…`, entradas `1A6hHWxI…`, recepción `1xK6vmAj…`; solo se truncó `144VGO`. El nombre `<host VPS>` resuelve en DNS público; «usuario SSH (redactado)»/`<usuario>@` persisten. | Truncar ids a 8 chars; eliminar FQDN; redactar usuario SSH. |
| M1 | Media | Integral A.1-1b | «evidencia directa» | VPS-03 la rotula «Correlación 24 h»; la evidencia directa es el tick 15:30Z (una muestra). | «Correlación fuerte 25/25; confirmación directa pendiente de G2 24 h». |
| M2 | Media | Integral A.1-1 | «noveno reinicio… ciclo (3,7 a 8,7 h)» | VPS-04: «causa no verificada». | Excluir del rango hasta leer el journal 10:01Z. |
| M3 | Media | Integral A.1-1 | «alguna credencial OpenAI sí se resuelve» | VPS-03 A3: `OPENAI_API_KEY` ausente; el 429 es verificado, la resolución es nota del coordinador. | Hipótesis. |
| M4 | Media | Integral D.13, D9; decisiones D9 | `settings.local.json` «atribuible a la sesión del juez» | JUEZ-01 declara «árbol intacto»; contradicción no anotada. | «Atribución no determinada; contradice la declaración del juez». |
| M5 | Media | Integral A.1-1, H; decisiones D1 | «97,6 s… PCRick reconectó 15:48:57Z» | stop 9,5 s + arranque 87,0 s = 96,8 s; PCRick «conectado 15:48:57Z» precede a «listening» 15:48:58,978Z. | «≈97 s»; marcar inconsistencia horaria. |
| M6 | Media | pruebas G1 | rutas del snapshot; `\|`; «NRestarts sin cambio» | El drop-in usa `--diagnostic-dir=/home/rick/dihr-diag`; `\|` es escape Markdown; NRestarts se reinició a 0. | `ls -la /home/rick/dihr-diag/`; `grep -ciE 'heap out of memory|Ineffective mark-compacts'`; línea base NRestarts=0. |
| M7 | Media | pruebas G2 | «sesión `canary`»; prosa en vez de comandos | Clave real `agent:main:canario`. | `jq` sobre ops_log por `.kind=="canary_inference"`; listado de sesiones filtrando `canario`. |
| M8 | Media | pruebas G3 y tabla «ejecutables hoy» | precondiciones y estados desactualizados | D3 exige clave válida y gateway parado; REPORT ya llegaron; G1b no se ejecutó. | Actualizar. |
| B1 | Baja | varios | Conteos (archivos en evidencia/, 34/22 vs 35/25, K 18 ámbitos vs 20 filas, «5 y 9 min», worktree) | — | Unificar. |
| B2 | Baja | decisiones D1 | Seis OOM 7–8 nov | fuente (lectura 00:51Z) no está en evidencia/. | Marcar Reportado. |
| B3 | Baja | A.1-1c; D12 | «fue rotada…»; «la app… ahora cifra» | inferencias en secciones «verificadas». | Hipótesis. |
| B4 | Baja | PCRick-01/03, VPS-03 A4 | nombre de tailnet, IPs LAN, huellas SSH completas | homogeneizar. | Redactar. |

## 2. Bien soportado
Causas (a)(b)(c) con comando y hora (VPS-03). Cadena de hashes coherente: openclaw.json ccc40458→f44ce55e→ccc40458; override 19b54e37; canario a2a708b1→5899e40d; release 125af3a→49404b9 (= merge real). Heap 2560 → 2.752 MB plausible. D13: causa raíz reproducida por el revisor. 2.532 ciclos ≈ (17-sep 13:30Z→9-nov 06:45Z)/30 min. D7/D9 fieles a PCRick-03. PBIX C23 coincide. Contradicciones Notion con URL y fecha. Reversiones existen en el script.

## 3. K alternativo (mismos pesos)
Inventario 70→10,5 · Diagnóstico 65→16,25 · Investigación 75→7,5 · Entrevista 85→8,5 · Propuestas 60→9,0 · Hoja de ruta 50→7,5 · Revisión 55→5,5 → **≈65 %**. Observación: la fila «Revisión» la puntúa el revisado; debería fijarla el revisor.

## 4. Veredicto
**APTO_CON_CORRECCIONES.** Mínimas para APTO: A1, A2, A3, A4, A5, M6, M7.

---
## Correcciones aplicadas por el coordinador (2026-11-09, tras esta revisión)
Ver sección final de ESTADO.md (checkpoint 11) y el commit de corrección en la rama del PR 712. Se adopta la puntuación del revisor para la fila «Revisión» y K se recalcula con ella.
