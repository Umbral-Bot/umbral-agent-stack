#!/usr/bin/env bash
# =================================================================
# umbral_alerting.sh — utilidades compartidas de alerta para los monitores del VPS.
#
# Nace del incidente del 2026-09-14/18 (Linear UMB-276): el stack estuvo 3,7 días
# sin poder generar texto y ningún monitor avisó, porque la cadena de aviso estaba
# rota en cuatro puntos independientes. Este archivo cierra esos cuatro puntos y
# añade deduplicación, enfriamiento y latido.
#
# Se usa con `source`. No ejecuta nada por sí mismo y no imprime secretos.
#
#   source "$(dirname "$0")/lib/umbral_alerting.sh"
#   umbral_load_env
#   umbral_heartbeat_write health-check
#   umbral_alert health-check "titulo corto" "cuerpo largo..."
# =================================================================

# Directorio DURABLE de estado de los monitores. No /tmp: allí systemd-tmpfiles
# borra a los 30 días justo la prueba de que un monitor enmudeció.
UMBRAL_MON_STATE_DIR="${UMBRAL_MON_STATE_DIR:-$HOME/.config/umbral/monitor}"

# Límite duro de la API de comentarios de Notion. El 2026-09-18T06:00:24 un aviso
# real murió con 400 por 2786 caracteres: la notificación fallaba justo cuando
# había mucho que contar.
UMBRAL_NOTION_MAX_CHARS="${UMBRAL_NOTION_MAX_CHARS:-1900}"

# Ventana de silencio por alerta repetida, en segundos.
UMBRAL_ALERT_COOLDOWN_S="${UMBRAL_ALERT_COOLDOWN_S:-3600}"

