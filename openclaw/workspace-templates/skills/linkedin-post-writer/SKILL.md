---
name: linkedin-post-writer
description: >-
  Redactar borradores LinkedIn/X desde un payload editorial y un encuadre AEC/BIM
  ya validado. Aplica las reglas completas de David para publicaciones LinkedIn,
  controla longitud, anti-slop, trazabilidad de fuentes y entrega handoff estructurado
  a rick-communication-director. No inventa angulo BIM/AEC, no agrega fuentes,
  no publica, no marca gates.
  Use when "redactar linkedin", "borrador linkedin", "escribir post candidata",
  "linkedin writer", "draft linkedin".
metadata:
  openclaw:
    emoji: "\u270D\uFE0F"
    requires:
      env: []
---

# LinkedIn Post Writer — Skill Editorial Umbral

## Proposito

Convertir un payload editorial con encuadre AEC/BIM en borradores LinkedIn y X listos para revision de voz y QA.

Este skill NO es dueno de:

- la seleccion de fuentes (eso es `editorial-source-curation` o `rick-editorial`);
- el angulo AEC/BIM (eso viene del encuadre previo);
- la voz final de David (eso es `rick-communication-director`);
- la validacion de claims (eso es `rick-qa`);
- la publicacion (eso es David + operador autorizado).

## Workflow obligatorio

### Paso 0 — Lectura de reglas

Antes de redactar, lee obligatoriamente:

1. `LINKEDIN_WRITING_RULES.md` — reglas completas de David para LinkedIn.
2. `CALIBRATION.md` — reglas persistentes de calibracion.

Si alguno no esta disponible, reporta riesgo y no generes borrador.

### Paso 1 — Verificar input

Verifica que recibes:

- payload editorial con premisa, claims, fuentes y clasificacion;
- encuadre AEC/BIM con `aec_angle`, `operational_examples`, `terms_to_avoid`, `claim_boundaries`, `source_trace`;
- restricciones explicitas (fuentes fijas, sin claims nuevos, sin fuentes nuevas).

Si falta el encuadre AEC/BIM, no inventes el angulo. Reporta: `BLOCKED: missing AEC/BIM context frame`.

### Paso 2 — Analisis interno antes de escribir

Antes de generar, responde internamente:

1. Cual es el objetivo del post?
2. Quien es la audiencia?
3. Que idea central debe quedar clara?
4. Que tono conviene?
5. Cual es el mejor gancho?
6. Que estructura hara mas legible el texto?
7. Que cierre generara interaccion?
8. Hay datos que no debo inventar?
9. El texto suena humano?
10. El post aporta valor real?

(Estas preguntas vienen de LINKEDIN_WRITING_RULES.md, seccion "Proceso interno antes de escribir".)

### Paso 3 — Redactar borrador LinkedIn

Escribe el borrador siguiendo las reglas de LINKEDIN_WRITING_RULES.md:

- gancho potente en la primera linea;
- estructura clara: gancho, contexto, desarrollo, aprendizaje, cierre;
- parrafos de 1-3 lineas;
- lenguaje profesional, humano, directo;
- sin frases genericas prohibidas;
- sin datos inventados;
- cierre con pregunta, reflexion o invitacion natural.

Reglas de estructura obligatorias:

1. **Tesis clara desde el inicio**: la primera o segunda oracion debe dejar claro de que trata el post.
2. **Contexto general antes de ejemplos tecnicos**: describir el problema en terminos de proceso, revision, entregable u observaciones antes de mencionar "modelo BIM", "modelo federado" o tecnologia especifica.
3. **Un solo hilo central**: no intentar cubrir dos ideas. Un post, una tesis.
4. **Ritmo movil**: escribir para lectura en pantalla de telefono. Parrafos cortos, frases que respiran, sin bloques densos.
5. **Vocabulario operativo en el desarrollo**: rotar con "revision", "observaciones", "entregables", "reportes", "rehacer", "aceptar", "decidir", "cerrar". No repetir la misma palabra abstracta mas de dos veces.

Anti-patrones que invalidan el borrador:

- Apertura abstracta sin situacion reconocible.
- Entrada directa a "modelo BIM" sin contexto de proceso.
- Tono de consultor: frases que suenan a informe o slide deck.
- Cierre moralizante o con slogan generico.
- Repeticion excesiva de la palabra nucleo (mas de 2 veces).
- Exceso de sustantivos abstractos sin aterrizaje operativo.
- Claims de mercado sin soporte ("cada vez mas empresas...").

