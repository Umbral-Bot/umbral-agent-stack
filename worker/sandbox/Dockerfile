# Umbral pytest sandbox image — Phase 2 slice 7b-infra.
#
# This image is used as the execution environment for the future
# `pytest_target` validation mode. The repo is NOT baked into the
# image; it is bind-mounted read-only from an ephemeral workspace at
# runtime. Only Python + the project's declared test dependencies are
# installed here so the layer is stable across code changes.
#
# Tag convention (see ./refresh.sh):
#   umbral-sandbox-pytest:<sha256(pyproject.toml)[:12]>
#
# Runtime invocation (enforced by the future runner — do NOT rely on
# it happening by default):
#   docker run --rm \
#     --network=none --read-only \
#     --tmpfs /tmp:size=64m,mode=1777,exec,nosuid,nodev \
#     --tmpfs /work/.pytest_cache:size=16m \
#     --tmpfs /work/__pycache__:size=16m \
#     --memory=512m --memory-swap=512m --cpus=1.0 \
#     --pids-limit=256 --cap-drop=ALL \
#     --security-opt=no-new-privileges --security-opt=seccomp=default \
#     --user 10001:10001 --ipc=none \
#     --mount type=bind,source=<ws>,target=/work,readonly \
#     --workdir /work \
#     --env PYTHONDONTWRITEBYTECODE=1 \
#     --env PYTHONUNBUFFERED=1 \
#     --env WORKER_TOKEN=sandbox-stub \
#     --env UMBRAL_DISABLE_CLAUDE=1 \
#     umbral-sandbox-pytest:<tag> \
#     python -m pytest <validation_target> -x -q --no-header \
#       --disable-warnings -p no:cacheprovider --rootdir=/work

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal build deps for wheels that may need compilation (fpdf2,
# cffi/weasyprint pulls etc.). Kept intentionally narrow; if a test
# in the allowlist needs more, we extend this explicitly.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml /build/pyproject.toml

# Install exactly the project's declared test extra plus the runtime
# dependencies that the tests transitively import (pytest discovers
# tests/conftest.py which imports worker.app which imports the full
# worker.tasks.* surface, so the runtime deps must be present).
#
# We deliberately do NOT `pip install -e .` the project itself here —
# the source tree is bind-mounted at /work at runtime, and making it
# editable inside the image would require re-baking on every commit.
RUN pip install --no-cache-dir \
        "pytest>=7.0.0" \
        "fakeredis>=2.0.0" \
        "fastapi>=0.104.0,<1.0.0" \
        "uvicorn[standard]>=0.24.0,<1.0.0" \
        "pydantic>=2.0.0,<3.0.0" \
        "httpx>=0.25.0,<1.0.0" \
        "pyyaml>=6.0.0,<7.0.0" \
        "google-auth>=2.0.0,<3.0.0" \
        "langfuse>=2.0.0,<3.0.0" \
        "redis>=5.0.0,<6.0.0" \
        "mcp[cli]>=1.0.0,<2.0.0" \
        "github-copilot-sdk>=0.2.0,<1.0.0" \
        "azure-search-documents>=11.4.0,<12.0.0" \
        "azure-identity>=1.15.0,<2.0.0" \
        "python-docx>=1.1.0" \
        "docxtpl>=0.16.0" \
        "fpdf2>=2.7.0" \
        "python-pptx>=0.6.23" \
        "openpyxl>=3.1.0" \
        "requests>=2.28.0,<3.0.0"

# Non-root runtime user. High uid avoids collisions with host uids
# commonly used in dev environments. The workspace is bind-mounted
# read-only at runtime, so this user only needs read access there.
RUN useradd -u 10001 -m -s /usr/sbin/nologin runner
USER 10001:10001

WORKDIR /work

# Default command intentionally left inert so accidental `docker run`
# without argv fails fast rather than silently exposing a shell.
CMD ["python", "-c", "import sys; sys.stderr.write('umbral-sandbox-pytest: provide a pytest argv\\n'); sys.exit(2)"]
