---
name: rick-skill-creator
description: crear o adaptar skills para rick y el stack openclaw de forma repo-first y openclaw-first. usar cuando david pida a rick crear una skill nueva, mejorar una skill existente, decidir si conviene extender o fusionar una skill, o generar una skill cargable para el arbol openclaw/workspace-templates/skills sin inventar estructura, tooling ni nombres ajenos al repo.
metadata:
  openclaw:
    emoji: "🛠"
    requires:
      env: []
---

# Rick Skill Creator

## Objetivo

Permitir que Rick cree skills utiles para este stack sin inventar formatos, rutas, tooling ni capacidades.

La prioridad es:
- leer el repo primero;
- entender si ya existe una skill cercana;
- decidir si conviene editar, extender, fusionar o crear una nueva;
- dejar la skill lista para el arbol OpenClaw.

## Regla maestra

No crear una skill "bonita". Crear una skill **usable** por Rick y por el stack real.

## Cuándo usar esta skill

Usarla cuando David pida:
- "crea una skill"
- "mejora esta skill"
- "adapta esto a OpenClaw"
- "haz una skill reusable"
- "conviene skill nueva o editar una existente?"

## Flujo obligatorio

1. leer el repo y la zona funcional relacionada
2. buscar skills ya existentes que se superpongan
3. decidir:
   - editar
   - extender
   - fusionar
   - crear skill nueva
4. definir outputs concretos de la skill
5. definir limites y anti-patrones
6. escribir `SKILL.md`
7. agregar `references/` solo si realmente reduce ruido en el cuerpo principal
8. validar que el nombre, descripcion y alcance disparen bien

## Regla repo-first

Antes de escribir una skill:
- leer los archivos del dominio afectado
- leer 1 o 2 skills parecidas
- inferir naming y estructura desde el repo

No inventar:
- rutas
- nombres de tools
- procesos
- agentes
- entregables

si el repo no los soporta.

Consultar `references/repo-first-design.md`.

## Regla OpenClaw-first

La skill final debe encajar en:

- `openclaw/workspace-templates/skills/<nombre>/SKILL.md`

Y, si hace falta:

- `references/`

No arrastrar estructuras pensadas para otros entornos salvo que David lo pida.

Consultar `references/openclaw-rick-guidelines.md`.

## Decisión: editar o crear

Antes de abrir carpeta nueva, responder estas preguntas:

1. Ya existe una skill que cubra 60% o más del caso?
2. El problema es de alcance, no de identidad?
3. La skill nueva solo duplicaría guardrails ya presentes?

Si la respuesta es sí, preferir editar o extender.

Consultar `references/skill-decision-framework.md`.

## Anatomía mínima de una buena skill

Una skill buena deja claro:
- objetivo
- cuándo usarla
- flujo obligatorio
- herramientas o límites
- salida esperada
- guardrails

No llenar con teoría general.

## Referencias

- `references/repo-first-design.md`
- `references/skill-decision-framework.md`
- `references/openclaw-rick-guidelines.md`
