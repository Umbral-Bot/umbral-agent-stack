# Task R16 — Búsqueda profunda: librerías y skills para crear dashboards Power BI (.pbix, .pbit, .pbip, .pbir)

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Cursor Agent Cloud  
**Branch:** `feat/research-powerbi-librerias-formatos`

---

## Contexto

Power BI usa varios formatos de archivo:

- **.pbix** — Archivo estándar (informe + modelo + datos embebidos)
- **.pbit** — Plantilla (informe sin datos)
- **.pbip** — Proyecto Power BI (formato para control de código)
- **.pbir** — Informe dentro de un proyecto (.pbip)

Se necesita saber si existen **librerías** (Python, .NET, JS, etc.) y/o **skills** (OpenClaw, documentación para agentes) que permitan **crear o generar** dashboards/informes de Power BI en alguno de estos formatos de forma programática.

---

## Objetivo

Realizar una **búsqueda profunda en la web** (repositorios, PyPI, npm, documentación oficial, blogs, GitHub) para:

1. Identificar librerías que permitan crear o modificar archivos .pbix, .pbit, .pbip o .pbir (o exportar a ellos).
2. Identificar skills, plantillas o guías para agentes (OpenClaw, Cursor, etc.) sobre generación de dashboards Power BI.
3. Documentar hallazgos en un informe claro (tabla de opciones, limitaciones, enlaces).

Todo en **español**. El resultado debe servir para decidir si el stack puede automatizar la generación de informes Power BI y en qué formato.

---

## Formatos a considerar

| Formato | Descripción |
|--------|-------------|
| .pbix | Archivo completo Power BI Desktop (informe + modelo + datos) |
| .pbit | Plantilla (informe + modelo, sin datos; el usuario conecta datos) |
| .pbip | Proyecto (carpeta con definiciones en formato abierto; control de versiones) |
| .pbir | Definición de informe dentro de un proyecto .pbip |

---

## Tareas requeridas

1. **Búsqueda web** — Consultar:
   - PyPI, npm, NuGet: "power bi", "pbix", "pbip", "pbir", "powerbi report", "create power bi programmatically"
   - GitHub: repos que manipulen .pbix / .pbip / .pbir
   - Documentación Microsoft: Power BI REST API, Embedded, deployment pipelines, formatos de archivo
   - Blogs y artículos: generación de informes Power BI con código

2. **Criterios** — Para cada hallazgo anotar:
   - Nombre y enlace
   - Lenguaje/entorno (Python, C#, Node, etc.)
   - Qué formatos soporta (.pbix, .pbit, .pbip, .pbir)
   - Si crea desde cero, modifica existentes o solo publica/administra
   - Limitaciones (solo lectura, solo REST API, requiere Power BI Desktop, etc.)

3. **Skills** — Buscar si existe documentación o skills (p. ej. OpenClaw SKILL.md) que enseñen a un agente a generar dashboards Power BI; si no, indicar qué habría que documentar.

4. **Entregable** — Crear en el repo un documento: `docs/63-powerbi-librerias-formatos-pbix-pbip.md` con:
   - Resumen ejecutivo (1 párrafo)
   - Tabla de librerías/herramientas encontradas (nombre, formato, lenguaje, enlace, limitaciones)
   - Sección de skills/agentes (hallazgos o recomendación)
   - Conclusión: viabilidad de generar dashboards en el stack Umbral y formato recomendado
   - Referencias (URLs consultadas)

5. **Idioma** — Todo el informe en **español**.

---

## Criterios de éxito

- [ ] Búsqueda realizada (múltiples fuentes)
- [ ] Documento `docs/63-powerbi-librerias-formatos-pbix-pbip.md` creado con tabla y conclusiones
- [ ] Referencias y enlaces incluidos
- [ ] PR abierto a `main`
