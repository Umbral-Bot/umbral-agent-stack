#!/usr/bin/env bash
# worker/sandbox/run-copilot-cli-smoke.sh — F2 hardened smoke runner.
#
# Runs the smoke test inside the umbral-sandbox-copilot-cli image with
# the FULL set of hardening flags. NO real Copilot token is passed.
# NO network is allowed. The host is not modified.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." &> /dev/null && pwd)"

IMAGE_TAG="$(bash "${SCRIPT_DIR}/refresh-copilot-cli.sh" --print)"

echo "run-copilot-cli-smoke.sh: image=${IMAGE_TAG}"
echo "run-copilot-cli-smoke.sh: repo_root=${REPO_ROOT}"
echo "run-copilot-cli-smoke.sh: NO token will be injected. NO network."

docker run --rm \
    --network=none \
    --read-only \
    --tmpfs /tmp:size=64m,mode=1777,exec,nosuid,nodev \
    --tmpfs /scratch:size=64m,mode=1777,nosuid,nodev \
    --tmpfs /home/runner/.cache:size=32m \
    --memory=1g --memory-swap=1g --cpus=1.0 \
    --pids-limit=256 \
    --cap-drop=ALL \
    --security-opt no-new-privileges \
    --user 10001:10001 \
    --ipc=none \
    --mount "type=bind,source=${REPO_ROOT},target=/work,readonly" \
    --workdir /work \
    "${IMAGE_TAG}" \
    /usr/local/bin/copilot-cli-smoke
