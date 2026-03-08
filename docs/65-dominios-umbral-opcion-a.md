# 65 — Estrategia de Dominios Umbral (Opción A)

> **Estado:** Documento de decisión  
> **Fecha:** 2026-03-08  
> **Decisión:** Unificar todos los proyectos bajo umbralbim.io como hub principal.

---

## 1. Arquitectura (Opción A)

### Hub principal: umbralbim.io

```
umbralbim.io              → Hub / Landing principal
umbralbim.io/app          → SaaS LLM (o app.umbralbim.io)
edu.umbralbim.io          → Educativo (Lovable — mantener)
blog.umbralbim.io         → Newsletter / Ghost (Hostinger)

umbralbim.cl              → 301 → umbralbim.io
umbral-arquitectura.com   → 301 → umbralbim.io
umbralbim.es              → 301 → umbralbim.io
umbralbim.online          → 301 → umbralbim.io
```

### Proyectos y hosting

| Proyecto | Subdominio/URL | Hosting | Estado |
|----------|----------------|---------|--------|
| **Hub / Landing** | umbralbim.io | Hostinger | Por crear |
| **SaaS LLM** | umbralbim.io o app.umbralbim.io | Lovable | En desarrollo |
| **Educativo** | edu.umbralbim.io | Lovable | Activo |
| **Newsletter** | blog.umbralbim.io | Hostinger (Ghost o estático) | Pendiente |

### Redirects 301

| Dominio | Destino |
|---------|---------|
| umbralbim.cl | https://umbralbim.io |
| umbral-arquitectura.com | https://umbralbim.io |
| umbralbim.es | https://umbralbim.io |
| umbralbim.online | https://umbralbim.io |
| www.umbralbim.io | https://umbralbim.io (si aplica) |

---

## 2. Análisis de hosting actual

### Lo que se verificó (2026-03-08)

| Dominio | Contenido visible | Hosting inferido |
|---------|-------------------|------------------|
| **umbralbim.cl** | Capacitación Microsoft AECO, Citizen Developer, Power Platform | Por confirmar (ver §3) |
| **umbral-arquitectura.com** | **Idéntico** a umbralbim.cl | Mismo proveedor que umbralbim.cl |
| **umbralbim.io** | 503 Service Unavailable | Lovable (SaaS LLM en desarrollo) |
| **edu.umbralbim.io** | "Umbral BIM \| IA para Arquitectura" — Lovable badge | Lovable |

### Acción para ubicar umbralbim.cl / umbral-arquitectura.com

1. **Revisar hPanel Hostinger**  
   - Hostinger hPanel → Websites  
   - Buscar umbralbim.cl y umbral-arquitectura.com en la lista de websites.

2. **Usar Hostinger API (MCP)**  
   ```json
   hosting_listWebsitesV1 {}
   domains_getDomainListV1 {}
   ```
   - `hosting_listWebsitesV1`: lista websites en Hostinger.  
   - `domains_getDomainListV1`: lista dominios en la cuenta Hostinger.

3. **Si no están en Hostinger**  
   - Revisar facturas / emails de compra de hosting.  
   - Posibles proveedores: WordPress.com, Wix, Carrd, Netlify, Vercel, otro shared hosting.

### Lovable (se mantiene)

- **umbralbim.io** — SaaS LLM (Lovable)  
- **edu.umbralbim.io** — Educativo (Lovable)

No hace falta mover estos dominios; Lovable gestiona el deploy. Solo configurar DNS (A/CNAME) hacia Lovable.

---

## 3. Hostinger API — Herramientas disponibles

### Dominios

| Tool | Uso |
|------|-----|
| `domains_getDomainListV1` | Listar dominios en la cuenta |
| `domains_getDomainDetailsV1` | Detalles de un dominio |
| `domains_createDomainForwardingV1` | **Crear redirect 301/302** — clave para unificar |
| `domains_getDomainForwardingV1` | Ver redirect actual |
| `domains_deleteDomainForwardingV1` | Eliminar redirect |
| `domains_updateDomainNameserversV1` | Cambiar nameservers |
| `domains_verifyDomainOwnershipV1` | Verificar propiedad |

### Hosting (websites)

| Tool | Uso |
|------|-----|
| `hosting_listWebsitesV1` | Listar websites — **usar para ver dónde están umbralbim.cl y umbral-arquitectura.com** |
| `hosting_createWebsiteV1` | Crear website (dominio + order_id) |
| `hosting_listAvailableDatacentersV1` | Datacenters disponibles |
| `hosting_verifyDomainOwnershipV1` | Verificar dominio antes de crear website |
| `hosting_deployStaticWebsite` | Deploy de sitio estático (ZIP) |
| `hosting_deployJsApplication` | Deploy de app JS/React |
| `hosting_importWordpressWebsite` | Importar WordPress |

