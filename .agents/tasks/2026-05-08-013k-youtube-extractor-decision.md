# Task: 013-K — Decisión extractor YouTube (David)

- **ID**: 013-K-decision
- **Owner**: David (decisión humana, no agente)
- **Estado**: blocked-on-decision
- **Bloquea**: 013-K (adapter Stage 2 youtube)
- **Creada**: 2026-05-07
- **Ref**: PR #336 (spike 013-J), `reports/spike-youtube-20260507T055904Z.md`

## Contexto

PR #336 confirmó que la IP de la VPS está **bloqueada por YouTube** en los 3 vectores probados desde la VPS:

- `yt-dlp` → 429 / sign-in challenge.
- `youtube-transcript-api` → IP block.
- Atom feed (`/feeds/videos.xml?channel_id=...`) → respuesta vacía / bloqueada.

Resultado runtime hoy: hay **15 items pendientes** de canal `youtube` en el pipeline editorial sin `body` (created_no_body), porque ningún path desde la VPS puede extraer transcript ni metadata enriquecida.

## Opciones

### Opción 1 — Mover extracción YouTube al Worker Windows VM (residencial)

- **Pro**: reusa infra existente; IP residencial argentina probablemente no bloqueada por YouTube; el handler `youtube.extract` queda igual, solo cambia el host de ejecución.
- **Con**: requiere VM estable encendida 24×7 (hoy no lo está); agrega dependencia de red entre VPS y VM (Tailscale ya existe pero un punto más de fallo); debuggeo más complejo.
- **Esfuerzo**: M (1-2 días). Implica wrapper HTTP en Worker VM + ruta dispatcher → VM cuando `channel == "youtube"`.

### Opción 2 — YouTube Data API v3 (oficial, sin transcripts)

- **Pro**: API oficial, sin riesgo de bloqueo IP; cuota generosa (10,000 unidades/día gratis); estable y documentada.
- **Con**: **NO** devuelve transcripts (esa es la limitación clave); solo metadata (título, descripción, tags, duración, estadísticas). Para nuestro pipeline editorial el transcript es lo más valioso del Stage 2.
- **Esfuerzo**: S (medio día). Solo OAuth2 + cliente HTTP + parser.

### Opción 3 — Proxy residencial (BrightData / Oxylabs)

- **Pro**: yt-dlp completo funciona, incluyendo transcripts; sin tocar arquitectura.
- **Con**: **costo recurrente** (~USD 50-500/mes según volumen); dependencia externa; posible degradación si YouTube refina detección anti-proxy.
- **Esfuerzo**: S (medio día). Solo configurar HTTP_PROXY en yt-dlp.

### Opción 4 — Aceptar `created_no_body` para canal=youtube y diferir

- **Pro**: 0 esfuerzo inmediato; descarga el problema a Q3.
- **Con**: 15 items quedan incompletos en el pipeline; UX degradada (David ve cards sin body); NO resuelve raíz, solo posterga.
- **Esfuerzo**: 0.

## Recomendación coordinador

**Combinar (1) + (2) — VM como primario, Data API como fallback estructurado.**

Razonamiento:

- Opción 1 da el máximo (transcript + metadata) cuando la VM está viva.
- Opción 2 garantiza al menos metadata estructurada cuando la VM está caída.
- El handler decide en runtime: `if vm_alive: extract_via_vm() else: extract_via_data_api()`.
- 0 costo recurrente (vs Opción 3).
- Riesgo distribuido (vs single point con cualquier opción individual).

Trade-off honesto: requiere mantener la VM más estable que hoy. Si David no quiere ese compromiso → Opción 3 (paga proxy) o Opción 4 (acepta créditos).

## Aceptación

David elige opción (o combinación) y se abre 013-K con scope concreto:

- **Si Opción 1**: 013-K-vm-extractor — handler en Worker VM + ruta condicional dispatcher.
- **Si Opción 2**: 013-K-data-api-fallback — cliente Data API v3 con OAuth.
- **Si Opción 1+2**: ambos handlers + lógica de fallback.
- **Si Opción 3**: 013-K-proxy — config yt-dlp con HTTP_PROXY + secret.
- **Si Opción 4**: marcar 013-K como wontfix Q2; revisar Q3.

## Referencias

- PR #336 (spike): https://github.com/Umbral-Bot/umbral-agent-stack/pull/336
- Reporte spike: [`reports/spike-youtube-20260507T055904Z.md`](../../reports/spike-youtube-20260507T055904Z.md)
- ADR-005 publicación multicanal: [`docs/adr/ADR-005-publicacion-multicanal.md`](../../docs/adr/ADR-005-publicacion-multicanal.md)
