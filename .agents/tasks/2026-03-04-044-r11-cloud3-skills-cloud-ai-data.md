---
id: "044"
title: "Skills Cloud, IA y Data — Azure, Google Cloud/Vertex, LangChain, MCP Protocol, Big Data Python"
assigned_to: cursor-agent-cloud-3
branch: feat/cloud3-skills-cloud-ai
round: 11
status: assigned
created: 2026-03-04
---

## Objetivo

Documentar plataformas cloud, frameworks de IA y herramientas de datos que forman la infraestructura del stack de Rick y de la consultoría de David.

## Herramientas a cubrir

| Skill | URL docs oficiales | Alcance |
|---|---|---|
| `azure-platform` | https://learn.microsoft.com/azure/ | Azure Functions, Blob Storage, CosmosDB, Service Bus, App Service, Azure OpenAI |
| `google-cloud-vertex` | https://cloud.google.com/vertex-ai/docs + https://ai.google.dev/gemini-api/docs | Vertex AI, Gemini API, embeddings, deployments, Imagen |
| `langchain-langgraph` | https://python.langchain.com/docs/ + https://langchain-ai.github.io/langgraph/ | Chains, agents, memory, tools, LangGraph state machines |
| `mcp-protocol` | https://modelcontextprotocol.io/docs + https://github.com/modelcontextprotocol/servers | MCP servers, resources, tools, prompts, conectar herramientas a LLMs |
| `big-data-python` | https://pandas.pydata.org/docs/ + https://docs.pola.rs/ + https://dask.org/docs | Pandas, Polars (alternativa rápida), Dask para datasets grandes |

## Contexto importante

- **Azure**: David ya tiene Azure OpenAI (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY) y Azure AI Foundry configurados en el stack. El skill debe cubrir tanto la plataforma general como el servicio OpenAI específicamente.
- **Vertex AI**: David tiene `GOOGLE_API_KEY_RICK_UMBRAL` y `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL` configurados.
- **LangChain/LangGraph**: Ya está en el stack como runtime de agentes en la VM.
- **MCP**: El stack ya usa MCPs (Figma, Linear, Notion, Supabase, Stripe, GitHub).

## Instrucciones

```bash
git pull origin main
git checkout -b feat/cloud3-skills-cloud-ai
```

Para cada skill:
1. Buscar docs oficiales en URLs indicadas
2. Enfocar en: setup rápido, comandos frecuentes, SDKs Python, casos de uso prácticos
3. Para Azure: cubrir Azure CLI + Python SDK + Azure OpenAI
4. Para MCP: incluir cómo crear un servidor MCP propio y cómo conectarlo a OpenClaw
5. Para Big Data: comparar Pandas vs Polars (Polars es más moderno y rápido)

### Validar

```bash
python scripts/validate_skills.py
```

### Commit y PR

```bash
git add openclaw/workspace-templates/skills/
git commit -m "feat: skills cloud ai data — azure, vertex, langchain, mcp, big-data-python"
git push -u origin feat/cloud3-skills-cloud-ai
gh pr create --title "feat: skills cloud/IA/data — azure, vertex, langchain, MCP, big data" \
  --body "5 SKILL.md from official docs for cloud, AI frameworks and data tools"
```

## Criterio de éxito

- 5 SKILL.md creados con frontmatter YAML válido
- `python scripts/validate_skills.py` → exit 0
- Azure skill cubre tanto plataforma general como Azure OpenAI
- MCP skill incluye cómo crear un server propio
- Big Data skill compara Pandas vs Polars con ejemplos
