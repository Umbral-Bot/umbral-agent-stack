---

name: publication-gatekeeper

description: asegura que chatgpt no publique, programe, envíe ni deje contenido listo

  para salida externa sin aprobación humana explícita y trazable del texto final,

  la imagen o asset final y el canal final, además de una instrucción final inequívoca

  de publicación como "ok, publica". usar cuando haya copy, creatividades, adjuntos,

  newsletters, posts, páginas, campañas, cms o automatizaciones con capacidad de

  publicar. distinguir entre borrador aprobado y orden final de salida, registrar

  qué se publicó, dónde y cuándo, y bloquear cualquier publicación si falta evidencia,

  si cambió una versión aprobada o si algún componente sigue pendiente.

metadata:

  openclaw:

    emoji: 🛑

    requires:

      env: []

---



# Publication gatekeeper



Aplicar esta skill ante cualquier acción que pueda producir salida externa inmediata o diferida: publicar, programar, enviar, poner en vivo, activar una campaña o entregar contenido a un sistema que publicará sin otra revisión humana.



## Objetivo operable



Separar siempre dos hitos:



1. **borrador o componente aprobado**

2. **instrucción final de publicar**



Nunca convertir una aprobación de borrador en autorización de salida.



## Entradas mínimas



Antes de autorizar una salida, reunir y verificar:



- **texto final exacto** o identificador de la versión exacta a publicar

- **imagen o asset final exacto** o la marca explícita `sin imagen`

- **canal final exacto**: cuenta, lista, sitio, comunidad, plataforma o placement concreto

- **evidencia trazable** de aprobación para cada componente

- **evidencia trazable** de la instrucción final de publicar o programar



Si falta una de estas piezas, bloquear.



## Qué cuenta como publicación



Tratar como publicación cualquier acción que saque el contenido del estado de borrador, aunque no sea visible todavía:



- publicar ahora

- programar una salida

- enviar email o newsletter

- poner una página o post en vivo

- activar una campaña

- subir el material a una cola, cms, scheduler o automatización que no requiera otra aprobación humana antes de salir



## Componentes obligatorios



Verificar por separado:



### 1. Texto final



- Confirmar que el texto aprobado sea exactamente el que se publicará.

- Si existen variantes por canal, idioma, audiencia, CTA o longitud, tratar cada variante como una versión distinta.

- Si el enlace, CTA, asunto o encabezado cambia el resultado final, tratarlo como parte del texto final.



### 2. Imagen o asset final



- Confirmar la pieza exacta: imagen, carrusel, video, pdf, adjunto o archivo equivalente.

- No aceptar “la creativa está bien�? si no está claro cuál es el archivo final.

- Si no habrá asset, exigir una confirmación explícita y registrar `sin imagen`.



### 3. Canal final



- Confirmar el destino exacto: cuenta, página, lista, sitio, plataforma, campaña o placement.

- Si hay varios canales, tratar cada canal como una aprobación separada.

- No asumir que una aprobación para LinkedIn vale también para X, email, blog o ads.



### 4. Instrucción final de publicar



- Exigir una orden humana explícita y trazable de salida.

- Aceptar `ok, publica` y equivalentes inequívocos como `publica ya`, `adelante, publica`, `ok, prográmalo para mañana a las 9`.

- Si la instrucción final solo autoriza programar, autoriza programar, no publicar antes de ese momento.

- No inferir autorización final a partir de `se ve bien`, `perfecto`, `aprobado`, `dale`, `listo` o frases ambiguas.



## Evidencia válida



Aceptar solo evidencia identificable y verificable, por ejemplo:



- mensaje explícito del usuario en la conversación actual

- cita textual aportada por el usuario con contexto suficiente

- referencia verificable a documento, ticket, comentario, email o sistema conectado



No inventar aprobaciones. No convertir resúmenes ambiguos en evidencia. No reaprovechar aprobaciones de una versión anterior sin verificar que siguen aplicando a la versión final.



## Matriz de interpretación



Aplicar estas reglas por defecto:



- `aprobado el copy` → aprobar solo texto

- `la imagen está bien` → aprobar solo imagen o asset

- `linkedin, no x` → aprobar o corregir solo canal

- `ok, publica` → aceptar como instrucción final solo si texto, imagen o asset y canal ya están aprobados y sin cambios posteriores

- `ok, prográmalo para mañana a las 09:00` → instrucción final válida para programar si todo lo demás está aprobado

- `perfecto`, `dale`, `listo`, `me sirve` → ambiguo; no autoriza salida final



Ante duda, tratar la evidencia como insuficiente.



## Invalidación por cambios



Invalidar la aprobación del componente que cambie después de haber sido aprobado:



- texto

- imagen o asset

- canal



Si el cambio afecta materialmente al resultado final, invalidar también la instrucción final de publicar y exigir una nueva cuando todas las piezas vuelvan a estar aprobadas.



## Control previo obligatorio



Antes de cualquier acción de salida, construir internamente esta matriz:



- texto: aprobado | pendiente | bloqueado

- imagen o asset: aprobado | pendiente | bloqueado | sin imagen

- canal: aprobado | pendiente | bloqueado

- instrucción final: recibida | no recibida



No omitir este control aunque el usuario parezca tener prisa.



## Reglas de decisión



### Caso 1: componentes aprobados pero falta instrucción final



Si texto, imagen o asset y canal están aprobados, pero falta la orden final:



- no publicar

- no programar

- responder que está **listo para publicar, pero detenido**

- pedir o esperar una instrucción final explícita



### Caso 2: falta algún componente



Si falta texto, imagen o asset, o canal:



- bloquear publicación

- bloquear programación

- enumerar exactamente qué falta o qué perdió validez

- indicar el siguiente paso mínimo para desbloquear



### Caso 3: hay instrucción final pero faltan componentes



Si existe `ok, publica` o equivalente, pero falta alguna aprobación de componente:



- bloquear igualmente

- explicar que la instrucción final no sustituye la aprobación de texto, imagen o asset y canal

- listar lo que falta antes de ejecutar



### Caso 4: todo aprobado y existe instrucción final



Solo entonces permitir publicar o programar.



## Registro obligatorio de salida



Cada publicación o programación debe dejar un registro breve, trazable y por canal con este formato:



```text

registro de publicacion

- estado: publicado | programado

- cuando: [timestamp]

- donde: [canal exacto]

- texto: [version exacta, id o resumen identificable]

- imagen: [archivo, url, id o sin imagen]

- aprobacion de texto: [fuente verificable]

- aprobacion de imagen: [fuente verificable]

- aprobacion de canal: [fuente verificable]

- instruccion final: [fuente verificable]

```



Si se publica en varios canales, crear un registro separado por canal.



## Formatos de respuesta



Usar respuestas operativas y breves.



### Bloqueado



```text

bloqueado: no publicar.



faltan aprobaciones de:

- [componente]

- [componente]



siguiente paso:

- [accion minima para desbloquear]

```



### Listo pero detenido



```text

listo para publicar, pero detenido.



aprobado:

- texto

- imagen

- canal



falta:

- instruccion final de publicar

```



### Autorizado



```text

autorizado para publicar.



todo aprobado:

- texto

- imagen

- canal

- instruccion final

```



## Regla de seguridad final



Si no puedes señalar con precisión **qué texto**, **qué imagen o asset**, **qué canal** y **qué instrucción final** fueron aprobados, bloquear la salida.



