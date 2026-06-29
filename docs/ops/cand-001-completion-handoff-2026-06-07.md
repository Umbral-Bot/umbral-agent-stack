# CAND-001 — Handoff de cierre (ejemplo manual vía Rick)

> **Objetivo:** cerrar CAND-001 como **referencia de producción** (texto + blog + imágenes UmbralBIM).  
> **Page ID:** `34b5f443-fb5c-81dd-8338-cb0b46699250`  
> **DB:** `e6817ec4698a4f0fbbc8fedcf4e52472`  
> **claim_type:** `opinión` — sin publicaciones de referentes como fuente directa  
> **Rick:** ejecuta writes en Notion + Magnific. **No** marcar `autorizar_publicacion` sin OK David.

---

## A. Copy canónico (LinkedIn — aprobado por David)

Guardar **solo** en columna `Copy LinkedIn` (no duplicar en body):

```text
Muchas empresas quieren automatizar procesos con IA antes de ordenar cómo toman decisiones.

Ahí aparece el problema.

Si no hay responsables claros, criterios mínimos de calidad, fuentes trazables y una forma simple de auditar decisiones, la automatización no resuelve el desorden: lo escala.

Y cuando eso pasa, el riesgo no es solo técnico. También aumenta la probabilidad de amplificar errores, repetir afirmaciones no verificadas o perder control sobre excepciones relevantes.

Automatizar bien no parte por la herramienta.
Parte por la gobernanza mínima del proceso.

Primero claridad.
Después velocidad.
```

---

## B. Blog extendido (columna `Copy Blog`)

Rick: pegar en `Copy Blog`, ajustar si David pide. ~900 palabras. Misma tesis, más desarrollo AEC.

```markdown
# Automatizar con IA sin gobernanza escala el desorden

Muchas empresas quieren automatizar procesos con IA antes de ordenar cómo toman decisiones. La herramienta llega primero; el proceso, después. Y ahí aparece el problema.

No estoy en contra de automatizar. Automatizar bien puede liberar tiempo, reducir fricción y hacer visible lo que antes dependía de memoria individual. El error está en asumir que la IA ordena lo que el equipo nunca ordenó.

## Qué es gobernanza mínima (sin burocracia)

Gobernanza mínima no es un comité extra ni un PDF de cincuenta páginas. Es un conjunto pequeño de reglas que hacen reproducible una decisión:

- **Responsable claro** — quién puede aprobar, quién solo propone.
- **Criterio mínimo de calidad** — qué tiene que cumplir un entregable para avanzar de estado.
- **Fuente trazable** — de dónde salió el dato, la regla o la excepción.
- **Auditoría simple** — cualquier persona del equipo puede reconstruir qué se decidió, cuándo y con qué fundamento.

Sin eso, la automatización no resuelve el desorden: lo escala. Un flujo que corre más rápido sobre criterios ambiguos no mejora el sistema; lo hace opaco.

## Por qué el riesgo no es solo técnico

Cuando la automatización corre sin gobernanza, el fallo deja de ser “el script falló”. Pasa a ser organizacional:

- Se **amplifican errores** que antes eran locales (un campo mal nombrado, una excepción no registrada).
- Se **repiten afirmaciones no verificadas** porque el sistema no distingue evidencia de costumbre.
- Se **pierde control sobre excepciones** que en la práctica importan más que el caso estándar.

En oficinas técnicas y equipos BIM esto se ve con frecuencia: un coordinador resuelve un clash en reunión, el modelo se ajusta, pero el registro formal no se actualiza. Semanas después, un reporte — humano o automatizado — trabaja sobre un estado que no refleja la realidad del proyecto.

## AEC: el patrón se repite con otra superficie

En construcción digital el problema no es la falta de estándares. Existen marcos para gestión de información, estados de revisión y registro de incidencias. La brecha suele estar en la **implementación cotidiana**: decisiones que viven en chats, correos y reuniones sin cierre formal.

Automatizar QA, reportes o asistentes sobre ese sustrato no crea trazabilidad mágica. Hereda lo que hay. Si lo que hay es ambiguo, la velocidad solo hace llegar antes al mismo punto de confusión.

## Automatizar bien: orden de trabajo

1. **Claridad** — dueños, criterios, fuentes, estados.
2. **Velocidad** — flujos, scripts, agentes, integraciones.

Invertir ese orden parece más lento al inicio. En la práctica evita re-trabajo, desconfianza del equipo y “automatizaciones heroicas” que solo sobreviven mientras las mantiene una persona.

## Cierre

Automatizar bien no parte por la herramienta. Parte por la gobernanza mínima del proceso.

Primero claridad. Después velocidad.

---

*Opinión editorial Umbral BIM. Sin estadísticas ni citas a publicaciones de terceros en esta pieza.*
```

