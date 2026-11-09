<!-- Informe del subagente de investigación (web, fuentes primarias, 2026-11-09), sesión coordinadora local_815b91f1. Sin ejecución local. Las cifras marcadas como estimación o secundarias se indican. -->

# D3 · Búsqueda de memoria en OpenClaw 2026.10.10 sin pago por uso: opciones de embeddings

Fecha de consulta: 2026-11-09. Restricción de David: cero pago por uso; solo infraestructura propia o suscripciones ya pagadas; no activar facturación; no cambiar el índice existente sin prueba reversible.

## Qué soporta OpenClaw (base para todas las vías)
- `memory.search.provider` acepta `openai` (por defecto), `gemini`, `local`, `ollama`, `openai-compatible`, `lmstudio`, `voyage`, `mistral`, `deepinfra`, `bedrock`, `github-copilot`, `omlx`, más `none` y `auto`, o cualquier `models.providers.<id>` propio. https://docs.openclaw.ai/concepts/memory-search · https://docs.openclaw.ai/reference/memory-config
- Cambiar proveedor, modelo, `outputDimensionality`, chunking o tokenizador invalida la identidad del índice: OpenClaw pausa la búsqueda vectorial y avisa, no re-embebe solo; hay que correr `openclaw memory index --force --agent <id>`. Si la dimensión difiere, reporta el desajuste y no compara vectores.
- Si el proveedor explícito falla en runtime, `memory_search` reporta memoria no disponible, sin caer a FTS. Solo `auto`/sin definir/`local` degradan a BM25.
- Índices por agente en `agents/<agentId>/agent/openclaw-agent.sqlite`; `openclaw memory status --deep` verifica proveedor y endpoints sin reindexar.
- Azure: proveedor personalizado con `baseUrl` = URL del despliegue y `api-version` en `headers`.

## A. Gemini API, nivel gratuito (statu quo: gemini-embedding-001, 3072 dims)
- Límites: la tabla oficial está tras login (aistudio.google.com/rate-limit). Cifras 100 RPM / 30.000 TPM / 1.000 RPD para el free tier provienen de fuentes secundarias (foro de desarrolladores, 19-dic-2025): confirmar en la consola.
- Gratuidad: proyecto sin cuenta de facturación vinculada. Precio pagado: gemini-embedding-001 $0,15/1M tokens; gemini-embedding-2 $0,20. https://aistudio.google.com/docs/pricing
- **Privacidad (crítico):** Términos (23-mar-2026), Unpaid Services: Google usa el contenido enviado y las respuestas «to provide, improve, and develop»; «human reviewers may read, annotate, and process your API input and output»; «Do not submit sensitive, confidential, or personal information». Paid Services: no se usan para mejorar productos. https://aistudio.google.com/docs/terms
- Google One AI Pro no cubre la API («plan benefits apply only within the Google AI Studio web interface»); los créditos del Google Developer Program exigen Cloud Billing activo (tarjeta). https://aistudio.google.com/docs/google-ai-plans
- Calidad: MTEB 68,16 (2048 dims). Impacto VPS nulo. Coste cero. Sin migración. Riesgo: privacidad + memoria «no disponible» si se agota el RPD.

## B. Local en el VPS
**B1. Ollama** (proveedor nativo `ollama`, `/api/embed`, modelo por defecto `nomic-embed-text`; requiere `ollama pull`). Instalación por script oficial, servicio systemd, bind 127.0.0.1:11434; CPU puro. https://docs.openclaw.ai/providers/ollama/advanced · https://docs.ollama.com/linux

| Modelo | Disco | Dims | Contexto | Calidad | Licencia |
|---|---|---|---|---|---|
| nomic-embed-text v1.5 | 274 MB | 768 (MRL) | 2K | MTEB 62,28 | Apache-2.0 |
| mxbai-embed-large | 670 MB | 1024 | 512 | MTEB 64,68 | Apache-2.0 |
| bge-m3 | 1,2 GB | 1024 | 8K | multilingüe 100+ idiomas | MIT |
| all-minilm | 46 MB | 384 | 256 | solo inglés | Apache-2.0 |

RAM y CPU (estimación): nomic ≈ 0,4–0,7 GB residentes; bge-m3 ≈ 1,3–1,8 GB. Un fragmento de 400 tokens con un modelo de 137M ≈ 50–200 ms en CPU de VPS; 9 chunks, segundos. Para español: nomic (con `queryInstruction`) o bge-m3.

**B2. Proveedor `local` de OpenClaw** (sin Ollama): `openclaw plugins install @openclaw/llama-cpp-provider` instala `llama-server` y descarga `embeddinggemma-300m-qat-Q8_0.gguf` (~0,3 GB; 768 dims; MTEB multilingüe 61,15; licencia Gemma). Degrada a BM25 si falla. Si corre bajo el servicio del gateway, cuenta dentro del cgroup de 5,5 GB.

**B3. Servidor OpenAI-compatible propio** (`openai-compatible` + `remote.baseUrl`): llama.cpp `llama-server --embeddings` o Hugging Face TEI (CPU).

Privacidad total. Coste cero. Impacto VPS: 0,4–1,8 GB extra sin swap en una máquina con 7,9 GB donde ya hay 5,5 GB de cgroup del gateway + 1,1 GB n8n + worker/Redis/MC: **riesgo de OOM real**; obligatorio `OLLAMA_KEEP_ALIVE` corto, un solo modelo y medir `free -m` antes. Migración: 3072→768/1024 dims = reindex forzado. Reversible.

