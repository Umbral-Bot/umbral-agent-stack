# Camino B · plantillas que se rutean

Pedido de David (G27): «un proceso tipo plantilla donde llega el brief, eso pasa por un prompt(1) que produce el
prompt(2) pára ser ingresado en magnific, y ese prompt(1) es una plantilla o son varias plantillas uqe se pueden
rutear, seleccionar según tipo o categporia de grafico».

Ninguna orden de `formula.py` llama a Magnific ni gasta créditos. El pedido sale como archivo y lo aprueba David.

## El recorrido

```
contenido (kicker, titular, bajada)
  └─ 1. rutear (código) ─────────────┬─ fondo     → camino A (recorte óptimo)
       evento por kicker             ├─ diagrama  → capa 3 (mientras no exista, fondo del camino A)
       institucional → fondo         ├─ clasificar → 2. clasificador LLM (lista cerrada)
       cifras o pasos → diagrama     │                  └─ aceptar (código): < 0,70 → fondo
       puntaje de palabras           └─ imagen + categoría
  └─ 3. preparar (código): prompt(1) = esqueleto común + bloque de la categoría
  └─ 4. un LLM lee prompt(1) y devuelve prompt(2) en JSON (o NO_ENCAJA → fondo, CIFRA → diagrama)
  └─ 5. validar (código): 15 reglas; si falla, 1 reintento con la lista de errores; si vuelve a fallar → fondo
  └─ 6. alineación: otro revisor (rick-qa o David) confirma que la imagen cuenta lo mismo que el titular
  └─ 7. OK de David a los créditos → Magnific (cuerpo + cola) o Nano Banana 2.1 (cuerpo + bloque de marca)
  └─ 8. pedido_magnific.py registrar / medir → catálogo con objeto y acento → motor con anclaje por acento
```

## Archivos

| Archivo | Qué es |
|---|---|
| `categorias.yaml` | Las seis plantillas: hallazgo, comparación, interfaz, pendiente, transformación, evento. Cada una con cuándo se usa, señales, inventario de sujetos, acentos, composición 16:9 y 21:9, prohibiciones, ejemplo y el bloque que se pega en prompt(1) |
| `ruteo.md` | Las reglas del ruteo, en orden (pasos 0 a 16) |
| `lexico.yaml` | Esas señales en forma de patrones que el código aplica |
| `clasificador.md` | El encargo del clasificador cuando el léxico no decide |
| `prompt1.md` | El esqueleto común de prompt(1), con los datos de la pieza como `{slots}` |
| `validacion.md` | Las 15 comprobaciones de prompt(2) |
| `formula.py` | `rutear`, `aceptar`, `preparar`, `validar` y `regresion` |
| `fixtures.yaml` | Casos de regresión del router (14 hoy; cada error de ruta suma uno) |
| `demo/` | Una pieza de punta a punta, sin créditos (ver `demo/README.md`) |
| `registro.jsonl` | Se crea con `validar --registrar`: sujetos de las últimas piezas, para no repetirlos |

## Cómo correr

```bash
python formula/formula.py rutear --contenido contenido/articulo-ejemplo.yaml --salida formula/demo/ruteo-ia-obra.json
python formula/formula.py preparar --ruteo formula/demo/ruteo-ia-obra.json --salida formula/demo/prompt1-ia-obra.md
# un LLM lee prompt1-ia-obra.md y deja su JSON en prompt2-ia-obra.json
python formula/formula.py validar --ruteo formula/demo/ruteo-ia-obra.json --prompt2 formula/demo/prompt2-ia-obra.json --salida formula/demo/pedido-ia-obra.json
python formula/formula.py regresion --ejemplos
```

Si `rutear` devuelve `clasificar`, el campo `prompt_clasificador` trae el encargo. La respuesta se cierra con
`formula.py aceptar --ruteo ... --clasificacion respuesta.json`.

## Lo que el código no decide

- **La alineación.** El código comprueba que exista «compara» y que la evidencia sea cita literal. Si la imagen
  cuenta lo mismo que el titular (regla CAND-WLCA-01) lo juzga otro revisor antes de los créditos.
- **El núcleo del sujeto** (comprobación 12) se saca con una regla simple: la última palabra antes de «with»,
  «where», «of» o una coma. Puede fallar con sujetos raros.
- **Calibración.** El cálculo a mano de `ruteo.md` daba al fixture openBIM interfaz 5 contra 3. Contado con la
  misma regla que «La IA entra a la obra», queda 5 contra 4 y decide el clasificador (eligió interfaz, 0,86).
  Tras unas 20 piezas reales se revisan el léxico y los umbrales (paso 15 de `ruteo.md`).
- **El caso CAND-WLCA-01** falta en la regresión: su copy real no está en el repo.
