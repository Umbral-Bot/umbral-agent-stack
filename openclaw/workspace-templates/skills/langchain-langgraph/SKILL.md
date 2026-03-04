---
name: langchain-langgraph
description: >-
  Build AI agents and orchestration pipelines with LangChain and LangGraph.
  Covers chains, tools, memory, retrieval, and LangGraph state machines.
  Use when "langchain agent", "langgraph", "chain pipeline", "tool calling",
  "agent memory", "react agent", "state machine ai", "rag pipeline".
metadata:
  openclaw:
    emoji: "\U0001F517"
    requires:
      env:
        - ANTHROPIC_API_KEY
        - OPENAI_API_KEY
---

# LangChain / LangGraph Skill

Construir agentes AI, pipelines de procesamiento y máquinas de estado con LangChain y LangGraph.

## Requisitos

Se necesita al menos una API key de LLM provider:

| Variable | Provider |
|----------|----------|
| `ANTHROPIC_API_KEY` | Claude (Anthropic) |
| `OPENAI_API_KEY` | GPT (OpenAI) |
| `GOOGLE_API_KEY` | Gemini (Google) |

### Instalación

```bash
pip install langchain langchain-anthropic langchain-openai langgraph langmem
```

## 1. LangChain — Chat rápido

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-4-6")
response = llm.invoke("Explicá qué es LangGraph en 2 oraciones.")
print(response.content)
```

### Con streaming

```python
for chunk in llm.stream("Contame sobre agentes AI"):
    print(chunk.content, end="")
```

## 2. Tools — Darle herramientas al LLM

```python
from langchain_core.tools import tool

@tool
def buscar_clima(ciudad: str) -> str:
    """Busca el clima actual de una ciudad."""
    return f"En {ciudad} hace 22°C y está soleado."

@tool
def calcular(expresion: str) -> str:
    """Evalúa una expresión matemática."""
    return str(eval(expresion))

llm_with_tools = llm.bind_tools([buscar_clima, calcular])
response = llm_with_tools.invoke("¿Cuánto es 42 * 17 y qué clima hace en CDMX?")
print(response.tool_calls)
```

## 3. LangGraph — Agente ReAct

El patrón más común: el LLM decide qué tool usar en cada paso.

```python
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
agent = create_react_agent(
    model=llm,
    tools=[buscar_clima, calcular],
    checkpointer=memory,
)

config = {"configurable": {"thread_id": "session-1"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "¿Clima en Buenos Aires?"}]},
    config=config,
)
print(result["messages"][-1].content)
```

## 4. LangGraph — Grafo personalizado

Para flujos con lógica condicional y múltiples pasos.

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    step: str

def clasificar(state: State) -> State:
    last = state["messages"][-1].content.lower()
    if "urgente" in last:
        return {**state, "step": "escalate"}
    return {**state, "step": "respond"}

def responder(state: State) -> State:
    resp = llm.invoke(state["messages"])
    return {"messages": [resp], "step": "done"}

def escalar(state: State) -> State:
    return {"messages": [{"role": "assistant", "content": "Escalado a David."}], "step": "done"}

def router(state: State) -> str:
    return state["step"]

graph = StateGraph(State)
graph.add_node("classify", clasificar)
graph.add_node("respond", responder)
graph.add_node("escalate", escalar)
graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", router, {"respond": "respond", "escalate": "escalate"})
graph.add_edge("respond", END)
graph.add_edge("escalate", END)

app = graph.compile()
result = app.invoke({"messages": [{"role": "user", "content": "Necesito ayuda urgente"}], "step": ""})
```

## 5. Memory — Conversaciones multi-turno

### Short-term (dentro de una sesión)

```python
from langgraph.checkpoint.memory import MemorySaver

agent = create_react_agent(model=llm, tools=tools, checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "user-123"}}

agent.invoke({"messages": [{"role": "user", "content": "Soy David"}]}, config=config)
agent.invoke({"messages": [{"role": "user", "content": "¿Cómo me llamo?"}]}, config=config)
```

### Long-term (entre sesiones)

```python
from langmem import create_manage_memory_tool, create_search_memory_tool

manage = create_manage_memory_tool(namespace=("user", "david"))
search = create_search_memory_tool(namespace=("user", "david"))

agent = create_react_agent(
    model=llm,
    tools=[manage, search],
    prompt="Usá las herramientas de memoria para recordar y buscar información del usuario.",
)
```

## 6. RAG — Retrieval Augmented Generation

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(documents)

vectorstore = FAISS.from_documents(chunks, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

results = retriever.invoke("¿Cómo funciona el dispatcher?")
```

## Conceptos clave de LangGraph

| Concepto | Descripción |
|----------|-------------|
| **State** | Datos compartidos entre nodos (`TypedDict` o `Pydantic`) |
| **Node** | Función que recibe state y devuelve updates |
| **Edge** | Conexión fija entre nodos |
| **Conditional Edge** | Bifurcación basada en una función router |
| **Checkpointer** | Persiste el state para recovery y multi-turno |
| **Reducer** | Controla cómo se mergen los updates al state (ej. `add_messages`) |

## Notas

- LangChain ya está en el stack de Rick como runtime de agentes en la VM.
- LangGraph v0.2.x es la versión estable actual.
- Preferir `create_react_agent` para agentes simples; usar `StateGraph` para flujos complejos.
- Docs: https://python.langchain.com/docs/ | https://langchain-ai.github.io/langgraph/
