---
name: docente-aec40
description: >-
  Asistente para preparar material docente del Master AEC 4.0. Genera clases,
  ejercicios, guias tecnicas y contenido pedagogico sobre programacion BIM,
  Dynamo, Revit API y metodologia Citizen Developer.
  Usar cuando: "preparar clase", "material docente", "dynamo scripting",
  "revit python", "citizen developer", "clase BIM", "guia tecnica AEC",
  "ejercicio programacion", "contenido curso", "diseno instruccional".
metadata:
  openclaw:
    emoji: "\U0001F393"
    requires:
      env: []
---

# Docente AEC 4.0 — Skill de David Moreira

Rick usa este skill para preparar material de clase, guias tecnicas y contenido pedagogico del Master AEC 4.0 en Butic New School y TEDIvirtual. El perfil docente combina expertise tecnico en Dynamo/Revit API con metodologia Citizen Developer.

## Perfil docente

| Campo | Valor |
|-------|-------|
| **Programa** | Master AEC 4.0 — Butic The New School + TEDIvirtual |
| **Rol** | Docente titular modulos Programacion BIM y Automatizacion |
| **Certificacion** | Autodesk Certified Instructor (ACI) ID: 86900 |
| **Especializacion** | Dynamo, Revit API, Python, IA aplicada a AEC |
| **Metodologia** | Citizen Developer — programacion para no programadores |
| **Audiencia** | Arquitectos y coordinadores BIM sin background en codigo |

---

## Enfoque pedagogico: Citizen Developer

El Citizen Developer en AEC es un profesional que crea automatizaciones sin ser programador de formacion. David lo ensena con este principio:

> "No formo programadores. Formo arquitectos que resuelven problemas reales con codigo."

### Los 3 niveles de Citizen Developer

| Nivel | Perfil | Herramientas | Objetivo |
|-------|--------|--------------|----------|
| **CD-1 Explorador** | Sin experiencia en codigo | Dynamo visual, nodos OOTB | Automatizar tareas repetitivas con nodos |
| **CD-2 Constructor** | Conoce nodos, primer contacto con Python | Dynamo + Code Block + Python OOTB | Crear scripts simples con Python basico |
| **CD-3 Orquestador** | Programa en Python, usa APIs | Dynamo + Python + Revit API | Flujos completos, integraciones externas |

### Progresion de aprendizaje

1. **Fundamentos** — Logica de nodos, tipos de datos, listas
2. **Automatizacion visual** — Grafos Dynamo sin codigo
3. **Python en Dynamo** — Code Block, input/output, depuracion
4. **Revit API** — Objetos, metodos, transacciones
5. **Integracion** — Scripts que leen/escriben datos externos
6. **IA aplicada** — LLMs como copiloto para generar y refinar scripts

---

## Dynamo — Buenas Practicas

### Estructura del grafo

- **Entrada** siempre a la izquierda, **salida** a la derecha
- Agrupar por funcion con colores: naranja = entrada, azul = proceso, verde = salida
- Un grafo = una funcion. Si hace mas de una cosa, dividir
- Usar nodos `Watch` en puntos clave para depuracion visible
- Nombrar nodos personalizados con verbo + objeto: `ObtenerElementosPorCategoria`

### Listas y niveles

```
# Regla de oro: si el resultado es inesperado, revisar el nivel de lista (L1, L2...)
# Usar List.Map y List.Combine para operaciones sobre listas anidadas
# @L1, @L2 en inputs de nodos Python para controlar aplanado
```

### Python en Dynamo — Plantilla base

```python
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *

# Inputs (siempre validar tipos)
doc = IN[0]
elementos = IN[1] if isinstance(IN[1], list) else [IN[1]]

resultados = []
errores = []

for elem in elementos:
    try:
        # === LOGICA PRINCIPAL ===
        resultado = elem.Name  # ejemplo
        resultados.append(resultado)
    except Exception as e:
        errores.append(f"Error en {elem.Id}: {str(e)}")

OUT = resultados, errores
```

### Anti-patterns Dynamo

