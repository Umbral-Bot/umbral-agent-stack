---
name: speckle-dalux-powerbi
description: >-
  Mentor tecnico para integracion Speckle, Dalux Field y Power BI en proyectos
  BIM. Guia sobre conectores, flujos de datos, dashboards y casos de uso
  practicos para coordinacion oficina-obra.
  Use when "speckle", "dalux", "power bi", "dashboard BIM",
  "integracion datos BIM", "conector speckle", "dalux field", "visual 3D".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env: []
---

# Speckle + Dalux + Power BI — Mentor de Integracion BIM

Rick usa este skill para guiar la integracion de Speckle (modelos BIM), Dalux Field (gestion de obra) y Power BI (dashboards y analisis) en flujos de trabajo BIM.

## Dominio Speckle

### Que es Speckle

Plataforma de colaboracion de diseno open source que sustituye flujos basados en archivos por conexiones en vivo entre herramientas CAD/BIM. Mantiene equipos sincronizados sin exportaciones manuales.

### Conceptos clave

| Concepto | Descripcion |
|----------|-------------|
| **Workspace** | Espacio de trabajo donde se organizan proyectos y equipos |
| **Project** | Contenedor de modelos dentro de un workspace |
| **Model** | Conjunto de datos (geometria y propiedades) de una disciplina |
| **Version** | Punto en el tiempo de un modelo. Cada envio crea nueva version |
| **Federation** | Combinar varios modelos en una vista unificada |

### Conectores

Plugins ligeros para Revit, Rhino, Grasshopper, Power BI, AutoCAD, Archicad, Blender, Tekla, Navisworks. Tambien acepta IFC, OBJ, STL por drag and drop.

### Conector Power BI

**Componentes:**
1. **Connector de datos:** Carga datos del modelo en tablas
2. **Visual 3D:** Muestra modelo 3D dentro del dashboard con interaccion

**Configuracion basica:**
1. Instalar conector desde https://app.speckle.systems/connectors
2. En Power BI: Get Data > buscar "Speckle" > Connect
3. Habilitar extensiones: File > Options > Security > Data Extensions > Allow any extension
4. Pegar URL del modelo
5. Importar visual 3D: Visualizations > ... > Import from file > `Documents/Power BI Desktop/Custom Visuals/Speckle 3D Visual.pbiviz`

**Configuracion del visual:**

| Campo | Requerido | Uso |
|-------|-----------|-----|
| Model Info | Si | Visualizacion |
| Object IDs | Si | Interactividad (drill-down) |
| Tooltip | No | Info al pasar cursor |
| Color by | No | Colorear por categoria/propiedad |

**Requisito:** Speckle Desktop Service debe estar en ejecucion.

### Helpers Power Query

| Funcion | Uso |
|---------|-----|
| `Speckle.Projects.Issues(url, getReplies)` | Issues del proyecto/modelo/version |
| `Speckle.Objects.Properties(record, filterKeys)` | Propiedades de un objeto |
| `Speckle.Objects.CompositeStructure(record, outputAsList)` | Capas de muros/suelos |
| `Speckle.Objects.MaterialQuantities(record, outputAsList)` | Cantidades materiales por objeto |
| `Speckle.Models.MaterialQuantities(table, addPrefix)` | Cantidades a nivel de modelo |
| `Speckle.Models.Federate(tables, excludeData)` | Federar modelos para visual 3D |
| `Speckle.Utils.ExpandRecord(table, columnName, FieldNames, UseCombinedNames)` | Expandir columnas tipo record |

### Intelligence Dashboards

Vistas interactivas dentro de Speckle (sin Power BI): Model Viewer, Dual viewer, Element count/table, Pivot table. Widgets por fuente: Revit (levels, categories, families), Tekla (profiles, phases, weight).

### Data Gateway (refresco programado)

Para Power BI Service: configurar Data Gateway (Personal o Standard). Anadir conector Speckle (.pqx) a carpeta Custom Connectors del gateway. Configurar OAuth2 en semantic model.

## Dominio Dalux Field

### Que es Dalux Field

Aplicacion de gestion de obra en campo: planos, tareas, formularios, inspecciones, registro diario, seguridad, reuniones. Integrado con flujo BIM.

### Funcionalidades principales

- **Planos y ubicaciones:** Cargar/actualizar planos sincronizados por zonas
- **Tareas y aprobaciones:** Crear, asignar, responder. Flujos RFI, defectos, incidencias
- **Formularios y QC:** Formularios estandar, planes de control de calidad, inspecciones
- **Captura:** Albums de fotos, fotos 360, SiteWalk
- **Seguridad:** Observaciones, inspecciones, problemas HSE, buenas practicas
- **Analiticas:** Tableros predefinidos con filtros por paquete, contrato, responsable, estado

### Paquetes y flujos de trabajo

Base de la organizacion en Dalux. Tipos de flujos:

| Tipo | Descripcion |
|------|-------------|
| **Aprobacion (unidireccional)** | Multiples pasos de aprobacion hasta cierre |
| **Tarea (bidireccional)** | Tareas que van y vienen entre creador y destinatarios |
| **Seguridad** | Para incidencias de seguridad |
| **Formulario puntos de retencion** | Asignacion por grupo/usuario |
| **Plan de calidad / inspeccion** | Vinculados a un plan concreto |

Recomendacion: usar grupos de usuarios en perfiles, no usuarios individuales.

### Estados de tarea

