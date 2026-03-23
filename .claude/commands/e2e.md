# E2E Diagnostics — Umbral Agent Stack

Diagnóstico del suite de tests E2E. El suite tiene historial de fallos flakey
en `composite.research` y routes de research (ver UMB-77).

## Correr suite completo
```bash
python -m pytest tests/ -q --tb=short
```

## Correr por área

### Dispatcher + routing
```bash
python -m pytest tests/test_dispatcher.py tests/test_intent_classifier.py \
  tests/test_dispatcher_escalation.py tests/test_provider_detection.py -v
```

### Resiliencia (con timeout)
```bash
python -m pytest tests/test_dispatcher_resilience.py -v --timeout=30
```

### Notion integration
```bash
python -m pytest tests/test_notion_poller.py tests/test_notion_database_page.py \
  tests/test_notion_project_registry.py -v
```

### Linear integration
```bash
python -m pytest tests/test_linear.py tests/test_linear_project_update.py \
  tests/test_audit_to_linear.py -v
```

### Worker API
```bash
python -m pytest tests/test_enqueue_api.py tests/test_openclaw_proxy.py -v
```

### Skills y validación
```bash
python -m pytest tests/test_skills_validation.py tests/test_skills_coverage.py -v -p no:cacheprovider
```

## Diagnóstico de fallos flakey

### Verificar si el fallo es de red vs. lógica
```bash
# Sin timeouts de red
python -m pytest tests/test_dispatcher_resilience.py -v --timeout=60 -x

# Solo tests que NO requieren servicios externos
python -m pytest tests/ -v -m "not integration" 2>/dev/null || \
python -m pytest tests/ -v --ignore=tests/test_e2e_validation.py
```

### Ver historial de fallos
```bash
# Últimos fallos en Redis (si el dispatcher está corriendo)
redis-cli keys "task:*:error" | head -20
```

### Test de smoke básico
```bash
python scripts/smoke_test.py 2>/dev/null || echo "smoke_test.py no disponible"
```

## E2E contra VPS real

### Validación completa
```bash
python scripts/e2e_validation.py
```

### Integration test
```bash
python scripts/integration_test.py
```

## Interpretar resultados

| Patrón de fallo | Causa probable |
|----------------|----------------|
| `ConnectionRefusedError` en worker | VM no disponible o servicio caído |
| `QuotaExceeded` | Cuota de modelo agotada — ver `/routing` |
| `redis.exceptions.ConnectionError` | Redis no corre en VPS |
| `notion.APIResponseError` | Token de Notion expirado |
| `AssertionError` en routing | Provider no configurado — ver `/routing` |
| Flakey en `composite.research` | Timeout de red o Tavily API rate limit |

## Archivos de referencia
- `tests/` — suite completo
- `scripts/e2e_validation.py` — validación E2E completa
- `scripts/smoke_test.py` — smoke test rápido
- `docs/40-hackathon-diagnostico-completo.md` — diagnóstico histórico
