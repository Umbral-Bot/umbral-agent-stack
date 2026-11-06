# Laboratorio · Motor paramétrico de piezas gráficas (Umbral BIM)

Prototipo para producir afiches, portadas, carruseles y slides de Umbral BIM a partir
de **packs de parámetros** probados, como una definición de Grasshopper con sliders:
entra el contenido de una pieza (por ejemplo, los datos de un evento), se elige un pack
y sale la pieza. Si no convence, se prueba otro pack.

Estado: **laboratorio**. Nada de esta carpeta es producción ni skill publicada. La skill
final se versionará en el registro de skills mediante PR, cuando exista acceso.

## Reglas del laboratorio

- Un solo escritor: la sesión de Claude Code en TARRO escribe en `labs/motor-piezas/`
  de esta rama y en sus propias subcarpetas de Drive (`07_Motor de piezas/` excepto
  `00_insumos/`, que es del Director Comercial y Marketing).
- Sin escrituras en Notion. La fila del experimento en «Desarrollos y Cambios de
  Sistema» la lleva el registrador (Claude Code VPS).
- Sin gasto: la exploración de maquetación es SVG/HTML. Antes de usar créditos de
  Magnific o Midjourney se informa cuántos y se espera el OK de David.
- Entrega: PR en borrador sin merge + nota de traspaso en la ficha
  `.agents/tasks/2026-11-06-001-motor-piezas-lab.md` (qué se probó, resultado, qué
  aplicar, riesgos, cómo revertir). Revisa el coordinador provisorio de UAS (Rick GPT);
  producción solo con GO de David.
- Insumos con licencia o pesados (fuentes, lockups, imágenes generadas) no se suben a
  git: se leen desde Drive o desde `insumos/` local, que está ignorado.

## Arquitectura

### Dos capas separadas

1. **Maquetación (determinista).** Formato, grilla, márgenes, escala tipográfica,
   paleta, contraste, jerarquía y posición del logo. SVG/HTML → PNG. El mismo pack
   produce siempre la misma pieza. Base: `generate.py` de la v2 (Drive), que hoy tiene
   los valores escritos en el código; el primer trabajo es sacarlos a parámetros.
2. **Imagen (generativa).** Ilustración o fondo hecho con Midjourney, Magnific u otro.
   Entra como un hueco con proporción y modo de encaje. Cada imagen se registra con
   herramienta, modelo, prompt, referencias de estilo (`--sref`, perfil o preset),
   semilla si existe y proporción. Mover un parámetro de maquetación nunca obliga a
   regenerar la imagen.

### Reglas fijas del Manual de Marca UB-3 (no son sliders)

- Tipografías: solo Inter y JetBrains Mono.
- Logo: lockups oficiales, nunca redibujados. Dominio `umbralbim.io`.
- Turquesa como acento; nunca como texto sobre fondo claro (usar el token de texto de
  marca para kickers en claro).
- Sin brillos ni degradados en piezas corporativas; espaciado en múltiplos de 4.
- Lo que rompa estas reglas se rotula como exploración, no como pieza.

### Pipeline (tres alternativas a comparar en la primera entrega)

- **A · Grilla primero:** la grilla manda y el contenido se acomoda.
- **B · Contenido primero:** tipo de pieza y cantidad de texto definen la jerarquía y
  luego la grilla.
- **C · Imagen primero:** la ilustración define la zona libre y el texto se ubica ahí.

### Esquema de parámetros

Borrador inicial en `parametros.borrador.yaml`. Cada parámetro declara capa, tipo,
opciones o rango, valor por defecto y si lo fija el manual. Un **pack** es un conjunto
de valores con nombre, el tipo de contenido para el que funciona y la decisión de David
que lo aprobó.

### Registro de decisiones

`decisiones.csv`: número de pieza, código, pack, comentario textual de David, fecha.
Es el insumo para aprender qué packs funcionan para qué contenido.

## Hipótesis de partida (de las piezas elegidas por David)

Elegidas: v1 1°; v2 1°, 12°, 20°, 22° y 24°. Comentario de David: buena distribución,
falta ajuste espacial y decisiones de diseño gráfico.

- El bloque de título funciona; las filas de fecha, hora y lugar quedan demasiado chicas
  para leerse en el celular.
- La isometría flota sin relación con la grilla y deja vacíos grandes abajo.
- En 20° la imagen está pegada como caja; en 22° y 24° funciona mejor a lienzo completo,
  pero en 24° el título queda chico y sin zona de lectura protegida.
- Los márgenes son fijos en píxeles en todos los formatos en vez de proporcionales.

Cada problema debe convertirse en un parámetro.
