<!-- Informe íntegro del subagente de inventario de Google Drive (sesión coordinadora local_815b91f1). Solo lectura vía conector MCP de Drive de la cuenta <cuenta Gmail personal de David>. Evidencia de lectura; no verificado ítem a ítem por el coordinador. -->

# Inventario de Google Drive — diagnóstico de gobernanza documental

**Cuenta inspeccionada:** <cuenta Gmail personal de David> (Mi unidad). **Modo:** solo lectura (search/list/metadata/permissions; `read_file_content` solo en 6 documentos de coordinación). **Ventana:** ≈ 2026-11-09 05:45–06:05 UTC (estimada por marcas de archivo).

## 1. Unidades compartidas
`list_shared_drives` devolvió vacío: **no hay unidades compartidas** visibles (o el conector no tiene el scope). Todo vive en Mi unidad de una cuenta Gmail personal.

## 2. Estructura
- Raíz: 01_Entrada, 02_Operacion, 06_Sistemas y Automatizaciones (2026-04-02), ChatGPT (2026-11-05). Todo propiedad de David.
- 02_Operacion: Clientes y Partners (22 subcarpetas), Entidades Propias, Proyectos y Asesorias, _Plantilla-Programa, Oportunidades sin Cuenta Anclada, **_local-secrets** (2026-09-03, sin hijos visibles; nombre indica secretos en Drive).
- Clientes y Partners (22): Butic, Dessau Peru, Konstruedu, N8N, WSP, Iglú, Mario Morales, USM, Speckle, Berrilan, Cecilia Sepulveda, Shimin, Netzun, Enjofrabim, Adarcus, Arquitectura Carola y David, Congrap, BIM Forum, OXXO, Universidad Continental, TEDI, Boragó.
- Tercer nivel: Butic {00_Relacion y Acuerdos, 10_Historico, Compartido, Curso BIM + IA, Lab y Base de Conocimiento, Master AEC 4.0, Eventos, Publicado, seguimiento-lovable-20261020, Curso Lovable Butic}; WSP {00_Cuenta, Agente Virtual, Copilot 365, Power Automate, **.claude**}; Dessau Peru {00_Cuenta, 01_Input Dessau, **.codex-build / .codex-work / .codex-finalizer-ppt-v8 / .codex-remote-attachments / .playwright-mcp**, `build_deck_plan_trabajo.py` suelto; 04_Coordinacion con `ledger-dessau.jsonl` y PKG-DESSAU-*}; N8N {Archive, docs, outputs, Evento 01/02, Familia AEC-flujo, Investigación, Paid Media Evidence, Seguimiento reembolsos, .playwright-mcp, ≥8 artefactos `_tmp_*`}.

### Ubicaciones UAS / coordinación fuera de 02_Operacion
| Ruta reconstruida | Qué contiene |
|---|---|
| 06_Sistemas y Automatizaciones / 04_Automatizacion y Herramientas / **Puente TARRO-MSI** / {inbox, outbox, control} (creada 2026-11-03) | Transporte de paquetes: PKG-DOT-MSI-*, PKG-TARRO-MSI-*, carpetas REPORT-2026110xT…, ACK/PONG; PROTOCOLO-BASE.md, PROTOCOLO.md, PROTOCOLO-1.1-LECTURA-PERIODICA.md |
| …/M05-actualizacion-Microsoft-20261003 / REPLANTEO-COPILOT-STUDIO-20261008 / **control** | Control WSP M5: PLAN-SPECKLE-SHAREPOINT-20261024 (HOJA-DE-RUTA.md vigente), PAQUETE-S33…S36, INTEGRACION-REPORT-03…06, PROMPT-CLAUDE-*, RELEVO-NOTEBOOK-S33 (>50 ítems) |
| 01_Entrada / **Respaldo Notion** / 1 (2026-04-30) | Export Notion: «Auditoría Mejora Continua — Umbral Agent Stack», «Tareas — Umbral Agent Stack», OODA Weekly Report, OpenClaw, Bandeja Puente |
| **ai-agents-export-2026-04-27** | ~30 copias de `umbral-agent-stack-codex` (snapshots horarios 2026-04-02 y 26-abr), cada una con `openclaw/`, reports .md |
| V6.7-CONTEXTO-SKILLS-20261008 / ensayo-claude / DEMO-R3-20261106 | CHECKPOINT-DM.md (Creador WSP V6.7 r3), modificado 09-nov 05:35Z |
| ChatGPT (raíz) | Google Doc «Control de lectura · comentarios del tablero» (automatización de lectura del tablero Notion, generación 583, 09-nov 05:41Z; escaneos cada 10 min; `cas_probe_status passed_stale_revision_rejected`) |

