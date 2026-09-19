#!/usr/bin/env bash
# =================================================================
# canary-inference.sh — ¿puede el stack generar texto AHORA MISMO?
#
# Esta es la pregunta que ningún monitor hacía. Entre el 2026-09-14 y el
# 2026-09-18 el gateway respondía {"ok":true,"status":"live"} y `supervisor.sh`
# decía «Restarted: none» mientras el agente no podía producir ni una respuesta
# (Linear UMB-276). Liveness no es capacidad.
#
# La sonda ejecuta un TURNO REAL del agente. No usa `capability model run`, y la
# razón está medida: el 2026-09-18, con los perfiles OAuth de OpenAI en cooldown,
# `capability model run` devolvía 200 por `openai/gpt-5.6-sol` usando un tercer
# perfil de api-key, mientras el agente —que corre con authMode=auth-profile—
# fallaba los tres modelos OpenAI y solo respondía por el fallback de Anthropic.
# Una sonda por la vía del CLI habría dado verde con el agente roto.
#
# CRITERIO DE SALUD: el ÉXITO ESTRUCTURAL del turno y el proveedor utilizado.
# El token textual es evidencia ADICIONAL de seguimiento de instrucciones, nunca
# el único criterio: tomarlo como tal producía falsos negativos (el 2026-09-18 el
# agente respondió bien y el canario declaró «no puede generar texto» solo porque
# el modelo no devolvió la cadena exacta).
#
# Salidas: 0 turno correcto (con o sin token literal)
#          1 el turno no completó — el stack no puede generar
#          2 problema de ENTORNO (falta el ejecutable), no de capacidad
#
#   bash scripts/vps/canary-inference.sh [--agent main] [--quiet]
# =================================================================
set -uo pipefail   # sin -e a propósito: aquí un fallo del modelo es un DATO, no un abort

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/lib/umbral_alerting.sh"
umbral_load_env || true

AGENT="main"
QUIET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT="${2:-main}"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    *) shift ;;
  esac
done

# El binario se resuelve a mano: bajo cron el PATH es mínimo y `openclaw` vive en
# ~/.npm-global/bin. Sin esto el canario reportaba «no puede generar texto» cuando
# en realidad no encontraba la herramienta — falsa alarma real en la corrida de
# cron de las 15:00 UTC del 2026-09-18.
OPENCLAW_BIN="${OPENCLAW_BIN:-}"
if [ -z "$OPENCLAW_BIN" ]; then
  if command -v openclaw >/dev/null 2>&1; then
    OPENCLAW_BIN="$(command -v openclaw)"
  else
    for cand in "$HOME/.npm-global/bin/openclaw" /usr/local/bin/openclaw /usr/bin/openclaw; do
      [ -x "$cand" ] && OPENCLAW_BIN="$cand" && break
    done
  fi
fi
if [ -z "$OPENCLAW_BIN" ] || [ ! -x "$OPENCLAW_BIN" ]; then
  echo "[ERROR] canario: no se encuentra el ejecutable 'openclaw'. Es un problema de ENTORNO, no de capacidad."
  umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"canary_inference\",\"release\":\"$(umbral_release_sha)\",\"agent\":\"$AGENT\",\"status\":\"entorno\",\"detail\":\"ejecutable openclaw no encontrado\"}"
  exit 2
fi

TOKEN="CANARIO-$(date -u +%Y%m%d%H%M%S)"
PROMPT="Responde unicamente con ${TOKEN} y nada mas."
START=$(date +%s%3N 2>/dev/null || date +%s000)

OUT=$(timeout 180 "$OPENCLAW_BIN" agent --agent "$AGENT" -m "$PROMPT" --json 2>&1)
RC=$?
END=$(date +%s%3N 2>/dev/null || date +%s000)
MS=$(( END - START ))

