# HITL-2 blog: preflight de red (PKG-MACRO-P5-Q12-T1, 2026-08-24)

**Q12 voto B, T1 = SOLO la red.** Comprueba que Notion Publicaciones → worker
VPS → gate `telegram_confirmed` existe y responde en dry-run, sin publicar
nada. El piloto (gates humanos + publish real) es T2, con GO de David — este
pack no lo arranca. Reconteo E6 filas 14–15 no se tocan: ninguna de las dos
binarias (abrir flags / encender piloto) se ejecuta acá.

## Mapa de red (confirmado, extremo a extremo)

```
Notion Publicaciones (page CAND-OLA3-03, Canal=blog)
   ↓ (fuera de scope T1: humano marca Estado imagen / autorizar_publicacion)
Telegram "ok publica <id>" → n8n B1 (7tNkwd7DkVCEI2oz, active=true)
   → Guard allowlist → Parse → POST /enqueue {telegram_confirmed:true}
   ↓
Worker VPS /enqueue → cola Redis → openclaw-dispatcher
   → task web.publish_editorial_post
   → gate D3: Estado imagen=Seleccionada AND autorizar_publicacion=true
     AND telegram_confirmed=true
```

## [E] Sondas (todas 2026-08-24, solo lectura)

| Sonda | Resultado |
|---|---|
| `git rev-parse HEAD` vs `origin/main` | `3d23a65c` — coincide exacto con el base esperado |
| `GET /health` (worker VPS) | `{"ok":true,"version":"0.4.0",...}` |
| `systemctl --user is-active` | `umbral-worker`, `openclaw-dispatcher`, `openclaw-gateway`: los 3 `active`. Sin unit `poller` separada (vive dentro del dispatcher) |
| `NOTION_POLLER_ENABLE_HITL2_SCAN` | `<unset>` — default off, fail-closed, **no encendido** |
| `MAGNIFIC_API_KEY` | **N** (not set) |
| `NOTION_PUBLICACIONES_DB_ID` | **Y** (set, 36 chars) |
| `WORKER_URL` | `http://127.0.0.1:8088` |
| `RICK_STAGE8_IMAGE_PROVIDER` / `RICK_STAGE8_GOOGLE_IMAGE_ENABLED` | ambos `<unset>` → defaults `magnific` / `false`, stage8 sigue contenido |
| `RICK_LINKEDIN_ORG_PUBLISH_ENABLED` | `<unset>` → default `false`, stage9c contenido |
| `n8n list:workflow --active=true` | `7tNkwd7DkVCEI2oz` (B1) + `iazEnIPcxCbipnKQ` (B3) — ambos vivos, KEEP intacto post-T8 |
| Nodos de B1 (export en `infra/n8n/workflows/`) | 9 nodos: Trigger → Guard → Parse → branch → `POST /enqueue` con `telegram_confirmed:true` en el body — confirmado leyendo el JSON, camino "ok publica" completo, no hay hueco |

## Dry-run del gate (blog, sin `--live`, sin `--telegram-confirmed`)

Candidato: `CAND-OLA3-03` (Canal=blog, Estado=Borrador), leído read-only vía
`notion.read_database` — sin crear filas, sin escribir Copy, sin tocar
`aprobado_contenido`/`autorizar_publicacion`.

Salida completa, sin recortar (no hay tokens ni PII que sacar):

```
$ python scripts/editorial/trigger_hitl2_publish.py --notion-page-id 3a55f443-fb5c-81d1-b1f6-fe1b95dfd336
{
  "ok": false,
  "error": "publication_not_authorized",
  "would_publish": false,
  "source": "notion",
  "slug": null,
  "notion_page_id": "3a55f443-fb5c-81d1-b1f6-fe1b95dfd336",
  "gates": {
    "autorizar_publicacion": false,
    "aprobado_contenido": false,
    "telegram_confirmed": false,
    "visual_asset": {
      "selection_property_present": true,
      "selection": null,
      "state": null,
      "ready": false,
      "reason": "selection_missing",
      "selected_property": null,
      "selected_url": "",
      "canonical_url": "",
      "hero_source": "none"
    }
  }
}
HITL2_BLOCKED error=publication_not_authorized page_id=3a55f443-fb5c-81d1-b1f6-fe1b95dfd336
```

Exactamente el fail-closed esperado.

## Huecos

Ninguno encontrado. El camino Telegram→B1→worker existe, está activo y
confirmado con `telegram_confirmed:true` cableado. El gate del worker
responde en vivo y bloquea correctamente sin las 3 condiciones D3.

## Veredicto

**RED_OK**
