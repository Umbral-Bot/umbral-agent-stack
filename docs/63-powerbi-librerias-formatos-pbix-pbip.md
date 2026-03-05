# Librerías y herramientas para crear dashboards Power BI programáticamente

> **Fecha:** 2026-03-05  
> **Tarea:** R16 — Búsqueda profunda de librerías y formatos  
> **Autor:** Cursor Agent Cloud

---

## Resumen ejecutivo

Crear archivos Power BI de forma 100 % programática (sin abrir Power BI Desktop) es posible, aunque con matices importantes según el formato de destino. El formato binario clásico **.pbix** no tiene especificación pública y las librerías que lo manipulan trabajan sobre ingeniería inversa del ZIP interno, con resultados frágiles. El camino más viable a día de hoy es el nuevo formato abierto **PBIP/PBIR** (Power BI Project + Enhanced Report Format), basado en carpetas de archivos JSON y TMDL legibles por máquina. Microsoft ha confirmado que **PBIR será el formato por defecto en Power BI Service desde enero 2026** (ya en curso) y en Desktop desde marzo 2026, con disponibilidad general plena en Q3 2026. Esto convierte a PBIR en la apuesta estratégica para cualquier pipeline de generación automatizada.

En Python, la librería **powerbpy** permite crear dashboards completos (páginas, visuales, datos) en formato .pbip/.pbir desde código. Complementariamente, **pbir_tools**, **pbir-utils** y **pypbireport** ofrecen capacidades de edición, validación y manipulación de informes existentes. Para publicar los archivos generados en el servicio Power BI / Fabric, se pueden usar las **Fabric REST APIs** o wrappers como **pbipy**, **SimplePBI** o el módulo PowerShell **FabricPS-PBIP**.

---

## Formatos de archivo Power BI

| Formato | Extensión | Descripción | Estado |
|---------|-----------|-------------|--------|
| **PBIX** | `.pbix` | Archivo binario (ZIP) con informe + modelo semántico + datos embebidos | Estable, vigente |
| **PBIT** | `.pbit` | Plantilla (informe + modelo, sin datos; el usuario conecta datos al abrir) | Estable, vigente |
| **PBIP** | `.pbip` | Proyecto (carpeta con definiciones en texto plano; para control de versiones) | Preview → GA Q3 2026 |
| **PBIR** | `.pbir` | Definición de informe dentro de un proyecto .pbip (JSON con esquema público) | Preview → Defecto desde ene 2026 (Service), mar 2026 (Desktop), GA Q3 2026 |

### Transición a PBIR (timeline de Microsoft)

- **Enero–febrero 2026:** PBIR es el formato por defecto en Power BI Service. Los informes existentes se convierten automáticamente al editar y guardar.
- **Marzo 2026:** PBIR por defecto en Power BI Desktop.
- **Q3 2026:** Disponibilidad general (GA). PBIR será el único formato de informe soportado; PBIR-Legacy quedará deprecado.
- El formato .pbix **no desaparece**; PBIR se almacena dentro de .pbix, por lo que la experiencia del usuario no cambia.

---

## Tabla de librerías y herramientas

### Librerías Python