# -----------------------------------------------------------------
# umbral_load_env — carga ~/.config/openclaw/env sin volcarlo.
#
# health-check.sh no hacía esto, así que bajo cron WORKER_TOKEN llegaba vacío y
# el aviso se saltaba por la rama "(WORKER_TOKEN not set)".
#
# El archivo aporta VALORES POR DEFECTO: nunca pisa una variable que ya venga
# definida por quien llama. Sin esa regla, un `WORKER_URL=...` puesto a propósito
# (por ejemplo para un ensayo dirigido a un stub local) quedaba sobrescrito por
# el valor real y el aviso salía al destino de producción. Ocurrió de verdad el
# 2026-09-18 durante el primer ensayo sintético: cuatro avisos de prueba
# terminaron en la página real de alertas.
#
# Nada se imprime ni se registra: los valores no pasan por stdout en ningún caso.
# -----------------------------------------------------------------
umbral_load_env() {
  local env_file="${UMBRAL_ENV_FILE:-$HOME/.config/openclaw/env}"
  [ -r "$env_file" ] || return 1
  local line key
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ''|'#'*) continue ;;
    esac
    line="${line#export }"
    key="${line%%=*}"
    # Solo nombres de variable plausibles, y solo si aún no tienen valor.
    case "$key" in
      *[!A-Za-z0-9_]*|'') continue ;;
    esac
    if [ -z "${!key:-}" ]; then
      local value="${line#*=}"
      # Quita comillas envolventes si las hay.
      case "$value" in
        \"*\") value="${value:1:${#value}-2}" ;;
        \'*\') value="${value:1:${#value}-2}" ;;
      esac
      export "$key=$value"
    fi
  done < "$env_file"
  return 0
}


# -----------------------------------------------------------------
# umbral_release_sha — commit REALMENTE en ejecucion.
# Devuelve el sha del release si se corre desde uno, o "arbol-de-trabajo:<sha>"
# si se corre desde el checkout. Esa distincion es el punto: un log que no
# distingue ambos casos no permite saber que codigo produjo un resultado.
# -----------------------------------------------------------------
umbral_release_sha() {
  # Este archivo vive en <raiz>/scripts/vps/lib/, asi que la raiz esta tres
  # niveles arriba. Con dos se apuntaba a <raiz>/scripts y el RELEASE_SHA nunca
  # se encontraba: todo evento se registraba como "arbol-de-trabajo:desconocido"
  # aunque corriera desde un release.
  local d; d="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  if [ -f "$d/RELEASE_SHA" ]; then
    cat "$d/RELEASE_SHA"
  else
    local s; s="$(git -C "$d" rev-parse HEAD 2>/dev/null || echo desconocido)"
    printf 'arbol-de-trabajo:%s' "$s"
  fi
}

# -----------------------------------------------------------------
# umbral_truncate <texto> [max]
# Recorta por debajo del máximo dejando constancia de que se recortó.
# -----------------------------------------------------------------
umbral_truncate() {
  local text="$1"
  local max="${2:-$UMBRAL_NOTION_MAX_CHARS}"
  local len=${#text}
  if [ "$len" -le "$max" ]; then
    printf '%s' "$text"
    return 0
  fi
  local suffix=" […recortado: ${len} caracteres; detalle completo en el log del monitor]"
  local keep=$(( max - ${#suffix} ))
  [ "$keep" -lt 1 ] && keep=1
  printf '%s%s' "${text:0:$keep}" "$suffix"
}

# -----------------------------------------------------------------
# umbral_fingerprint <texto>
# Huella del estado CUALITATIVO. Se normalizan los valores volátiles (horas,
# duraciones, pids, contadores) para que un mismo fallo no genere una huella
# nueva en cada ciclo — que es lo que convierte un monitor en ruido.
# -----------------------------------------------------------------
umbral_fingerprint() {
  printf '%s' "$1" \
    | sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9:]+Z?//g; s/\b[0-9]+(\.[0-9]+)?(ms|s|m|h)\b//g; s/\bpid=[0-9]+//g; s/\b[0-9]{3,}\b//g' \
    | tr -s ' ' \
    | sha256sum | cut -d' ' -f1
}

# -----------------------------------------------------------------
# umbral_should_alert <monitor> <huella>
# 0 = hay que avisar (estado nuevo, o venció el enfriamiento).
# 1 = callar (mismo estado dentro de la ventana).
# Registra también la transición a sano para poder avisar de la RECUPERACIÓN.
# -----------------------------------------------------------------
umbral_should_alert() {
  local monitor="$1" fp="$2"
  mkdir -p "$UMBRAL_MON_STATE_DIR"
  local f="$UMBRAL_MON_STATE_DIR/${monitor}.alert"
  local now; now=$(date +%s)
  if [ -f "$f" ]; then
    local prev_fp prev_ts
    prev_fp=$(sed -n '1p' "$f" 2>/dev/null || true)
    prev_ts=$(sed -n '2p' "$f" 2>/dev/null || echo 0)
    if [ "$prev_fp" = "$fp" ] && [ $(( now - prev_ts )) -lt "$UMBRAL_ALERT_COOLDOWN_S" ]; then
      return 1
    fi
  fi
  printf '%s\n%s\n' "$fp" "$now" > "$f"
  return 0
}

# -----------------------------------------------------------------
# umbral_clear_alert <monitor>
# Marca el estado sano. Devuelve 0 solo si VENÍA de estar en alerta, para que
# quien llama pueda avisar de la recuperación una sola vez.
# -----------------------------------------------------------------
umbral_clear_alert() {
  local monitor="$1"
  local f="$UMBRAL_MON_STATE_DIR/${monitor}.alert"
  if [ -f "$f" ]; then
    rm -f "$f"
    return 0
  fi
  return 1
}

# -----------------------------------------------------------------
# umbral_heartbeat_write <monitor>
# Marca de última ejecución correcta, en sitio durable. La detección de que un
# monitor murió se hace por AUSENCIA de marca fresca, no por presencia de logs.
# -----------------------------------------------------------------
umbral_heartbeat_write() {
  local monitor="$1"
  mkdir -p "$UMBRAL_MON_STATE_DIR"
  date +%s > "$UMBRAL_MON_STATE_DIR/${monitor}.beat"
}

# -----------------------------------------------------------------
# umbral_heartbeat_age <monitor>
# Segundos desde la última marca. -1 si nunca la hubo.
# -----------------------------------------------------------------
umbral_heartbeat_age() {
  local monitor="$1"
  local f="$UMBRAL_MON_STATE_DIR/${monitor}.beat"
  if [ ! -f "$f" ]; then echo -1; return 0; fi
  local beat now
  beat=$(cat "$f" 2>/dev/null || echo 0)
  now=$(date +%s)
  echo $(( now - beat ))
}

# -----------------------------------------------------------------
# umbral_heartbeat_stale <monitor> <max_s>
# 0 = la marca está rancia o no existe (el monitor no corrió) → incidente.
# -----------------------------------------------------------------
umbral_heartbeat_stale() {
  local age; age=$(umbral_heartbeat_age "$1")
  [ "$age" -lt 0 ] && return 0
  [ "$age" -gt "$2" ] && return 0
  return 1
}

# -----------------------------------------------------------------
# umbral_ops_log <evento_json>
# Escribe en la fuente canónica. Append-only, una línea por evento.
# No se crea ninguna superficie de estado nueva: ops_log.jsonl ya existe.
# -----------------------------------------------------------------
umbral_ops_log() {
  local dir="${UMBRAL_OPS_LOG_DIR:-$HOME/.config/umbral}"
  mkdir -p "$dir"
  printf '%s\n' "$1" >> "$dir/ops_log.jsonl"
}

# -----------------------------------------------------------------
# umbral_alert <monitor> <titulo> <cuerpo> [severidad]
# Aviso deduplicado, con enfriamiento y troceado por debajo del máximo de Notion.
# Devuelve 0 si avisó, 1 si calló por deduplicación, 2 si no pudo enviar.
# Nunca imprime el token.
# -----------------------------------------------------------------
umbral_alert() {
  local monitor="$1" title="$2" body="$3" sev="${4:-warn}"
  local fp; fp=$(umbral_fingerprint "$title $body")

  # Un aviso informativo (tipicamente la recuperacion) lleva su propio estado.
  # Si escribiera el estado de FALLO, umbral_clear_alert lo encontraria en el
  # ciclo siguiente y volveria a anunciar la recuperacion, una y otra vez.
  local key="$monitor"
  [ "$sev" = "info" ] && key="${monitor}.info"

  if ! umbral_should_alert "$key" "$fp"; then
    echo "(alerta silenciada: mismo estado dentro de la ventana de ${UMBRAL_ALERT_COOLDOWN_S}s)"
    umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"monitor_alert_suppressed\",\"monitor\":\"$monitor\",\"severity\":\"$sev\",\"fingerprint\":\"$fp\"}"
    return 1
  fi

  local text; text=$(umbral_truncate "Rick [$sev] $title — $body")
  umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"monitor_alert\",\"release\":\"$(umbral_release_sha)\",\"monitor\":\"$monitor\",\"severity\":\"$sev\",\"fingerprint\":\"$fp\",\"chars\":${#text}}"

  local url="${WORKER_URL:-http://127.0.0.1:8088}"
  local token="${WORKER_TOKEN:-}"
  if [ -z "$token" ]; then
    echo "(sin WORKER_TOKEN tras cargar el env: no se pudo enviar el aviso)"
    return 2
  fi

  local payload
  payload=$(python3 -c 'import json,sys; print(json.dumps({"task":"notion.add_comment","input":{"text":sys.argv[1]}}))' "$text")
  if curl -sf -X POST "${url}/run" \
        -H "Authorization: Bearer ${token}" \
        -H "Content-Type: application/json" \
        -H "X-Umbral-Caller: cron.${monitor}" \
        -d "$payload" > /dev/null 2>&1; then
    echo "(aviso enviado, ${#text} caracteres)"
    return 0
  fi
  echo "(fallo al enviar el aviso)"
  return 2
}
