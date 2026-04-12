"""
RAG Indexer — manages Azure AI Search index + document upload with embeddings.

Env vars:
    AZURE_SEARCH_ENDPOINT  — Azure AI Search service endpoint
    AZURE_SEARCH_API_KEY   — Admin API key for index operations
    AZURE_OPENAI_ENDPOINT  — For embedding generation
    AZURE_OPENAI_API_KEY   — For embedding generation
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT — Embedding model deployment name
                                        (default: text-embedding-3-large)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger("worker.rag.indexer")

DEFAULT_INDEX_NAME = "umbral-knowledge"
DEFAULT_EMBEDDING_DEPLOYMENT = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072  # text-embedding-3-large
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"


def _get_search_credentials() -> tuple[str, str]:
    """Return (endpoint, api_key) for Azure AI Search."""
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "").strip()
    api_key = os.environ.get("AZURE_SEARCH_API_KEY", "").strip()
    if not endpoint or not api_key:
        raise EnvironmentError(
            "AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set."
        )
    return endpoint, api_key


def _get_embedding_config() -> tuple[str, str, str]:
    """Return (endpoint, api_key, deployment) for Azure OpenAI embeddings."""
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    deployment = os.environ.get(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", DEFAULT_EMBEDDING_DEPLOYMENT
    ).strip()
    if not endpoint or not api_key:
        raise EnvironmentError(
            "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set for embeddings."
        )
    return endpoint, api_key, deployment


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings via Azure OpenAI embeddings API."""
    endpoint, api_key, deployment = _get_embedding_config()

    url = (
        f"{endpoint.rstrip('/')}/openai/deployments/{deployment}"
        f"/embeddings?api-version={AZURE_OPENAI_API_VERSION}"
    )
    payload = json.dumps({"input": texts}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # Sort by index to maintain order
    sorted_data = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in sorted_data]


def ensure_index(index_name: str = DEFAULT_INDEX_NAME) -> Dict[str, Any]:
    """Create or update the search index with vector search profile."""
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SearchField,
        SearchFieldDataType,
        SearchableField,
        SimpleField,
        VectorSearch,
        HnswAlgorithmConfiguration,
        VectorSearchProfile,
    )
    from azure.core.credentials import AzureKeyCredential

    endpoint, api_key = _get_search_credentials()
    client = SearchIndexClient(endpoint, AzureKeyCredential(api_key))

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            analyzer_name="standard.lucene",
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            analyzer_name="standard.lucene",
        ),
        SimpleField(
            name="source",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="source_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="chunk_index",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="default-vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="default-hnsw"),
        ],
        profiles=[
            VectorSearchProfile(
                name="default-vector-profile",
                algorithm_configuration_name="default-hnsw",
            ),
        ],
    )

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
    )

    result = client.create_or_update_index(index)
    logger.info("Index '%s' ensured (fields=%d)", result.name, len(result.fields))
    return {"index_name": result.name, "fields": len(result.fields)}


def _make_doc_id(source: str, chunk_index: int) -> str:
    """Deterministic document ID from source + chunk index."""
    raw = f"{source}::chunk::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks by character count."""
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


def index_documents(
    documents: List[Dict[str, Any]],
    index_name: str = DEFAULT_INDEX_NAME,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> Dict[str, Any]:
    """
    Chunk, embed, and upload documents to Azure AI Search.

    Each document dict should have:
        content (str, required): Full text content
        title (str, optional): Document title
        source (str, optional): Source identifier (URL, file path, etc.)
        source_type (str, optional): Category (notion, file, web, etc.)

    Returns summary with counts.
    """
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential

    endpoint, api_key = _get_search_credentials()
    search_client = SearchClient(endpoint, index_name, AzureKeyCredential(api_key))

    # Chunk all documents
    all_chunks: List[Dict[str, Any]] = []
    for doc in documents:
        content = str(doc.get("content", "")).strip()
        if not content:
            continue
        title = str(doc.get("title", "")).strip()
        source = str(doc.get("source", "unknown")).strip()
        source_type = str(doc.get("source_type", "unknown")).strip()

        chunks = chunk_text(content, chunk_size, chunk_overlap)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "content": chunk,
                "title": title,
                "source": source,
                "source_type": source_type,
                "chunk_index": i,
                "_doc_id_source": source,
            })

    if not all_chunks:
        return {"indexed": 0, "chunks": 0, "errors": []}

    # Generate embeddings in batches of 16
    batch_size = 16
    for batch_start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[batch_start : batch_start + batch_size]
        texts = [c["content"] for c in batch]
        embeddings = generate_embeddings(texts)
        for chunk, embedding in zip(batch, embeddings):
            chunk["content_vector"] = embedding

    # Upload to index
    upload_docs = []
    for chunk in all_chunks:
        doc_id = _make_doc_id(chunk["_doc_id_source"], chunk["chunk_index"])
        upload_docs.append({
            "id": doc_id,
            "content": chunk["content"],
            "title": chunk["title"],
            "source": chunk["source"],
            "source_type": chunk["source_type"],
            "chunk_index": chunk["chunk_index"],
            "content_vector": chunk["content_vector"],
        })

    # Upload in batches of 100
    errors: List[str] = []
    indexed = 0
    for batch_start in range(0, len(upload_docs), 100):
        batch = upload_docs[batch_start : batch_start + 100]
        try:
            result = search_client.upload_documents(batch)
            for r in result:
                if r.succeeded:
                    indexed += 1
                else:
                    errors.append(f"{r.key}: {r.error_message}")
        except Exception as e:
            errors.append(f"Batch upload error: {e}")

    logger.info(
        "Indexed %d chunks from %d documents into '%s' (%d errors)",
        indexed, len(documents), index_name, len(errors),
    )
    return {
        "indexed": indexed,
        "chunks": len(all_chunks),
        "documents": len(documents),
        "errors": errors[:10],  # cap error list
    }
