# 02 - Permissions By Surface

> Politica V1 de permisos por superficie. El objetivo es reducir el riesgo de tocar la fuente canonica equivocada.

## 1. Niveles de operacion

| Nivel | Significado |
| --- | --- |
| `comment` | solo deja comentario o nota de revision; no cambia propiedades canonicas |
| `propose` | crea propuesta, candidato o sugerencia fuera del canon final; no muta la fila canonica |
| `edit` | crea o actualiza una fila canonica o una seccion reservada; siempre bajo las reglas de capitalizacion |

## 2. Regla general

- Toda superficie compartida debe declarar explicitamente si permite `comment`, `propose` o `edit`.
- Si una superficie no esta listada en esta politica, el modo por defecto es `comment`.
- `edit` no significa libertad total; significa edicion acotada, target verificado y trazabilidad.

## 3. Superficies donde Rick puede editar libremente

Rick solo puede editar libremente estas superficies o artefactos:

1. `raw` o inbox exclusivo de captura.
2. `sesion capitalizable` mientras este en staging.
3. `Bandeja Puente` o inbox operativo exclusivo.
4. artefactos propios en `Entregables Rick` o equivalente.
5. bloques o filas de dashboard reservados para metricas runtime.

Fuera de esas superficies, Rick opera con `comment` o `propose`, salvo target verificado y regla explicita.

## 4. Matriz por superficie

| Superficie | Protegida | Rick | Notion AI | Cursor live | Regla |
| --- | --- | --- | --- | --- | --- |
| `<RAW_SESSIONS_DB_NAME>` | No | `edit` | `propose` | `edit` | append-only; no se corrige historia salvo error tecnico evidente |
| `<CAPITALIZABLE_SESSIONS_DB_NAME>` | No | `edit` | `edit` | `edit` | staging oficial V1; aqui vive la interpretacion |
| `<BRIDGE_DB_NAME>` | No | `edit` | `propose` | `edit` | inbox operativo y handoff; no reemplaza canon final |
| `<DELIVERABLES_DB_NAME>` | Parcial | `edit` en artefactos propios, `propose` en el resto | `propose` | `edit` | outputs revisables de Rick pueden editarse; entregables humanos ajenos no |
| `<HUMAN_TASKS_DB_NAME>` | Compartida | `edit` con target verificado o tarea runtime-propia | `propose` | `edit` | no crear tareas si falta contexto o target |
| `<CRM_CLIENTS_OPPORTUNITIES_DB_NAME>` | Si | `edit` solo con target verificado; si no, `propose` | `propose` | `edit` | CRM protegido; nada de updates por inferencia vaga |
| `<PROJECTS_DB_NAME>` | Si | `edit` solo con target verificado; si no, `propose` | `propose` | `edit` | proyectos compartidos y sensibles exigen mayor cuidado |
| `<PROGRAMS_COURSES_DB_NAME>` | Si | `propose` por defecto; `edit` solo con target verificado | `propose` | `edit` | no crear programas o cursos por deduccion |
| `<RESOURCES_DB_NAME>` | Parcial | `propose` por defecto; `edit` en registros runtime-propios | `propose` | `edit` | V1 liviano; evitar sobre-structurar o reescribir |
| `<RESEARCH_DB_NAME>` | Parcial | `propose` por defecto; `edit` en registros runtime-propios | `propose` | `edit` | evidencia primero, taxonomia minima |
| `Mi Perfil` | Si | `comment` | `comment` | `edit` solo por instruccion humana explicita | nunca auto-editar perfil personal |
| `OpenClaw` | Si | `comment` | `comment` | `edit` solo para setup de vistas o bloques reservados | hub protegido; no deposito de contenido |
| `Referencias` | Si | `propose` | `propose` | `edit` | no sobreescribir notas canonicas sin confirmacion |
| `Docencia y Contenido` | Si | `propose` | `propose` | `edit` | contenido humano protegido; runtime no reescribe copy canonica |
| `Dashboards` | Si | `edit` solo en bloques reservados de runtime; si no, `comment` | `comment` | `edit` | layout y narrativa del dashboard quedan protegidos |
| `CRM / clientes sensibles` | Si | `comment` o `propose`; `edit` solo con target verificado y campo explicito | `propose` | `edit` | prioridad alta de proteccion |
| `Proyectos sensibles` | Si | `comment` | `comment` | `edit` solo por encargo humano explicito | nunca auto-mutar si existe duda |

## 5. Reglas especificas para superficies protegidas minimas

### 5.1 Mi Perfil

- No se crean ni se reescriben atributos personales automaticamente.
- Si el runtime detecta informacion util, deja comentario o propuesta.

### 5.2 OpenClaw

- `OpenClaw` es hub operativo, no deposito de paginas sueltas.
- El runtime solo puede tocar bloques o bases explicitamente reservados para el sistema.

### 5.3 Referencias

- La regla por defecto es `propose`.
- Si hay duda entre actualizar una referencia existente o crear una nueva, se propone y no se edita.

### 5.4 Docencia y Contenido

- El runtime puede sugerir estructura, backlog o nuevos artefactos.
- El contenido canonico de clases, guiones, newsletters o posts se preserva para revision humana.

### 5.5 Dashboards

- Solo las metricas, embeds o bloques reservados al runtime admiten `edit`.
- El layout general y el copy editorial del dashboard se consideran protegidos.

### 5.6 CRM y proyectos sensibles

- Requieren target verificado y payload explicito.
- Si no hay target verificado, el modo correcto es comentario o propuesta.

## 6. Regla de excepcion

- Si David o Cursor dejan una instruccion explicita por superficie y por campo, esa instruccion prevalece.
- La excepcion debe quedar trazada en comentario, ticket o sesion capitalizable.
