# Task 013-A — Stage 2 (Fase A): Deploy RSSHub self-hosted en VPS

- **Date:** 2026-05-06
- **Assigned to:** copilot-vps
- **Type:** infra deploy (Docker container, no toca código del stack)
- **Depends on:**
  - Task 012 GREEN (Stage 1 smoke `overall_pass: true`, commit `90f739c`).
  - Docker disponible en VPS (asumido — verificar en pre-check 1).
  - Puerto interno libre: `1200` (default RSSHub). Si está ocupado, usar `1201`.
- **Plan reference:** `docs/plans/linkedin-publication-pipeline.md` §11 items 5-7 (Etapa 1 discovery).
- **Session memory:** `/memories/session/stage2-linkedin-pipeline-plan.md` (Copilot Chat lo tiene; Copilot VPS no — contexto resumido en este task).
- **Status:** ready
- **Estimated effort:** ~30-45 min (incluye troubleshooting Docker).

---

## Contexto

Stage 2 del pipeline LinkedIn = **Etapa 1 del plan: descubrir publicaciones nuevas por referente**. Antes de codear el script de discovery (Task 013-C, futuro), necesitamos un **adapter unificado** que normalice todas las fuentes (RSS, YouTube, web feeds, eventualmente LinkedIn) a formato RSS estándar.

Decisión arquitectónica acordada con David: **RSSHub self-hosted vía Docker** en la VPS. Razones:
- Cubre RSS nativo + YouTube (sin necesidad de provisionar `YOUTUBE_API_KEY` ahora) + 1000+ rutas.
- $0/mes vs $30+ de SaaS (Apify/PhantomBuster).
- Cuando David provisione `YOUTUBE_API_KEY` más adelante, swap solo el adapter de YouTube; RSSHub sigue cubriendo el resto.
- LinkedIn route quedará disponible para Fase B futura (cuenta dummy + cookie `li_at`), pero NO se configura en este task.

**Este task NO toca el código del stack.** Solo levanta el container y verifica que responde a queries básicas.

## Pre-checks (antes de ejecutar)

1. **Repo sincronizado y Docker disponible:**
   ```bash
   cd ~/umbral-agent-stack && git checkout main && git pull --ff-only origin main
   git log --oneline -1   # debe mostrar 90f739c o más reciente
   docker --version       # debe responder; si no, abortar y notificar
   docker ps              # confirmar que el daemon corre y el user puede usarlo sin sudo
   ```
   Si Docker no está instalado o el user no tiene permisos: **abortar y notificar a David**. NO instalar Docker en este task.

2. **Puerto 1200 libre (o decidir alternativa):**
   ```bash
   ss -tlnp | grep -E ':(1200|1201)\s' || echo "puertos 1200/1201 libres"
   ```
   Si `1200` está ocupado, usar `1201` y dejar nota en el reporte. Si ambos están ocupados: abortar y notificar.

3. **Directorio de datos para persistencia (cache opcional de RSSHub):**
   ```bash
   mkdir -p ~/rsshub-data
   ls -ld ~/rsshub-data
   ```

## Comando de ejecución

```bash
# Variables (ajustar PUERTO si pre-check 2 forzó cambio)
PUERTO=1200
CONTAINER_NAME=rsshub
IMAGE=diygod/rsshub:chromium-latest

# Pull de la imagen (la chromium-latest pesa ~1GB; la non-chromium pesa ~200MB
# pero no soporta rutas que requieren JS render. Para nuestro alcance Stage 2
# (RSS + YouTube + Web-RSS) la non-chromium alcanza. Para LinkedIn futuro se
# necesita chromium. Usamos chromium para no migrar después.)
docker pull "$IMAGE"

# Run con restart automático y bind solo a localhost (no exponer público)
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p 127.0.0.1:${PUERTO}:1200 \
  -e CACHE_TYPE=memory \
  -e CACHE_EXPIRE=300 \
  -e NODE_ENV=production \
  "$IMAGE"

# Esperar que arranque (RSSHub tarda ~10-15s en estar listo)
sleep 20

# Verificar que el container está corriendo
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Smoke tests (el deliverable)

Ejecutar los 3 en orden. **Todos deben devolver HTTP 200 con XML válido (`<rss>` o `<feed>` en el body).**

```bash
PUERTO=1200   # o 1201 según pre-check

# (1) Endpoint raíz — health básico
curl -fsS -o /tmp/rsshub-root.html -w "ROOT: HTTP %{http_code}, %{size_download} bytes\n" \
  "http://127.0.0.1:${PUERTO}/"

