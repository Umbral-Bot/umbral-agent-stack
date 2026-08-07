---
fuente: Microsoft Copilot 365 / Graph
prompt_origen: Prompt 7 (docs/plans/sys-diag-capture-prompts-2026-07-17.md)
fecha_captura: 2026-07-17 (según David; confirmar al pegar)
superficie: calendario, Teams, SharePoint/OneDrive, Power Automate
modo: read-only
estado_completitud: COMPLETE_WITH_CONNECTOR_LIMITS (ingerido verbatim por orquestador Cursor desde transcript de-9d13c3, linea 4342)
redacciones_por_ingesta: 0
---

## Salida final de la IA (verbatim)

# Auditoría read-only — entorno M365 de David Moreira

**Ventana:** 19-jun → 31-jul-2026 · **Alcance:** calendario, Teams, OneDrive/SharePoint, huella de automatizaciones. Solo títulos/patrones/timestamps; no reproduzco contenido de correos/documentos de terceros.

---

## 1. Calendario (últimas 4 sem + próximas 2)

Solo **6 eventos** en toda la ventana (todos entre 29-jun y 17-jul). Las **próximas 2 semanas están vacías**.

| Patrón recurrente | Tipo | Instancias en la ventana | Carga aprox. |
|---|---|---|---|
| Bloques "Foco / trabajo profundo" auto-agendados, 08:00–11:00 | **Interno** | "🎯 Foco: trabajo profundo" + "Foco: trabajo profundo" (29-jun, **duplicados en el mismo horario**) · "Foco: ponerme al día" (2-jul) | ~6 h esa semana; 0 el resto |
| Reuniones "Copilot / Agente" con Daniel Muñoz (WSP) | **Cliente** | "Copilot 365 (Seguimiento mensual)" 30-jun (2 h) · "documento propuesta agente" 8-jul (0,5 h) · "Propuesta David - Agente Copilot" 17-jul (0,5 h) | ~1 h/sem promedio |
| Docencia (Máster AEC 4.0, cursos ARQ/clases) | **Docencia** | **Ninguna en el calendario** | **0 h visibles** |

**Carga semanal por tipo:** Interno ≈ 6 h (una semana puntual) · Cliente ≈ 3 h repartidas en 3 semanas · Docencia = 0 h en Outlook.

> **UNKNOWN:** tu calendario M365 está prácticamente sin usar y **la docencia no aparece** (vive fuera de Outlook, probablemente en tu sistema Notion). Detecté un bloque "Foco" duplicado el 29-jun (mismo horario, dos entradas).

---

## 2. Teams (actividad real desde 17-jun)

| Equipo › canal | Actividad último mes | Propósito (inferido) | Etiqueta |
|---|---|---|---|
| **TED** › 🤖 Automatizaciones | Sí, hasta **7-jul** (tarjetas "KB Pipeline", gates PASS/FAIL) | Pipeline de conocimiento del agente "Ejecutivo": monitorea docs oficiales + aprobaciones | **ACTIVE_HEALTHY** |
| **TED** › General | Sí, hasta **17-jul** (incidencias Speckle vía n8n) | Notificaciones BIM (Speckle → Sheets/SharePoint/Teams) | **ACTIVE_HEALTHY** |
| **Master AEC 4.0 V2** › General | Sí, muy activo hasta **16-jul** (Rhino Inside, MCP Rhino, n8n, "Módulo 02") | Cohorte **vigente** del Máster AEC 4.0 | **ACTIVE_HEALTHY** |
| **Webinar Butic** › Proyectos | Marginal, hasta **25-jun** (flujo "Aprobado el punto…") | Sandbox demo de aprobación (evaluación de locales) | ACTIVE (demo) |
| **Webinar Butic** › s4-pruebas | No, última huella **27-abr** (flujo doc., con errores) | Sandbox demo aprobación documental S4 | **OBSOLETE** |
| **Master AEC 4.0** (V1) › Comunicaciones | No, última actividad **8-jun** (inscripciones 7-may) | Espacio del Máster, cohorte previa **reemplazada por V2** | **OBSOLETE** |
| **USM - Aula I+D** › General | No, última actividad **14-sep-2025** | Colaboración investigación Aula I+D (USM) | **OBSOLETE** |

> **Hallazgo:** **Master AEC 4.0** y **Master AEC 4.0 V2** son equipos duplicados (misma descripción); V1 quedó obsoleto. **UNKNOWN:** no evalúo chats 1:1/privados aquí; "actividad" = mensajes de canal por timestamp.

---

## 3. SharePoint / OneDrive (ediciones recientes, AEC/cursos)

Solo tienes **OneDrive personal (Documentos)** + una lib de caché de sistema (ignorable). No hay sitios SharePoint de equipo con archivos tuyos fuera de los Teams.