## C. Sin embeddings: `memory.search.provider: "none"` (FTS-only)
BM25 sobre SQLite; se pierde la recuperación por significado (sinónimos, paráfrasis, otro idioma); se conserva la coincidencia exacta de términos, IDs, nombres. Coste cero; libera recursos; sin migración; el índice vectorial actual queda inerte; reversión inmediata (volver a `gemini` con el mismo modelo no cambia la identidad del índice).

## D. Azure OpenAI `text-embedding-3-small` con créditos de patrocinio
- Los créditos de Microsoft for Startups cubren modelos facturados por Azure, incluidos embeddings. https://learn.microsoft.com/en-us/startups/build/getting-started/foundry-model-sponsorship-coverage (22-oct-2026).
- **Al agotarse** los créditos o llegar la fecha fin, la suscripción pasa automáticamente a pago por uso y se carga la tarjeta registrada (oferta MS-AZR-0036P). Hoy coste cero, pero no «sin tarjeta»: mitigar con presupuesto y alertas de Cost Management. https://learn.microsoft.com/en-us/startups/build/getting-started/azure-usage-and-billing
- Requisitos: recurso Azure OpenAI/Foundry en la suscripción patrocinada; despliegue `text-embedding-3-small` (1.536 dims, 8.192 tokens; GA, retiro 2028-02-09).
- Privacidad: entradas, salidas y embeddings no se usan para entrenar modelos ni están disponibles para OpenAI. https://learn.microsoft.com/en-us/legal/cognitive-services/openai/data-privacy (18-may-2026).
- OpenClaw: proveedor personalizado en `models.providers.<id>` con `baseUrl` y `api-version`. Calidad MTEB 62,3; MIRACL 44,0. Impacto VPS nulo. Migración: reindex (1.536 dims). Reversible.
- Contexto UAS: la suscripción patrocinada es la misma que tiene abierto un reclamo de cobro con soporte Microsoft (crédito ISV 5.000 USD, saldo observado 4.822 USD el 7-nov, vigencia hasta 10-jun-2027).

## E. ChatGPT Plus/Pro, Claude Pro/Max, Microsoft 365 Copilot
- OpenAI: ChatGPT y la API tienen facturación separada; sin API de embeddings cubierta. OpenClaw menciona «eligible Codex OAuth» para el proveedor openai de embeddings: sin término de OpenAI que lo autorice para `/v1/embeddings`; no se cuenta como vía válida.
- Anthropic: la suscripción no cubre API y Anthropic no ofrece modelo de embeddings.
- M365 Copilot: sin API de embeddings. OpenClaw lista `github-copilot` como proveedor: solo con suscripción GitHub Copilot (distinta de M365), términos no verificados.

## Tabla comparativa
| Vía | Coste real | Privacidad | Calidad | RAM VPS extra | Reindex | Riesgo principal |
|---|---|---|---|---|---|---|
| A. Gemini free | 0 | **Baja** (mejora de productos + revisión humana) | 68 | 0 | no | términos Unpaid Services; RPD |
| B1. Ollama nomic | 0 | Total | 62,3 | 0,4–0,7 GB | sí (768) | OOM sin swap |
| B1. Ollama bge-m3 | 0 | Total | multilingüe fuerte | 1,3–1,8 GB | sí (1024) | OOM casi seguro |
| B2. `local` embeddinggemma | 0 | Total | 61,2 | ~0,4–0,6 GB (en cgroup) | sí (768) | presión sobre 5,5 GB |
| C. `none` | 0 | Total | sin semántica | libera | no | pérdida de recall semántico |
| D. Azure + créditos | 0 hoy; PAYG al agotar | Alta | 62,3 / MIRACL 44 | 0 | sí (1536) | tarjeta al agotarse créditos |
| E. Suscripciones | n/a | n/a | n/a | n/a | n/a | no existe API cubierta |

## Recomendación del subagente
Primera: **D** (Azure OpenAI con créditos de patrocinio): cero coste efectivo con créditos ya concedidos, privacidad contractual, cero RAM en una VPS sin margen, soporte documentado en OpenClaw. Condiciones: presupuesto y alertas en Cost Management; revisar saldo y fecha fin antes de depender; si el saldo se acerca a cero, bajar a C.
Segunda: **C** (`none`) como red de seguridad inmediata; **B1** (Ollama nomic) solo si se mide ≥ 1 GB libre estable tras n8n, worker, Redis y MC. Mantener A solo aceptando que la memoria del agente alimenta el entrenamiento de Google.

## Cómo probar sin tocar producción
1. Copia de seguridad de `agents/<agentId>/agent/openclaw-agent.sqlite` y de `openclaw.json`.
2. Configurar el proveedor candidato y correr `openclaw memory status --deep` (valida credenciales/endpoint sin reindexar).
3. Reindexar un agente de prueba: `openclaw memory index --force --agent <agente-prueba>`; comparar consultas semánticas y léxicas frente al índice gemini actual.
4. Rollback: restaurar `openclaw.json` y el sqlite; `memory status` debe reportar identidad coherente.

## No confirmado con fuente primaria
Límites exactos del free tier de Gemini para embeddings (tras login); precio oficial Azure de text-embedding-3-small (página dinámica); huella RAM real de Ollama/llama-server en esa VPS (lo mide PKG-DIHR-VPS-07); legitimidad de Codex OAuth / GitHub Copilot como fuente de embeddings bajo sus términos.
