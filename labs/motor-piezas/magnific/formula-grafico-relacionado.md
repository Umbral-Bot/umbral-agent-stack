# Fórmula de gráfico relacionado (camino B) · motor de piezas

Pedido de David (2026-11-11): «otro camoino para tener una formula donde podamos tener graficos
relacionados (revisa lo que está en el proyecto de automatizacion editorial del repo
umbral-agent-stack para que tengas de referencia unavance a ver si nos sirve algo de eso para ir porr
acá)». Destilada por cuatro agentes que leyeron la capa visual editorial del repo; probada en G27
(variantes B1 y B2).

> **Desde G28 esta fórmula es una de seis plantillas.** La versión que se usa está en `../formula/`: un router
> elige la plantilla según el contenido (hallazgo, comparación, interfaz, pendiente, transformación o evento),
> prompt(1) escribe el prompt(2) y el código lo valida antes de gastar. Esta página queda como la primera versión,
> la de G27, que corresponde a la plantilla «hallazgo».

## De dónde sale

- **Contrato vigente:** el *visual brief* v2 (`docs/ops/editorial-visual-brief-v2-2026-08-29.md`,
  `openclaw/workspace-templates/skills/nano-banana-image-briefs/references/visual-brief-v2.yaml`).
  Un LLM saca del texto el hecho central, la consecuencia y la metáfora; el Worker arma los prompts
  de forma determinista y falla cerrado si el brief no valida.
- **Regla dura** (`openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`): la metáfora cuenta la
  misma comparación que el copy. Una metáfora coherente que cuenta otra historia invalida el brief
  (caso CAND-WLCA-01).
- **ADR-006** (`docs/adr/ADR-006-capa-visual-editorial.md`): si el texto trae una cifra o un proceso
  verificable, no se pide imagen: corresponde un diagrama (capa 3).

## Paso 1 · brief (8 campos)

| Campo | Qué es | Quién |
|---|---|---|
| `sujeto` | un solo objeto técnico entero del dominio, compacto (16:9) y alargado (21:9). Sale del kicker; si el kicker es un tipo de pieza (Artículo, Webinar), del sustantivo de dominio del titular o la bajada | juicio acotado |
| `central_fact` | el titular, literal | código |
| `ignored_consequence` | la bajada, literal (en el motor: lo que el texto opone) | código |
| `contraste` | la comparación del texto contada en el mismo sujeto, en una frase | juicio |
| `acentos` | hasta 2 partes en turquesa: lo que el texto señala | juicio, tope en código |
| `negative_prohibitions` | el remedio o la lectura que el texto niega; lista de revisión, no va al prompt | juicio; vacío = no se pide |
| `avoid` | lista fija (texto, cifras, marcadores, logo, personas, cortes de diagrama) | código |
| `composicion` | una por formato, desde las máscaras: sujeto entero y centrado | código |

## Paso 2 · ensamblado (determinista)

- **16:9:** «Isometric line illustration of {sujeto compacto}, whole and centred with wide empty space
  around it. Only {n≤2} parts are flat teal, {motivo}: {acento_1} and {acento_2}. {contraste en una
  frase}. No text, no markers, no logo.»
- **21:9:** «Isometric line illustration: {sujeto alargado}, centred, empty margins at both ends. Only
  {n≤2} parts are flat teal, the single {motivo}: {acento_1} and {acento_2}. {contraste}. No text, no
  markers, no logo.» El ancho alarga el sujeto; nunca repite el hallazgo ni lo vuelve secuencia.

## Paso 3 · validación (si algo falla, no se pide)

25 a 60 palabras por prompt · 2 acentos como máximo · sin hex ni paleta salvo «teal» · la cola «No
text, no markers, no logo» intacta · los dos prompts distintos · `negative_prohibitions` no vacío.

## Paso 4 · pedido

Magnific One con el kit «Umbral BIM», sin plantilla, 2k, la proporción como parámetro, la imagen
principal aprobada como referencia de estilo (para el trazo fino). 180 créditos por imagen. Al
recibirla: `pedido_magnific.py registrar` (objeto, fondo y procedencia; `medir --percentil 1` si una
línea suelta alarga la caja).

## Aplicada a «La IA entra a la obra»

- **Sujeto:** el armazón de un edificio con una tubería (compacto de dos pisos; largo de cuatro vanos).
- **Contraste:** la revisión automática encuentra y marca el choque entre la tubería y la viga (lo que
  cambia); cómo se resuelve queda abierto, con dos recorridos alternativos tenues, ninguno elegido (lo
  que depende del equipo).
- **Acentos:** el tramo de tubería del choque y el tramo de viga que atraviesa.
- **No mostrar:** el choque resuelto ni una ruta elegida; robot, cerebro, chip ni haz de escaneo;
  personas por el equipo; en 21:9, el choque repetido en cada vano.

## Qué del repo no sirve aquí

- Los 5 `variation_axes` de v2: el motor necesita 2 formatos de un brief, no 5 variantes de uno.
- El sufijo anti-slop de `worker/tasks/magnific.py`: trae otra paleta (fondo oscuro); el kit ya la pone.
- Los defaults de crítica irónica del 30-ago (dos estados enfrentados): sirven para posts de crítica,
  y dos objetos rompen la máscara.
- El `VisualBrief` v1 de Stage 7 (nunca conectado, sin 21:9) y Stage 8 de Gemini (apagado).
- Los endpoints REST del Worker (Nano Banana, Mystic): no son Magnific One y no aplican el kit.
- La gobernanza del pipeline (propiedad Notion, gates, validador PIT sin 21:9): el laboratorio está
  fuera de ese circuito.
