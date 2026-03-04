---
name: google-cloud-vertex
description: >-
  Use Google Cloud Vertex AI and the Gemini API for text generation, embeddings,
  multimodal inputs, model tuning, and deployment via Python SDK.
  Use when "vertex ai", "gemini api", "google cloud ai", "embeddings vertex",
  "imagen", "gemini model", "google ai studio", "vertex deploy".
metadata:
  openclaw:
    emoji: "\U0001F48E"
    requires:
      env:
        - GOOGLE_API_KEY_RICK_UMBRAL
        - GOOGLE_CLOUD_PROJECT_RICK_UMBRAL
---

# Google Cloud / Vertex AI Skill

Generar texto, embeddings e imágenes con Gemini y Vertex AI, tanto desde Google AI Studio (API key) como desde Vertex AI (proyecto GCP).

## Requisitos

| Variable | Descripción |
|----------|-------------|
| `GOOGLE_API_KEY_RICK_UMBRAL` | API key de Google AI Studio |
| `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL` | Proyecto GCP para Vertex AI |

### Instalación

```bash
pip install google-genai google-cloud-aiplatform
gcloud auth application-default login
gcloud config set project $GOOGLE_CLOUD_PROJECT_RICK_UMBRAL
```

> **Nota:** `google-cloud-aiplatform` será deprecado en mayo 2026. Google recomienda migrar a `google-genai`.

## 1. Google AI Studio — Gemini con API key

La forma más rápida de usar Gemini. No requiere proyecto GCP.

```python
from google import genai

client = genai.Client(api_key=GOOGLE_API_KEY)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explicá qué es Vertex AI en 3 líneas.",
)
print(response.text)
```

### Streaming

```python
for chunk in client.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="Escribí un poema sobre la nube.",
):
    print(chunk.text, end="")
```

## 2. Vertex AI — Gemini con proyecto GCP

Para uso enterprise con IAM, VPC, logging y billing por proyecto.

```python
from google import genai

client = genai.Client(
    vertexai=True,
    project="mi-proyecto",
    location="us-central1",
)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Analizá este dataset de ventas.",
)
print(response.text)
```

### SDK Legacy (google-cloud-aiplatform)

```python
import vertexai
from vertexai.generative_models import GenerativeModel

vertexai.init(project="mi-proyecto", location="us-central1")
model = GenerativeModel("gemini-2.5-pro")
response = model.generate_content("Tu prompt aquí")
print(response.text)
```

## 3. Embeddings

### Con google-genai

```python
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents="Texto a embeddear",
)
vector = result.embeddings[0].values  # list[float], hasta 3072 dims
```

### Con Vertex AI SDK legacy

```python
from vertexai.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("text-embedding-005")
embeddings = model.get_embeddings(["Texto a embeddear"])
vector = embeddings[0].values  # 768 dims
```

### Modelos de embedding disponibles

| Modelo | Dims | Notas |
|--------|------|-------|
| `gemini-embedding-001` | 3072 | State-of-the-art, multilingüe |
| `text-embedding-005` | 768 | Inglés/código |
| `text-multilingual-embedding-002` | 768 | Multilingüe |

## 4. Multimodal — Imagen + Texto

```python
import PIL.Image

img = PIL.Image.open("plano.png")
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[img, "Describí qué ves en esta imagen."],
)
print(response.text)
```

## 5. Imagen — Generación de imágenes

```python
from vertexai.preview.vision_models import ImageGenerationModel

model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
images = model.generate_images(
    prompt="Logo minimalista de un agente AI",
    number_of_images=1,
    aspect_ratio="1:1",
)
images[0].save("logo.png")
```

## 6. gcloud CLI — Comandos útiles

```bash
gcloud ai models list --region=us-central1
gcloud ai endpoints list --region=us-central1
gcloud ai endpoints predict ENDPOINT_ID --region=us-central1 --json-request=input.json
gcloud services enable aiplatform.googleapis.com
```

## Modelos Gemini disponibles

| Modelo | Caso de uso |
|--------|-------------|
| `gemini-2.5-pro` | Razonamiento complejo, coding |
| `gemini-2.5-flash` | Rápido y barato, tareas simples |
| `gemini-2.5-flash-lite` | Ultra-rápido, latencia mínima |

## Notas

- Rick ya tiene `GOOGLE_API_KEY_RICK_UMBRAL` y `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL` configurados.
- AI Studio es para prototyping rápido; Vertex AI es para producción con controles enterprise.
- El alias `gemini_vertex` en `llm.generate` de Rick enruta automáticamente a Vertex AI.
- Docs: https://cloud.google.com/vertex-ai/docs | https://ai.google.dev/gemini-api/docs
