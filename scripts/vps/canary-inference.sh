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
# `capability model run` devolvía 200 por `openai/gpt-5.6-sol` usando el tercer
# perfil (api-key `openai:default`), mientras el agente —que corre con
# authMode=auth-profile— fallaba los tres modelos OpenAI y solo respondía por el
# fallback de Anthropic. Una sonda por la vía del CLI habría dado verde con el
# agente roto: exactamente el falso positivo que este trabajo existe para cerrar.
#
# Salida: 0 canario correcto, 1 respuesta ausente o incorrecta, 2 error de entorno.
# Escribe el resultado en la fuente canónica (ops_log.jsonl). No imprime secretos.
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

# El binario hay que resolverlo a mano: bajo cron el PATH es minimo y `openclaw`
# vive en ~/.npm-global/bin. Sin esto el canario reporta "no puede generar texto"
# cuando en realidad no encuentra la herramienta — una falsa alarma que ya ocurrio
# de verdad en la corrida de cron de las 15:00 UTC del 2026-09-18.
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
  echo "[ERROR] canario: no se encuentra el ejecutable 'openclaw'. Esto es un problema de ENTORNO, no de capacidad del modelo."
  umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"canary_inference\",\"agent\":\"$AGENT\",\"status\":\"entorno\",\"detail\":\"ejecutable openclaw no encontrado\"}"
  exit 2
fi

TOKEN="CANARIO-$(date -u +%Y%m%d%H%M%S)"
PROMPT="Responde unicamente con ${TOKEN} y nada mas."
START=$(date +%s%3N 2>/dev/null || date +%s000)

# --json y sin --deliver: no se envía a ningún canal, solo se mide la capacidad.
OUT=$(timeout 180 "$OPENCLAW_BIN" agent --agent "$AGENT" -m "$PROMPT" --json 2>&1)
RC=$?
END=$(date +%s%3N 2>/dev/null || date +%s000)
MS=$(( END - START ))

# Proveedor/modelo EFECTIVOS: el último candidato de la cascada con result=success.
read -r PROVIDER MODEL FALLBACK <<<"$(printf '%s' "$OUT" | python3 -c '
import sys,json,re
raw=sys.stdin.read()
prov=mod="desconocido"; fb="false"
try:
    d=json.loads(raw[raw.index("{"):raw.rindex("}")+1])
except Exception:
    print(prov,mod,fb); raise SystemExit
def walk(o):
    if isinstance(o,dict):
        if o.get("result")=="success" and o.get("provider"): yield o
        if "fallbackUsed" in o: yield {"_fb":bool(o["fallbackUsed"])}
        for v in o.values(): yield from walk(v)
    elif isinstance(o,list):
        for v in o: yield from walk(v)
for e in walk(d):
    if "_fb" in e: fb="true" if e["_fb"] else "false"
    else: prov,mod=e.get("provider","?"),e.get("model","?")
print(prov,mod,fb)
')"
[ -z "${PROVIDER:-}" ] && PROVIDER="desconocido"
[ -z "${MODEL:-}" ] && MODEL="desconocido"
[ -z "${FALLBACK:-}" ] && FALLBACK="false"

STATUS="fail"
DETAIL=""
if [ $RC -eq 124 ]; then
  DETAIL="timeout de 180 s sin respuesta"
elif [ $RC -ne 0 ]; then
  DETAIL=$(printf '%s' "$OUT" | grep -viE '^\[(config|provider-transport-fetch)\]' | tail -3 | tr '\n' ' ')
  [ -z "$DETAIL" ] && DETAIL="exit $RC"
elif printf '%s' "$OUT" | grep -qF "$TOKEN"; then
  STATUS="ok"
else
  DETAIL="respuesta sin el token canario (respuesta vacia o incorrecta)"
fi

umbral_ops_log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"kind\":\"canary_inference\",\"agent\":\"$AGENT\",\"status\":\"$STATUS\",\"provider\":\"$PROVIDER\",\"model\":\"$MODEL\",\"fallback_used\":$FALLBACK,\"latency_ms\":$MS,\"detail\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$DETAIL")}"

if [ "$QUIET" -eq 0 ]; then
  if [ "$STATUS" = "ok" ]; then
    if [ "$FALLBACK" = "true" ]; then
      echo "[OK]  canario: ${PROVIDER}/${MODEL} respondio en ${MS} ms (POR FALLBACK: el primario no sirvio)"
    else
      echo "[OK]  canario: ${PROVIDER}/${MODEL} respondio en ${MS} ms"
    fi
  else
    echo "[FAIL] canario: el agente '$AGENT' no pudo generar texto — ${DETAIL}"
  fi
fi

[ "$STATUS" = "ok" ] && exit 0
# 127 = ejecutable ausente; 126 = no ejecutable. Son problemas de ENTORNO y no
# deben contarse como "el modelo no responde".
{ [ $RC -eq 126 ] || [ $RC -eq 127 ]; } && exit 2
exit 1
