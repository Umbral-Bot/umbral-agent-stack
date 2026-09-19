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

# Ventana de silencio por alerta repetida, en segundos. Es la PRIMERA ventana:
# si el mismo estado persiste, cada reaviso la duplica hasta el tope de abajo.
UMBRAL_ALERT_COOLDOWN_S="${UMBRAL_ALERT_COOLDOWN_S:-3600}"

# Tope del retroceso exponencial: "como mucho, un aviso al dia". Un estado
# degradado que ya esta registrado en un incidente abierto no debe avisar cada
# hora indefinidamente: eso desensibiliza a quien lo lee, que es como se pierde
# el aviso que si importa. Medido el 2026-09-18: el aviso "responde solo por
# fallback" era CIERTO y aun asi genero 15 comentarios en Notion en 18,5 horas
# sobre una condicion ya conocida.
#
# Son 23 h y no 24 a proposito. e2e-validation corre una vez al dia (0 6 * * *):
# con un tope de exactamente 86400 s, la comparacion contra el ciclo del dia
# siguiente se decide por unos segundos de deriva —lo que tarde la suite antes
# de avisar— y el aviso se va a 48 h la mitad de las veces. El tope tiene que
# quedar por DEBAJO de la cadencia del monitor mas lento, o deja de ser un tope
# y pasa a ser una loteria.
UMBRAL_ALERT_BACKOFF_MAX_S="${UMBRAL_ALERT_BACKOFF_MAX_S:-82800}"

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
# umbral_alert_window <reavisos>
# Ventana de silencio, en segundos, para un estado que ya se avisó <reavisos>
# veces. Es la cadencia DOCUMENTADA del retroceso exponencial:
#
#   reavisos: 0     1     2     3     4      5+
#   ventana : 1 h   2 h   4 h   8 h   16 h   23 h (tope: un aviso al dia)
#
# Función pura: no lee el reloj ni el disco, para que la cadencia pueda
# comprobarse sin depender del tiempo real.
# -----------------------------------------------------------------
umbral_alert_window() {
  local n="${1:-0}" ventana="$UMBRAL_ALERT_COOLDOWN_S" i=0
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  while [ "$i" -lt "$n" ] && [ "$ventana" -lt "$UMBRAL_ALERT_BACKOFF_MAX_S" ]; do
    ventana=$(( ventana * 2 )); i=$(( i + 1 ))
  done
  [ "$ventana" -gt "$UMBRAL_ALERT_BACKOFF_MAX_S" ] && ventana="$UMBRAL_ALERT_BACKOFF_MAX_S"
  printf '%s' "$ventana"
}

# -----------------------------------------------------------------
# umbral_alert_reavisos <monitor>
# Cuántas veces se ha REAVISADO ya del estado actual. 0 si no hay estado.
# -----------------------------------------------------------------
umbral_alert_reavisos() {
  local f="$UMBRAL_MON_STATE_DIR/${1}.alert" n=0
  [ -f "$f" ] && n=$(sed -n '3p' "$f" 2>/dev/null || echo 0)
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  printf '%s' "$n"
}

# -----------------------------------------------------------------
# umbral_should_alert <monitor> <huella>
# DECIDE. No escribe nada.
# 0 = hay que avisar (estado nuevo, o venció la ventana).
# 1 = callar (mismo estado dentro de la ventana).
# Deja en UMBRAL_ALERT_PENDING_N el contador que habrá que guardar si —y solo
# si— el aviso llega a ENTREGARSE.
#
# Decidir y guardar estaban unidos hasta el 2026-09-19: el estado de silencio se
# escribía ANTES de intentar el envío, así que un aviso que no lograba salir
# silenciaba igualmente el intento siguiente, y cada reintento que sí cruzaba la
# ventana duplicaba el silencio. Como la vía de aviso sale por el worker que se
# vigila, "no se pudo entregar" coincide exactamente con el caso en que hay que
# insistir. Es la misma familia de fallo que el incidente UMB-276: dar por
# avisado lo que nadie recibió.
# -----------------------------------------------------------------
umbral_should_alert() {
  local monitor="$1" fp="$2"
  local f="$UMBRAL_MON_STATE_DIR/${monitor}.alert"
  local now; now=$(date +%s)
  UMBRAL_ALERT_PENDING_N=0
  if [ -f "$f" ]; then
    local prev_fp prev_ts prev_n ventana
    prev_fp=$(sed -n '1p' "$f" 2>/dev/null || true)
    prev_ts=$(sed -n '2p' "$f" 2>/dev/null || echo 0)
    prev_n=$(sed -n '3p' "$f" 2>/dev/null || echo 0)
    case "$prev_ts" in ''|*[!0-9]*) prev_ts=0 ;; esac
    case "$prev_n" in ''|*[!0-9]*) prev_n=0 ;; esac
    if [ "$prev_fp" = "$fp" ]; then
      ventana=$(umbral_alert_window "$prev_n")
      if [ $(( now - prev_ts )) -lt "$ventana" ]; then
        return 1
      fi
      # Mismo estado y ventana vencida: toca reavisar, con la ventana siguiente.
      UMBRAL_ALERT_PENDING_N=$(( prev_n + 1 ))
    fi
    # Estado distinto: se avisa ya y el retroceso vuelve a empezar (PENDING_N=0).
  fi
  return 0
}

# -----------------------------------------------------------------
# umbral_commit_alert <monitor> <huella> [reavisos]
# Abre la ventana de silencio. Se llama SOLO después de una entrega confirmada:
# el silencio lo gana un aviso entregado, nunca un aviso intentado.
# -----------------------------------------------------------------
umbral_commit_alert() {
  local monitor="$1" fp="$2" n="${3:-${UMBRAL_ALERT_PENDING_N:-0}}"
  mkdir -p "$UMBRAL_MON_STATE_DIR"
  printf '%s\n%s\n%s\n' "$fp" "$(date +%s)" "$n" > "$UMBRAL_MON_STATE_DIR/${monitor}.alert"
}

