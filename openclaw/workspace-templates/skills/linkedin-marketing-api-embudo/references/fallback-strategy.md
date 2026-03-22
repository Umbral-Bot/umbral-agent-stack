# fallback strategy

Usar esta guía cuando el deseo del usuario supera lo que la API oficial soporta o lo que el acceso actual permite.

## 1. principio

No reemplazar una limitación oficial con una automatización frágil sin decirlo claramente.

Cada fallback debe etiquetarse como uno de estos:
- `manual viable`
- `semi-automatizable con gate humano`
- `técnicamente posible pero no recomendado`
- `rechazar por fuera de scope`

## 2. orden de fallback

### A. rediseñar el caso hacia organization

Cuando el pedido apunta a perfil personal pero el objetivo real es distribución, reporting, captura o community management institucional, intentar mover el diseño a:
- organization posting
- analytics de organization
- lead forms oficiales
- reporting de ads

### B. automatizar solo el handoff interno

Cuando la acción final no conviene automatizarse:
- usar Notion para cola y checklist
- usar Linear para seguimiento
- usar OpenClaw para preparar borradores y decisiones
- usar n8n para handoff, observabilidad y recordatorios

### C. browser o RPA con uso mínimo y explícito

Solo considerar browser o RPA cuando:
- no haya alternativa oficial suficiente
- el caso sea puntual y reversible
- exista aprobación humana clara
- no contradiga documentación ni términos aplicables

Nunca vender esto como capacidad nativa de LinkedIn Marketing API.

## 3. situaciones comunes

### deseo: automatizar perfil personal
Respuesta base:
- `soportado por la api`: no asumirlo como baseline de embudo
- `requiere aprobacion`: depende del producto exacto y del scope exacto
- `no recomendado`: usar member automation como pilar del embudo
- `fallback`: mover a company page o dejar publicación manual con gate humano

### deseo: leer actividad personal a escala
Respuesta base:
- no venderlo como capacidad estándar
- recordar que `r_member_social` es restringido
- fallback: usar reporting de organization o trazabilidad interna

### deseo: leer posts de terceros o perfiles a escala
Respuesta base:
- no venderlo como Marketing API
- no redirigir a scraping como solución cómoda
- fallback: curación manual o diseño alternativo del caso

### deseo: enviar DMs automáticos
Respuesta base:
- bloquear por defecto
- no redirigir a bots o scraping como salida fácil
- fallback: nurturing por contenido, lead forms oficiales o handoff humano

### deseo: community management en tiempo real desde Development tier
Respuesta base:
- revisar si el flujo depende de social action webhooks o `BATCH_GET`
- si depende de eso, marcar `requiere aprobacion` o `semi-automatizable con gate humano`
- fallback: polling moderado, colas internas y revisión humana

### deseo: nueva captación basada en page lead forms
Respuesta base:
- validar primero el estado actual del producto
- no prometer creación nueva si la documentación vigente la limita
- fallback: aprovechar forms existentes, event leads, ad leads o rediseñar la captura

## 4. redacción recomendada ante un bloqueo

Usar frases como:
- `para embudo sí conviene automatizar x por api, pero y queda bloqueado hasta aprobación`
- `la alternativa prudente es dejar esta parte manual y automatizar solo el handoff interno`
- `esto no debería entrar al alcance inicial porque empuja al stack hacia automatización no soportada`
- `conviene rediseñar el caso para organization, lead sync o analytics`

## 5. redacción a evitar

Evitar frases como:
- `se puede scrapeando`
- `si no da la api, usamos browser y listo`
- `hacemos lo mismo sobre perfil personal`
- `después vemos permisos`
- `seguro nos lo aprueban`

## 6. salida final en un caso bloqueado

Cuando el caso no sea viable por API oficial, cerrar con:
1. qué parte sí conviene automatizar
2. qué parte requiere aprobación o queda bloqueada
3. qué parte no se recomienda perseguir
4. fallback mínimo aceptable
5. siguiente acción de bajo riesgo
