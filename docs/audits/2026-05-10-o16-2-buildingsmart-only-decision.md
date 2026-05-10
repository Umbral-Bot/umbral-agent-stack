# O16.2 — Decisión scope smoke: buildingSMART-only (2026-05-10)

**Owner:** Copilot Chat (autonomous mandate, dm@umbralbim.cl)
**Hilo origen:** Coordinador de Agentes / Automatización Agentes — O16.2
**Status:** DECIDIDO. Pendiente ratificación de David antes de ejecutar el smoke live.

## TL;DR

Para cumplir el acceptance criterion del Friday retro 2026-06-26 (Bot cita un párrafo
buildingSMART/IFC con `aeco-kb-es-vYYYYMMDD` + URL fuente), **basta correr el smoke con
`buildingsmart` como única `source_type`**. Las otras tres (`iram`, `nmx`, `minvu`) NO
son requeridas para el accept y solo agregan riesgo (URLs estatales con 404 conocidos).

## Veredicto

> **Smoke Q2 (junio 2026) corre con `--source buildingsmart` únicamente.**
> Iram/Nmx/Minvu se freezan como seeds-presentes-pero-no-corridas hasta Q3.

## Justificación

| Dimensión | buildingSMART | iram | nmx | minvu |
|---|---|---|---|---|
| URLs vivas hoy | 3/3 OK (status 200 verificado) | 0/2 verificado | 0/2 verificado | 0/2 verificado (DDU-475, DDU-470 → 404 conocido) |
| Cubre accept criterion (IFC párrafo + URL) | ✅ Sí | ❌ No | ❌ No | ❌ No |
| Fix del seed key (`doc_id`) | ya correcto | aplicado en `coord-o16/fix-o16-2-seed-doc-id-key` `3cc2cc5b` | aplicado en mismo commit | placeholder, sin entries afectadas |
| Riesgo de fallar el smoke por URL 404 | bajo | medio | medio | alto |
| Valor docente / contenido publishable | alto (IFC4.3) | medio | medio | bajo (boletines DDU) |

El acceptance criterion del retro no exige cobertura latam — exige **un solo párrafo
citado correctamente con `aeco-kb-es-vYYYYMMDD` + URL**. buildingSMART entrega eso con
el mínimo radio de error.

## Alcance del smoke buildingsmart-only

- `bash scripts/aeco-kb/run_pipeline.sh buildingsmart`
- `python scripts/aeco-kb/verify_kb.py --min-chunks 150` (umbral bajado de 500 → 150
  porque 3 PDFs IFC ≈ 150-300 chunks; 500 era umbral pensado para los 4 sources combinados)
- Smoke `AgenteUB`: pregunta-tipo "¿Qué dice IFC4.3 sobre `IfcSpace`?" → respuesta debe
  incluir `aeco-kb-es-v<YYYYMMDD>` + URL `standards.buildingsmart.org/IFC/RELEASE/IFC4_3/...`

## Lo que NO cambia con esta decisión

- Los 4 seeds YAML siguen versionados en repo (`scripts/aeco-kb/seeds/`).
- El seed-key fix (`id` → `doc_id`) se aplica a iram/nmx igual, porque deja el repo
  consistente y desbloquea Q3 sin trabajo extra.
- El Bicep umbrella `infra/azure/aeco-kb-pipeline.bicep` queda igual — el filtrado por
  `source_type` se hace en el job runtime via flag, no en infra.

## Lo que SÍ cambia

- `scripts/aeco-kb/run_pipeline.sh` (si recibe lista posicional de sources): se invoca
  solo con `buildingsmart` en el smoke Q2. El script ya soporta filtrar por arg.
- `verify_kb.py --min-chunks 500` baja a `150` para el smoke Q2 buildingsmart-only.
  Cuando Q3 active iram/nmx/minvu, vuelve a 500.

## Q3 reactivation criteria

Para reactivar iram/nmx/minvu en Q3:

1. Re-validar las 6 URLs (`scripts/aeco-kb/check_seed_urls.py` o equivalente).
2. Reemplazar URLs 404 por archivos espejo en blob propio (`stumbralagentsprod/crudos/aeco/mirror/`).
3. Volver a correr smoke con `buildingsmart minvu iram nmx` y `--min-chunks 500`.
4. Documentar resultado en `docs/audits/2026-Q3-aeco-kb-latam-expansion.md`.

## Decisión pendiente (David)

- [ ] Confirmar que el smoke Q2 corre solo con buildingsmart.
- [ ] Confirmar `--min-chunks 150` como umbral aceptable.
- [ ] Confirmar postergar latam a Q3 (no es renuncia, es freeze deliberado).

## Referencias

- Audit previo: [docs/audits/2026-05-08-o16-2-smoke-deploy.md](2026-05-08-o16-2-smoke-deploy.md)
- Seed fix branch: `coord-o16/fix-o16-2-seed-doc-id-key` commit `3cc2cc5b`
- Plan ejecución: [2026-05-10-o16-2-execution-plan.md](2026-05-10-o16-2-execution-plan.md)
- Kill list Q2: [2026-05-10-q2-runtime-focus-and-kill-list.md](2026-05-10-q2-runtime-focus-and-kill-list.md)
