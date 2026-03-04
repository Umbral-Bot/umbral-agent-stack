---
name: mcp-protocol
description: >-
  Build and connect Model Context Protocol (MCP) servers that expose tools,
  resources and prompts to LLMs. Create custom MCP servers in Python with
  FastMCP and integrate them into OpenClaw or Claude Desktop.
  Use when "mcp server", "model context protocol", "mcp tools", "mcp resources",
  "connect tool to llm", "create mcp", "fastmcp".
metadata:
  openclaw:
    emoji: "\U0001F50C"
    requires:
      env:
        - WORKER_TOKEN
---

# MCP Protocol Skill

Crear y conectar servidores MCP (Model Context Protocol) que exponen herramientas, recursos y prompts a LLMs de forma estandarizada.

## Requisitos

| Variable | Descripción |
|----------|-------------|
| `WORKER_TOKEN` | Token para autenticar contra el Worker (al integrar con OpenClaw) |

### Instalación

```bash
pip install fastmcp
```

## 1. ¿Qué es MCP?

MCP es un protocolo abierto que estandariza cómo los LLMs se conectan a herramientas y datos externos. Un servidor MCP expone tres primitivas:

| Primitiva | Descripción | Ejemplo |
|-----------|-------------|---------|
| **Tools** | Funciones invocables por el LLM | Crear issue en Linear, buscar en DB |
| **Resources** | Datos de solo lectura | Archivos de config, datos de API |
| **Prompts** | Templates de prompt reutilizables | Prompt de análisis de código |

## 2. Crear un servidor MCP con FastMCP

### Server básico

```python
from fastmcp import FastMCP

mcp = FastMCP(name="Mi Server MCP")

@mcp.tool
def sumar(a: int, b: int) -> int:
    """Suma dos números."""
    return a + b

@mcp.tool
def buscar_tareas(estado: str = "pending") -> list[dict]:
    """Busca tareas por estado en la base de datos."""
    # lógica real de búsqueda
    return [{"id": 1, "title": "Revisar PR", "status": estado}]

if __name__ == "__main__":
    mcp.run()  # stdio transport por defecto
```

### Agregar Resources

```python
@mcp.resource("resource://config")
def get_config() -> dict:
    """Configuración actual del sistema."""
    return {"version": "1.0", "environment": "production"}

@mcp.resource("resource://users/{user_id}")
def get_user(user_id: str) -> dict:
    """Datos de un usuario por ID (resource template)."""
    return {"id": user_id, "name": "David", "role": "admin"}
```

### Agregar Prompts

```python
@mcp.prompt
def analizar_codigo(lenguaje: str = "python") -> str:
    """Prompt para análisis de código."""
    return f"""Analizá el siguiente código {lenguaje}.
Reportá: bugs, mejoras de performance, y sugerencias de estilo.
Sé conciso y usá bullet points."""
```

## 3. Transportes

| Transporte | Uso | Comando |
|------------|-----|---------|
| **stdio** | Local (Claude Desktop, Cursor) | `mcp.run()` |
| **HTTP** | Remoto (servers en la nube) | `mcp.run(transport="http", port=8000)` |

### Ejecutar con CLI

```bash
fastmcp run server.py:mcp                          # stdio
fastmcp run server.py:mcp --transport http --port 8000  # HTTP
```

## 4. Cliente MCP — Conectarse a un server

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp") as client:
        tools = await client.list_tools()
        print(f"Tools disponibles: {[t.name for t in tools]}")

        result = await client.call_tool("sumar", {"a": 5, "b": 3})
        print(f"Resultado: {result}")

        resources = await client.list_resources()
        config = await client.read_resource("resource://config")
        print(f"Config: {config}")

asyncio.run(main())
```

## 5. Integrar con Claude Desktop

Agregar al archivo de configuración de Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mi-server": {
      "command": "python",
      "args": ["/ruta/a/server.py"],
      "env": {
        "API_KEY": "mi-key"
      }
    }
  }
}
```

## 6. Integrar con OpenClaw

El stack de Rick ya usa MCPs para varios servicios. Para agregar uno nuevo:

1. Crear el server MCP con FastMCP
2. Desplegarlo con transporte HTTP en un puerto disponible
3. Registrar la URL en la configuración del Dispatcher
4. El Dispatcher enrutará llamadas al server MCP como cualquier otro handler

### MCPs ya integrados en el stack

| MCP Server | Función |
|------------|---------|
| Figma | Leer archivos, exportar frames, comentarios |
| Linear | Crear issues, listar proyectos, asignar tareas |
| Notion | Leer/escribir páginas, bases de datos, comentarios |
| Supabase | Queries SQL, gestión de datos |
| Stripe | Pagos, suscripciones, invoices |
| GitHub | Repos, PRs, issues, actions |

## 7. Server MCP avanzado — Con estado y dependencias

```python
from fastmcp import FastMCP, Context
from dataclasses import dataclass

@dataclass
class AppState:
    db_url: str
    cache: dict

mcp = FastMCP(name="Advanced Server")

@mcp.tool
async def query_db(ctx: Context, sql: str) -> list[dict]:
    """Ejecuta una query SQL contra la base de datos."""
    await ctx.report_progress(0.5, "Ejecutando query...")
    # lógica con ctx.state.db_url
    return [{"result": "data"}]

@mcp.tool
async def long_task(ctx: Context, input: str) -> str:
    """Tarea que reporta progreso."""
    for i in range(5):
        await ctx.report_progress(i / 5, f"Paso {i+1}/5")
    return f"Completado: {input}"
```

## Notas

- FastMCP genera automáticamente JSON schemas desde type hints y docstrings de Python.
- Los type hints son obligatorios para que el LLM entienda los parámetros.
- Los docstrings se usan como descripción de la tool — escribirlos claros y concisos.
- MCP evoluciona rápido; pinear la versión del SDK en `requirements.txt`.
- Docs: https://modelcontextprotocol.io/docs | https://gofastmcp.com/
