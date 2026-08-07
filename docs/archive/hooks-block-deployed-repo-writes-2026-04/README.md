# HISTÓRICO — hook `block-deployed-repo-writes.sh` (2026-04)

> **Estado:** SUPERSEDED / ARCHIVO — no runtime canónico.
> **Fuente:** `origin/rick/test-github-mvp-smoke` @ `9d983463`
> **Blob:** `7d18d8c1ae82cb79e3b6f383001450609b8a69ac` (byte-idéntico al tip; verificado con `git hash-object`)
> **Pack:** PKG-UAS-P1-2-ORPHAN58-CHERRY4-ARCHIVE-KILL · GO David 2026-08-07 (opción d: archive + KILL)

## Por qué no vive en `.claude/hooks/`

`main` gitignorea explícitamente ese path (`.gitignore:78`) como superficie **VPS local-only**:
el hook hardcodea rutas de clones en la VPS (`/home/rick/umbral-agent-stack` vs
`-main-clean`) y “difiere por entorno”. Forzar `git add -f` contradiría esa política.

Este archive conserva el texto para trazabilidad sin cablear `PreToolUse` ni tocar
`.claude/settings.json`.

## Qué hace (resumen)

Hook bash `PreToolUse`: parsea JSON stdin; para `Write/Edit/MultiEdit` bloquea paths fuera
de `.claude/` y `.github/copilot-instructions.md`; para `Bash` bloquea comandos que parecen
escritura sobre el clone deployado (heurística de path VPS).

## Cómo reutilizarlo hoy (si hace falta)

1. Copiar el `.sh` **solo en la VPS** al path local ignorado `.claude/hooks/…`.
2. Revisar/actualizar rutas hardcodeadas a la topología actual de clones.
3. Wirearlo en `.claude/settings.json` local de esa máquina (también gitignored) — **GO aparte**.

No forma parte del contrato compartido del repo.
