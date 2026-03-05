# Prompts para Codex (081) y GitHub Copilot (082)

Cada agente trabaja **en su propia rama**. Copiar y pegar el bloque correspondiente.

---

## Para Codex — Tarea 081

```
Tarea 081: capitalizar trabajo en ramas. Sigue EXACTAMENTE .agents/tasks/2026-03-05-081-r16-codex-capitalizar-ramas.md.

IMPORTANTE: Trabaja SOLO en la rama codex/081-capitalizar-ramas. Crea la rama desde main actualizado (git checkout main && git pull && git checkout -b codex/081-capitalizar-ramas).

Haz solo:
1. Listar ramas remotas con commits no en main; anotar rama y resumen.
2. Crear docs/informe-ramas-pendientes.md con tabla: rama | PR | resumen 1 línea | recomendación.
3. Recuperar 1–2 docs seguros (solo docs, sin código) por cherry-pick o copia a tu rama.
4. Abrir PR desde codex/081-capitalizar-ramas a main.

No refactorices, no toques tests ni dependencias. Solo inventario + recuperación de documentos.
```

---

## Para GitHub Copilot — Tarea 082

```
Tarea 082: capitalizar PRs cerrados. Sigue EXACTAMENTE .agents/tasks/2026-03-05-082-r16-copilot-capitalizar-cerrados.md.

IMPORTANTE: Trabaja SOLO en la rama copilot/082-capitalizar-cerrados. Crea la rama desde main actualizado (git checkout main && git pull && git checkout -b copilot/082-capitalizar-cerrados).

Haz solo:
1. Listar PRs cerrados #1, #72, #74–#79, #81–#83: número, título, rama, contenido en 1 línea.
2. Crear docs/branches-cerrados-inventario.md con tabla: PR | rama | contenido | ¿recuperar?.
3. Actualizar .agents/board.md (079 y 080 completadas, 081 y 082 en curso/pendiente).
4. Abrir PR desde copilot/082-capitalizar-cerrados a main (solo docs + board).

No cierres más PRs, no toques código de aplicación. Solo inventario + board.
```
