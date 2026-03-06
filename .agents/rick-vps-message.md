# Rick — Estado del Stack (2026-03-06)

Hola David (y @Cursor),

He aplicado el nuevo flujo de trabajo: a partir de ahora operaré sobre la rama **`rick/vps`**.

### Resumen de logros hoy:
1. **Conectividad VM Windows (Browser Relay):**
   - Se logró conectar con éxito el nodo de la VM (`PCRick`) al Gateway del VPS.
   - **Solución técnica:** Usamos `tailscale serve` en el VPS para exponer el puerto 18789 con SSL (`wss://`), sorteando el bloqueo de seguridad de OpenClaw para conexiones remotas en texto plano.
   - Se resolvieron conflictos de puerto (18792) deteniendo el Gateway local que David tenía en Windows.
   - **Estado:** El nodo está emparejado y es visible desde el VPS.

2. **Pendiente Crítico (VM):**
   - Configurar la persistencia del nodo en Windows usando `openclaw node install` para que arranque como servicio y sobreviva a reinicios.

3. **Proyecto AEC News:**
   - David aprobó un enfoque híbrido (Blog + Newsletter) usando **Ghost CMS**.
   - Issue creado en Linear: **UMB-19**.

4. **Automatización n8n:**
   - Configurado workflow de correo diario de prueba (SMTP rick.asistente@gmail.com).
   - Testeado modelo `nano-banana-pro-preview` para generación de imágenes.

### Nota para Cursor:
He habilitado la capacidad de que Rick (en el VPS) controle el navegador de la VM Windows a través del sistema de nodos de OpenClaw. La idea es usar la VM como Execution Plane para tareas que requieran una sesión de navegador real y persistente de David (Browser Relay).

Rick: Recibido y Operativo.

### ACTUALIZACIÓN 17:45 — Reinicio Proyecto Embudo (V2)
David ha ordenado el reinicio total del **Proyecto Embudo** con un enfoque autónomo y basado en datos reales.

**Acuerdos y Próximos Pasos:**
1.  **Identidad:** Mi primera tarea es absorber la identidad de David desde la carpeta de Drive en la VM. (Requiere que el nodo `PCRick` esté activo).
2.  **Investigación Real:** Usaré mis capacidades de búsqueda y análisis (Vertex, Tavily) para detectar oportunidades comerciales reales en AEC e IA, evitando alucinaciones.
3.  **Coordinación:** Dividiré el trabajo entre mis sub-agentes (Tracker, QA, Delivery) para que el stack trabaje 24/7.
4.  **Ecosistema:** Integraré el Portal AEC Tech (Ghost) como el motor de captación principal.

**Estado Git:** Trabajando en rama `rick/vps`. He creado `docs/project-embudo-master-plan.md`.
