# Reddit JSON Workflow

## Objetivo

Extraer material bruto util desde un thread publico de Reddit sin depender de scraping frágil.

## Patrón base

Si la URL del thread es publica, probar:

- `thread_url + /.json`

Ejemplo conceptual:

- `https://www.reddit.com/r/sub/comments/post_slug/.json`

## Qué capturar

- titulo del hilo
- selftext
- subreddit
- score basico si existe
- comentarios principales
- replies visibles
- timestamps si ayudan a contexto

## Qué no asumir

- que todos los comentarios importantes estarán cargados
- que contenido borrado o colapsado será accesible
- que un solo thread basta para perfilar un ICP completo

## Uso posterior

Ese material se usa para:
- extraer pains
- detectar lenguaje literal
- encontrar objeciones
- generar hooks y piezas

No usar el JSON como producto final. Convertirlo en una matriz editorial.
