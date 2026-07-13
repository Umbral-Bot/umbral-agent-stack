# Worker/editorial → OpenAI OAuth — opciones de migración

- **Fecha:** 2026-07-13
- **Estado:** diseño; sin implementación runtime
- **Decisión recomendada:** Opción A, Worker → gateway OpenClaw → Codex OAuth

## Problema real

OpenAI OAuth en este stack pertenece al auth store y al runtime Codex de OpenClaw. El Worker no tiene un cliente OAuth: `worker/tasks/llm.py` selecciona `_call_azure_foundry` cuando existen `AZURE_OPENAI_*` y `_call_openai` solo cuando existe `OPENAI_API_KEY`. Ninguna ruta usa el perfil ChatGPT/Codex almacenado por OpenClaw.

El cambio de `azure-openai-responses/gpt-5.5` a `openai/gpt-5.6-sol` en YAML no sería suficiente. Sin un cambio de transporte, el guard podría pasar mientras el Worker sigue usando API key o falla por credenciales ausentes.

## Opción A — gateway local OpenClaw (recomendada)

```text
Dispatcher task_type
  → provider lógico openclaw_oauth
  → model ref openai/*
  → Worker /v1/chat/completions en 127.0.0.1:18789
  → OpenClaw auth order
  → Codex runtime + OpenAI OAuth
```

### Ventajas

- Un solo owner del lifecycle OAuth y refresh: OpenClaw.
- El Worker conoce únicamente `OPENCLAW_GATEWAY_TOKEN`, nunca el access/refresh token OpenAI.
- S6 y S7.5 ya usan el gateway y sirven como patrón de integración.
- Permite routing discriminado por task type sin reintroducir keys OpenAI/Foundry.
- Rollback de código independiente del auth store.

### Cambios repo propuestos

| Archivo | Cambio |
|---|---|
| `config/quota_policy.yaml` | Sustituir Foundry/Gemini por provider `openclaw_oauth`; separar rutas `heavy`, `coding`, `light`, `research` o añadir `model_id` por task type. |
| `dispatcher/model_router.py` | Requisito `openclaw_oauth: [OPENCLAW_GATEWAY_TOKEN]`; retirar Foundry/Gemini de defaults. |
| `dispatcher/service.py` | Mapear provider lógico a refs `openai/*`; evitar que todos los task types terminen en un único modelo. |
| `worker/tasks/llm.py` | Añadir selección explícita `openclaw_oauth` para modelos OpenAI; reutilizar/refactorizar `_call_openclaw_proxy`; no caer en `_call_azure_foundry`. |
| `worker/app.py` | Actualizar el dashboard de providers y mostrar transporte `openclaw_oauth`, sin declarar OAuth por presencia de slug. |
| `worker/tasks/rag.py` | Respuesta generativa por gateway; separar el gap de embeddings. |
| `worker/tasks/tournament.py` | Eliminar default `azure_foundry`; exigir modelos por lane o un default OAuth explícito. |
| `copilot_agent/agent.py` | Enrutar por gateway o deprecar el cliente BYOK; su default 5.4 sigue atado a Azure. |
| `config/team_workflows.yaml` | Sustituir el modelo Gemini del team `data` por el light OAuth verificado. |
| `worker/research_backends.py` | Retirar Gemini grounded; usar OpenAI web search vía gateway si el tool smoke pasa, o Tavily + síntesis OAuth. |
| `worker/tasks/google_audio.py` | Deshabilitar Google TTS y resolver voz en un gate separado. |
| `config/editorial-model.yaml` | Cambiar provider/model a target OAuth y mantener `fail_explicit`. |
| `scripts/editorial/editorial_model_guard.py` | Mensajes y validación del contrato nuevo; verificar modelo efectivo y, en E2E, auth/runtime. |
| `openclaw/workspace-agent-overrides/*/ROLE.md` | Refs canónicas por rol; sin Foundry/Gemini. |

### Contrato recomendado

El router no debe confundir provider lógico con model id:

```yaml
routing:
  coding:
    preferred: openclaw_oauth
    model_id: openai/gpt-5.3-codex
  writing:
    preferred: openclaw_oauth
    model_id: openai/gpt-5.6-sol
  research:
    preferred: openclaw_oauth
    model_id: openai/gpt-5.5
  light:
    preferred: openclaw_oauth
    model_id: openai/gpt-5.4-mini  # solo si catálogo OAuth lo expone
    fallback_model_id: openai/gpt-5.3-codex
```

El schema exacto puede variar, pero el modelo debe ser una propiedad explícita del route. Reutilizar una sola key de provider como si fuera a la vez proveedor y modelo mantiene la limitación actual.

### Guard editorial

El contrato editorial propuesto:

```yaml
required_transport: openclaw_oauth
required_provider: openai
required_model: gpt-5.6-sol
required_model_id: openai/gpt-5.6-sol
thinking_default_editorial: xhigh
allowed_fallback_after_failure:
  - openai/gpt-5.5
on_model_mismatch: fail_explicit
```