| Estado | Significado |
|--------|-------------|
| Gris — Nuevo | Asignada, no vista/iniciada |
| Amarillo — En proceso | En trabajo por responsable |
| Verde con tick — Reportado listo | Esperando aprobacion |
| Verde — Aprobado/cerrado | Trabajo aceptado |
| Rojo — Rechazado | Trabajo no aceptado |
| Negro — Archivado | Tarea eliminada o no valida |

### Ejemplos de flujo

**Defectos:** Gestion crea tarea > Subcontratista corrige > Gestion verifica > Aprueba o reasigna.

**RFI:** Electricista crea RFI > Gestion recibe > Asigna a Arquitecto/Ingeniero > Responde > Devuelve a Gestion > Cierra.

### BIM Viewer

Navegacion (orbita, pan, zoom, primera persona WASD), cortes en X/Y/Z, filtros por disciplina (Arq, Est, MEP), propiedades BIM al clic, split view 2D+3D sincronizado.

### Exportar datos

Exportar a Excel (analisis, tablas dinamicas) o PDF (informes con fotos/planos). Proceso: vista lista > filtrar > seleccionar > exportar. Portal del Promotor para descarga restringida. Dalux Handover para archivo final.

## Power BI en ecosistema BIM

### Rol

- Analisis de datos BIM: cantidades, propiedades, materiales, niveles
- Visualizacion 3D interactiva con drill-down
- Dashboards ejecutivos: KPIs, tendencias, comparaciones versiones
- Integracion datos obra: combinar Dalux (tareas) con Speckle (modelo)

### Relacion con Dalux

Power BI no tiene conector nativo a Dalux. Opciones:
1. Exportacion Dalux a CSV/Excel + carga manual o Power Query
2. API (si disponible) + Power Query / Power Automate
3. Base de datos intermedia que consolida Dalux + Speckle

### Buenas practicas

- Usar "latest" para ultima version; fijar version para analisis historico
- Limitar propiedades cargadas para rendimiento en modelos grandes
- Combinar visual 3D con graficos y tablas para drill-down geometria-metricas

### Troubleshooting frecuente

| Problema | Solucion |
|----------|---------|
| No carga modelo | Verificar Speckle Desktop Service en ejecucion |
| Error autenticacion | File > Options > Security > desmarcar "Use my default web browser" |
| Token caducado | Clear Permissions en Data source settings. Eliminar PowerBITokenCache.db |
| Sin permisos | Verificar acceso al proyecto en Speckle. Re-autenticar |

## Flujos de integracion

### Flujo 1: Modelo BIM > Power BI

1. Speckle: publicar modelos desde Revit/Rhino/Tekla
2. Power BI: conectar con URL del modelo via conector Speckle
3. Resultado: tablas de elementos + visual 3D para drill-down

Casos: quantity takeoff, analisis materiales, comparacion versiones, dashboards ejecutivos.

### Flujo 2: Dalux > Power BI (datos de obra)

1. Dalux: exportar tareas/inspecciones/formularios a Excel
2. Power BI: cargar Excel con Get Data
3. Resultado: dashboards seguimiento tareas, incidencias, control calidad

### Flujo 3: Speckle + Dalux + Power BI (vision unificada)

1. Speckle: modelos BIM centralizados
2. Dalux: tareas vinculadas a ubicaciones/planos
3. Power BI: cargar ambos, crear modelo relacional por ubicacion/nivel/disciplina
4. Resultado: dashboards que combinan estado del modelo BIM con tareas e inspecciones en campo

### Speckle Intelligence vs Power BI

| Criterio | Speckle Intelligence | Power BI |
|----------|---------------------|----------|
| Fuente datos | Solo modelos Speckle | Speckle + Dalux + otras |
| Integracion Dalux | No nativa | Manual o API |
| Visual 3D | Integrado | Visual Speckle 3D |
| Colaboracion | Workspace Speckle | Power BI Service |

Recomendacion: Speckle Intelligence para analisis solo de modelos. Power BI cuando se necesite combinar con Dalux u otras fuentes.

## Casos de uso practicos

### 1. Quantity takeoff (Speckle > Power BI)
Publicar modelo > conectar > Power Query para filtrar propiedades (area, volumen) > graficos por nivel/categoria + visual 3D.

### 2. Seguimiento tareas (Dalux > Power BI)
Exportar tareas a Excel > cargar > metricas: abiertas, cerradas, por responsable, estado, fecha.

### 3. Comparacion versiones (Speckle > Power BI)
Federar dos versiones > cargar > comparar conteo elementos, diferencias por categoria.

### 4. Control de calidad (Dalux + Power BI)
Exportar inspecciones > cargar > indicadores: % cumplimiento por zona, tendencia, responsables.

### 5. Vision integrada BIM + Obra (Speckle + Dalux + Power BI)
Cargar modelo Speckle + datos Dalux > relacion por nivel/zona > visual 3D coloreado por estado de tarea.

### 6. Materiales y carbono (Speckle > Power BI)
Usar `Speckle.Objects.MaterialQuantities` > graficos por material, nivel, area > totales carbono.

### 7. Seguridad HSE (Dalux > Power BI)
Exportar observaciones/inspecciones seguridad > indicadores: indice seguridad, tendencia, categorias.

## Referencias

- Speckle docs: https://docs.speckle.systems/
- Speckle Power BI: https://docs.speckle.systems/connectors/power-bi/power-bi
- Dalux Field: https://support.dalux.com/hc/es/categories/4405292014738-Field
- Dalux Academy: https://academy.dalux.com/
