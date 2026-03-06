# Revisión de Seguridad — Umbral Agent Stack
**Fecha:** 2026-03-05
**Branch:** `claude/090-implementar-notion-bitacora`
**Scope:** worker/, dispatcher/, infra/, scripts/, config/, .env.example

---

## Resumen ejecutivo

| Severidad | Cantidad |
| --------- | -------- |
| Critico   | 3        |
| Alto      | 5        |
| Medio     | 5        |
| Bajo      | 4        |

Los tres hallazgos críticos comparten un patrón: **input de usuario alcanza subprocesos del sistema operativo sin sanitización efectiva** (windows.py). Los hallazgos de severidad alta están relacionados con la gestión de secretos y el mecanismo de autenticación.

---

## 1. Secretos y credenciales

### [CRITICO] SEC-1 — WORKER_TOKEN escrito en archivo de texto plano

**Archivo:** `worker/tasks/windows.py:222-227`

La función `handle_windows_write_worker_token` recibe el token como input HTTP y lo escribe directamente en `C:\openclaw-worker\worker_token` sin cifrado. Cualquier proceso local en Windows puede leer ese archivo.

```python
# windows.py:222-227
with open(r"C:\openclaw-worker\worker_token", "w") as f:
    f.write(token)
```

**Recomendación:** Eliminar este handler o cifrar con `infra/secrets.py` (SecretStore / Fernet). Si el objetivo es inicializar el token en la VM, hacerlo fuera de banda (Ansible, SCP + chmod 600) en lugar de enviarlo por HTTP.

---

### [ALTO] SEC-2 — Tailscale IPs reales en `.env.example`

**Archivo:** `.env.example:112-113`

Las líneas de comentario contienen IPs de Tailscale de producción:
```
# VPS_IP=100.113.249.25
# VM_IP=100.109.16.40
```

Aunque son IPs de una red privada Tailscale, su exposición en el repositorio público revela la topología de red interna.

**Recomendación:** Sustituir por `100.x.x.x` o `<VPS_TAILSCALE_IP>` antes de hacer el repo público.

---

### [ALTO] SEC-3 — Notion DB ID hardcodeado en scripts

**Archivos:**
- `scripts/add_resumen_amigable.py:37`
- `scripts/enrich_bitacora_pages.py:45`

```python
# add_resumen_amigable.py:37
DB_ID = os.getenv("NOTION_BITACORA_DB_ID", "85f89758684744fb9f14076e7ba0930e")
```

El ID de la base de datos Notion de producción está hardcodeado como valor por defecto. Si un atacante obtiene acceso a `NOTION_API_KEY` (e.g., leak en logs), ya tiene el ID del recurso objetivo.

**Recomendación:** Hacer el argumento obligatorio (sin default) o leer exclusivamente de env var sin fallback hardcodeado. Añadir `NOTION_BITACORA_DB_ID` a `.env.example`.

---

### [ALTO] SEC-4 — `config.py` sobreescribe todo el entorno con archivo externo

**Archivo:** `worker/config.py:33`

```python
# _load_openclaw_env()
for k, v in env_pairs:
    os.environ[k] = v   # sobreescribe TODO el entorno
```

El archivo `~/.config/openclaw/env` sobreescribe `os.environ` completo, incluyendo potencialmente `PATH`, `LD_PRELOAD`, `PYTHONPATH` u otras variables sensibles. Si ese archivo es comprometido (e.g., escritura de otro proceso), el worker ejecutaría con un entorno controlado por el atacante.

**Recomendación:** Filtrar las claves permitidas (whitelist) antes de aplicar; o usar un namespace prefijado (`UMBRAL_*`, `OPENCLAW_*`) y solo sobreescribir claves dentro de ese namespace.

---

### [MEDIO] SEC-5 — `LINEAR_WEBHOOK_SECRET` ausente en `.env.example`

**Archivo:** `.env.example` (ausente)

El dispatcher valida firmas HMAC del webhook de Linear usando `LINEAR_WEBHOOK_SECRET`, pero esta variable no aparece en `.env.example`. Un operador nuevo podría desplegar sin ella, dejando el endpoint de webhooks sin validación.

**Recomendación:** Añadir `LINEAR_WEBHOOK_SECRET=` (con nota "required") a `.env.example`.

---

### [BAJO] SEC-6 — SecretStore (Fernet) no integrado con worker/dispatcher

**Archivo:** `infra/secrets.py` (existe pero no se usa)

`worker/config.py` y `dispatcher/` cargan todos los secretos directamente desde `os.environ`. El `SecretStore` con cifrado Fernet existe pero ningún componente lo llama.

**Recomendación:** Adoptar `SecretStore` progresivamente para al menos las claves de API de LLMs y Notion, o documentar explícitamente que la fuente de secretos es el entorno del sistema y que SecretStore está disponible pero no activo.

---

## 2. Autenticación

### [ALTO] SEC-7 — Comparación de WORKER_TOKEN no es timing-safe

**Archivo:** `worker/app.py:183`

