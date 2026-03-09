---
name: editorial-voice-profile
description: construye y mantiene un perfil editorial editable a partir de materiales
  del autor, contenido de notion y referentes de divulgacion. usar cuando chatgpt
  deba leer corpus propios desde notion o texto pegado, estudiar referentes sin imitarlos,
  separar narrativa, tono, estilo, framing, cta, estrategia comunicativa y reglas
  por canal, producir una primera version editable para david, actualizar el perfil
  con feedback humano, o usar ese perfil para redactar piezas especificas sin sonar
  generico.
metadata:
  openclaw:
    emoji: ???
    requires:
      env: []
---

# Editorial Voice Profile

## Overview

Convertir materiales dispersos del autor y de sus referentes en un perfil editorial utilizable, editable y reusable.

Separar siempre evidencia, inferencia y decision humana. Escribir con provisionalidad cuando la muestra sea pequena, sesgada o incompleta.

## Expected inputs

Aceptar uno o varios de estos insumos:

- paginas, subpaginas o bases de datos de notion
- piezas pegadas en chat: posts, newsletters, guiones, notas, transcripciones o borradores
- lista de referentes de divulgacion con ejemplos concretos
- feedback humano posterior de david
- instrucciones sobre canales objetivo: linkedin, newsletter, video corto, x, web, email u otros

Si faltan materiales del autor, advertir que solo se puede proponer una hipotesis inicial y no un perfil estable.

## Source handling priority

Priorizar las fuentes en este orden cuando exista eleccion:

1. texto completo pegado en el chat
2. enlaces directos o paginas puntuales de notion claramente identificadas
3. paginas de notion recuperadas via app con sincronizacion o conector de chat
4. descripciones resumidas hechas por el usuario

Si el pedido depende de matices finos de voz, preferir menos piezas pero completas antes que muchas piezas resumidas.

## Notion retrieval notes

Antes de inferir el perfil, asumir estas reglas operativas:

- tratar notion como fuente principalmente documental y de solo lectura
- no asumir que todo el workspace ya esta indexado o sincronizado
- no asumir que imagenes, videos o otros contenidos no textuales esten disponibles para analisis semantico
- si el usuario necesita trabajar con lo mas reciente y una pagina no aparece, proponer trabajar con texto pegado, enlace directo o una pagina concreta en vez de generalizar con evidencia incompleta
- si el usuario menciona una "database" o una tabla de notion, tratarla tambien como posible "data source" y describir la fuente con ese lenguaje amplio en lugar de depender de una nomenclatura unica

Consultar [references/notion-retrieval-notes.md](references/notion-retrieval-notes.md) cuando haga falta recordar limitaciones practicas de recuperacion.

## Working model

Distinguir de forma explicita estas capas. No fusionarlas en un solo bloque:

- **narrativa**: historia recurrente que organiza el discurso; tension, promesa, antagonista, transformacion y punto de vista
- **tono**: temperatura emocional y relacion con la audiencia; cercania, autoridad, humor, rigor, energia, vulnerabilidad
- **estilo**: decisiones de frase, ritmo, sintaxis, vocabulario, estructura, densidad, recursos retoricos y patron de ejemplos
- **estrategia comunicativa**: para quien escribe, que cambio busca, que valor entrega antes de pedir algo, como construye confianza y como encadena ctas
- **reglas por canal**: adaptaciones concretas por formato, longitud, cadencia, apertura, cierre y llamada a la accion

Mantener tambien separado el **framing** de cada tema: desde que angulo se presenta, que creencia se desafia, que problema se redefine y que promesa se hace.

## Workflow

Seguir este orden.

1. **reunir corpus**
   - separar corpus propio y corpus de referentes
   - anotar para cada pieza: canal, fecha si existe, audiencia aparente, tema, apertura, estructura, cierre, cta y nivel de especializacion
   - detectar si el corpus esta dominado por un solo canal o un solo momento temporal
   - registrar cobertura de fuentes: cuantas piezas completas, cuantos fragmentos y que canales quedaron subrepresentados

2. **auditar suficiencia de muestra**
   - decidir si la muestra alcanza para perfilar o solo para plantear hipotesis
   - etiquetar el estado como: suficiente, parcial o insuficiente
   - si la muestra es parcial o insuficiente, mantener la propuesta pero elevar preguntas abiertas y bajar confianza

3. **leer referentes**
   - extraer patrones de framing, ritmo, claridad, manejo de ejemplos, densidad conceptual, autoridad, vulnerabilidad, humor y cta
   - identificar que admirar sin convertirlo en imitacion
   - prohibir copiar tics verbales, muletillas, slogans o estructuras demasiado reconocibles del referente

4. **leer materiales de david**
   - localizar obsesiones tematicas, promesas recurrentes, conflictos que suele plantear, tipo de ejemplos, grado de concrecion y forma de cerrar
   - distinguir que rasgos son realmente propios y cuales parecen prestados o circunstanciales
   - inferir audiencia principal, secundaria y audiencia aspiracional si la evidencia lo permite

5. **inferir primera propuesta**
   - usar el esquema recomendado de [references/editorial-profile-schema.md](references/editorial-profile-schema.md)
   - completar una version inicial editable
   - marcar cada inferencia importante con una confianza: alta, media o baja
   - anotar evidencia breve por campo cuando la inferencia no sea obvia
   - agregar preguntas abiertas para david en vez de rellenar huecos con vaguedades

6. **convertir la propuesta en perfil editable**
   - redactar campos como decisiones editables, no como analisis academico
   - preferir listas cortas, contrastes claros y ejemplos de uso o no uso
   - permitir que david pueda reescribir cada campo sin tener que reinterpretar tu analisis