### Paso 4 — Control de longitud

| Tipo | Rango objetivo | Maximo normal |
|------|---------------|---------------|
| LinkedIn medio (default) | 180-260 palabras | 300 palabras |
| LinkedIn corto | 80-150 palabras | 150 palabras |
| LinkedIn largo | 300-600 palabras | 600 palabras |

Si el borrador supera 300 palabras sin justificacion explicita, comprime obligatoriamente.

Contar palabras y reportar en `length_check`.

### Paso 5 — Redactar borrador X

X debe ser directo. No intentes resumir todo el post LinkedIn en X.

Tomar una sola tesis o insight y formularla como take propio.

Objetivo: <280 caracteres.

### Paso 6 — Anti-slop check

Verificar que el borrador NO contiene:

Frases genericas prohibidas:
- "En el dinamico mundo actual"
- "Como todos sabemos"
- "Hoy quiero hablar de"
- "La formula definitiva"
- "El secreto que nadie te cuenta"
- "Transforma tu vida"
- "Resultados garantizados"
- "sinergia", "ecosistema robusto", "solucion integral"
- "apalancar", "potenciar", "empoderar" sin contexto
- "Me complace", "Es un honor"

Terminologia sectorial prohibida en apertura:
- "escalacion" como sustantivo en copy publico
- "AEC/BIM" como apertura generica sola
- "nivel de coordinacion" sin aterrizaje operativo

Terminologia de consultor/paper prohibida:
- "capacidad tecnologica" (preferir "las herramientas ya estan" o similar)
- "criterio operativo explicito" (preferir "reglas de revision", "que se acepta")
- "umbrales de decision" (preferir "cuando algo pasa o no pasa")
- "amplificar la confusion" / "amplificar el desorden" (preferir "el desorden crece" o "el problema se repite mas rapido")
- "impacto operativo" (preferir "lo que cambia en la practica")
- "sistemas algoritmicos para gestionar trabajo" (preferir formulacion concreta)

Anti-patrones estructurales:
- Apertura abstracta sin escena operativa reconocible.
- Entrada directa a "modelo BIM" sin contexto de proceso previo.
- Cierre con moraleja generica o slogan ("El verdadero desafio es...").
- Repeticion de la palabra nucleo mas de 2 veces.
- Claims de mercado sin soporte directo en las fuentes del payload.

Si se detecta alguno, reescribir antes de entregar.

### Paso 7 — Trazabilidad de fuentes

Para cada claim en el borrador, verificar que:

- la fuente esta en el payload original;
- la clasificacion (evidencia / inferencia / hipotesis) esta correcta;
- no se agrego ninguna fuente nueva;
- no se convirtio inferencia en hecho;
- no se atribuyo a personas como autoridad publica.

### Paso 8 — Entregar output estructurado

```yaml
variant_id: ""
variant_name: ""
linkedin_candidate: |
  (texto completo del borrador LinkedIn)
x_candidate: |
  (texto completo del borrador X)
length_check:
  linkedin_words: 0
  x_chars: 0
  within_target: true/false
source_trace:
  - claim: ""
    source: ""
    confidence: ""
risk_flags:
  - ""
handoff_to_rick_communication_director:
  ready: true/false
  notes: ""
  calibration_applied: true/false
  slop_check_passed: true/false
  source_trace_verified: true/false
```

### Paso 9 — Handoff

Entregar el output a `rick-communication-director` para calibracion de voz.

No entregar directamente a Notion, QA, o publicacion.

## Reglas de seguridad

- No publicar.
- No marcar `aprobado_contenido`.
- No marcar `autorizar_publicacion`.
- No cambiar gates.
- No escribir en Notion.
- No inventar claims.
- No agregar fuentes nuevas.
- No inventar el angulo AEC/BIM.
- No decidir que un claim es seguro sin QA.
- No convertir inferencia en hecho.
- No citar personas como autoridad publica.

## Composicion con otros skills y agentes

| Etapa | Responsable | Este skill... |
|-------|-------------|---------------|
| Fuentes y senales | `editorial-source-curation` / `rick-editorial` | Recibe, no produce |
| Encuadre AEC/BIM | `editorial-source-curation` (seccion framing) / `rick-editorial` | Recibe, no produce |
| Borrador LinkedIn/X | **este skill** | Produce |
| Voz David | `rick-communication-director` | Entrega handoff |
| QA | `rick-qa` | No interactua directamente |
| Notion | Operador autorizado | No interactua |
| Publicacion | David | No interactua |
