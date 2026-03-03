# 37 — Variables de entorno en tu máquina (Windows)

Las claves y tokens no deben quedar en el repo. En tu PC usá **variables de entorno** y/o un archivo **`.env`** (gitignored).

## Opción A: Archivo .env (recomendado para desarrollo)

1. En la raíz del repo: `copy .env.example .env`
2. Editá `.env` y reemplazá cada `CHANGE_ME_...` por el valor real.
3. Los scripts que usan `scripts/env_loader.py` cargarán `.env` al arrancar (sin sobrescribir variables ya definidas).
4. **No commitees** `.env` (está en `.gitignore`).

## Opción B: Variables de entorno de Windows (persistentes)

1. Dejá tus claves en `.env` (como en A).
2. Ejecutá una vez (PowerShell, desde la raíz del repo):
   ```powershell
   .\scripts\set_env_from_dotenv.ps1
   ```
3. Eso copia cada variable de `.env` al **entorno de usuario** de Windows (persistente).
4. Cerrá y volvé a abrir la terminal (o Cursor) para que los programas vean las nuevas variables.
5. A partir de ahí podés borrar `.env` si querés; las claves quedan solo en Windows.

## Uso en scripts Python

- **Diagnóstico Google Cloud:** `python scripts/diagnose_google_cloud_apis.py` — usa `env_loader` y lee desde `.env` o desde el entorno.
- **Otros scripts:** Si necesitan las mismas claves, añadí al inicio:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
  import scripts.env_loader  # noqa: F401
  scripts.env_loader.load()
  ```

## Resumen

| Dónde están las claves | Quién las usa |
|------------------------|----------------|
| `.env` en la raíz (gitignored) | Scripts que llaman `env_loader.load()` |
| Variables de usuario de Windows | Cualquier proceso que arranques después de ejecutar `set_env_from_dotenv.ps1` |

Nunca subas `.env` ni pongas valores reales en `.env.example`.
