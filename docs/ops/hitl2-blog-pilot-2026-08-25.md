# HITL-2 blog: piloto live — closeout (PKG-MACRO-P5-Q12-T2, 2026-08-25)

Q12 voto B, T2 = el piloto live (no dry-run). Candidato horneado en T1:
`CAND-OLA3-03`, page_id `3a55f443-fb5c-81d1-b1f6-fe1b95dfd336`, Canal=blog.
Ver preflight de red: [docs/ops/hitl2-red-preflight-2026-08-24.md](hitl2-red-preflight-2026-08-24.md).

## Fase A — preflight (solo lectura, 2026-08-25)

| Sonda | Resultado |
|---|---|
| `git rev-parse HEAD` vs `origin/main` | `c950126c` — coincide exacto |
| `GET /health` | `{"ok":true,"version":"0.4.0",...}` |
| `systemctl --user is-active` | `umbral-worker`, `openclaw-dispatcher`, `openclaw-gateway`: los 3 `active` |
| `n8n list:workflow --active=true` | B1 (`7tNkwd7DkVCEI2oz`) + B3 (`iazEnIPcxCbipnKQ`): ambos vivos |
| `notion.read_database` (read-only) sobre `CAND-OLA3-03` | Canal=`blog`, Estado=`Borrador`, Copy Blog **presente** (480 chars, no vacío, no basura — no se leyó el contenido completo ni se reescribió), Estado imagen=`None`, `aprobado_contenido`=`false`, `autorizar_publicacion`=`false`, `published_url`=`None`, `publish_error`=`''` |
| Dry-run CLI (`trigger_hitl2_publish.py`, sin `--live`) | `would_publish:false`, `error:publication_not_authorized`, `visual_asset.reason:selection_missing` — idéntico a T1, sin cambios desde el 2026-08-24 |

Sin `BLOCKED_CONTENT` (Copy Blog tiene contenido real). Selección de imagen
sigue faltando (`selection_missing`) — no se generó nada por Magnific
(`MAGNIFIC_API_KEY` sigue ausente, confirmado en T1 y no re-verificado acá
por no tocarla). Se sigue al checklist humano en vez de cortar en un
BLOCKED separado, per el propio mandato del pack.

### ⚠ Hallazgo no pedido por el pack, pero no se puede ocultar

[docs/ops/editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md)
(2026-07-22, un mes antes de este pack) ya marcó `CAND-OLA3-03` como **ejemplo negativo real**
de atribución de fuentes: usa `buildingsmart.org` (home de la organización)
en vez de la URL de la pieza concreta — no conforme con las reglas #5/#6/#7
de [editorial-source-attribution-policy.md](editorial-source-attribution-policy.md).
Releído `Fuente primaria` ahora (2026-08-25, solo lectura): **sigue siendo
`https://www.buildingsmart.org/`** — sin corregir, y `Comentarios revisión`
sigue vacío (nadie se lo marcó a David). No es Copy Blog vacío/basura (por
eso no es `BLOCKED_CONTENT` en el sentido literal del pack), pero es un
defecto de contenido conocido y sin resolver en el mismo candidato que este
checklist le pide aprobar. No lo arreglo yo (no reescribo Copy ni fuentes,
fuera de scope) — lo dejo explícito en el checklist de abajo para que David
decida con esa información, no a ciegas.

## Fase B — checklist humano (publicado, sin marcar nada Claude)

0. **Antes de aprobar:** `Fuente primaria` de `CAND-OLA3-03` es la home de
   buildingsmart.org, no la pieza concreta — ya marcado como no conforme el
   2026-07-22, sigue sin corregir. Corregir la fuente o elegir otro
   candidato antes de seguir.
1. Revisar Copy Blog de `CAND-OLA3-03` en Publicaciones.
2. Marcar `aprobado_contenido`.
3. Estado imagen = Seleccionada (asset ya existente; sin Magnific).
4. Marcar `autorizar_publicacion`. Después, en el chat Telegram allowlisteado
   de B1: **ok publica CAND-OLA3-03**.

Sin confirmación de David en este hilo al momento de cerrar T2. Los 3 gates
+ selección de imagen siguen en su estado de Fase A.

## Fase C — monitor live

**No ejecutada.** Fase B no llegó a confirmación humana en esta sesión — no
hay disparo de Telegram que correlacionar. Ningún n8n exec, ningún task_id
de worker, ningún `published_url` que citar. No se inventa evidencia de
Fase C.

## Qué NO se hizo, a propósito

Sin escribir Copy. Sin crear filas. Sin marcar `aprobado_contenido`,
`autorizar_publicacion`, ni Estado imagen. Sin `--live` ni
`telegram_confirmed=true` desde CLI/VPS (eso sería bypass de Telegram). Sin
encender Magnific/stage8/stage9c/`NOTION_POLLER_ENABLE_HITL2_SCAN`. Sin
tocar B1/B3. `openclaw.json` sin mutar.

## Veredicto

**BLOCKED_HUMAN_GATES** — cierre válido de T2, no es FAIL. Retomar cuando
David resuelva la fuente (paso 0) y confirme el resto del checklist.