| Librería | Versión | Formatos | Capacidad | Limitaciones | Enlace |
|----------|---------|----------|-----------|--------------|--------|
| **powerbpy** | 0.2.0 | .pbip / .pbir | **Crear desde cero**: dashboards, páginas, visuales (charts, cards, slicers, tablas, mapas, botones, text boxes), importar datos CSV/ADLS/TMDL | Requiere Python ≥3.10. Requiere Power BI Desktop para visualizar. Necesita activar features preview (PBIP, TMDL, PBIR). Sin soporte .pbix directo. | [PyPI](https://pypi.org/project/powerbpy/) · [Docs](https://www.russellshean.com/powerbpy/) |
| **pbir_tools** | — | .pbir | **Crear y editar** archivos PBIX en formato PBIR | Proyecto joven, documentación limitada. Licencia MIT. | [GitHub](https://github.com/david-iwdb/pbir_tools) |
| **pbir-utils** | 2.2.5 | .pbir | **Validar, optimizar y gestionar** informes PBIR: reglas personalizadas, extracción de metadata, limpieza de medidas no usadas, wireframes, sanitización | No crea desde cero; trabaja sobre informes existentes. Python ≥3.10. CLI + Web UI + API Python. MIT. | [PyPI](https://pypi.org/project/pbir-utils/) · [GitHub](https://github.com/akhilannan/pbir-utils) |
| **pypbireport** | 0.2.4 | .pbix (binario) | **Editar** informes .pbix existentes: modificar visuales, agregar bookmarks, gestionar medidas del modelo | Solo modifica existentes, no crea desde cero. Python ≥3.9. Manipula el ZIP internamente (frágil). MIT. | [PyPI](https://pypi.org/project/pypbireport/) · [GitHub](https://github.com/IsmaelMiranda11/py-powerbi-report) |
| **python-pbi** | — | .pbix | **Leer y modificar** archivos .pbix: descargar, alterar texto/formato/visuales, republicar | Solo modifica existentes. GPL-3.0. Proyecto pequeño. | [GitHub](https://github.com/JChamboredon/pbi) |
| **PowerPy** | — | .pbix | **Crear y editar** informes como código: agregar secciones, duplicar informes | Proyecto muy pequeño (4 stars). GPL-3.0. Manipulación .pbix interna. | [GitHub](https://github.com/nathangiusti/PowerPy) |
| **pbipy** | 2.9.0 | REST API | **Administrar** vía API REST: apps, dataflows, datasets, reports, workspaces | No crea archivos locales; interactúa con el servicio Power BI. Python ≥3.10. | [PyPI](https://pypi.org/project/pbipy/) · [GitHub](https://github.com/andrewvillazon/pbipy) |
| **SimplePBI** | 1.0.2 | REST API + Fabric | **Wrapper simplificado** de Power BI REST API y Fabric REST API (>80% de endpoints cubiertos) | No crea archivos locales; solo gestión vía API. | [PyPI](https://pypi.org/project/SimplePBI/) |
| **pbi-tools** (Python) | 2.3.1 | REST API | Wrapper orientado a objetos de la API REST de Power BI | Alpha. Solo REST API, no crea archivos. MIT. | [PyPI](https://pypi.org/project/pbi-tools/) |
| **semantic-link-labs** | — | .pbir (Fabric) | **Crear y modificar** informes dentro de Fabric Notebooks: `clone_report()`, `create_report_from_reportjson()`, `ReportWrapper` para PBIR | Solo funciona dentro de Microsoft Fabric Notebooks. No genera archivos locales. | [Docs](https://semantic-link-labs.readthedocs.io/) |

### Herramientas CLI / .NET / PowerShell

| Herramienta | Lenguaje | Formatos | Capacidad | Limitaciones | Enlace |
|-------------|----------|----------|-----------|--------------|--------|
| **pbi-tools CLI** | .NET (C#) | .pbix → carpeta, carpeta → .pbix/.pbit | **Extract** (descomponer .pbix en carpeta), **Compile** (generar .pbix/.pbit desde carpeta), **Deploy**, **Convert** | Desktop CLI requiere Windows + PBI Desktop. Core CLI es cross-platform pero más limitado. AGPLv3. | [pbi.tools](https://pbi.tools/) · [GitHub](https://github.com/pbi-tools/pbi-tools) |
| **Tabular Editor** | C# | TMDL / .bim / .pbix | **Crear y editar** modelos semánticos programáticamente con C# scripting y API de TOM | Tabular Editor 3 es comercial (licencia paga). Tabular Editor 2 es open source pero más limitado. Solo modelos, no visuales de informe. | [tabulareditor.com](https://tabulareditor.com/) · [Docs](https://docs.tabulareditor.com/) |
| **AMO/TOM** (.NET) | C# | Modelo semántico + TMDL | **Crear y modificar** modelos semánticos: tablas, columnas, medidas, relaciones. Serializar/deserializar TMDL. | Solo modelos semánticos, no genera la capa visual del informe. Requiere .NET. | [NuGet: Microsoft.AnalysisServices](https://www.nuget.org/packages/Microsoft.AnalysisServices/) · [Docs](https://learn.microsoft.com/en-us/analysis-services/tom/) |
| **FabricPS-PBIP** | PowerShell | .pbip → Fabric | **Desplegar** proyectos .pbip a Fabric/Power BI Service vía REST APIs | Solo despliegue (no creación). Requiere PowerShell 7.1+ y Az.Accounts. No soportado oficialmente por Microsoft. | [GitHub](https://github.com/microsoft/Analysis-Services/tree/master/pbidevmode/fabricps-pbip) |
| **PowerBIDotNet** | C# (.NET) | REST API | Wrapper .NET para la API REST de Power BI | Solo gestión vía API, no genera archivos locales. | [NuGet](https://www.nuget.org/packages/PowerBIDotNet) |

### Librerías JavaScript / Node.js

| Librería | Formatos | Capacidad | Limitaciones | Enlace |
|----------|----------|-----------|--------------|--------|
| **powerbi-report-authoring** | Embedded (iframe) | **Editar** informes embebidos en el navegador: crear/modificar páginas y visuales programáticamente | Solo funciona en contexto de Power BI Embedded (web). Requiere embed token. No genera archivos locales. | [npm](https://www.npmjs.com/package/powerbi-report-authoring) |
| **powerbi-client** | Embedded (iframe) | **Embeber** informes y dashboards Power BI en aplicaciones web | Solo embedido, no generación de archivos. | [npm](https://www.npmjs.com/package/powerbi-client) |
| **pbix** (Node.js) | .pbix (lectura) | **Leer** archivos .pbix | Solo lectura, no escritura. Proyecto pequeño. | [GitHub](https://github.com/mfeyx/pbix) |

### APIs de Microsoft (REST)

| API | Capacidad | Limitaciones | Enlace |
|-----|-----------|--------------|--------|
| **Power BI REST API** | Clonar, exportar (.pbix), publicar, rebindear informes. Gestionar datasets, workspaces, refresh. | No crea informes desde cero (solo clona o importa). Requiere Azure AD app + licencia Pro/Premium. Throttling. | [Docs](https://learn.microsoft.com/en-us/rest/api/power-bi/) |
| **Fabric REST API — Create Report** | **Crear informes** enviando definición PBIR (JSON base64). Crear modelos semánticos. | Requiere licencia Fabric. `definition.pbir` debe usar referencias `byConnection` (no rutas relativas). Preview. | [Docs](https://learn.microsoft.com/en-us/rest/api/fabric/report/items/create-report) |
| **Fabric REST API — Deploy Project** | **Desplegar** proyectos .pbip completos (modelo + informe) a un workspace Fabric | Requiere licencia Fabric + permisos de contributor. | [Docs](https://learn.microsoft.com/en-us/rest/api/fabric/articles/get-started/deploy-project) |

---

## Skills y agentes para generación de dashboards Power BI

### Estado actual

- **OpenClaw** tiene un skill de "dashboard" que genera dashboards **HTML estáticos** (no .pbix/.pbip). También tiene un skill de "usage-export" que genera CSV compatibles con Power BI para importación manual. No existe un skill dedicado a generar archivos Power BI nativos.
- **LangGraph + Power BI** es un patrón emergente documentado en blogs para orquestar generación automatizada de informes: extract → validate → analyze → narrate → publish. Utiliza las REST APIs para publicar, no genera archivos locales.
- **Microsoft Fabric con agentes IA** permite proponer modelos semánticos, definir medidas DAX y seleccionar visuales, pero requiere el ecosistema Fabric completo.

### Recomendación para el stack Umbral

No existe un skill predefinido para que un agente genere archivos Power BI nativos. Se recomienda **crear un skill propio** que documente:

1. La estructura de carpetas del formato PBIP/PBIR (esquema JSON público de Microsoft).
2. Cómo usar `powerbpy` para generar dashboards desde Python.
3. Cómo usar `pbir-utils` para validar y optimizar el resultado.
4. Cómo publicar a Fabric/Power BI Service usando `SimplePBI` o la Fabric REST API.
5. Plantillas base (templates TMDL + PBIR) que el agente pueda clonar y adaptar.

---

## Análisis comparativo: viabilidad por formato

| Formato | ¿Se puede crear desde cero? | Herramienta recomendada | Viabilidad para automatización |
|---------|----------------------------|------------------------|-------------------------------|
| **.pbix** | Parcialmente. Requiere compilar desde carpeta (pbi-tools) o manipular ZIP interno (frágil). | pbi-tools CLI (compile) | ⚠️ Media — formato binario, ingeniería inversa, propenso a errores |
| **.pbit** | Sí, vía pbi-tools compile o exportando .pbix existente | pbi-tools CLI (compile) | ⚠️ Media — mismas limitaciones que .pbix |
| **.pbip / .pbir** | **Sí, completamente.** Estructura de carpetas con JSON + TMDL. | **powerbpy** (Python), pbir_tools, Fabric REST API | ✅ **Alta** — formato abierto, esquema documentado, text-based, compatible con control de versiones |
| Publicar en servicio | Sí, via REST API | SimplePBI, pbipy, Fabric REST API, FabricPS-PBIP | ✅ Alta — APIs maduras y bien documentadas |

---

## Conclusión y recomendación

### Formato recomendado: **PBIP/PBIR**

Para el stack Umbral, el formato **PBIP/PBIR** es la opción más viable para la generación automatizada de dashboards Power BI por las siguientes razones:

1. **Formato abierto y documentado**: estructura de carpetas con archivos JSON (esquema público) y TMDL, completamente legibles y generables por código.
2. **Dirección estratégica de Microsoft**: PBIR ya es el formato por defecto en Power BI Service (enero 2026) y lo será en Desktop (marzo 2026), con GA en Q3 2026.
3. **Tooling Python maduro**: `powerbpy` permite crear dashboards completos desde cero, `pbir-utils` valida y optimiza, y `SimplePBI`/Fabric API publican al servicio.
4. **Compatible con control de versiones**: al ser archivos de texto, se integra naturalmente con Git.
5. **Compatible con agentes**: un agente puede generar los JSON/TMDL siguiendo los esquemas, sin necesidad de interfaz gráfica.

### Pipeline propuesto para Umbral

```
[Agente/Worker] → powerbpy (crear .pbip/.pbir)
              → pbir-utils (validar/optimizar)
              → SimplePBI o Fabric REST API (publicar a Power BI Service)
```

### Limitaciones a considerar

- **Power BI Desktop sigue siendo necesario** para visualizar y validar los archivos .pbip/.pbir localmente antes de publicar.
- **PBIR aún está en Preview**: aunque Microsoft lo impulsa agresivamente, pueden haber cambios en el esquema hasta la GA.
- **Licencia Fabric/Premium** requerida para usar las Fabric REST APIs de creación de informes.
- **powerbpy es un proyecto comunitario** (no de Microsoft), lo que implica riesgo de mantenimiento a largo plazo.
- **No existe generación de .pbix "puro"** desde cero de forma confiable; siempre pasa por el formato intermedio de carpetas.

---

## Referencias

1. **powerbpy** — Documentación: https://www.russellshean.com/powerbpy/ | PyPI: https://pypi.org/project/powerbpy/
2. **pbir_tools** — GitHub: https://github.com/david-iwdb/pbir_tools
3. **pbir-utils** — PyPI: https://pypi.org/project/pbir-utils/ | GitHub: https://github.com/akhilannan/pbir-utils
4. **pypbireport** — PyPI: https://pypi.org/project/pypbireport/ | GitHub: https://github.com/IsmaelMiranda11/py-powerbi-report
5. **python-pbi** — GitHub: https://github.com/JChamboredon/pbi
6. **PowerPy** — GitHub: https://github.com/nathangiusti/PowerPy
7. **pbipy** — PyPI: https://pypi.org/project/pbipy/ | GitHub: https://github.com/andrewvillazon/pbipy
8. **SimplePBI** — PyPI: https://pypi.org/project/SimplePBI/
9. **pbi-tools CLI** — Sitio: https://pbi.tools/ | GitHub: https://github.com/pbi-tools/pbi-tools
10. **Tabular Editor** — Sitio: https://tabulareditor.com/ | Docs: https://docs.tabulareditor.com/
11. **AMO/TOM (.NET)** — NuGet: https://www.nuget.org/packages/Microsoft.AnalysisServices/ | Docs: https://learn.microsoft.com/en-us/analysis-services/tom/
12. **FabricPS-PBIP** — GitHub: https://github.com/microsoft/Analysis-Services/tree/master/pbidevmode/fabricps-pbip
13. **Power BI REST API** — Docs: https://learn.microsoft.com/en-us/rest/api/power-bi/
14. **Fabric REST API — Create Report** — Docs: https://learn.microsoft.com/en-us/rest/api/fabric/report/items/create-report
15. **Fabric REST API — Deploy Project** — Docs: https://learn.microsoft.com/en-us/rest/api/fabric/articles/get-started/deploy-project
16. **PBIR como formato por defecto** — Blog Microsoft: https://powerbi.microsoft.com/en-us/blog/pbir-will-become-the-default-power-bi-report-format-get-ready-for-the-transition/
17. **Formato PBIP** — Docs Microsoft: https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview
18. **Formato PBIR** — Docs Microsoft: https://learn.microsoft.com/en-us/power-bi/developer/embedded/projects-enhanced-report-format
19. **powerbi-report-authoring (npm)** — npm: https://www.npmjs.com/package/powerbi-report-authoring
20. **semantic-link-labs** — Docs: https://semantic-link-labs.readthedocs.io/
21. **OpenClaw Dashboard Skill** — https://playbooks.com/skills/openclaw/skills/dashboard
22. **LangGraph + Power BI** — https://bix-tech.com/langgraph-power-bi-how-to-automate-report-generation-without-losing-governance/
23. **AI y desarrollo agéntico para BI (SQLBI)** — https://www.sqlbi.com/articles/introducing-ai-and-agentic-development-for-business-intelligence/