```python
# app.py:183
if parts[1] != WORKER_TOKEN:
    raise HTTPException(status_code=401, ...)
```

El operador `!=` puede filtrar información del token mediante timing attacks. El mismo codebase usa `hmac.compare_digest` correctamente en `dispatcher/linear_webhook.py:195`.

**Recomendación:**
```python
import hmac
if not hmac.compare_digest(parts[1], WORKER_TOKEN):
    raise HTTPException(status_code=401, ...)
```

---

### [MEDIO] SEC-8 — Token único compartido, sin rotación ni scoping

**Archivo:** `worker/app.py`, `worker/config.py`

Un único `WORKER_TOKEN` autentica todas las operaciones del worker, incluyendo las tareas de alto riesgo de Windows. No existe mecanismo de rotación, expiración ni alcance por operación.

**Recomendación:** Documentar un procedimiento de rotación. Considerar tokens con scopes (e.g., `windows:*` requiere token adicional). Como mínimo, emitir un log de auditoría en cada autenticación fallida.

---

### [BAJO] SEC-9 — Sin rate limiting en endpoints de autenticación fallida

**Archivo:** `worker/app.py`

El `RateLimiter` se aplica globalmente (60 RPM por IP), pero no existe un contador específico de fallos de autenticación. Un atacante puede intentar fuerza bruta desde múltiples IPs a baja frecuencia.

**Recomendación:** Añadir un contador de fallos de auth por IP con backoff (e.g., bloquear IP tras 10 fallos en 60 s).

---

## 3. Validación de inputs y command injection

### [CRITICO] SEC-10 — `run_as_password` de HTTP enviado a `schtasks /rp`

**Archivo:** `worker/tasks/windows.py:145-155`

```python
# windows.py:151
password = input_data.get("run_as_password", "")
cmd = ["schtasks", "/create", ..., "/rp", password, ...]
subprocess.run(cmd, ...)
```

La contraseña llega como campo HTTP JSON sin validación y se pasa directamente a `schtasks`. Aunque `subprocess.run` con lista evita shell injection, el valor se expone en logs del proceso y en el historial de `schtasks`. Adicionalmente, si el handler alguna vez migra a `shell=True`, se convierte en RCE.

**Recomendación:** No recibir contraseñas como input HTTP. Almacenarlas en el entorno de la VM fuera de banda. Si es imprescindible, cifrar en tránsito y nunca loguear.

---

### [CRITICO] SEC-11 — `name` de firewall rule pasado a `netsh` sin validación

**Archivo:** `worker/tasks/windows.py:244-261`

```python
# windows.py:247-261
name = input_data.get("name", f"Umbral-Port-{port}")
cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
       f"name={name}", ...]
subprocess.run(cmd, ...)
```

El campo `name` se interpola directamente dentro del argumento `name=<valor>`. En Windows, `netsh` puede interpretar ciertos caracteres especiales en el nombre de la regla. Un nombre como `foo" protocol=any dir=in action=allow` podría alterar el comando.

**Recomendación:** Validar `name` con allowlist estricta (`[A-Za-z0-9_-]+`, max 64 chars) antes de pasarlo a `netsh`.

---

### [ALTO] SEC-12 — Username de input usado en construcción de path del sistema

**Archivo:** `worker/tasks/windows.py:312-317`

```python
# windows.py:312-317
username = input_data.get("username", "openclaw")
startup_path = rf"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
```

Un username con `..` o caracteres especiales podría escapar del path esperado. La función `_require_allowed_path()` de `windows_fs.py` NO se llama aquí.

**Recomendación:** Validar `username` con allowlist (`[A-Za-z0-9_.-]+`, max 20 chars) y aplicar `_require_allowed_path()` antes de operar sobre la ruta.

---

### [MEDIO] SEC-13 — `_check_injection()` detecta pero no bloquea

**Archivo:** `worker/sanitize.py`

```python
def _check_injection(value: str) -> None:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning("Possible injection: %r", value)
            # ← NO raise, NO block
```

Patrones de inyección SQL/shell/script se detectan y logean pero la ejecución continúa. La función es informativa, no defensiva.

Agravante: en `app.py:237` el resultado de `sanitize_input()` se descarta (bug P0 de `02-bugs.md`), por lo que incluso el truncado de inputs largos no se aplica.

**Recomendación:** `_check_injection()` debe `raise ValueError` o devolver un flag que el caller convierta en `HTTP 422`. Corregir también el bug de `app.py:237` para aplicar el valor retornado de `sanitize_input()`.

---

### [MEDIO] SEC-14 — Bloques Notion sin sanitización de contenido

**Archivo:** `worker/notion_client.py`

El contenido de las páginas Notion se construye directamente desde campos de tareas (e.g., `task_name`, `resumen`, `content`) sin escape de caracteres especiales de Markdown o de la API de Notion. Si un atacante puede inyectar tareas en la cola de Redis, podría escribir contenido arbitrario en páginas Notion.

