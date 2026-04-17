#!/usr/bin/env bash
# worker/sandbox/refresh.sh — idempotent sandbox image builder.
#
# Computes a deterministic tag from the sha256 of pyproject.toml (the
# only source of dep definitions consumed by the Dockerfile) and
# builds umbral-sandbox-pytest:<tag> only if it doesn't already exist
# locally.
#
# Usage:
#   bash worker/sandbox/refresh.sh            # build if missing
#   bash worker/sandbox/refresh.sh --force    # always rebuild
#   bash worker/sandbox/refresh.sh --print    # print the resolved tag and exit 0
#
# This script deliberately does NOT:
#   - push to any registry
#   - pull anything from a remote registry beyond the python:3.11-slim base
#   - touch the running worker service
#   - run any tests

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." &> /dev/null && pwd)"
PYPROJECT="${REPO_ROOT}/pyproject.toml"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile"

IMAGE_NAME="umbral-sandbox-pytest"

if [[ ! -f "${PYPROJECT}" ]]; then
    echo "refresh.sh: pyproject.toml not found at ${PYPROJECT}" >&2
    exit 2
fi
if [[ ! -f "${DOCKERFILE}" ]]; then
    echo "refresh.sh: Dockerfile not found at ${DOCKERFILE}" >&2
    exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "refresh.sh: docker not installed or not in PATH" >&2
    exit 127
fi

# Deterministic tag: first 12 chars of sha256(pyproject.toml). Anyone
# can verify by running `sha256sum pyproject.toml | cut -c1-12`.
TAG="$(sha256sum "${PYPROJECT}" | awk '{ print substr($1, 1, 12) }')"
FULL_REF="${IMAGE_NAME}:${TAG}"

mode="build_if_missing"
for arg in "$@"; do
    case "${arg}" in
        --force) mode="force" ;;
        --print) mode="print" ;;
        --help|-h)
            sed -n '1,20p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *)
            echo "refresh.sh: unknown argument '${arg}'" >&2
            exit 64
            ;;
    esac
done

if [[ "${mode}" == "print" ]]; then
    echo "${FULL_REF}"
    exit 0
fi

if [[ "${mode}" == "build_if_missing" ]] \
   && docker image inspect "${FULL_REF}" >/dev/null 2>&1; then
    echo "refresh.sh: ${FULL_REF} already present — nothing to do"
    exit 0
fi

echo "refresh.sh: building ${FULL_REF}"
# Build context is only the sandbox directory + the pyproject.toml we
# stage into it. We copy the pyproject into the context dir via a
# secondary bind during the build to keep the context minimal and
# avoid accidentally including the whole repo.
BUILD_CTX="$(mktemp -d -t umbral-sbx-build.XXXXXX)"
trap 'rm -rf "${BUILD_CTX}"' EXIT
cp "${DOCKERFILE}" "${BUILD_CTX}/Dockerfile"
cp "${PYPROJECT}"  "${BUILD_CTX}/pyproject.toml"

docker build \
    --tag "${FULL_REF}" \
    --file "${BUILD_CTX}/Dockerfile" \
    "${BUILD_CTX}"

echo "refresh.sh: built ${FULL_REF}"
