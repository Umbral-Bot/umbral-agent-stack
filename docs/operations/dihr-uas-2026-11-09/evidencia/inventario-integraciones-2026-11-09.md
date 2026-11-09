# Inventario de integraciones observado desde TARRO (sesión coordinadora), 2026-11-09 ~05:55Z

Lecturas directas con conectores MCP de esta sesión. Solo lectura. Lo que no aparece aquí no se pudo observar desde esta superficie.

| Sistema | Superficie usada | Observado | Límite |
|---|---|---|---|
| n8n Cloud «dmbutic» | MCP n8n-dmbutic get_instance_context | 32 flujos. Recientes: «Slack → Notion AI (piloto)» (publicado), «Slack → Grok Bot · Rick Grok (relay)» (publicado, 42 ejecuciones recientes, todas OK, última hace 1 min), 6 flujos «[M5 S34/S35]» MCP Speckle/ACC (docentes). Actividad intensa hace 3 días vía n8n-mcp (≈40 versiones en un día sobre los dos flujos Slack). | Es la instancia cloud de dmbutic (memoria: no es runtime UAS; retención 7 días). El n8n del VPS (5678/5679 loopback, unit n8n activa) no se inspeccionó desde aquí. |
| Slack | MCP Slack search_channels | Canal privado #uas (C0CG0FZG456), creado por David el 2026-11-05. | No se leyeron mensajes. Capacidades de envío existen pero no se usaron. |
| Azure | MCP Azure subscription_list | Tenant f67a8c0b…; 3 suscripciones Enabled: «Azure subscription 1» (default, f14f61f0…), «MCPP Subscription» ×2 (a0d082b9…, fbb6fa43…). | No se consultaron costos ni recursos. El frente «Azure: resolver cobro y créditos» tiene un correo a soporte Microsoft enviado el 8/9-nov (hilo Rick GPT, turno 4). |
| Notion | MCP Notion | Teamspace único «Sede de Personal» (owner). Dashboard provisional (última edición 09-nov 01:07Z), ficha DIHR, 4 fichas de dependencia, página «Umbral Agent Stack» (última edición 05-oct 17:11Z). | Escritura no intentada. Rick GPT reportó bloqueo automático al editar la ficha DIHR (restricción del monitor del tablero). |
| GitHub | gh CLI (cuenta UmbralBIM, PAT) | umbral-agent-stack: PRs abiertos 710 (motor piezas, draft), 709 (cloud pilot, draft, 29-sep), 693 (HIGIENE-01, draft, 14-sep). notion-governance: PRs 48 (ADR 11 #uas), 6, 3 abiertos. origin/main UAS 97f2d87. | — |
| Google Drive | MCP Drive (subagente en curso) | pendiente | — |
| Microsoft 365 / Copilot / Outlook / SharePoint | ninguna | **No hay conector M365 en esta sesión.** | No accesible desde aquí; requiere Copilot M365 (navegador autenticado) u otra sesión. |
| Granola | ninguna directa | Solo vía Notion meeting notes (herramienta disponible, no consultada) y tarea GranolaWatcher en PCRick (última 07-11). | — |
| Linear | MCP requiere auth | No accesible. UMB-276 (incidente Rick VPS) citado como abierto al 27-sep. | Autorizar /mcp si se necesita. |
| Supabase | MCP requiere auth | No accesible. | — |
| Telegram | MCP falló conexión | No accesible desde aquí; Rick envía por Telegram desde el VPS (56 envíos desde el reset, según sesión VPS). | — |
| Mission Control | repo + VPS | Código en `mission_control/` (FastAPI+HTMX, read-only, ADR-009 de 2026-05-04). Unit `mission-control` activa en VPS desde 23-oct, /health 200, **solo loopback 127.0.0.1:8089**. Sin URL pública ni túnel: por eso Rick GPT no encontró enlace vigente. | Datos: lee openclaw.json, colas Redis, quota; «banner synthetic» en PIT. No se abrió la UI. |
