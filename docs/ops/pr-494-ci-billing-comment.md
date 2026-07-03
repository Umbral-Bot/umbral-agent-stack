## CI rojo — no es regresión de código

El workflow **Tests** (`28565380353`) falló en ~2s **sin ejecutar pytest**.

**Anotación GitHub Actions:**
> The job was not started because your account is locked due to a billing issue.

### Verificación local (rama `761f6ec`, Windows)
- `pytest tests/test_editorial_function_shared.py tests/test_editorial_unpublish.py tests/test_editorial_publish.py` → **64 passed**, 1 skipped
- Deploy + smoke unpublish en prod → **OK** (fixture eliminado, CAND-001 intacto)

### Para merge
1. Resolver billing en org `Umbral-Bot` (Settings → Billing)
2. Re-run workflow en este PR
3. Merge cuando CI esté verde (o merge manual si se acepta evidencia local + prod)
