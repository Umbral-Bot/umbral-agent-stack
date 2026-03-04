---
name: ifc-python
description: >-
  Leer, modificar y exportar archivos IFC con IfcOpenShell. Extrae elementos,
  propiedades, geometría y metadatos de modelos BIM. Usa cuando el usuario diga
  "IFC", "IfcOpenShell", "modelo IFC", "propiedades IFC", "exportar IFC",
  "leer IFC", "interoperabilidad BIM", "open BIM".
metadata:
  openclaw:
    emoji: "🏗️"
    requires:
      env: []
---

# IFC Python Skill — IfcOpenShell y herramientas open BIM

Rick usa este skill para leer, analizar, modificar y exportar archivos IFC (Industry Foundation Classes) usando IfcOpenShell y herramientas Python open source.

## Instalación y setup

```bash
pip install ifcopenshell
```

IfcOpenShell soporta IFC2x3, IFC4 e IFC4x3. La versión de Python debe coincidir con la del paquete (3.9-3.12).

Para geometría y visualización:

```bash
pip install ifcopenshell[geometry]
pip install OCC  # Open CASCADE para renderizado
```

Paquetes complementarios:

| Paquete | Uso |
|---------|-----|
| `ifcopenshell` | Lectura, escritura y modificación de IFC |
| `ifcpatch` | Transformaciones batch sobre archivos IFC |
| `ifcdiff` | Comparación entre versiones de modelos IFC |
| `ifcclash` | Detección de interferencias geométricas |
| `ifccsv` | Exportar/importar propiedades IFC a CSV |
| `bimtester` | Validación de requisitos BIM con Gherkin |

## Abrir y explorar un modelo IFC

```python
import ifcopenshell

ifc = ifcopenshell.open("modelo.ifc")

print(f"Schema: {ifc.schema}")           # IFC2X3, IFC4, IFC4X3
print(f"Nombre: {ifc.header.file_name.name}")
print(f"Elementos totales: {len(ifc.by_type('IfcProduct'))}")
```

### Resumen de elementos por tipo

```python
from collections import Counter

tipos = Counter(e.is_a() for e in ifc.by_type("IfcProduct"))
for tipo, cantidad in tipos.most_common():
    print(f"  {tipo}: {cantidad}")
```

Salida típica:

```
  IfcWallStandardCase: 142
  IfcDoor: 87
  IfcWindow: 64
  IfcSpace: 38
  IfcColumn: 24
  IfcSlab: 18
  IfcBeam: 12
```

## Extraer propiedades de elementos

### IfcPropertySet y IfcPropertySingleValue

```python
def get_properties(element):
    """Extrae todas las propiedades de un elemento IFC como dict."""
    props = {}
    for definition in element.IsDefinedBy:
        if definition.is_a("IfcRelDefinesByProperties"):
            pset = definition.RelatingPropertyDefinition
            if pset.is_a("IfcPropertySet"):
                for prop in pset.HasProperties:
                    if prop.is_a("IfcPropertySingleValue"):
                        value = prop.NominalValue.wrappedValue if prop.NominalValue else None
                        props[prop.Name] = value
    return props

wall = ifc.by_type("IfcWall")[0]
props = get_properties(wall)
for name, value in props.items():
    print(f"  {name}: {value}")
```

### Quantity Sets (cantidades)

```python
def get_quantities(element):
    """Extrae IfcElementQuantity (áreas, volúmenes, longitudes)."""
    quantities = {}
    for definition in element.IsDefinedBy:
        if definition.is_a("IfcRelDefinesByProperties"):
            qset = definition.RelatingPropertyDefinition
            if qset.is_a("IfcElementQuantity"):
                for q in qset.Quantities:
                    if q.is_a("IfcQuantityArea"):
                        quantities[q.Name] = q.AreaValue
                    elif q.is_a("IfcQuantityVolume"):
                        quantities[q.Name] = q.VolumeValue
                    elif q.is_a("IfcQuantityLength"):
                        quantities[q.Name] = q.LengthValue
    return quantities

slab = ifc.by_type("IfcSlab")[0]
print(get_quantities(slab))
# {'NetArea': 45.2, 'GrossVolume': 9.04, 'Width': 0.2}
```

## Filtrar elementos por tipo

