---
name: azure-platform
description: >-
  Manage Azure cloud services including Functions, Blob Storage, CosmosDB,
  Service Bus, App Service and Azure OpenAI via Azure CLI and Python SDK.
  Use when "azure functions", "blob storage", "cosmosdb", "service bus",
  "app service", "azure openai", "azure deploy", "az cli".
metadata:
  openclaw:
    emoji: "\u2601"
    requires:
      env:
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_API_KEY
        - AZURE_SUBSCRIPTION_ID
---

# Azure Platform Skill

Interactuar con servicios de Azure para compute serverless, almacenamiento, bases de datos, mensajería y modelos OpenAI hospedados en Azure.

## Requisitos

| Variable | Descripción |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Endpoint del recurso Azure OpenAI |
| `AZURE_OPENAI_API_KEY` | API key del recurso Azure OpenAI |
| `AZURE_SUBSCRIPTION_ID` | ID de suscripción Azure (para CLI / SDK de gestión) |

### Instalación

```bash
pip install azure-identity azure-storage-blob azure-cosmos azure-servicebus openai
az login
```

## 1. Azure CLI — Comandos frecuentes

```bash
az login
az account set --subscription $AZURE_SUBSCRIPTION_ID
az group list --output table
az resource list --resource-group myRg --output table
```

### Functions

```bash
func init MyApp --worker-runtime python
func new --template "HTTP trigger" --name HelloFunc
func start                           # local
func azure functionapp publish MyApp # deploy
```

### Blob Storage

```bash
az storage account create --name myacct --resource-group myRg --sku Standard_LRS
az storage container create --name data --account-name myacct
az storage blob upload --account-name myacct --container-name data --file ./data.csv --name data.csv
az storage blob list --account-name myacct --container-name data --output table
```

## 2. Python SDK — Blob Storage

```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

credential = DefaultAzureCredential()
client = BlobServiceClient(
    account_url="https://myacct.blob.core.windows.net",
    credential=credential,
)

container = client.get_container_client("data")
with open("local.csv", "rb") as f:
    container.upload_blob(name="remote.csv", data=f, overwrite=True)

blob = container.download_blob("remote.csv")
content = blob.readall()
```

## 3. Python SDK — CosmosDB (NoSQL)

```python
from azure.cosmos import CosmosClient

client = CosmosClient(url=ENDPOINT, credential=KEY)
db = client.get_database_client("mydb")
container = db.get_container_client("items")

container.upsert_item({"id": "1", "name": "Rick", "role": "agent"})

results = container.query_items(
    query="SELECT * FROM c WHERE c.role = @role",
    parameters=[{"name": "@role", "value": "agent"}],
    enable_cross_partition_query=True,
)
for item in results:
    print(item)
```

## 4. Python SDK — Service Bus

```python
from azure.servicebus import ServiceBusClient, ServiceBusMessage

conn_str = "Endpoint=sb://myns.servicebus.windows.net/;SharedAccessKey=..."
with ServiceBusClient.from_connection_string(conn_str) as client:
    sender = client.get_queue_sender("tasks")
    with sender:
        sender.send_messages(ServiceBusMessage("hello"))

    receiver = client.get_queue_receiver("tasks")
    with receiver:
        for msg in receiver.receive_messages(max_wait_time=5):
            print(str(msg))
            receiver.complete_message(msg)
```

## 5. Azure OpenAI — Chat Completions

```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2025-12-01-preview",
)

response = client.chat.completions.create(
    model="gpt-4o",  # nombre del deployment en Azure
    messages=[
        {"role": "system", "content": "Sos un asistente útil."},
        {"role": "user", "content": "Explicá Azure Functions en 3 líneas."},
    ],
    max_tokens=512,
    temperature=0.7,
)
print(response.choices[0].message.content)
```

### Embeddings

```python
resp = client.embeddings.create(
    model="text-embedding-3-large",  # deployment name
    input=["texto a embeddear"],
)
vector = resp.data[0].embedding  # list[float], 3072 dims
```

## 6. App Service — Deploy rápido

```bash
az webapp up --runtime PYTHON:3.12 --sku B1 --name my-api
```

Sube el directorio actual como una web app Python (Flask/FastAPI). Crea Resource Group, App Service Plan y App Service automáticamente si no existen.

## Autenticación

La forma recomendada es `DefaultAzureCredential` de `azure-identity`, que detecta automáticamente el método de auth según el entorno:

| Entorno | Método |
|---------|--------|
| Local dev | Azure CLI (`az login`) |
| Azure VM / App Service | Managed Identity |
| CI/CD | Service Principal (env vars) |
| Containers | Workload Identity |

## Notas

- El stack de Rick ya tiene `AZURE_OPENAI_ENDPOINT` y `AZURE_OPENAI_API_KEY` configurados.
- Azure AI Foundry permite desplegar modelos GPT, Codex y embeddings con rate limits configurables.
- CosmosDB soporta vector search nativo para RAG.
- Docs oficiales: https://learn.microsoft.com/azure/
