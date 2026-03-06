# 37 — n8n en la VPS (automatizaciones)

## Objetivo

**n8n** se instala en la VPS (Hostinger) para ampliar la capacidad de automatizaciones sin depender solo de crons y del Worker: flujos visuales, webhooks, integraciones (Notion, Linear, Telegram, HTTP, etc.) y orquestación entre servicios. Rick lo instalará en la VPS; este doc deja el criterio y la referencia.

## Responsable de la instalación

- **Rick** (o quien ejecute en la VPS) instala y deja n8n operativo según la documentación oficial y las restricciones de la VPS (ver abajo).

## Requisitos y consideraciones en la VPS

- **Entorno:** Linux (VPS Hostinger). Node.js 18+ para n8n (o usar imagen Docker si está disponible).
- **Puerto:** Por defecto n8n usa **5678**. Exponer solo por Tailscale o reverse proxy (no abrir a internet sin auth).
- **Persistencia:** Directorio de datos de n8n (workflows, credenciales) en disco persistente (ej. `~/.n8n` o volumen Docker).
- **Credenciales:** No commitear en el repo. n8n guarda las suyas en su propio almacén; para que los flujos accedan a Notion/Linear/Telegram/etc., configurarlas en la UI de n8n o por variables de entorno de n8n.
- **Arranque:** Servicio systemd o Docker para que n8n sobreviva reinicios.

## Integración con el stack Umbral

- n8n puede **consumir webhooks** (p. ej. desde Notion, Linear o el Worker si se añade un endpoint).
- n8n puede **llamar al Worker** (HTTP) o a Redis para encolar tareas, y a Notion/Linear APIs con las credenciales que se configuren en n8n.
- **No reemplaza** al protocolo `.agents/` ni al board: Cursor/Codex/Copilot siguen leyendo `PROTOCOL.md` y `board.md`. n8n es una capa extra de automatización (flujos recurrentes, notificaciones, sincronizaciones).

## Instalación típica en la VPS (npm global)

Rick (o quien instale) suele dejar n8n en:

- **Binario:** `~/.npm-global/bin/n8n`
- **Problema:** ese directorio no está en `PATH` por defecto, por eso el comando `n8n` no se encuentra.

### Arreglar PATH y dejar n8n en segundo plano

En la VPS, como el usuario que instaló n8n (ej. `rick`), ejecutar:

```bash
cd ~/umbral-agent-stack && bash scripts/vps/n8n-path-and-service.sh
```

Ese script:

1. Añade `export PATH="$HOME/.npm-global/bin:$PATH"` a `~/.bashrc` (si no está) para que en nuevas sesiones `n8n` funcione directo.
2. Crea un servicio systemd de usuario `~/.config/systemd/user/n8n.service` para arrancar n8n en segundo plano y que sobreviva a reinicios.

Después de ejecutarlo:

- **Solo PATH (sin servicio):** en una terminal nueva `n8n` ya funciona; para levantarlo a mano: `n8n start` (o `n8n`).
- **Con servicio:** activar y arrancar n8n como servicio de usuario:
  ```bash
  systemctl --user daemon-reload
  systemctl --user enable n8n
  systemctl --user start n8n
  systemctl --user status n8n
  ```
  Acceso: `http://localhost:5678` (o la IP Tailscale de la VPS:5678 si el firewall lo permite).

## Documentación oficial

- [n8n.io docs](https://docs.n8n.io/) — instalación, configuración, nodos (Notion, Linear, Telegram, HTTP, etc.).
- Instalación con npm: `npm install n8n -g` (o con npx/docker; ver docs).
- Variables de entorno n8n: `N8N_PORT`, `N8N_PROTOCOL`, `N8N_HOST`, etc. (opcional para customizar puerto y URL).

## Checklist post-instalación (Rick o quien instale)

- [ ] Ejecutar `scripts/vps/n8n-path-and-service.sh` en la VPS (PATH + unit systemd).
- [ ] Opcional: `systemctl --user enable --now n8n` para que n8n arranque con el usuario.
- [ ] n8n accesible (ej. `http://localhost:5678` o vía Tailscale).
- [ ] Credenciales de Notion/Linear/Telegram (las que hagan falta) configuradas en la UI de n8n, no en el repo.
- [ ] Si se expone fuera de localhost, usar HTTPS y auth (reverse proxy o auth nativo de n8n).

## Referencias en el repo

- Dashboard y métricas: [docs/22-notion-dashboard-gerencial.md](22-notion-dashboard-gerencial.md).
- Control Room y Enlace: [docs/18-notion-enlace-rick-convention.md](18-notion-enlace-rick-convention.md).
- Linear: [docs/30-linear-notion-architecture.md](30-linear-notion-architecture.md).
- **Kimi como recurso LLM para n8n:** [docs/kimi-recurso-n8n.md](kimi-recurso-n8n.md) — endpoint, headers y uso en flujos cuando Rick use Kimi en automatizaciones.