## 3. Búsquedas por nombre
- UAS / Umbral Agent Stack: `tester-wsp-uas` (24-sep), export Notion, ~45 carpetas `umbral-agent-stack*` en el export de agentes.
- hoja de ruta: HOJA-DE-RUTA.md ×4 (tamaños 19.212 / 23.937 / 23.092 / 21.711 B → versiones distintas en 4 carpetas), 00_HOJA-DE-RUTA-hasta-14-sep.md.
- **macro-plan, stack-roadmap, DIHR, Mission Control, pedido revisado: 0 coincidencias por título.** «conciliada»: solo `preparar-entrega72-conciliada.py` (27-oct). **La hoja «UAS-hoja-conciliada-2026-11-09.md» no está en Drive por título.**
- ledger: ledger-dessau / -konstruedu / -familia-aec-flujo / -conecta3 / -campo-mcp-roleplay / -entrevistas .jsonl, LEDGER.jsonl ×2.
- REPORT-2026: 6 carpetas en Puente TARRO-MSI/outbox con REPORT.md, MANIFEST.json, EVIDENCE.json, READY.json.
- PKG-: PKG-DOT-MSI-* (5), PKG-TARRO-MSI-* (2), PKG-DESSAU-* (2), PKG-WSP-S5-TESTER…zip, PKG-C25-DALUX…zip, PKG-N8N-ADS-PLAN-02.
- TARRO / PCRick / OpenClaw / Rick: recibos TARRO ×4, RETORNO-TARRO-20261022, ACCION-PCRICK-RUSTDESK, MANIFIESTO-TRANSFERENCIA-PCRICK ×2, openclaw-vps-operator ×3, R4-PLAYBOOK_MIGRACION_OPENCLAW.md, rick-grok (06-nov), umbral-rick-runtime ×3, CHECKPOINT-RICK-CLOUD, PROMPT-RICK-* ×5.

## 4. Duplicaciones (30 hallazgos, resumen)
~30 copias de la carpeta `umbral-agent-stack-codex` y ~17 de `openclaw` en el export de agentes; 15 copias idénticas de varios reports .md; `plantilla-pedido.md` ≥28 copias (espejo de skills, 06-oct); HOJA-DE-RUTA.md ×4 con tamaños distintos; REGISTRO-ENTREVISTA.md ×3 / ENTREVISTA.jsonl ×4; LEDGER.jsonl ×2 (64.761 vs 2.787 B); skills `pkg-receiver-protocol`, `umbral-rick-runtime`, `openclaw-vps-operator` ×3 cada una; carpeta `Butic` 5 propias + 1 ajena; PROTOCOLO.md y PROTOCOLO-BASE.md idénticos (6.715 B); MANIFIESTO-TRANSFERENCIA-PCRICK ×2 con tamaños distintos; recibos TARRO ×4 (~42,9 KB cada uno); versionado por sufijo en Konstruedu (v2…v6) y Dessau (v12…v17). **Ejemplo bueno:** `INDICE-MATERIALES-v1.1 (sustituido…)` / `v1.2 (VIGENTE)` con sustitución documentada en `description`.

## 5. Recientes (01–09 nov)
Última actividad 09-nov 05:36Z en `e2/evidencias/T0.txt`; CHECKPOINT-DM.md 05:35Z; «Control de lectura · comentarios del tablero» 05:32Z; carpeta `2026-11-09_G14` (motor de piezas) 05:17–05:18Z con decisiones_G14.csv, galería y piezas. `list_recent_files` inutilizable (JPG con fecha 2030 por reloj de cámara).