**Recomendación:** Truncar y sanitizar los campos textuales antes de enviarlos a la API de Notion. El acceso a Redis no debe ser público.

---

## 4. Dependencias

### [BAJO] SEC-15 — Sin lock files; rangos amplios en requirements.txt

**Archivos:** `worker/requirements.txt`, `dispatcher/requirements.txt`

Todas las dependencias usan rangos amplios (`>=x, <y`) sin `requirements.lock` ni `pip.lock`. Esto permite que una actualización automática introduzca una versión con CVE sin que el equipo lo note.

```
fastapi>=0.104.0,<1.0.0
requests>=2.28.0,<3.0.0
pyyaml>=6.0.0,<7.0.0
langfuse>=2.0.0,<3.0.0
```

**Recomendación:** Fijar versiones exactas en producción (usando `pip freeze > requirements.lock`) o usar `pip-tools` / `uv lock`. Integrar `pip-audit` en CI.

**Cómo ejecutar auditoría de dependencias:**
```bash
pip install pip-audit
pip-audit -r worker/requirements.txt
pip-audit -r dispatcher/requirements.txt
```

---

### [BAJO] SEC-16 — `weasyprint` requiere librerías de sistema no declaradas

**Archivo:** `worker/requirements.txt:14`

`weasyprint>=61.0` depende de Cairo y Pango en el SO. Si el entorno no tiene estas libs, el import falla en runtime (no en instalación). No hay verificación en el healthcheck del worker.

**Recomendación:** Añadir al `Dockerfile` (cuando exista): `apt-get install -y libcairo2 libpango-1.0-0 libpangocairo-1.0-0`. Añadir un smoke test que importe `weasyprint` al inicio del worker.

---

## 5. Configuraciones inseguras

### [MEDIO] SEC-17 — Sin cabeceras de seguridad HTTP en el worker

**Archivo:** `worker/app.py`

El servidor FastAPI no configura cabeceras de seguridad HTTP (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`). Aunque el worker es interno (Tailscale), buenas prácticas dictan incluirlas.

**Recomendación:** Añadir middleware de cabeceras o usar `starlette.middleware.trustedhost.TrustedHostMiddleware`.

---

## Tabla resumen priorizada

| ID     | Severidad | Descripción breve                                      | Archivo principal                        |
| ------ | --------- | ------------------------------------------------------ | ---------------------------------------- |
| SEC-10 | Critico   | run_as_password HTTP → schtasks subprocess             | worker/tasks/windows.py:151              |
| SEC-11 | Critico   | name firewall rule → netsh sin validación              | worker/tasks/windows.py:247              |
| SEC-1  | Critico   | WORKER_TOKEN escrito en plaintext                      | worker/tasks/windows.py:222              |
| SEC-7  | Alto      | WORKER_TOKEN: `!=` en vez de `hmac.compare_digest`    | worker/app.py:183                        |
| SEC-4  | Alto      | config.py sobreescribe TODO os.environ                 | worker/config.py:33                      |
| SEC-12 | Alto      | username de input en path del sistema sin validación   | worker/tasks/windows.py:312              |
| SEC-2  | Alto      | IPs Tailscale de producción en .env.example            | .env.example:112-113                     |
| SEC-3  | Alto      | Notion DB ID hardcodeado como default en scripts       | scripts/add_resumen_amigable.py:37       |
| SEC-13 | Medio     | _check_injection() solo loguea, no bloquea             | worker/sanitize.py                       |
| SEC-14 | Medio     | Contenido Notion sin sanitización                      | worker/notion_client.py                  |
| SEC-8  | Medio     | Token único, sin rotación ni scoping                   | worker/app.py                            |
| SEC-17 | Medio     | Sin cabeceras de seguridad HTTP                        | worker/app.py                            |
| SEC-5  | Medio     | LINEAR_WEBHOOK_SECRET ausente en .env.example          | .env.example                             |
| SEC-6  | Bajo      | SecretStore (Fernet) existe pero no se usa             | infra/secrets.py                         |
| SEC-9  | Bajo      | Sin rate limiting específico para fallos de auth       | worker/app.py                            |
| SEC-15 | Bajo      | Sin lock files; no hay pip-audit en CI                 | worker/requirements.txt                  |
| SEC-16 | Bajo      | weasyprint sin verificación de libs de sistema         | worker/requirements.txt:14               |

---

## Acciones inmediatas recomendadas (Quick Wins)

1. **SEC-7** — 1 línea: cambiar `!=` por `hmac.compare_digest` en `app.py:183`
2. **SEC-11** — Añadir validación de allowlist para `name` antes del comando `netsh`
3. **SEC-13** — Hacer que `_check_injection()` lance excepción en lugar de solo loguear
4. **SEC-3** — Eliminar default hardcodeado del Notion DB ID en los scripts
5. **SEC-2** — Reemplazar IPs reales en `.env.example` con placeholders
6. **SEC-5** — Añadir `LINEAR_WEBHOOK_SECRET=` a `.env.example`
