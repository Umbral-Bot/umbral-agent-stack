# Contributing

Gracias por contribuir a Umbral Agent Stack.

## Ejecutar tests en local

```bash
# 1. Crear virtualenv e instalar dependencias
python -m venv .venv
source .venv/bin/activate
pip install -r worker/requirements.txt
pip install -r dispatcher/requirements.txt
pip install fakeredis

# 2. Ejecutar la suite de tests
WORKER_TOKEN=test python -m pytest tests/ -v
```

No se necesita Redis real ni claves de API — los tests usan `fakeredis` y mocks.

## Integración Continua (CI)

Cada push a `main` y cada pull request dispara el workflow de GitHub Actions definido en `.github/workflows/test.yml`. El job:

1. Instala dependencias de Worker, Dispatcher y test (`fakeredis`).
2. Ejecuta `pytest tests/ -v --tb=short` con `WORKER_TOKEN=test`.
3. Falla si algún test no pasa.

La matrix de CI cubre Python **3.11** y **3.12**.

## Convenciones

- Crear una **feature branch** desde `main` y abrir un **PR** para revisión.
- Asegurar que todos los tests pasen antes de solicitar review.
- No commitear archivos `.env`, tokens ni claves API.
