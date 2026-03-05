# Análisis: impacto de muchas ramas en R16

**Fecha:** 2026-03-05  
**Objetivo:** Ser sincero sobre si se perdió esfuerzo, se duplicó trabajo o el resultado neto fue positivo.

---

## Qué pasó

- Varios agentes (Cursor Agent Cloud, Codex, Copilot) trabajaron en paralelo en tareas 071–080.
- Se abrieron muchos PRs: integración (74, 75, 77, 80, 82), CI (73, 79), docs (72, 76, 78, 81), limpieza (84).
- **Solo se mergeó a main:** #80 (integración 69+70+71+73), #69, #70, #71, #73 (vía #80). Resultado: **main estable**, pytest 847 passed, CI en verde.
- **Se cerraron sin mergear:** #81, #78, #79, #72, #76, #83, #82, #77, #75, #74, #1. Copilot los cerró como redundantes/stale/WIP.

---

## ¿Se perdió esfuerzo o información?

**Sí, en parte.** El trabajo que está **solo en ramas** (no en main) sigue disponible en el repo, pero “escondido”:

| PR cerrado | Contenido probable en rama | ¿En main? |
|------------|----------------------------|-----------|
| #81 | Browser Automation VM — plan + skill OpenClaw | No |
| #78 | Research Power BI (.pbix, .pbip, .pbir) | No |
| #72 | Bitácora enriquecida, CONTRIBUTING, board | Parcial (si #84 mergea, algo puede entrar) |
| #76 | Board estado R8–R15 | No |
| #79 | CI + README tests | Parcial (CI ya está vía #73/#80) |
| #82, #77, #75, #74 | Integración redundante | No (obsoletos; #80 ganó) |
| #83 | Cierre y documentación | Parcial |
| #1 | WIP repo inicial | Obsoleto |

**Conclusión:** No se “borró” nada (las ramas siguen), pero **documentos y mejoras útiles** (browser automation, Power BI, Bitácora, board actualizado) **no están en main** salvo que se recuperen por cherry-pick o merge selectivo.

---

## ¿Se duplicó trabajo?

**Sí.** Varios PRs hicieron cosas parecidas:

- **Integración:** 74, 75, 77, 80, 82 — todos “merge 69+70+71(+73) y dejar pytest verde”. Se hizo el mismo trabajo varias veces; solo #80 se mergeó.
- **CI / README:** 73 (mergeado vía #80) y 79 (cerrado) — solapamiento.
- **Board/docs:** 72, 76, 83 — actualizaciones de board y documentación repartidas.

Eso implica: más revisiones, más conflictos potenciales, más ruido en la lista de PRs. El resultado final (main verde + CI) es uno solo; el camino fue redundante.

---

## ¿Fue para mejor?

**En resultado final, sí.** Main quedó:

- Con pytest en verde (847 passed).
- Con CI (workflow pytest en push/PR).
- Con dependencias y fixes (69, 70, 71) integrados.

El “daño” es sobre todo **organizativo**: trabajo valioso repartido en ramas cerradas y trabajo duplicado. No se perdió el repo ni la estabilidad; se puede **capitalizar** recuperando lo bueno de esas ramas (docs, skills, board) en un solo lugar.

---

## Recomendación

1. **Inventariar** ramas con contenido único (por PR cerrado y por rama remota).
2. **Decidir** por cada una: merge a main, cherry-pick a una rama “doc” o “recuperación”, o dejar como referencia.
3. **Documentar** en el board o en un doc (`docs/branches-cerrados-inventario.md`) qué hay en cada rama para no olvidar.
4. De aquí en adelante: **una rama por agente** (p. ej. `codex/081-...`, `copilot/082-...`) y tareas más acotadas para reducir duplicación.
