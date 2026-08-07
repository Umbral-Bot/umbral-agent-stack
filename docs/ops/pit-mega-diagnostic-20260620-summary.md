# PIT Mega-diagnóstico 2026-06-20 — resumen ejecutivo

> **Estado: HISTÓRICO.** Frente PIT archivado por gobernanza (inventario
> `docs/ops/uas-north-inventory-2026-08-06.md` §1 A.2). Registro del diagnóstico — no describe
> estado runtime vigente.

- **Status:** P0 summary — 2026-06-20.
- **Fuente:** mega-diagnóstico operativo 2026-06-20, resumido sin secrets.
- **Evidencia runtime:** referencia genérica `~/.coord-ag-evidence/pit-mega-diagnostic-20260620-1515/`.
- **Contrato canónico relacionado:** [`pit-tournament-v2-contract.md`](pit-tournament-v2-contract.md).

---

## Veredicto ejecutivo

El sistema PIT tiene piezas útiles ya verificadas, pero Ruta B broker-real no
queda validada.

Veredictos:

| Área | Veredicto | Lectura |
|---|---|---|
| Broker | `BROKER_READY: DRY_RUN_ONLY` | `EXECUTE=false` y `egress=false`; no hay ejecución Copilot CLI real todavía |
| Integridad torneo #2 | `TORNEO2_INTEGRITY: NEEDS_RERUN` | El torneo no siguió el contrato broker-only |
| Judge Mission Control | OK | `/pit/judge/{pit_id}` funcionó para comparación visual |
| Resultado torneo #2 | `ACCEPT_VISUAL_ONLY` | Útil como demo visual, no como prueba broker-real |
| Siguiente acción | P1 Copilot-VPS | Imagen Docker sandbox + red `copilot-egress` |

## Qué sí es válido

- Mission Control judge respondió para el PIT evaluado.
- El cierre visual del torneo #2 produjo señal útil.
- La lane `lane-prototype-demo` puede conservarse como evidencia visual.
- El patrón de comparación en `/pit/judge/{pit_id}` es reutilizable.
- El diagnóstico identificó gaps concretos y empaquetables.

## Qué no es válido como broker-real

- Las lanes del torneo #2 usaron OpenClaw directo en vez de Worker
  `copilot_cli.run`.
- El entorno seguía en `DRY_RUN_ONLY`.
- No había egress controlado disponible.
- No había imagen sandbox Copilot CLI construida.
- `force_default_model:true` impidió validar competencia real por lane/modelo.
- Las misiones eran read-only con `max_files_touched:0`.
- El schema produjo `invalid_input` para `reasoning_effort`.
- La auditoría no estaba normalizada con `lane_id` y `pit_id`.
- El mega-diagnóstico reportó 82/82 worker calls como `invalid_input`.

## Torneo #2 — lectura correcta

El torneo #2 queda cerrado como:

```text
ACCEPT_VISUAL_ONLY
```

Eso significa:

- Se acepta como demo visual.
- Se acepta como prueba de lectura/judge visual.
- No se acepta como validación Ruta B broker-real.
- No se debe convertir retrospectivamente en `PIT_RUN_PASS_BROKER_REAL`.

El veredicto broker-real correcto es:

```text
NEEDS_RERUN
```

Pero el re-run queda bloqueado hasta que P1-P6 estén completos.

## Evidencia y trazabilidad

Referencias permitidas:

- `~/.coord-ag-evidence/pit-mega-diagnostic-20260620-1515/`
- `/pit/judge/{pit_id}`
- `metrics/token_ledger.yaml` cuando exista en un run broker-real futuro
- audit JSONL de Worker `copilot_cli.run` cuando P2 lo habilite
- OpenClaw session JSONL sanitizado

No deben copiarse en docs:

- tokens
- bearer strings
- cookies
- paths con credenciales
- contenido sensible de sesiones
- valores de variables de entorno

## Gaps priorizados

| Gap | Impacto | Paquete |
|---|---|---|
| `NO_SANDBOX_IMAGE_BUILT` | No hay entorno Copilot CLI confiable | P1 |
| `NO_EGRESS_NETWORK` | Copilot CLI no tiene red controlada | P1 |
| `DRY_RUN_ONLY` | No hay ejecución real | P2 |
| `invalid_input reasoning_effort` | Worker rechaza payloads | P2/P4 |
| audit sin `lane_id`/`pit_id` | No hay trazabilidad por lane | P2/P4 |
| `force_default_model:true` | No hay competencia real de modelos | P3 |
| token ledger incompleto | No hay budget kill-switch real | P3/P6 |
| parser/gates no alineados v2 | Riesgo de spawn inválido | P5 |

## Siguiente acción

El próximo paquete no es re-run.

El próximo paquete es:

```text
P1 Copilot-VPS: imagen Docker umbral-sandbox-copilot-cli + red copilot-egress
```

Condiciones P1:

- No ejecutar torneo real.
- No tocar repo producto.
- No imprimir secrets.
- No activar L5.
- Producir evidencia de sandbox y egress allowlist.

Cuando P1-P6 estén verdes, Rick puede pedir a David un gate explícito para
re-run PIT y recién ahí buscar `PIT_RUN_PASS_BROKER_REAL`.
