# 66 — Instrucciones para Rick: Dominios Umbral y Estructura de Páginas

> **Para David:** Usa este documento para encargar a Rick la unificación de dominios y la estructura de páginas.  
> **Para Rick:** Lee este doc y ejecuta según el encargo de David. Referencia técnica: [docs/65-dominios-umbral-opcion-a.md](65-dominios-umbral-opcion-a.md)

---

## 1. Objetivo

Unificar todos los proyectos de David bajo **umbralbim.io** como hub principal (Opción A), configurar redirects de los demás dominios y establecer la estructura de páginas.

---

## 2. Estructura de páginas (definición)

### Mapa de URLs y contenido

| URL | Proyecto | Contenido | Hosting |
|-----|----------|-----------|---------|
| **umbralbim.io** | Hub / Landing | Página principal: quién es David, servicios, enlaces a producto/edu/blog, CTA | Hostinger |
| **umbralbim.io/app** o **app.umbralbim.io** | SaaS LLM | Producto Umbral BIM (chatbot IA para AECO) | Lovable |
| **edu.umbralbim.io** | Educativo | Ruta autodidacta, formación, recursos | Lovable |
| **blog.umbralbim.io** | Newsletter | Artículos, newsletter, contenido AEC/BIM | Hostinger (Ghost o estático) |

### Jerarquía y navegación

```
umbralbim.io (Hub)
├── Sección: Sobre mí / David Moreira
├── Sección: Servicios (consultoría, formación, producto)
├── Enlaces a:
│   ├── Umbral BIM (app) → umbralbim.io/app
│   ├── Edu → edu.umbralbim.io
│   └── Blog / Newsletter → blog.umbralbim.io
├── CTA: Registrarse / Probar gratis
└── Footer: contacto, redes, legal

umbralbim.io/app (SaaS)
├── Login / Registro
├── Rutas: autodidacta / guiada / premium
└── CTA: Upgrade a Pro

edu.umbralbim.io (Educativo)
├── Rutas de aprendizaje
├── Recursos curados
└── CTA: Ir al producto

blog.umbralbim.io (Newsletter)
├── Artículos
├── Suscripción newsletter
└── Enlaces al hub y al producto
```

### Reglas de contenido por página

| Página | Tono | Enlaces obligatorios |
|--------|------|----------------------|
| Hub | Directo, profesional, orientado a conversión | App, Edu, Blog, contacto |
| App (SaaS) | Técnico, orientado a uso | Hub, Edu |
| Edu | Didáctico, recursos | App, Hub |
| Blog | Informal, valor, storytelling | Hub, App, suscripción |

### Redirects (301)

| Dominio | Destino |
|---------|---------|
| umbralbim.cl | https://umbralbim.io |
| umbral-arquitectura.com | https://umbralbim.io |
| umbralbim.es | https://umbralbim.io |
| umbralbim.online | https://umbralbim.io |
| www.umbralbim.io | https://umbralbim.io |

---

## 3. Instrucciones paso a paso para Rick

### Fase 1: Diagnóstico (hacer primero)

1. **Listar dominios en Hostinger**
   - Usar MCP `hostinger-mcp` → `domains_getDomainListV1` (argumentos vacíos).
   - Documentar en un comentario o en `.agents/rick-vps-message.md` qué dominios aparecen (umbralbim.cl, umbral-arquitectura.com, umbralbim.io, etc.).

2. **Listar websites en Hostinger**
   - Usar MCP `hostinger-mcp` → `hosting_listWebsitesV1` (sin filtros o con `domain` para umbralbim.cl, umbral-arquitectura.com).
   - Documentar qué websites existen y a qué dominio pertenecen.

3. **Informar a David**
   - Resumir: qué dominios están en Hostinger, qué websites existen y dónde está alojado el contenido actual de umbralbim.cl y umbral-arquitectura.com.
   - Si umbralbim.cl no está en Hostinger, indicar que David debe revisar facturas/emails para localizar el proveedor.

### Fase 2: Redirects (si los dominios están en Hostinger)

4. **Crear redirects 301** para cada dominio secundario:
   - `domains_createDomainForwardingV1`: domain, redirect_type "301", redirect_url "https://umbralbim.io"
   - Dominios: umbralbim.cl, umbral-arquitectura.com, umbralbim.es, umbralbim.online
   - Solo si el dominio aparece en `domains_getDomainListV1`. Si no está en Hostinger, saltar y reportar.

5. **Verificar redirects**
   - Usar `domains_getDomainForwardingV1` para cada dominio tras configurarlos.

### Fase 3: Documentación (siempre)

