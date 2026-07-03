# Magnific — integración editorial (2026-06-06)

> **Estado:** configuración inicial
> **Flujo:** `docs/editorial-pipeline/production-flow-v2-2026-06-06.md` — imágenes **después** de Gate 1 "Texto aprobado"
> **Proveedor:** Magnific MCP `https://mcp.magnific.com` (OAuth cuenta Magnific; sin API key en MCP)

## Rol en el pipeline

```text
Gate 1 texto aprobado (Notion)
  → Rick / Worker llama Magnific
  → images_generate (N variantes, p.ej. 3)
  → creations_wait / creation_status hasta COMPLETED
  → subir URLs/archivos a Notion (Imágenes candidatas)
  → David elige 1 imagen + Gate 2
```

## Tools Magnific relevantes

| Tool | Uso editorial |
|------|----------------|
| `account_balance` | Smoke: créditos antes de generar |
| `images_generate` | Generar variantes desde brief visual del post |
| `images_models_list` | Elegir modelo; hero editorial **`4:3`** |
| `creations_wait` / `creation_status` | Esperar jobs async |
| `creations_get` / `creations_show` | Recuperar URL final |

Magnific también expone REST API (`x-magnific-api-key`) para integraciones headless sin OAuth. El MCP es el camino para **Rick/OpenClaw**; el REST queda como fallback Worker si OAuth en VPS es incómodo.

## Cursor (Windows — smoke manual)

En `~/.cursor/mcp.json`:

```json
"magnific": {
  "url": "https://mcp.magnific.com"
}
```

1. Recargar MCP en Cursor (Settings → MCP → Reload).
2. Primera conexión: OAuth Magnific en el browser.
3. Smoke: pedir `account_balance` y una `images_generate` de prueba.

## OpenClaw VPS (Rick producción)

```bash
export PATH=/home/rick/.npm-global/bin:/usr/bin:/bin:$PATH
openclaw mcp set magnific '{"command":"npx","args":["-y","mcp-remote","https://mcp.magnific.com"]}'
openclaw mcp list
systemctl --user restart openclaw-gateway
```

**OAuth en VPS (obligatorio una vez):** `mcp-remote` guarda tokens en `~/.mcp-auth/mcp-remote-0.1.37/`. Sin tokens, OpenClaw devuelve `Authentication required` o timeout 30s al arrancar `bundle-mcp`.

### Flujo recomendado (túnel + browser)

**Terminal 1 (Windows):**
```powershell
ssh -N -L 11390:127.0.0.1:11390 vps-umbral
```

**Terminal 2 (VPS):**
```bash
bash ~/umbral-agent-stack/scripts/ops/magnific-oauth-vps.sh
```

1. El script imprime una URL `auth.magnific.com/...` — abrirla **en el browser** (no reutilizar URLs viejas).
2. Iniciar sesión en Magnific y aprobar.
3. El redirect a `http://localhost:11390/oauth/callback` debe volver por el túnel SSH.
4. Cuando aparezca `*_tokens.json` en `~/.mcp-auth/mcp-remote-0.1.37/`, OAuth OK.

**Si ves `400 Client not found`:** el cliente OAuth quedó huérfano. Reset:
```bash
pkill -f mcp-remote || true
rm -f ~/.mcp-auth/mcp-remote-0.1.37/d26f403b39e8b4247ae67c898076d604_*
bash ~/umbral-agent-stack/scripts/ops/magnific-oauth-vps.sh
```
(usar la URL **nueva** que imprima el script)

**Alternativa UI:** OpenClaw Control → Automations → `1 MCP server` → Configure (misma cuenta Magnific).

**Fallback producción (sin MCP OAuth):** API key REST en `~/.config/openclaw/env` como `MAGNIFIC_API_KEY` + script Worker.

## Brief visual para `images_generate` (plantilla)

Derivar del copy aprobado en Notion:

```yaml
prompt: >
  Professional LinkedIn hero for AEC/BIM audience. [escena del post].
  Sobrio, técnico, anti-hype. No personas foto-real generadas.
  Composición clara para feed LinkedIn.
aspect_ratio: "4:3"
variants: 3
```

Reglas ADR-006 anti-slop: sin rostros foto-real AI; preferir diagramas/screenshots cuando el post es técnico.

## Notion — propiedades (v2)

| Propiedad | Tipo sugerido | Quién escribe |
|-----------|---------------|---------------|
| `Imágenes candidatas` | Files o URLs en body | Rick automático |
| `Imagen seleccionada` | Select / relation | David (Gate 2) |

## Veredictos operativos

| Veredicto | Cuándo |
|-----------|--------|
| `MAGNIFIC_MCP_CONNECTED` | `account_balance` responde |
| `MAGNIFIC_IMAGES_READY` | N imágenes en Notion tras Gate 1 |
| `MAGNIFIC_INSUFFICIENT_CREDITS` | balance bajo — bloquear generación |

## Pendientes

- [ ] OAuth Magnific completado en Cursor
- [ ] OAuth Magnific completado en OpenClaw VPS (o REST fallback)
- [ ] Script `scripts/editorial/magnific_generate_variants.py` (Gate 1 → Notion)
- [ ] Skill Rick `openclaw/workspace-templates/skills/magnific-editorial/SKILL.md`

## Referencias

- Magnific MCP: https://docs.magnific.com/modelcontextprotocol
- `docs/adr/ADR-006-capa-visual-editorial.md` (update Magnific)
- `docs/editorial-pipeline/production-flow-v2-2026-06-06.md`