## 6. Documentos de coordinación leídos (cabecera)
- **HOJA-DE-RUTA.md** (PLAN-SPECKLE-SHAREPOINT-20261024, 24-oct 16:01): «Hoja de ruta vigente — incidencias Speckle y revisiones por disciplina… Codex coordina y acepta; puede usar Claude Code Desktop…». Es la hoja de ruta de WSP M5, no de UAS.
- **CHECKPOINT-DM.md** (09-nov 05:35): Creador WSP V6.7 r3; Etapa 0 cerrada 03:58Z, 30/30 SHA-256; Etapa 2 NOT_RUN 05:37Z por bloqueo de acceso (Chrome TARRO redirigió a inicio de sesión organizativo).
- **LEER-PRIMERO-RETORNO-TARRO-S33-20261022.md**: recepción revisada en TARRO; 167/168 archivos; notebook Revit 2027.3.
- **REPORT.md** (Puente TARRO-MSI/outbox/REPORT-20261105T165445Z-4c673526): «Corrección formal terminada. Estado REPORTADO… Pendiente de validación y recibo del coordinador».
- **INVESTIGACION-DECISIONES.md** (24-oct): piloto nativo real favorece A.
- **Control de lectura · comentarios del tablero** (GDoc, 09-nov 05:32): JSON schema 1, automation_id 6aea5bb4…, «Registro privado de versiones leídas y avisos del tablero. No autoriza ejecutar comentarios», generation 583, escaneos cada 10 min. **Este es el monitor del tablero cuya restricción bloqueó la escritura de Rick GPT en la ficha DIHR.**

## 7. Permisos
- 02_Operacion, 01_Entrada, Butic, WSP, Dessau Peru, N8N, Puente TARRO-MSI, control WSP M5, _local-secrets, Respaldo Notion: solo **owner** (David), privadas.
- «Butic» compartida por tercero (`1wj_dBsCa…`): propietario externo gmail de un tercero (handle redactado); **anyoneWithLink → reader**; compartida con David 2026-02-26.

## 8. Diagnóstico
### Fuentes canónicas candidatas
HOJA-DE-RUTA.md de PLAN-SPECKLE-SHAREPOINT-20261024 (WSP); Puente TARRO-MSI inbox/outbox/control (transporte oficial del puente, 03→05-nov); PROTOCOLO-BASE.md; ledger-dessau.jsonl; CHECKPOINT-DM.md; Control de lectura del tablero; INDICE-MATERIALES v1.2 (práctica de versionado a replicar). Respaldo Notion/1 es snapshot histórico, no canónico.

### Riesgos
| Riesgo | Severidad |
|---|---|
| Carpeta externa «Butic» con anyoneWithLink reader, propiedad de un gmail de tercero | Alta si contiene material del Máster |
| `_local-secrets` dentro de 02_Operacion (Drive sincronizado) | Alta por diseño; confirmar contenido |
| Estado de agentes (`.claude`, `.codex-*`, `.playwright-mcp`) dentro de carpetas de cliente y export de ~30 snapshots con `openclaw/` | Media-alta (pueden incluir settings/tokens) |
| Toda la operación en una cuenta Gmail personal, sin unidades compartidas, owner único | Media (continuidad / bus factor) |
| Export Notion UAS en 01_Entrada, desactualizado (abril) | Media |
| `_tmp_*`, `.py` sueltos, PDFs de pago en raíz de cliente N8N | Baja-media |

## 9. No pude verificar
Unidades compartidas (vacío ≠ ninguna); «modificado por» de los 30 recientes; contenido de `_local-secrets`; PROTOCOLO-BASE.md (mime octet-stream rechazado por read_file_content); búsquedas fullText de «DIHR», «Mission Control», «macro-plan» (no se hizo para no indexar contenido de clientes); conteos exactos de snapshots (paginación); padres de 5 carpetas; horas UTC exactas.

**Sin modificaciones:** no se compartió, movió, eliminó ni descargó nada; no se copiaron secretos.