| Evitar | Por que | Alternativa |
|--------|---------|-------------|
| Grafos con 200+ nodos sin grupos | Inmantenible | Dividir en subgrafos con Custom Nodes |
| Python sin try/except | Falla silenciosa | Siempre capturar errores |
| `Element.SetParameterByName` en bucle | Rendimiento lento | Transaccion unica por batch |
| Hardcodear IDs de elementos | Fragilidad | Filtrar por categoria/tipo |
| `*` import (from X import *) | Colisiones namespace | Importar solo lo necesario |

---

## Revit API — Buenas Practicas

### Conceptos fundamentales

| Concepto | Explicacion |
|----------|-------------|
| **Document** | Modelo activo. Acceso a todos los elementos |
| **Element** | Unidad basica: muros, puertas, vistas, familias |
| **ElementId** | Identificador unico dentro del documento |
| **Parameter** | Propiedad del elemento. Tipos: texto, numero, si/no, elemento |
| **Transaction** | Envuelve modificaciones. Commit o Rollback |
| **FilteredElementCollector** | Herramienta para buscar elementos por categoria, clase o parametro |

### Patron basico de lectura

```python
# Obtener todos los muros del modelo
collector = FilteredElementCollector(doc)
muros = collector.OfCategory(BuiltInCategory.OST_Walls) \
                 .WhereElementIsNotElementType() \
                 .ToElements()
```

### Patron basico de escritura (con Transaction)

```python
with Transaction(doc, "Actualizar parametro") as t:
    t.Start()
    try:
        for elem in elementos:
            param = elem.LookupParameter("Comentarios")
            if param and not param.IsReadOnly:
                param.Set("Revisado por David")
        t.Commit()
    except Exception as e:
        t.RollBack()
        raise e
```

### Filtros eficientes

```python
# Filtrar por tipo especifico (mas rapido que filtrar todos)
elementos = FilteredElementCollector(doc) \
    .OfClass(Wall) \
    .ToElements()

# Filtrar por parametro (Rule-based filter)
rule = ParameterFilterRuleFactory.CreateEqualsRule(
    param_id, "Prefabricado", True
)
```

### Errores comunes en Revit API

| Error | Causa | Solucion |
|-------|-------|---------|
| `InvalidOperationException: Document is closed` | Acceder al doc fuera del contexto | Pasar doc como IN[0] desde Dynamo |
| `Autodesk.Revit.Exceptions.ModificationForbiddenException` | Escribir fuera de Transaction | Envolver en `with Transaction(doc, ...) as t` |
| `NullReferenceException` en parametro | Parametro no existe en esa familia | Validar `if param is not None` antes de Set |
| Rendimiento lento con 1000+ elementos | Crear Transaction por elemento | Una Transaction para todo el batch |

---

## Diseno instruccional para clases AEC 4.0

### Estructura de modulo (90 min)

| Segmento | Tiempo | Proposito |
|----------|--------|-----------|
| **Hook** | 5 min | Problema real o "por que importa esto hoy" |
| **Concepto clave** | 15 min | Maxima 1 concepto central por clase |
| **Demo en vivo** | 20 min | David muestra el flujo completo funcional |
| **Practica guiada** | 30 min | Alumnos replican con soporte |
| **Variacion libre** | 15 min | Alumnos adaptan a su propio contexto |
| **Cierre + nexo** | 5 min | Que resolvimos, que viene en la proxima clase |

### Principios pedagogicos

1. **Problema primero** — Empezar con el dolor real, no con la teoria
2. **Demo antes de explicar** — Mostrar el resultado antes de desglosarlo
3. **Error visible** — Cometer errores en vivo y mostrar como depurar
4. **Contexto AEC siempre** — Todo ejemplo sobre muros, puertas, vistas, familias
5. **Copia-pega valido** — El codigo de la clase es para usar, no para memorizar

### Tipos de ejercicios

