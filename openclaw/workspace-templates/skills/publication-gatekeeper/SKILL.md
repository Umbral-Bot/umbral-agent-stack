---
name: publication-gatekeeper
description: asegura que chatgpt no publique, programe, envÃ­e ni deje contenido listo
  para salida externa sin aprobaciÃ³n humana explÃ­cita y trazable del texto final,
  la imagen o asset final y el canal final, ademÃ¡s de una instrucciÃ³n final inequÃ­voca
  de publicaciÃ³n como "ok, publica". usar cuando haya copy, creatividades, adjuntos,
  newsletters, posts, pÃ¡ginas, campaÃ±as, cms o automatizaciones con capacidad de
  publicar. distinguir entre borrador aprobado y orden final de salida, registrar
  quÃ© se publicÃ³, dÃ³nde y cuÃ¡ndo, y bloquear cualquier publicaciÃ³n si falta evidencia,
  si cambiÃ³ una versiÃ³n aprobada o si algÃºn componente sigue pendiente.
metadata:
  openclaw:
    emoji: 🛑
    requires:
      env: []
---

# Publication gatekeeper

Aplicar esta skill ante cualquier acciÃ³n que pueda producir salida externa inmediata o diferida: publicar, programar, enviar, poner en vivo, activar una campaÃ±a o entregar contenido a un sistema que publicarÃ¡ sin otra revisiÃ³n humana.

## Objetivo operable

Separar siempre dos hitos:

1. **borrador o componente aprobado**
2. **instrucciÃ³n final de publicar**

Nunca convertir una aprobaciÃ³n de borrador en autorizaciÃ³n de salida.

## Entradas mÃ­nimas

Antes de autorizar una salida, reunir y verificar:

- **texto final exacto** o identificador de la versiÃ³n exacta a publicar
- **imagen o asset final exacto** o la marca explÃ­cita `sin imagen`
- **canal final exacto**: cuenta, lista, sitio, comunidad, plataforma o placement concreto
- **evidencia trazable** de aprobaciÃ³n para cada componente
- **evidencia trazable** de la instrucciÃ³n final de publicar o programar

Si falta una de estas piezas, bloquear.

## QuÃ© cuenta como publicaciÃ³n

Tratar como publicaciÃ³n cualquier acciÃ³n que saque el contenido del estado de borrador, aunque no sea visible todavÃ­a:

- publicar ahora
- programar una salida
- enviar email o newsletter
- poner una pÃ¡gina o post en vivo
- activar una campaÃ±a
- subir el material a una cola, cms, scheduler o automatizaciÃ³n que no requiera otra aprobaciÃ³n humana antes de salir

## Componentes obligatorios

Verificar por separado:

### 1. Texto final

- Confirmar que el texto aprobado sea exactamente el que se publicarÃ¡.
- Si existen variantes por canal, idioma, audiencia, CTA o longitud, tratar cada variante como una versiÃ³n distinta.
- Si el enlace, CTA, asunto o encabezado cambia el resultado final, tratarlo como parte del texto final.

### 2. Imagen o asset final

- Confirmar la pieza exacta: imagen, carrusel, video, pdf, adjunto o archivo equivalente.
- No aceptar â€œla creativa estÃ¡ bienâ€ si no estÃ¡ claro cuÃ¡l es el archivo final.
- Si no habrÃ¡ asset, exigir una confirmaciÃ³n explÃ­cita y registrar `sin imagen`.

### 3. Canal final

- Confirmar el destino exacto: cuenta, pÃ¡gina, lista, sitio, plataforma, campaÃ±a o placement.
- Si hay varios canales, tratar cada canal como una aprobaciÃ³n separada.
- No asumir que una aprobaciÃ³n para LinkedIn vale tambiÃ©n para X, email, blog o ads.

### 4. InstrucciÃ³n final de publicar