### DNS

| Tool | Uso |
|------|-----|
| `DNS_validateDNSRecordsV1` | Validar registros DNS antes de aplicar |
| `DNS_deleteDNSRecordsV1` | Borrar registros |

### Requisitos para usar la API

- **API_TOKEN** de Hostinger (hPanel → Profile → API)  
- Dominios que vayan a usarse para forwarding deben estar **en la cuenta Hostinger** o usar nameservers de Hostinger.

---

## 4. Pasos para ejecutar (orden sugerido)

### Paso 1: Ubicar hosting de umbralbim.cl / umbral-arquitectura.com

```
1. Llamar hosting_listWebsitesV1 (MCP hostinger-mcp)
2. Llamar domains_getDomainListV1
3. Si aparecen: están en Hostinger → seguir con Paso 2
4. Si NO aparecen: buscar en facturas/emails o hPanel manual
```

### Paso 2: Migrar contenido a Hostinger (si aplica)

Si umbralbim.cl está en otro proveedor y quieres unificar en Hostinger:

- Exportar/descargar el sitio actual.  
- Crear website en Hostinger: `hosting_createWebsiteV1` con dominio `umbralbim.io`.  
- Subir contenido (estático: `hosting_deployStaticWebsite`, o WordPress/otro según tipo).  
- Ajustar DNS de umbralbim.io para que apunte a Hostinger (si aún no lo hace).

### Paso 3: Configurar redirects vía API

Con los dominios en Hostinger, crear redirects 301:

```json
domains_createDomainForwardingV1
  domain: "umbralbim.cl"
  redirect_type: "301"
  redirect_url: "https://umbralbim.io"

domains_createDomainForwardingV1
  domain: "umbral-arquitectura.com"
  redirect_type: "301"
  redirect_url: "https://umbralbim.io"

domains_createDomainForwardingV1
  domain: "umbralbim.es"
  redirect_type: "301"
  redirect_url: "https://umbralbim.io"

domains_createDomainForwardingV1
  domain: "umbralbim.online"
  redirect_type: "301"
  redirect_url: "https://umbralbim.io"
```

**Importante:** Si los dominios están en otro registrar (ej. NIC Chile para .cl) y no usan nameservers de Hostinger, el forwarding de Hostinger no aplica. En ese caso:

- Opción A: Transferir el dominio a Hostinger.  
- Opción B: Configurar redirect en el panel del registrar actual (si lo permite).  
- Opción C: Apuntar el dominio con CNAME o A a un servicio de redirect (Hostinger, Cloudflare, etc.) según la configuración que uses.

### Paso 4: Newsletter (Ghost)

- Crear website en Hostinger para blog.umbralbim.io, o  
- Usar Ghost (self-hosted en VPS o Ghost(Pro)) y apuntar blog.umbralbim.io vía CNAME.  
- Documentar en este mismo doc cuando esté definido.

### Paso 5: Lovable

- Mantener umbralbim.io y edu.umbralbim.io en Lovable.  
- Asegurar que umbralbim.io (raíz) sea el hub o el SaaS según la decisión de UX.  
- Si el hub va a estar en Hostinger, usar por ejemplo www.umbralbim.io como hub y umbralbim.io como SaaS, o subdominios como se definió arriba.

---

## 5. Resumen de necesidades Hostinger

| Necesidad | API Hostinger | ¿Suficiente? |
|-----------|---------------|--------------|
| Listar dominios | domains_getDomainListV1 | Sí |
| Listar websites | hosting_listWebsitesV1 | Sí |
| Crear redirects 301 | domains_createDomainForwardingV1 | Sí |
| Crear website | hosting_createWebsiteV1 | Sí |
| Deploy estático | hosting_deployStaticWebsite | Sí |
| Gestionar DNS | DNS_* (validar, borrar) | Parcial — depende de si usas DNS de Hostinger |

**Conclusión:** La API de Hostinger cubre lo necesario para Opción A, siempre que los dominios estén en la cuenta Hostinger o usen sus nameservers.

---

## 6. Próximos pasos inmediatos

1. [ ] Ejecutar `hosting_listWebsitesV1` y `domains_getDomainListV1` para confirmar dónde están umbralbim.cl y umbral-arquitectura.com.  
2. [ ] Actualizar este doc con el proveedor real de umbralbim.cl.  
3. [ ] Definir si el hub va en umbralbim.io (Hostinger) o en Lovable; ajustar arquitectura si hace falta.  
4. [ ] Configurar redirects una vez confirmado que los dominios se gestionan desde Hostinger.  
5. [ ] Crear en Hostinger el sitio para blog.umbralbim.io (Ghost o estático) cuando esté listo.