# (2) YouTube — Kurzgesagt (canal estable, alta cadencia)
curl -fsS -o /tmp/rsshub-youtube.xml -w "YOUTUBE: HTTP %{http_code}, %{size_download} bytes\n" \
  "http://127.0.0.1:${PUERTO}/youtube/channel/UCsXVk37bltHxD1rDPwtNM8Q"

# (3) RSS passthrough — feed conocido (Hacker News front page)
curl -fsS -o /tmp/rsshub-hn.xml -w "HN: HTTP %{http_code}, %{size_download} bytes\n" \
  "http://127.0.0.1:${PUERTO}/hackernews"

# Verificar contenido XML válido en (2) y (3)
head -c 200 /tmp/rsshub-youtube.xml
echo ""
head -c 200 /tmp/rsshub-hn.xml
```

## Criterios de éxito

- **Container `rsshub`:** `docker ps` lo muestra como `Up`.
- **Smoke (1):** HTTP 200, body con HTML del welcome page de RSSHub.
- **Smoke (2):** HTTP 200, body XML que empieza con `<?xml` o `<rss` o `<feed`, contiene al menos 1 `<item>` o `<entry>` con `<title>` que no sea vacío.
- **Smoke (3):** Mismo criterio que (2) pero para Hacker News.
- **Bind seguro:** `ss -tlnp | grep ':1200'` muestra `127.0.0.1:1200`, NO `0.0.0.0:1200` (no debe ser accesible público).
- **Memoria/CPU razonable:** `docker stats rsshub --no-stream` muestra <500MB RAM, <5% CPU en idle.

## Si falla

- **`docker pull` falla con timeout o `manifest unknown`:** problema de red o registry. Reintentar 1 vez. Si persiste, abortar y notificar.
- **Container arranca pero `docker logs rsshub` muestra `EADDRINUSE`:** el puerto se ocupó entre pre-check y `docker run`. Detener container (`docker rm -f rsshub`), cambiar a 1201, reintentar.
- **Smoke (1) responde 200 pero (2) o (3) responden 503/timeout:** RSSHub está vivo pero las rutas externas fallan. Esperar 30s más y reintentar (cold start). Si persisten: pegar `docker logs rsshub --tail 50` en el reporte y abortar.
- **Smoke (2) responde 200 con XML pero sin `<item>`:** ruta YouTube rota (improbable, Kurzgesagt es estable). Probar otro canal: `/youtube/channel/UCBJycsmduvYEL83R_U4JriQ` (MKBHD). Si el segundo también falla vacío, pegar logs y notificar.
- **Container se reinicia en loop (`docker ps` lo muestra como `Restarting`):** problema de imagen o config. Pegar `docker logs rsshub --tail 100` y `docker inspect rsshub | head -50` en el reporte.

En cualquier fallo: **NO** modificar código del stack, **NO** abrir puertos en el firewall, **NO** intentar swap a otra imagen sin notificar.

## Restricciones operacionales

- **NO** exponer RSSHub a internet (bind solo `127.0.0.1`).
- **NO** configurar la cookie `li_at` de LinkedIn en este task (Fase B futura).
- **NO** modificar `~/.config/openclaw/env` ni el `.env` del worker.
- **NO** committear cambios al repo (este task es solo runtime).
- **NO** instalar Docker si no está; abortar y notificar.
- Cookie / credenciales sensibles: si en algún momento futuro se inyectan vía `-e LINKEDIN_COOKIE=...`, NO loguearlas en el reporte.

## Reporte de cierre

Pegar abajo (sección `## Resultado YYYY-MM-DD`):

1. Hash del commit en `main` al momento de ejecutar (no debería cambiar, este task no commitea).
2. Puerto usado (`1200` o `1201`).
3. Output de `docker ps --filter "name=rsshub"`.
4. Output de los 3 `curl` con sus `HTTP %{http_code}` y bytes.
5. Primeras 200 chars del XML de smoke (2) y (3).
6. Output de `ss -tlnp | grep ':1200'` (o el puerto usado) — confirmar bind localhost.
7. Output de `docker stats rsshub --no-stream`.
8. Decisión sugerida: `PASS → Fase A lista, esperar Fase B (cuenta LinkedIn) o avanzar Fase C (script discovery)` / `FAIL → razón`.

## Quality gate

- [ ] Pre-checks 1-3 verdes.
- [ ] Container `rsshub` corriendo y persistente (`--restart unless-stopped`).
- [ ] 3 smoke tests verdes.
- [ ] Bind solo a `127.0.0.1`, no público.
- [ ] Reporte pegado en este archivo con todos los puntos 1-8.
- [ ] Repo VPS en `main`, working tree clean al cerrar.

---

## Resultado YYYY-MM-DD

_(pegar acá el reporte de cierre)_
