#!/usr/bin/env bash
# Load ~/.config/openclaw/env safely, preserving values with spaces.

load_openclaw_env() {
    local env_file="${1:-$HOME/.config/openclaw/env}"
    local raw_line=""
    local line=""
    local key=""
    local value=""

    if [ ! -f "$env_file" ]; then
        return 0
    fi

    while IFS= read -r raw_line || [ -n "$raw_line" ]; do
        line="${raw_line%$'\r'}"
        line="${line#"${line%%[![:space:]]*}"}"

        if [ -z "$line" ] || [[ "$line" == \#* ]]; then
            continue
        fi

        if [[ "$line" == export\ * ]]; then
            line="${line#export }"
        fi

        if [[ "$line" != *=* ]]; then
            continue
        fi

        key="${line%%=*}"
        value="${line#*=}"

        key="${key%"${key##*[![:space:]]}"}"
        value="${value#"${value%%[![:space:]]*}"}"

        if [[ "$value" == \"*\" && "$value" == *\" ]]; then
            value="${value:1:${#value}-2}"
        elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
            value="${value:1:${#value}-2}"
        fi

        export "$key=$value"
    done < "$env_file"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    load_openclaw_env "$@"
fi
