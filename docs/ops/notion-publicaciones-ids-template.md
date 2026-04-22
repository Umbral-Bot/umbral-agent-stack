# Notion Publicaciones — IDs & Location Registry

> **ADVERTENCIA**: No pegar `NOTION_API_KEY`, tokens, credenciales, ni secretos en este archivo. Este archivo es solo para IDs de recursos Notion (pages y databases), que no son secretos.

---

## Hub principal — Sistema Editorial Rick

| Recurso | ID | URL | Notas |
|---------|----|-----|-------|
| Sistemas y Automatizaciones (parent) | `d9f44c45f20848d1a7eb330a9884afb3` | | Página raíz del workspace |
| **Sistema Editorial Rick** (hub) | `5894ba351e2749729077ca971fd9f52a` | [link](https://www.notion.so/Sistema-Editorial-Rick-5894ba351e2749729077ca971fd9f52a) | Hub operativo/documental principal |
| Sistema Editorial Rick (OpenClaw) | `31e5f443fb5c8180bec7cbcda641b3b7` | [link](https://www.notion.so/Sistema-Editorial-Rick-31e5f443fb5c8180bec7cbcda641b3b7) | Registro/proyecto técnico bajo OpenClaw |

## Ubicación en Notion

```
Sistemas y Automatizaciones
├── Sistema Editorial Rick          ← hub principal (5894ba35...)
│   ├── (futuro) DB Publicaciones
│   ├── (futuro) Perfil editorial David
│   └── (futuro) Flujo editorial Rick
└── OpenClaw
    └── Proyectos técnicos - Rick
        └── Sistema Editorial Rick  ← proyecto técnico (31e5f443...)
```

## Decisión de gobernanza

- El hub operativo/documental principal vive como hija directa de "Sistemas y Automatizaciones".
- La página bajo OpenClaw se conserva como registro/proyecto técnico relacionado.
- No se mueve ni borra la página de OpenClaw.

## Bases de datos

| Recurso | ID | Estado | Notas |
|---------|----|--------|-------|
| DB `Publicaciones` | _(pendiente)_ | No creada | Crear manualmente siguiendo el runbook |
| DB `Referentes` | _(completar o N/A)_ | | |
| DB/página `Fuentes confiables` | _(completar o N/A)_ | | |

## Páginas internas

| Recurso | ID | Estado |
|---------|----|--------|
| Perfil editorial David | _(pendiente)_ | No creada |
| Flujo editorial Rick | _(pendiente)_ | No creada |

## Último resultado del auditor

```
_(pegar salida de scripts/audit_notion_publicaciones.py aquí cuando se ejecute)_
```

## Notas

- Hub creado 2026-04-22.
- DB Publicaciones no creada todavía.
- Rick no participa todavía.
