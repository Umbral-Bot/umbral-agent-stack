# Próxima candidata — Pipeline completo desde cero (CAND-004+)

> **Después** de cerrar CAND-001 como ejemplo manual.  
> **Gate CAND-001:** `CAND001_BLOG_EXAMPLE_COMPLETE` alcanzado 2026-07-02 (`docs/ops/cand-001-closeout-2026-07-02.md`).  
> **Tipo:** source-driven (con trazabilidad de publicaciones).  
> **Rick + Worker + n8n** según `production-flow-v2-2026-06-06.md`.

---

## Fases

| Fase | Qué | Owner | Output |
|------|-----|-------|--------|
| 0 | David selecciona señales en DB Referentes | David | 2–5 URLs / referentes |
| 1 | S2 ingest + S3 promote (VPS cron) | Worker | SQLite candidatos |
| 2 | S6 combine AEC + payload | rick-editorial | YAML payload repo |
| 3 | QA + benchmark | rick-qa | pass / pass_with_changes |
| 4 | S7/S4 push Notion | Operator/Rick | fila `Borrador` |
| 5 | S7.5 copy LinkedIn | stage7_5 (FROZEN) o Rick | `Copy LinkedIn` columna |
| 6 | Decision Brief §1–5 en body + **fuentes con links** | Rick | props `Fuente primaria`, tabla §3 |
| 7 | David Gate 1 | David | `aprobado_contenido` |
| 8 | Magnific UmbralBIM × 3 | Rick | `imagen_alt_*` |
| 9 | David Gate 2 + imagen | David | `Selección imagen`, `autorizar_publicacion` |
| 10 | Telegram `ok publica` | David | publish multicanal |

---

## Diferencias vs CAND-001 (ejemplo)

| Aspecto | CAND-001 ejemplo | CAND-004+ pipeline |
|---------|------------------|-------------------|
| Fuentes | Opinión, sin URLs referentes | Tabla §3 + `Fuente primaria` obligatoria |
| Copy | Manual / Rick | S7.5 + director comunicación |
| Imágenes | UmbralBIM manual | UmbralBIM tras Gate 1 (automatizar poller) |
| Blog | Rick extiende desde LinkedIn | Paquete multicanal desde master |
| Trazabilidad | Repo handoff | publication_id + trace_id + source intake doc |

---

## Rick — prompt de arranque (cuando CAND-001 esté en `CAND001_EXAMPLE_COMPLETE`)

```text
Iniciar CAND-004 pipeline completo (source-driven).

1) Leer DB Referentes vista 71d3f67e… — proponer 3 ángulos dedup-safe vs CAND-001/002/003.
2) David elige ángulo.
3) Ejecutar source intake → docs/ops/cand-004-source-intake.md con URLs exactas de publicaciones.
4) Payload + variants benchmark interno.
5) rick-qa pass antes de Notion.
6) Crear fila Publicaciones con Decision Brief + copies SOLO en columnas.
7) NO gates hasta David.

Veredicto: CAND004_READY_FOR_HUMAN_REVIEW
```

---

## Automatización pendiente (post-ejemplo)

- [ ] Poller: `aprobado_contenido` → tarea `editorial.magnific_generate`
- [ ] Worker: `Selección imagen` → copiar `Visual asset URL`
- [ ] Logo viñeta PNG overlay (asset en Drive → Worker compose)
- [ ] Diagramas blog: Mermaid en repo → PNG → opcional pasada Magnific estilo 2D limpio