| Carpeta / archivo | Últimas ediciones | Relación AEC / curso | ¿Duplica Notion/Drive? |
|---|---|---|---|
| **Agentes/** (03..06, Consultor, Plantilla_Clase_Copilot365, bitácoras .md) | 29-jun → 3-jul | Desarrollo de agentes IA para WSP (Ferroviario, Tráfico, Agent Builder) + material Copilot365 | UNKNOWN. **Interno:** `Consultor` y `Consultor - Cur` parecen **DUPLICATE** (23 items, mismo tamaño) |
| **Trabajo/WSP** | 14-jul | Cliente WSP | UNKNOWN |
| **Trabajo/Umbral BIM** | 29-jun | Tu firma | UNKNOWN |
| Raíz: `Propuesta_Asistente_Implementacion_Copilot_365_WSP.docx` | **17-jul (hoy)** | Propuesta cliente WSP | UNKNOWN |
| Raíz: `25-ARQ331-Presentación del curso.pptx`, `Clase 6.3/7.6/7.7`, `Presentación Radar BIM.pptx` | mar–may 2026 | Material docente | UNKNOWN |
| **Trabajo/USM** (~83 GB) · **Trabajo/EnjofraBIM** (~20 GB) · **Comgrap** | oct–dic 2025 | Proyectos BIM / docencia USM (antiguas) | UNKNOWN — candidatas a archivar |
| Raíz: `Copia de BFCh_avances capitulo bSMART chile.pptx` × 2 | 29-may | Capítulo bSMART Chile | **DUPLICATE** (idéntico tamaño, "Copia de … - copia") |
| Raíz: `Doc1/Doc5/Document/Documento`, `Libro1/12`, `prueba/Prueba_2/_3`, `Presentación/Presentación1` | may–jun 2026 | Borradores/pruebas sueltas | Clutter, probable duplicación (nombres genéricos) |

> **UNKNOWN:** **no tengo acceso a tu Notion** ni verifiqué Google Drive → la columna "duplica Notion/Drive" queda UNKNOWN salvo los duplicados **internos** de OneDrive que sí veo. Recordatorio: no puedo borrar archivos de OneDrive/SharePoint (eso lo haces tú manualmente).

---

## 4. Automatizaciones (huella observable)

No existe API de Power Automate/n8n en mis herramientas → **no puedo enumerar flujos, dueños ni historial de corridas**. Lo siguiente está **inferido por su huella en Teams** (bot "Workflows" = Power Automate; webhooks de n8n). "Última corrida" = último mensaje observado, no run history real.

| Automatización | Plataforma | Trigger (inferido) | Última corrida (huella) | Etiqueta |
|---|---|---|---|---|
| KB Pipeline del agente "Ejecutivo" | n8n (+ tarjeta vía Workflows/Power Automate) | Monitor semanal hash-diff de docs oficiales (Dynamo, Revit IFC, Forma, Copilot Studio, Speckle, Giraffe); auto-aprueba 72 h + gate golden-set | **7-jul-2026** | ACTIVE_HEALTHY |
| Speckle → Sheets/SharePoint/Teams | n8n | Webhook `issue_created` en Speckle (proyectos BIM) | **17-jul-2026 (hoy)** | ACTIVE (en pruebas) |
| Aprobación de "puntos"/locales | Power Automate ("Workflows") | Aprobación de item en lista (evaluación de locales) | **25-jun-2026** | ACTIVE (demo) |
| Aprobación documental S4 | Power Automate ("Workflows") | Cambio de estado de doc en biblioteca SharePoint → mueve a `/S4_03_Publicado/`, asigna revisor por disciplina | **27-abr-2026** | **OBSOLETE / con errores** |

> **Riesgo:** las tarjetas de aprobación del KB Pipeline enlazan a `http://localhost:5680` (n8n local). Los botones "Aprobar/Rechazar" **solo funcionan desde tu propia máquina/red**; si ese equipo está apagado, la aprobación queda colgada.
> **UNKNOWN:** no veo flujos que **no** publiquen en Teams (p. ej. flujos de fondo en SharePoint), ni su estado real de conexión/errores.

---

## 5. Oportunidades: reducir fricción M365 ↔ Notion

1. **Estado central en Notion para lo que hoy “muere” en Teams.** Tanto el KB Pipeline como las incidencias Speckle ya pasan por n8n. Agrega un nodo que escriba cada pendiente/incidencia como item en una **DB de Notion** (con estado y botón), y deja Teams solo como notificación con enlace a Notion. Esto te saca de la dependencia de `localhost:5680` y devuelve el control del estado a tu centro.

2. **Bitácoras y documentación de agentes: Notion como fuente única.** Tienes bitácoras de desarrollo y tests de prompts como `.md` sueltos en `OneDrive/Agentes` — justo el contenido que ya gestionas en Notion. Sincronízalas a una DB de Notion (con el mismo n8n) y reserva OneDrive para binarios (pptx, videos, entregables). Elimina el "¿cuál es la última versión?" entre ambos.

3. **Reflejar docencia y proyectos en Outlook desde Notion.** Tu calendario M365 está casi vacío (0 clases visibles) mientras el Máster AEC 4.0 V2 está en plena marcha. Un sync **Notion → Outlook** de tu agenda docente y de proyectos evitaría choques con las reuniones de WSP y alimentaría la gestión de disponibilidad, sin obligarte a agendar dos veces.

---

**Cobertura / límites:** Calendario, Teams y OneDrive auditados vía Graph. **Sin acceso** a: Notion, Google Drive, definiciones/run-history de Power Automate y n8n, y borrado de archivos SharePoint/OneDrive. ¿Quieres que convierta esto en un documento Word/Excel para archivar, o que profundice en alguna sección (p. ej., limpiar los duplicados de OneDrive o consolidar los dos equipos "Master AEC 4.0")?