- Exigir una orden humana explÃ­cita y trazable de salida.
- Aceptar `ok, publica` y equivalentes inequÃ­vocos como `publica ya`, `adelante, publica`, `ok, progrÃ¡malo para maÃ±ana a las 9`.
- Si la instrucciÃ³n final solo autoriza programar, autoriza programar, no publicar antes de ese momento.
- No inferir autorizaciÃ³n final a partir de `se ve bien`, `perfecto`, `aprobado`, `dale`, `listo` o frases ambiguas.

## Evidencia vÃ¡lida

Aceptar solo evidencia identificable y verificable, por ejemplo:

- mensaje explÃ­cito del usuario en la conversaciÃ³n actual
- cita textual aportada por el usuario con contexto suficiente
- referencia verificable a documento, ticket, comentario, email o sistema conectado

No inventar aprobaciones. No convertir resÃºmenes ambiguos en evidencia. No reaprovechar aprobaciones de una versiÃ³n anterior sin verificar que siguen aplicando a la versiÃ³n final.

## Matriz de interpretaciÃ³n

Aplicar estas reglas por defecto:

- `aprobado el copy` â†’ aprobar solo texto
- `la imagen estÃ¡ bien` â†’ aprobar solo imagen o asset
- `linkedin, no x` â†’ aprobar o corregir solo canal
- `ok, publica` â†’ aceptar como instrucciÃ³n final solo si texto, imagen o asset y canal ya estÃ¡n aprobados y sin cambios posteriores
- `ok, progrÃ¡malo para maÃ±ana a las 09:00` â†’ instrucciÃ³n final vÃ¡lida para programar si todo lo demÃ¡s estÃ¡ aprobado
- `perfecto`, `dale`, `listo`, `me sirve` â†’ ambiguo; no autoriza salida final

Ante duda, tratar la evidencia como insuficiente.

## InvalidaciÃ³n por cambios

Invalidar la aprobaciÃ³n del componente que cambie despuÃ©s de haber sido aprobado:

- texto
- imagen o asset
- canal

Si el cambio afecta materialmente al resultado final, invalidar tambiÃ©n la instrucciÃ³n final de publicar y exigir una nueva cuando todas las piezas vuelvan a estar aprobadas.

## Control previo obligatorio

Antes de cualquier acciÃ³n de salida, construir internamente esta matriz:

- texto: aprobado | pendiente | bloqueado
- imagen o asset: aprobado | pendiente | bloqueado | sin imagen
- canal: aprobado | pendiente | bloqueado
- instrucciÃ³n final: recibida | no recibida

No omitir este control aunque el usuario parezca tener prisa.

## Reglas de decisiÃ³n

### Caso 1: componentes aprobados pero falta instrucciÃ³n final

Si texto, imagen o asset y canal estÃ¡n aprobados, pero falta la orden final:

- no publicar
- no programar
- responder que estÃ¡ **listo para publicar, pero detenido**
- pedir o esperar una instrucciÃ³n final explÃ­cita

### Caso 2: falta algÃºn componente

Si falta texto, imagen o asset, o canal:

- bloquear publicaciÃ³n
- bloquear programaciÃ³n
- enumerar exactamente quÃ© falta o quÃ© perdiÃ³ validez
- indicar el siguiente paso mÃ­nimo para desbloquear

### Caso 3: hay instrucciÃ³n final pero faltan componentes

Si existe `ok, publica` o equivalente, pero falta alguna aprobaciÃ³n de componente:

- bloquear igualmente
- explicar que la instrucciÃ³n final no sustituye la aprobaciÃ³n de texto, imagen o asset y canal
- listar lo que falta antes de ejecutar

### Caso 4: todo aprobado y existe instrucciÃ³n final

Solo entonces permitir publicar o programar.

## Registro obligatorio de salida

Cada publicaciÃ³n o programaciÃ³n debe dejar un registro breve, trazable y por canal con este formato:

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

Si no puedes seÃ±alar con precisiÃ³n **quÃ© texto**, **quÃ© imagen o asset**, **quÃ© canal** y **quÃ© instrucciÃ³n final** fueron aprobados, bloquear la salida.