# Tres hechos independientes, leídos del JSON del propio turno:
#   1. algún candidato de la cascada terminó con result=success y proveedor;
#   2. el turno cerró (stopReason o finishReason presente);
#   3. hay texto de respuesta no vacío.
EVAL=$(printf '%s' "$OUT" | TOKEN_ESPERADO="$TOKEN" python3 -c '
import sys, json, os
raw = sys.stdin.read()
tok = os.environ.get("TOKEN_ESPERADO", "")
prov = mod = "desconocido"
fb = cerro = texto = False
try:
    d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
except Exception:
    d = None
def walk(o):
    global prov, mod, fb, cerro, texto
    if isinstance(o, dict):
        if o.get("result") == "success" and o.get("provider"):
            prov, mod = o.get("provider", "?"), o.get("model", "?")
        if "fallbackUsed" in o:
            fb = bool(o["fallbackUsed"]) or fb
        if o.get("stopReason") or o.get("finishReason"):
            cerro = True
        for k, v in o.items():
            if k in ("text", "reply") and isinstance(v, str) and v.strip():
                texto = True
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
if d is not None:
    walk(d)
est = "si" if (prov != "desconocido" and cerro and texto) else "no"
print("estructura=%s" % est)
print("proveedor=%s" % prov)
print("modelo=%s" % mod)
print("fallback=%s" % str(fb).lower())
print("token=%s" % ("si" if tok and tok in raw else "no"))
')
EV_ESTRUCTURA=$(printf '%s' "$EVAL" | sed -n 's/^estructura=//p')
PROVIDER=$(printf '%s' "$EVAL" | sed -n 's/^proveedor=//p')
MODEL=$(printf '%s' "$EVAL" | sed -n 's/^modelo=//p')
FALLBACK=$(printf '%s' "$EVAL" | sed -n 's/^fallback=//p')
TOKEN_OK=$(printf '%s' "$EVAL" | sed -n 's/^token=//p')
[ -z "$EV_ESTRUCTURA" ] && EV_ESTRUCTURA="no"
[ -z "$PROVIDER" ] && PROVIDER="desconocido"
[ -z "$MODEL" ] && MODEL="desconocido"
[ -z "$FALLBACK" ] && FALLBACK="false"
[ -z "$TOKEN_OK" ] && TOKEN_OK="no"

STATUS="fail"
DETAIL=""
if [ $RC -eq 124 ]; then
  DETAIL="timeout de 180 s sin respuesta"
elif [ $RC -ne 0 ]; then
  DETAIL=$(printf '%s' "$OUT" | grep -viE '^\[(config|provider-transport-fetch)\]' | tail -3 | tr '\n' ' ')
  [ -z "$DETAIL" ] && DETAIL="exit $RC"
elif [ "$EV_ESTRUCTURA" = "si" ]; then
  if [ "$TOKEN_OK" = "si" ]; then
    STATUS="ok"
  else
    STATUS="ok_sin_token"
    DETAIL="el turno fue correcto pero la respuesta no incluye el token literal"
  fi
else
  DETAIL="el turno no completo: sin proveedor con exito, sin cierre o sin texto de respuesta"
fi

umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"canary_inference\",\"release\":\"$(umbral_release_sha)\",\"agent\":\"$AGENT\",\"status\":\"$STATUS\",\"provider\":\"$PROVIDER\",\"model\":\"$MODEL\",\"fallback_used\":$FALLBACK,\"token_literal\":\"$TOKEN_OK\",\"latency_ms\":$MS,\"detail\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$DETAIL")}"

if [ "$QUIET" -eq 0 ]; then
  case "$STATUS" in
    ok)
      if [ "$FALLBACK" = "true" ]; then
        echo "[OK]  canario: ${PROVIDER}/${MODEL} respondio en ${MS} ms (POR FALLBACK: el primario no sirvio)"
      else
        echo "[OK]  canario: ${PROVIDER}/${MODEL} respondio en ${MS} ms"
      fi ;;
    ok_sin_token)
      echo "[OK]  canario: ${PROVIDER}/${MODEL} completo el turno en ${MS} ms, sin el token literal (no-conformidad del modelo, no fallo de salud)" ;;
    *)
      echo "[FAIL] canario: el agente '$AGENT' no pudo generar texto — ${DETAIL}" ;;
  esac
  # Linea legible por maquina, SIEMPRE, sea cual sea el estado. Quien vigile la
  # degradacion no debe tener que reconocer una frase en prosa: el aviso "POR
  # FALLBACK" solo se imprimia en el estado ok, de modo que un turno correcto
  # sin el token literal ocultaba que el primario no habia servido. Es el mismo
  # defecto que tenia el ensayo sintetico al comprobar el registro por
  # coincidencia de texto.
  echo "[CANARIO] status=${STATUS} provider=${PROVIDER} model=${MODEL} fallback=${FALLBACK} latency_ms=${MS}"
fi

case "$STATUS" in
  ok|ok_sin_token) exit 0 ;;
esac
{ [ $RC -eq 126 ] || [ $RC -eq 127 ]; } && exit 2
exit 1