7. **actualizar con feedback humano**
   - clasificar cada comentario como: confirmar, cambiar, eliminar, agregar, priorizar o posponer
   - nunca sobrescribir una preferencia explicita de david con una inferencia del modelo
   - mantener mini changelog con: campo, version anterior, version nueva y motivo del cambio
   - conservar tensiones no resueltas como preguntas abiertas si el feedback es ambiguo

8. **usar el perfil para redactar**
   - convertir el perfil en instrucciones de redaccion concretas para la pieza pedida
   - elegir solo 2 o 3 rasgos de estilo activos por pieza para evitar voz caricaturesca
   - asegurar que narrativa, tono, estilo, estrategia y reglas por canal esten alineados entre si
   - revisar el borrador contra anti-patrones antes de entregarlo

## Output format

Usar este formato por defecto para una primera version.

# perfil editorial inicial

## 0. cobertura de fuentes
- estado de muestra: suficiente | parcial | insuficiente
- fuentes usadas
- canales cubiertos
- huecos detectados

## 1. snapshot
- quien escribe
- para quien escribe
- cambio que quiere provocar
- promesa editorial central

## 2. narrativa
- tesis central
- tension recurrente
- antagonista o falso atajo
- transformacion prometida
- framing habitual
- lo que conviene evitar

## 3. tono
- tono base
- grados permitidos
- grados a evitar
- distancia con la audiencia
- marcadores utiles

## 4. estilo
- ritmo de frase
- nivel de tecnicidad
- tipo de ejemplos
- recursos retoricos frecuentes
- recursos a limitar
- micro-reglas de redaccion

## 5. estrategia comunicativa
- audiencia principal
- audiencia secundaria
- valor que se entrega primero
- mecanismo de credibilidad
- logica de cta
- frecuencia o intensidad sugerida de cta

## 6. reglas por canal
- linkedin
- newsletter
- video corto
- x u otro canal si aplica

## 7. anti-patrones
- lista priorizada de errores que rompen la voz

## 8. preguntas para david
- dudas puntuales para afinar el perfil

## 9. cambios aplicados
- solo cuando exista feedback nuevo

## 10. changelog
- version
- cambios clave
- motivo

## Editable-field rules

Tratar como editables todos los campos del perfil. En especial:

- tesis central y promesa editorial
- tension y framing preferidos
- tono base y grados permitidos
- vocabulario preferido y vocabulario vetado
- reglas de apertura, desarrollo y cierre
- sistema de cta
- reglas por canal
- anti-patrones
- preguntas abiertas y decisiones pendientes

Escribir cada campo en lenguaje de decision. Ejemplo:

- mejor: `explicar desde friccion real de practica profesional; evitar tono de gurú`
- peor: `su estilo parece combinar claridad y experiencia`

## Anti-patterns

Evitar estos fallos:

- mezclar narrativa, tono, estilo y estrategia en una sola descripcion borrosa
- declarar rasgos con seguridad alta cuando la evidencia es escasa
- copiar el timbre o las muletillas de los referentes
- entregar adjetivos genericos sin instrucciones accionables: `cercano`, `humano`, `autentico`, `inspirador`
- producir un perfil tan literario que david no pueda editarlo rapido
- imponer reglas por canal contradictorias con la estrategia general
- llenar huecos con frases de marca vacias o lenguaje de consultoria
- usar ctas uniformes para todos los canales
- convertir preferencias temporales en reglas permanentes
- fingir cobertura suficiente cuando notion o el corpus recuperado es parcial

## Drafting from the profile without sounding generic

Cuando uses el perfil para escribir una pieza:

1. elegir una sola idea principal y una sola tension por pieza
2. activar solo los rasgos de tono y estilo que ayudan a esa idea
3. incluir ejemplos, escenas, objeciones o detalles del dominio en vez de etiquetas abstractas
4. convertir el cta en una continuacion natural del argumento, no en un injerto comercial
5. revisar estas senales de genericidad antes de entregar:
   - frases intercambiables con cualquier creador
   - aperturas con lugares comunes
   - promesas infladas
   - exceso de adjetivos y poca observacion concreta
   - ritmo uniforme sin contrastes

Si detectas genericidad, reescribir desde una friccion, una observacion o una experiencia concreta del autor.

## Confidence and evidence rules

Mostrar confianza por campo cuando el perfil se derive de una muestra limitada o heterogenea.

Usar esta logica:

- **alta**: patron repetido en varias piezas y canales
- **media**: patron consistente pero con muestra reducida o concentrada en un solo contexto
- **baja**: hipotesis util para comenzar, pendiente de validacion humana

No saturar el perfil con notas metodologicas. Anotar evidencia solo donde ayude a que david acepte, rechace o edite mejor la propuesta.

## Example requests

Usar como referencia prompts de este tipo:

- `lee estas paginas de notion con mis posts, estos 5 newsletters y estos 4 referentes. construye una primera version editable de mi perfil editorial separando narrativa, tono, estilo, estrategia comunicativa, framing, cta y reglas para linkedin, newsletter y video corto.`
- `actualiza mi perfil editorial con este feedback: menos tono profesor, mas criterio y contraste; ctas mas conversacionales; en linkedin quiero entradas mas tensas y menos resumen.`
- `usa mi perfil editorial actual para redactar un post de linkedin sobre automatizacion editorial sin sonar a plantilla de ghostwriter.`

## Resources

Consultar estos recursos cuando hagan falta detalles adicionales:

- [references/editorial-profile-schema.md](references/editorial-profile-schema.md) para esquema, campos y plantilla editable
- [references/notion-retrieval-notes.md](references/notion-retrieval-notes.md) para limites practicos de Notion y manejo de cobertura parcial