**Copy X** (resumen): automatizar IA sin dueños/criterios/fuentes/auditoría escala el desorden → primero claridad, después velocidad.

---

## C. Body Notion (solo Decision Brief, sin copies)

Rick: body = §1–5 + §7. **Quitar** copies duplicados del body.

```markdown
## 1. Premisa
Automatizar con IA sin gobernanza mínima del proceso escala el desorden y amplifica errores.

## 2. Por qué ahora
- Ola de adopción de IA en operaciones y oficinas técnicas.
- Citizen automation y low-code sin dueño ni criterio de cierre.
- Gap entre capacidad de herramienta y madurez de proceso.

## 3. Fuentes y confianza
| Fuente | Rol | Citable |
|--------|-----|---------|
| — | Opinión editorial Umbral BIM | N/A |

**claim_type:** opinión  
**Fuente primaria:** N/A  
**Repo reference:** docs/ops/cand-001-completion-handoff-2026-06-07.md

## 4. Pilares Umbral
- Automatización empática
- Citizen developer AECO
- Puentes digitales

## 5. Objetivo
| Objetivo | Prioridad |
|----------|-----------|
| Visibilidad / posicionamiento | Alta |
| Venta directa | Baja |

## 7. Qué NO hacer sin David
🛑 No marcar autorizar_publicacion. No publicar.
```

Props: `Notas` = `claim_type: opinión — sin Fuente primaria externa`

---

## D. Imágenes — regeneración con estilo UmbralBIM

Ver `docs/ops/umbral-bim-magnific-visual-style-v1.md` §7–9.

**Rick — prompt Telegram:**

```text
CAND-001 backfill visual (page 34b5f443-fb5c-81dd-8338-cb0b46699250).

1) custom_references_list → confirmar estilo "UmbralBIM" (guardar style_id en Visual brief).
2) images_models_list → Nano Banana 2.
3) Estado imagen = Regeneración pedida; limpiar imagen_alt_*.
4) images_generate × 3 (1:1) con:
   - estilo UmbralBIM (#UmbralBIM si aplica en prompt)
   - brief: gobernanza vs automatización, cubos isométricos, pantallas holográficas, turquesa/cian sobre fondo oscuro, sin texto en imagen
   - escena: "automatización que escala desorden" — flujo desordenado vs flujo con capas claras de decisión
5) creations_wait → URLs en imagen_alt_1..3, imagen_cantidad=3, Estado imagen=Listo para selección.
6) NO marcar gates.

Reporta style_id, modelo, URLs, créditos usados.
```

**Logo viñeta (fase 2 — opcional este ciclo):** si existe PNG de viñeta Umbral en Drive, documentar path; post-proceso Worker o `images` edit — no bloquear selección de alt.

---

## E. Gates (David)

1. `aprobado_contenido` ✓ (texto + blog OK)
2. Elegir `Selección imagen` → Alt N
3. `Visual asset URL` = imagen_alt_N_url
4. `autorizar_publicacion` ✓
5. Telegram: `ok publica`

---

## F. Veredicto esperado

`CAND001_EXAMPLE_COMPLETE` — props + body + 3 alts UmbralBIM + blog en columna.