6. **Actualizar docs**
   - En `docs/65-dominios-umbral-opcion-a.md`, sección "Análisis de hosting actual", completar la tabla "Hosting inferido" con el resultado del diagnóstico.
   - Marcar como hechos los pasos ejecutados.

7. **Dejar mensaje para David**
   - En `.agents/rick-vps-message.md` (rama `rick/vps`): qué hizo, qué falló (si aplica), qué requiere decisión de David.

---

## 4. Limitaciones de Rick

- **Rick en VPS** no tiene MCP Hostinger por defecto. Si David quiere que Rick ejecute las herramientas Hostinger, debe hacerlo desde un contexto donde Rick tenga acceso a ese MCP (por ejemplo Cursor con el MCP activo, o una tarea que invoque la API de Hostinger vía Worker si se implementa).
- **Lovable** se gestiona desde Lovable.dev; Rick no puede desplegar ni modificar edu.umbralbim.io o umbralbim.io/app desde aquí.
- **Ghost** (blog) se configura manualmente o con scripts; Rick puede documentar los pasos pero no ejecutar la instalación de Ghost sin que David lo autorice y proporcione credenciales.

---

## 5. Prompt listo para David (copiar y pegar a Rick)

### Opción corta (Notion / Telegram)

```
Rick: Necesito que ejecutes la unificación de dominios Umbral (Opción A). 

1. Usa el MCP hostinger-mcp para llamar domains_getDomainListV1 y hosting_listWebsitesV1.
2. Documenta qué dominios y websites aparecen en Hostinger (en especial umbralbim.cl y umbral-arquitectura.com).
3. Si esos dominios están en Hostinger, configura redirects 301 de umbralbim.cl, umbral-arquitectura.com, umbralbim.es y umbralbim.online hacia https://umbralbim.io.
4. Actualiza docs/65-dominios-umbral-opcion-a.md con el resultado del diagnóstico.
5. Deja un resumen en .agents/rick-vps-message.md.

Referencia: docs/66-rick-instrucciones-dominios-y-paginas.md y docs/65-dominios-umbral-opcion-a.md.
```

### Opción completa (con estructura de páginas)

```
Rick: Ejecuta la unificación de dominios Umbral (Opción A) y documenta la estructura de páginas.

**Dominios y redirects:**
- Hub principal: umbralbim.io
- Redirects 301: umbralbim.cl, umbral-arquitectura.com, umbralbim.es, umbralbim.online → https://umbralbim.io

**Estructura de páginas:**
- umbralbim.io → Hub/Landing (Hostinger): quién es David, servicios, enlaces a app/edu/blog, CTA
- umbralbim.io/app o app.umbralbim.io → SaaS LLM (Lovable)
- edu.umbralbim.io → Educativo (Lovable, mantener)
- blog.umbralbim.io → Newsletter (Hostinger, Ghost o estático)

**Pasos:**
1. Usa MCP hostinger-mcp: domains_getDomainListV1 y hosting_listWebsitesV1.
2. Documenta en docs/65-dominios-umbral-opcion-a.md dónde están umbralbim.cl y umbral-arquitectura.com.
3. Si están en Hostinger, crea redirects 301 con domains_createDomainForwardingV1.
4. Deja resumen en .agents/rick-vps-message.md.

Ref: docs/66-rick-instrucciones-dominios-y-paginas.md
```

### Opción solo estructura (para redacción de contenido)

```
Rick: Cuando redactes o generes contenido para las páginas de umbralbim.io, sigue esta estructura:

**umbralbim.io (Hub):** Quién es David, servicios (consultoría, formación, producto), enlaces a app, edu y blog. Tono directo, profesional. CTA principal: registrarse o probar el producto.

**umbralbim.io/app (SaaS):** Producto LLM para AECO. Rutas autodidacta/guiada/premium. Tono técnico.

**edu.umbralbim.io:** Educativo, recursos, rutas de aprendizaje. Tono didáctico.

**blog.umbralbim.io:** Newsletter, artículos AEC/BIM. Tono informal, valor.

Cada página debe enlazar a las otras cuando sea relevante. Ref: docs/66-rick-instrucciones-dominios-y-paginas.md
```

---

## 6. Referencias

- **Decisión y arquitectura:** [docs/65-dominios-umbral-opcion-a.md](65-dominios-umbral-opcion-a.md)
- **Instrucciones VPS y rama rick/vps:** [docs/rick-instrucciones-vps-rama-rick.md](rick-instrucciones-vps-rama-rick.md)
- **Mensaje para David/Cursor:** [.agents/rick-vps-message.md](../.agents/rick-vps-message.md)