```python
# Muros
walls = ifc.by_type("IfcWall")

# Puertas
doors = ifc.by_type("IfcDoor")

# Espacios (habitaciones, zonas)
spaces = ifc.by_type("IfcSpace")

# Elementos estructurales
columns = ifc.by_type("IfcColumn")
beams = ifc.by_type("IfcBeam")
slabs = ifc.by_type("IfcSlab")

# Instalaciones MEP
ducts = ifc.by_type("IfcDuctSegment")
pipes = ifc.by_type("IfcPipeSegment")

# Todos los elementos con geometría
products = ifc.by_type("IfcProduct")
```

### Filtrar por atributo

```python
# Muros de un nivel específico
level_2_walls = [
    w for w in ifc.by_type("IfcWall")
    if any(
        rel.RelatingStructure.Name == "Nivel 2"
        for rel in getattr(w, "ContainedInStructure", [])
    )
]

# Elementos por GlobalId
element = ifc.by_guid("2O2Fr$t4X7Zf8NOew3FLOH")
```

## Exportar a CSV/JSON para análisis

### Exportar a CSV

```python
import csv

walls = ifc.by_type("IfcWall")
with open("muros.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["GlobalId", "Name", "Tag", "ObjectType"])
    for wall in walls:
        writer.writerow([
            wall.GlobalId,
            wall.Name or "",
            wall.Tag or "",
            wall.ObjectType or ""
        ])
```

### Exportar a JSON

```python
import json

def element_to_dict(el):
    return {
        "id": el.GlobalId,
        "type": el.is_a(),
        "name": el.Name or "",
        "properties": get_properties(el),
        "quantities": get_quantities(el),
    }

data = [element_to_dict(e) for e in ifc.by_type("IfcSpace")]
with open("espacios.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

## Modificar propiedades y guardar IFC

```python
import ifcopenshell
import ifcopenshell.api

ifc = ifcopenshell.open("modelo.ifc")

wall = ifc.by_type("IfcWall")[0]

# Cambiar el nombre del elemento
wall.Name = "Muro Exterior Principal"

# Agregar/modificar una propiedad en un PropertySet existente
for definition in wall.IsDefinedBy:
    if definition.is_a("IfcRelDefinesByProperties"):
        pset = definition.RelatingPropertyDefinition
        if pset.is_a("IfcPropertySet") and pset.Name == "Pset_WallCommon":
            for prop in pset.HasProperties:
                if prop.Name == "IsExternal":
                    prop.NominalValue = ifc.createIfcBoolean(True)

# Crear un nuevo PropertySet con ifcopenshell.api
pset = ifcopenshell.api.run("pset.add_pset", ifc,
    product=wall,
    name="Custom_Props"
)
ifcopenshell.api.run("pset.edit_pset", ifc,
    pset=pset,
    properties={
        "EspesorNominal": 0.20,
        "Acabado": "Pintura blanca",
        "FechaRevision": "2026-03-01"
    }
)

ifc.write("modelo_modificado.ifc")
```

## Integración con `llm.generate` para análisis de modelos

```python
import json

spaces = ifc.by_type("IfcSpace")
space_data = []
for space in spaces:
    props = get_properties(space)
    quants = get_quantities(space)
    space_data.append({
        "name": space.Name or space.LongName or "Sin nombre",
        "area_m2": quants.get("NetFloorArea", quants.get("GrossFloorArea", "N/D")),
        "properties": props
    })

prompt = f"""Analiza los espacios de este modelo IFC y genera un resumen ejecutivo:
- Total de espacios: {len(space_data)}
- Datos: {json.dumps(space_data[:20], indent=2, ensure_ascii=False)}

Incluye: superficie total, distribución por uso, observaciones sobre normativa."""

# Enviar a Rick para análisis con LLM
result = await client.execute_task("llm.generate", {
    "prompt": prompt,
    "model": "gemini-2.5-flash"
})
```

## Integración con `windows.fs.*` para leer IFC desde VM

```python
# Leer un IFC almacenado en la VM (G:\Mi unidad\...)
result = await client.execute_task("windows.fs.read_binary", {
    "path": r"G:\Mi unidad\Rick-David\Modelos BIM\edificio.ifc"
})

# Guardar localmente, procesar con IfcOpenShell
import tempfile, os
with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
    tmp.write(result["content"])
    tmp_path = tmp.name

