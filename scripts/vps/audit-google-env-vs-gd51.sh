#!/usr/bin/env bash
# G-D5.2 closeout audit — compare live env vars vs G-D5.1 expected state.
# Prints var names + SET/UNSET only. NEVER prints secret values.
set -eo pipefail

ENV="${HOME}/.config/openclaw/env"
EVID="${HOME}/.coord-ag-evidence/G-D5.2"
mkdir -p "$EVID"

if [[ ! -f "$ENV" ]]; then
  echo "FATAL: env file not found: $ENV" >&2
  exit 1
fi

# Load env names only (no export to stdout)
declare -A env_vars=()
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  key="${line%%=*}"
  [[ -z "$key" || "$key" == "$line" ]] && continue
  env_vars["$key"]="SET"
done < "$ENV"

echo "=== G-D5.2 closeout audit: env vars vs G-D5.1 ==="
echo ""

# G-D5.1 expected SET (7 vars)
EXPECTED_SET=(
  GOOGLE_GMAIL_CLIENT_ID
  GOOGLE_GMAIL_CLIENT_SECRET
  GOOGLE_GMAIL_REFRESH_TOKEN
  GOOGLE_CALENDAR_CLIENT_ID
  GOOGLE_CALENDAR_CLIENT_SECRET
  GOOGLE_CALENDAR_REFRESH_TOKEN
  GOOGLE_CLOUD_LOCATION
)

# G-D5.1 expected UNSET (3 vars)
EXPECTED_UNSET=(
  GOOGLE_GMAIL_TOKEN
  GOOGLE_CALENDAR_TOKEN
  GOOGLE_SERVICE_ACCOUNT_JSON
)

set_count=0
unset_count=0
fail=0

echo "| Var | Expected | Actual | Match |"
echo "|---|---|---|---|"

for var in "${EXPECTED_SET[@]}"; do
  actual="UNSET"
  [[ -n "${env_vars[$var]+x}" ]] && actual="SET"
  if [[ "$actual" == "SET" ]]; then
    echo "| $var | SET | SET | OK |"
    set_count=$((set_count + 1))
  else
    echo "| $var | SET | UNSET | **FAIL** |"
    fail=$((fail + 1))
  fi
done

for var in "${EXPECTED_UNSET[@]}"; do
  actual="UNSET"
  [[ -n "${env_vars[$var]+x}" ]] && actual="SET"
  if [[ "$actual" == "UNSET" ]]; then
    echo "| $var | UNSET | UNSET | OK |"
    unset_count=$((unset_count + 1))
  else
    echo "| $var | UNSET | SET | **UNEXPECTED** |"
    fail=$((fail + 1))
  fi
done

echo ""
echo "SET count: $set_count / ${#EXPECTED_SET[@]}"
echo "UNSET count: $unset_count / ${#EXPECTED_UNSET[@]}"
echo "Failures: $fail"

if [[ $fail -eq 0 ]]; then
  echo "AUDIT_RESULT=PASS"
else
  echo "AUDIT_RESULT=FAIL"
  exit 1
fi