| Tipo | Descripcion | Cuando usar |
|------|-------------|-------------|
| **Replicar** | Copiar exactamente lo que David hizo | Primera exposicion a un concepto |
| **Adaptar** | Modificar el script para otro caso | Segunda clase del mismo concepto |
| **Disenar** | Resolver un problema con la API | Cierre de modulo |
| **Depurar** | Encontrar y corregir bugs en un script dado | Refuerzo de logica |
| **Integrar** | Combinar dos scripts anteriores | Evaluacion de modulo |

### Criterios de evaluacion Citizen Developer

- El script corre sin errores en el modelo de prueba
- Maneja al menos un caso de error con mensaje claro
- El alumno puede explicar que hace cada bloque
- Resuelve el problema planteado (no necesariamente de forma optima)

---

## Tendencias tecnologicas AEC 4.0

### IA en el flujo BIM

| Aplicacion | Herramienta | Caso de uso docente |
|------------|-------------|---------------------|
| Generacion de codigo Dynamo/Python | Copilot, Claude, Gemini | Alumno describe lo que quiere, IA genera draft, alumno refina |
| Revision de codigo | ChatGPT, Copilot | Pegar script y pedir "encuentra los bugs" |
| Documentacion automatica | LLMs | Generar comentarios y README del script |
| Clasificacion de elementos | Vision AI | Reconocimiento de tipos en nubes de puntos |

### Stack recomendado para el curso

```
Nivel 1 (CD-1): Dynamo 2.x + Revit 2024+ + nodos OOTB
Nivel 2 (CD-2): + Python 3.x en Dynamo + Visual Studio Code
Nivel 3 (CD-3): + pyRevit + Revit API docs + GitHub
Transversal: ChatGPT/Copilot como asistente de codigo
```

### Que NO ensena este curso

- Programacion orientada a objetos pura (fuera del contexto AEC)
- Backend, APIs REST, despliegue en nube (nivel avanzado separado)
- Addins .NET de Revit en C# (requiere perfil de desarrollador)

---

## Templates de material docente

### Enunciado de ejercicio

```
## Ejercicio [N]: [Nombre descriptivo]

**Objetivo:** Al finalizar este ejercicio, el alumno podra [verbo + resultado concreto].

**Contexto:** [Descripcion del problema real en un proyecto AEC]

**Entregables:**
1. Script Dynamo (.dyn) que [hace X]
2. Screenshot del resultado en el modelo
3. (Opcional) 3 variaciones probadas

**Criterio de exito:** [Descripcion observable y verificable]

**Recursos:** [Links a docs, nodos, ejemplos]
```

### Slide de concepto tecnico

```
TITULO: [Concepto en 5 palabras max]
PROBLEMA: [Que falla sin esto]
SOLUCION: [Como lo resuelve el concepto]
CODIGO: [Snippet minimo funcional]
RESULTADO: [Screenshot o descripcion del output esperado]
TRAMPA: [Error comun y como evitarlo]
```

### Checklist pre-clase

- [ ] Script demo funciona en la version de Revit del curso
- [ ] Modelo de prueba distribuido a alumnos
- [ ] Casos de error identificados para mostrar en vivo
- [ ] Ejercicio probado: puede completarse en 30 min
- [ ] Nexo claro con clase anterior y siguiente

---

## Conceptos clave por modulo

### Modulo 1 — Fundamentos Dynamo
Nodos, wires, tipos de datos (number, string, boolean, element), listas y sublistas, Watch y Watch 3D, ejecucion automatica vs manual.

### Modulo 2 — Geometria y Parametros
Sistemas de coordenadas en Revit, crear/mover/rotar elementos, leer y escribir parametros de instancia y tipo, filtros por categoria.

### Modulo 3 — Python en Dynamo
Sintaxis Python basica, listas en Python vs listas Dynamo, importar clr y Revit API, transacciones, depuracion con print/errores.

### Modulo 4 — Revit API Avanzada
FilteredElementCollector, ParameterFilter, familia y tipo, vistas y sheets, exportar datos a Excel/CSV.

### Modulo 5 — IA aplicada
Prompts para generar scripts, revision asistida de codigo, IA como par programador, limitaciones y verificacion humana.