ifc = ifcopenshell.open(tmp_path)
# ... procesar ...
os.unlink(tmp_path)
```

## Ejemplo completo: extraer áreas de todos los espacios

```python
import ifcopenshell
import csv

def extract_space_areas(ifc_path: str, output_csv: str):
    """Extrae GlobalId, nombre, nivel y área de todos los IfcSpace."""
    ifc = ifcopenshell.open(ifc_path)
    spaces = ifc.by_type("IfcSpace")

    rows = []
    for space in spaces:
        name = space.LongName or space.Name or "Sin nombre"
        global_id = space.GlobalId

        level = "N/D"
        for rel in getattr(space, "ContainedInStructure", []):
            if rel.RelatingStructure.is_a("IfcBuildingStorey"):
                level = rel.RelatingStructure.Name
                break

        area = None
        for definition in space.IsDefinedBy:
            if definition.is_a("IfcRelDefinesByProperties"):
                qset = definition.RelatingPropertyDefinition
                if qset.is_a("IfcElementQuantity"):
                    for q in qset.Quantities:
                        if q.is_a("IfcQuantityArea") and "Floor" in q.Name:
                            area = round(q.AreaValue, 2)
                            break

        rows.append({
            "GlobalId": global_id,
            "Nombre": name,
            "Nivel": level,
            "Area_m2": area or "N/D"
        })

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["GlobalId", "Nombre", "Nivel", "Area_m2"])
        writer.writeheader()
        writer.writerows(rows)

    total = sum(r["Area_m2"] for r in rows if isinstance(r["Area_m2"], (int, float)))
    print(f"Espacios: {len(rows)} | Superficie total: {total:.2f} m²")
    return rows

# Uso
extract_space_areas("edificio.ifc", "espacios_areas.csv")
```

## Herramientas complementarias

### ifcpatch — Transformaciones batch

```bash
ifcpatch -i modelo.ifc -o resultado.ifc -r OffsetObjectPlacement -a 1000,2000,0
ifcpatch -i modelo.ifc -o resultado.ifc -r ResetAbsoluteCoordinates
```

### ifcdiff — Comparar versiones

```bash
ifcdiff modelo_v1.ifc modelo_v2.ifc -o cambios.json
```

### ifcclash — Detección de interferencias

```python
from ifcclash import ifcclash

settings = ifcclash.IfcClashSettings()
settings.output = "clashes.json"
clasher = ifcclash.IfcClash(settings)
clasher.add_group("Estructura", "estructura.ifc")
clasher.add_group("MEP", "mep.ifc")
clasher.clash()
clasher.export()
```

## Ejemplos de uso con Rick

- **Rick: "Extraé todas las puertas con sus dimensiones del IFC"** → `by_type("IfcDoor")` + `get_properties()` + exportar a CSV.
- **Rick: "Cuántos m² de espacios tiene el modelo?"** → `extract_space_areas()` con sum de áreas.
- **Rick: "Compará las dos versiones del modelo IFC"** → `ifcdiff` entre v1 y v2, generar reporte.
- **Rick: "Agregá la propiedad 'Zona Sísmica' a todos los muros"** → `ifcopenshell.api.run("pset.edit_pset")` en loop.
- **Rick: "Hacé un clash detection entre estructura y MEP"** → `ifcclash` con dos grupos de archivos.

## Recursos oficiales

- IfcOpenShell docs: https://ifcopenshell.org/
- IfcOpenShell Python API: https://docs.ifcopenshell.org/ifcopenshell-python/
- buildingSMART IFC spec: https://standards.buildingsmart.org/IFC/
- BlenderBIM (IfcOpenShell GUI): https://blenderbim.org/
- IfcOpenShell GitHub: https://github.com/IfcOpenShell/IfcOpenShell

## Notas

- IfcOpenShell es la librería Python de referencia para IFC. Es mantenida por la comunidad y usada en BlenderBIM.
- Los archivos IFC son texto plano (STEP/SPF), legibles y versionables con Git.
- IFC4 es el schema recomendado para proyectos nuevos; IFC2x3 sigue siendo común en proyectos existentes.
- Para geometría 3D (visualización, clash), se necesita el módulo `geometry` que depende de Open CASCADE.
- `ifcopenshell.api` provee una API de alto nivel para crear y modificar entidades IFC de forma segura.
