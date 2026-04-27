# Resumen: Estrategia web y páginas Umbral

> Redactado a partir de la Opción A (docs/65, 66) y perfil/servicios (identity/).  
> Uso: brief para equipos, Rick, o para pedir diseños/copys.

---

## 1. Idea central

Unificar la presencia digital de David Moreira (Umbral BIM) bajo **umbralbim.io** como hub principal. Un solo punto de entrada que presenta quién es David, qué ofrece y lleva a cada producto: la app de IA para AECO, la formación (Edu), el blog y la newsletter. El resto de dominios (umbralbim.cl, umbral-arquitectura.com, umbralbim.es, umbralbim.online) redirigen con 301 al hub.

---

## 2. Estructura de páginas y proyectos

### Hub / Landing — umbralbim.io

- **Qué es:** Página principal del ecosistema.
- **Contenido:** Quién es David (Arquitecto, consultor en transformación digital, docente y comunicador; perfil T-shaped: BIM + IA y automatización; propuesta “traductor tecnológico para AECO”). Sección de **servicios** (consultoría, formación, producto). Enlaces claros a la app, a Edu y al blog/newsletter. Llamadas a la acción (registrarse, probar producto, contactar).
- **Tono:** Directo, profesional, orientado a conversión.
- **Hosting:** Hostinger (por crear).

### Servicios (en el Hub)

La oferta se presenta en el hub y se profundiza en cada subdominio:

- **Consultoría:** Transformación digital, BIM, IA aplicada a AECO, BI/CDEs, coordinación.
- **Formación:** Cursos, docencia (Master AEC 4.0, COMGRAP, UTFSM), capacitación.
- **Producto:** Umbral BIM como SaaS (chatbot IA para AECO), accesible desde umbralbim.io/app o app.umbralbim.io.

### App (SaaS) — umbralbim.io/app o app.umbralbim.io

- **Qué es:** Producto Umbral BIM: aplicación con IA (LLM) para el sector AECO.
- **Contenido:** Login/registro, rutas de uso (autodidacta, guiada, premium), CTAs de upgrade.
- **Tono:** Técnico, orientado al uso del producto.
- **Hosting:** Lovable (en desarrollo).

### Edu — edu.umbralbim.io

- **Qué es:** Sitio educativo: rutas de aprendizaje y recursos curados.
- **Contenido:** Rutas autodidacta, formación, recursos; enlaces al producto y al hub.
- **Tono:** Didáctico.
- **Hosting:** Lovable (activo).

### Blog y newsletter — blog.umbralbim.io

- **Qué es:** Blog + newsletter: artículos y contenido AEC/BIM, suscripción.
- **Contenido:** Artículos, suscripción a newsletter, enlaces al hub y al producto.
- **Tono:** Más informal, aporte de valor, storytelling.
- **Hosting:** Hostinger (Ghost o sitio estático; pendiente).

### Sobre mí / David Moreira

- **Dónde:** Sección destacada en el hub (umbralbim.io) y, si se desea, página dedicada (p. ej. david.moreira.umbralbim.io o umbralbim.io/sobre-mi).
- **Contenido:** Perfil profesional (Arquitecto UTFSM, consultor, docente, comunicador), casos relevantes (OXXO Chile, Borago, WSP España, Dessau Perú), propuesta de valor y enlace a servicios y productos.

---

## 3. Navegación y enlaces

Desde el hub (umbralbim.io):

- **Servicios** → consultoría, formación, producto (con enlace a la app).
- **Umbral BIM (app)** → umbralbim.io/app (o app.umbralbim.io).
- **Edu** → edu.umbralbim.io.
- **Blog / Newsletter** → blog.umbralbim.io.
- **Sobre mí / David Moreira** → sección o página dedicada.
- **Footer:** contacto, redes, legal.

Cada subsitio (app, edu, blog) enlaza de vuelta al hub y, cuando aplique, a los otros (app, edu, blog).

---

## 4. Redirects (301)

| Dominio                | Redirige a           |
|------------------------|----------------------|
| umbralbim.cl           | https://umbralbim.io |
| umbral-arquitectura.com| https://umbralbim.io |
| umbralbim.es           | https://umbralbim.io |
| umbralbim.online       | https://umbralbim.io |
| www.umbralbim.io       | https://umbralbim.io |

---

## 5. Resumen en una frase

**Un hub en umbralbim.io (David, servicios, CTAs) que enlaza a la app de IA (Lovable), al sitio educativo (Edu) y al blog/newsletter (Hostinger); el resto de dominios redirigen al hub.**

---

## Referencias en repo

- [65-dominios-umbral-opcion-a.md](65-dominios-umbral-opcion-a.md) — Decisión y detalle técnico (hosting, API Hostinger).
- [66-rick-instrucciones-dominios-y-paginas.md](66-rick-instrucciones-dominios-y-paginas.md) — Instrucciones para Rick (diagnóstico, redirects, estructura).
- `identity/01-perfil.md`, `identity/02-servicios-actuales.md` — Perfil y servicios actuales.
