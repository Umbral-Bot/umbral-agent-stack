# Model Routing Config — Umbral Agent Stack

Diagnóstico y configuración del routing de modelos LLM en el Umbral Agent Stack.
Ref: `config/quota_policy.yaml`, `dispatcher/model_router.py`, `dispatcher/quota_tracker.py`

## Estado actual del routing (UMB-77)

El drift conocido: `claude_*` providers declarados en quota_policy.yaml pero
**sin configurar en Worker** (variables de entorno faltantes en `.env`).

## Verificar configuración actual

### Ver quota_policy.yaml
```bash
cat config/quota_policy.yaml
```

### Ver variables de entorno de modelos en VPS
```bash
ssh $VPS_USER@$VPS_HOST "grep -E 'ANTHROPIC|OPENAI|AZURE|GOOGLE|GEMINI' ~/umbral-agent-stack/.env"
```

### Verificar qué modelos responden realmente
```bash
python -c "
from dispatcher.model_router import ModelRouter
from dispatcher.quota_tracker import QuotaTracker
qt = QuotaTracker()
mr = ModelRouter(qt)
print(mr.get_available_providers('coding'))
print(mr.get_available_providers('general'))
"
```

### Ver estado de cuotas en Redis
```bash
ssh $VPS_USER@$VPS_HOST "redis-cli keys 'quota:*' | sort"
```

## Routing declarado por task_type

| task_type | Providers en orden de prioridad |
|-----------|--------------------------------|
| coding    | claude_pro → gemini_pro → azure_foundry → gemini_flash |
| general   | claude_pro → gemini_pro → azure_foundry → gemini_flash |
| writing   | claude_pro → claude_opus → gemini_pro |
| research  | gemini_pro → gemini_vertex → claude_pro → gemini_flash |
| critical  | claude_opus → claude_pro → gemini_pro |
| light     | gemini_flash → gemini_flash_lite → claude_haiku → gemini_pro |
| ms_stack  | azure_foundry → gemini_pro → claude_pro |

## Configurar claude_* en Worker

Variables requeridas en `.env` del VPS:
```bash
ANTHROPIC_API_KEY=sk-ant-...
# Opcional: para separar cuotas
ANTHROPIC_MODEL_PRO=claude-sonnet-4-6
ANTHROPIC_MODEL_OPUS=claude-opus-4-6
ANTHROPIC_MODEL_HAIKU=claude-haiku-4-5-20251001
```

Aplicar sin reiniciar:
```bash
ssh $VPS_USER@$VPS_HOST "cd ~/umbral-agent-stack && source .env && systemctl restart dispatcher"
```

## Verificar E2E post-configuración

```bash
python -m pytest tests/test_dispatcher.py tests/test_intent_classifier.py -v -k "routing"
python -m pytest tests/test_dispatcher_resilience.py -v --timeout=30
```

## Cuotas por provider

| Provider | Límite | Window |
|----------|--------|--------|
| azure_foundry | 2000 req | /hora |
| claude_pro | 200 req | /5h |
| claude_opus | 50 req | /5h |
| claude_haiku | 500 req | /5h |
| gemini_pro | 500 req | /día |
| gemini_flash | 1000 req | /día |

## Resetear cuota manualmente (testing)
```bash
ssh $VPS_USER@$VPS_HOST "redis-cli del quota:claude_pro quota:claude_opus"
```

## Archivos de referencia
- `config/quota_policy.yaml` — Configuración de cuotas y routing
- `dispatcher/model_router.py` — Lógica de selección de modelo
- `dispatcher/quota_tracker.py` — Tracking de uso en Redis
- `docs/15-model-quota-policy.md` — Documentación completa
- `docs/ADR-004-model-quota-policy.md` — Decisión arquitectural
