#!/usr/bin/env bash
# worker/sandbox/refresh-copilot-cli.sh — idempotent build of
# umbral-sandbox-copilot-cli.
#
# This script is the F2 build entrypoint. It deliberately:
#   - does NOT push to any registry
#   - does NOT install anything on the host
#   - does NOT pull network resources beyond the node:22 base + npm
#     install of @github/copilot pinned in the Dockerfile
#   - does NOT touch the running worker / dispatcher / gateway
#   - does NOT run the smoke test (use run-copilot-cli-smoke.sh for that)
#
# Usage:
#   bash worker/sandbox/refresh-copilot-cli.sh            # build if missing
#   bash worker/sandbox/refresh-copilot-cli.sh --force    # always rebuild
#   bash worker/sandbox/refresh-copilot-cli.sh --print    # print resolved tag

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile.copilot-cli"
SMOKE_SH="${SCRIPT_DIR}/copilot-cli-smoke"
WRAPPER_SH="${SCRIPT_DIR}/copilot-cli-wrapper"

IMAGE_NAME="umbral-sandbox-copilot-cli"

if [[ ! -f "${DOCKERFILE}" ]]; then
    echo "refresh-copilot-cli.sh: Dockerfile.copilot-cli not found" >&2
    exit 2
fi
if [[ ! -f "${SMOKE_SH}" || ! -f "${WRAPPER_SH}" ]]; then
    echo "refresh-copilot-cli.sh: smoke or wrapper script missing" >&2
    exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "refresh-copilot-cli.sh: docker not installed or not in PATH" >&2
    exit 127
fi

# Deterministic tag = first 12 chars of sha256 over Dockerfile + smoke
# + wrapper. Any change in any of those three triggers a rebuild.
TAG="$(cat "${DOCKERFILE}" "${SMOKE_SH}" "${WRAPPER_SH}" | sha256sum | awk '{ print substr($1,1,12) }')"
FULL_REF="${IMAGE_NAME}:${TAG}"

mode="build_if_missing"
for arg in "$@"; do
    case "${arg}" in
        --force) mode="force" ;;
        --print) mode="print" ;;
        --help|-h)
            sed -n '1,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *)
            echo "refresh-copilot-cli.sh: unknown argument '${arg}'" >&2
            exit 64 ;;
    esac
done

if [[ "${mode}" == "print" ]]; then
    echo "${FULL_REF}"; exit 0
fi

if [[ "${mode}" == "build_if_missing" ]] \
   && docker image inspect "${FULL_REF}" >/dev/null 2>&1; then
    echo "refresh-copilot-cli.sh: ${FULL_REF} already present"
    exit 0
fi

echo "refresh-copilot-cli.sh: building ${FULL_REF}"
BUILD_CTX="$(mktemp -d -t umbral-sbx-copilot.XXXXXX)"
trap 'rm -rf "${BUILD_CTX}"' EXIT
cp "${DOCKERFILE}"  "${BUILD_CTX}/Dockerfile"
cp "${SMOKE_SH}"    "${BUILD_CTX}/copilot-cli-smoke"
cp "${WRAPPER_SH}"  "${BUILD_CTX}/copilot-cli-wrapper"

docker build \
    --tag "${FULL_REF}" \
    --file "${BUILD_CTX}/Dockerfile" \
    "${BUILD_CTX}"

echo "refresh-copilot-cli.sh: built ${FULL_REF}"
echo "TAG=${TAG}"