# -----------------------------------------------------------------
# umbral_alert_active <monitor>
# 0 si el monitor está en alerta entregada (hay ventana abierta).
# -----------------------------------------------------------------
umbral_alert_active() {
  [ -f "$UMBRAL_MON_STATE_DIR/${1}.alert" ]
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
# Aviso deduplicado, con retroceso exponencial y troceado por debajo del máximo
# de Notion. Devuelve 0 si se ENTREGÓ, 1 si calló por deduplicación, 2 si no
# pudo entregarse. Nunca imprime el token.
#
# El orden importa: primero se intenta entregar y solo una entrega confirmada
# abre la ventana de silencio y se registra como aviso emitido. Un intento
# fallido se registra aparte, como lo que es, y deja el siguiente ciclo libre
# para insistir.
# -----------------------------------------------------------------
umbral_alert() {
  local monitor="$1" title="$2" body="$3" sev="${4:-warn}"
  local fp; fp=$(umbral_fingerprint "$title $body")
  local ts; ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # Un aviso informativo (tipicamente la recuperacion) lleva su propio estado.
  # Si escribiera el estado de FALLO, umbral_clear_alert lo encontraria en el
  # ciclo siguiente y volveria a anunciar la recuperacion, una y otra vez.
  local key="$monitor"
  [ "$sev" = "info" ] && key="${monitor}.info"

  if ! umbral_should_alert "$key" "$fp"; then
    local ventana; ventana=$(umbral_alert_window "$(umbral_alert_reavisos "$key")")
    echo "(alerta silenciada: mismo estado dentro de la ventana de ${ventana}s)"
    umbral_ops_log "{\"ts\":\"$ts\",\"kind\":\"monitor_alert_suppressed\",\"monitor\":\"$monitor\",\"severity\":\"$sev\",\"fingerprint\":\"$fp\",\"ventana_s\":$ventana}"
    return 1
  fi

  local pendiente="${UMBRAL_ALERT_PENDING_N:-0}"
  local text; text=$(umbral_truncate "Rick [$sev] $title — $body")
  local release; release=$(umbral_release_sha)

  local url="${WORKER_URL:-http://127.0.0.1:8088}"
  local token="${WORKER_TOKEN:-}"
  if [ -z "$token" ]; then
    echo "(sin WORKER_TOKEN tras cargar el env: no se pudo enviar el aviso)"
    umbral_ops_log "{\"ts\":\"$ts\",\"kind\":\"monitor_alert_failed\",\"release\":\"$release\",\"monitor\":\"$monitor\",\"severity\":\"$sev\",\"fingerprint\":\"$fp\",\"motivo\":\"sin_token\"}"
    return 2
  fi

  local payload
  payload=$(python3 -c 'import json,sys; print(json.dumps({"task":"notion.add_comment","input":{"text":sys.argv[1]}}))' "$text")
  # Con tiempo maximo: un envio colgado bajo cron deja al monitor sin terminar,
  # y un monitor que no termina es un monitor que no vuelve a comprobar nada.
  #
  # 90 s, no 20: worker/notion_client.py usa TIMEOUT=60.0 contra la API de
  # Notion. Con 20 s se cortaria una entrega lenta que el worker SI va a
  # completar, se contaria como fallida, y el ciclo siguiente la repetiria:
  # un comentario duplicado en Notion, que es justo el ruido que se viene a
  # quitar. El tope sigue acotado muy por debajo del ciclo de 30 min.
  if curl -sf -m "${UMBRAL_ALERT_TIMEOUT_S:-90}" -X POST "${url}/run" \
        -H "Authorization: Bearer ${token}" \
        -H "Content-Type: application/json" \
        -H "X-Umbral-Caller: cron.${monitor}" \
        -d "$payload" > /dev/null 2>&1; then
    umbral_commit_alert "$key" "$fp" "$pendiente"
    # Fallo y recuperacion son las dos mitades de una misma transicion. Si al
    # abrir un incidente sobreviviera el estado del ultimo "ya esta sano", el
    # proximo aviso de recuperacion —cuyo texto es siempre el mismo, y por tanto
    # su huella tambien— quedaria silenciado por la ventana que gano la vez
    # anterior, y con el retroceso acumulado eso llega a ser un dia entero. El
    # resultado seria una cadena de fallos anunciados sin ningun cierre.
    [ "$sev" = "info" ] || rm -f "$UMBRAL_MON_STATE_DIR/${monitor}.info.alert"
    umbral_ops_log "{\"ts\":\"$ts\",\"kind\":\"monitor_alert\",\"release\":\"$release\",\"monitor\":\"$monitor\",\"severity\":\"$sev\",\"fingerprint\":\"$fp\",\"chars\":${#text},\"reavisos\":$pendiente,\"proxima_ventana_s\":$(umbral_alert_window "$pendiente"),\"entrega\":\"ok\"}"
    echo "(aviso enviado, ${#text} caracteres)"
    return 0
  fi
  umbral_ops_log "{\"ts\":\"$ts\",\"kind\":\"monitor_alert_failed\",\"release\":\"$release\",\"monitor\":\"$monitor\",\"severity\":\"$sev\",\"fingerprint\":\"$fp\",\"motivo\":\"error_de_envio\"}"
  echo "(fallo al enviar el aviso: no se abre ventana de silencio, se reintenta en el proximo ciclo)"
  return 2
}
