# 29 — Estructura de Repos y Proyectos

## Organización GitHub: Umbral-Bot

| Repo | Tipo | Uso |
|------|------|-----|
| **umbral-agent-stack** | Infraestructura | Worker, Dispatcher, OpenClaw config, scripts, docs operativos, protocolo inter-agentes |
| **umbral-marketing** | Equipo | SEO, Social Media, Copywriting — entregas y contenido del equipo Marketing |
| **umbral-advisory** | Equipo | Financiero, Lifestyle — entregas del equipo Asesoría Personal |
| **umbral-lab** | Laboratorio | Experimentos: multiagent MVP, Telegram audio, Granola sync, PAD/RPA |

Todos los repos son **privados**.

## Criterio de separación

- **Infraestructura** (`umbral-agent-stack`): código del sistema, configuración, runbooks, auditorías, protocolo `.agents/`. No mezclar con entregas de negocio.
- **Equipos** (`umbral-marketing`, `umbral-advisory`): un repo por equipo. Rick abre PRs; David (o Cursor) revisa y mergea.
- **Lab** (`umbral-lab`): experimentos sin impacto productivo. Si un experimento madura, se mueve a su propio repo o se integra al stack.

## Archivos pesados

Git no maneja bien archivos grandes (audio, video, exports). Usar **Google Drive** (`G:\Mi unidad\Rick-David\`) para eso. La VM tiene acceso directo a esa carpeta.

## Tracking

- **Notion** (Dashboard Rick + Kanban): vista gerencial, estado de tareas, progreso por equipo.
- **GitHub** (issues + PRs): vista técnica por repo.
- Opcionalmente: un GitHub Project que cruce issues/PRs de todos los repos (cuando haya volumen).