El guard repo-side puede validar el model id. La prueba de `oauth=1` pertenece al preflight/E2E de runtime; no debe intentar leer el auth store desde el proceso Worker.

## Opción B — OAuth directo en Worker (no recomendada)

Implementar OAuth directo requeriría:

- flujo de login y refresh;
- cifrado/storage del token;
- selección de perfiles y account/workspace;
- manejo de rate limits/rotación;
- cliente Codex app-server o transporte OAuth soportado;
- aislamiento para que tokens no aparezcan en logs, OpsLogger o trazas.

Leer `~/.openclaw/agents/main/agent/openclaw-agent.sqlite` no es una solución válida: es storage privado, acopla versiones, rompe ownership y expone secretos. Tampoco es válido copiar el access token a `.env`.

Esta opción solo debe reabrirse si OpenClaw/OpenAI publican un contrato estable de delegación OAuth para servicios headless distinto del gateway.

## Opción C — OpenAI Platform API key (control, fuera de objetivo)

`_call_openai` ya puede usar `OPENAI_API_KEY`, pero esto es billing API, no ChatGPT/Codex OAuth. Puede ser técnicamente simple, pero viola el objetivo de esta migración. No se recomienda como fallback silencioso.

## Stages editoriales

| Stage | Estado real | Migración |
|---|---|---|
| S6 | `openclaw/main` por gateway | hereda OAuth de `main`; actualizar doc stale |
| S7 | publicación determinística de draft | sin LLM; no inventar migración |
| S7.5 | `openclaw/main` por gateway | actualizar guard/contrato y ejecutar un post E2E dry-run |
| S8 | Google image directo | reemplazar por Magnific-only; no pertenece a Opción A/B texto |
| S9 | payload determinístico | sin LLM; mantener gates |

## Gaps no cubiertos por el proxy de texto

### Embeddings RAG

`worker/rag/indexer.py` usa Azure `text-embedding-3-large`. Un perfil Codex OAuth para agent turns no equivale a un endpoint público de embeddings. Opciones para decisión separada:

1. pausar indexación vectorial y usar keyword search;
2. adoptar embeddings locales;
3. contratar un provider API específico y explícito.

No reutilizar OAuth de agent turns por inferencia.

### Realtime / audio

`worker/tasks/azure_audio.py` usa WebSocket Azure `gpt-realtime`. La documentación oficial de OpenClaw separa Codex OAuth de Realtime público, que requiere API key. Mantener voz con un proveedor no-Foundry existente o abrir un gate de arquitectura; no esconderlo dentro del PR editorial.

`worker/tasks/google_audio.py` tampoco puede quedar como fallback: usa Gemini TTS directo y contradice la eliminación de Gemini. La decisión de voz debe considerar ambos handlers a la vez.

### Research grounded

`worker/research_backends.py` combina Gemini 2.5 Flash con Google Search. Sustituir solo el model id perdería retrieval. El target debe probar OpenAI server-side web search por OpenClaw o mantener Tavily como retrieval y usar OAuth únicamente para la síntesis.

### Imágenes

OpenClaw puede generar imágenes con OAuth, pero David ratificó Magnific-only para S8. Por eso el target editorial visual no es `openai/gpt-image-*`.

## Pruebas mínimas

### Unitarias

- route `coding` → `openclaw_oauth` + `openai/gpt-5.3-codex`;
- route `writing` → Sol; fallback 5.5;
- route `light` usa mini solo cuando el catálogo/gate lo habilita;
- sin Azure/Google configurado, el router sigue seleccionando OAuth si gateway token existe;
- `_detect_provider` no envía `openai/*` a Foundry;
- el guard acepta solo el contrato nuevo y rechaza Foundry/Gemini;
- tournament y RAG answer no tienen default `azure_foundry`.

### Integración local

- mock del gateway verifica body `model=openai/*` y ausencia de tokens OAuth;
- errores 401/429/timeout son explícitos y no disparan fallback a API key;
- logs no contienen Authorization ni perfiles.

### E2E VPS autorizado

Un post sintético, sin writes Notion/publicación:

1. S6 o handler equivalente con texto mínimo.
2. Verificar respuesta y `model` efectivo.
3. `models status` confirma `oauth=1` para OpenAI.
4. Ops log registra provider lógico/modelo, no credenciales.
5. Un fallo forzado demuestra fallback 5.5 o error explícito; nunca Foundry/Gemini.

## Secuencia de PRs recomendada

1. **PR contract/router:** policy + Worker gateway + tests.
2. **PR editorial contract:** YAML + guard + ROLEs + docs + dry-run fixture.
3. **PR S8 Magnific-only:** handler/broker + tests visuales, separado del texto.
4. **PR cleanup:** retirar código/env/docs legacy solo después del soak.

No mezclar embeddings o Realtime en esos PRs; cada uno necesita su decisión de arquitectura.

## Criterio de decisión

Adoptar **Opción A** salvo que exista un requisito explícito de ejecutar el Worker sin gateway. Si aparece ese requisito, no saltar a Opción B automáticamente: primero definir un contrato de auth soportado y revisar seguridad.
