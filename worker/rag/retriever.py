"""
RAG Retriever — hybrid search (keyword + vector) against Azure AI Search.

Supports:
  - Pure keyword search
  - Pure vector search
  - Hybrid (keyword + vector combined)

Env vars:
    AZURE_SEARCH_ENDPOINT  — Azure AI Search service endpoint
    AZURE_SEARCH_API_KEY   — Query API key
    AZURE_OPENAI_ENDPOINT  — For query embedding
    AZURE_OPENAI_API_KEY   — For query embedding
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .indexer import (
    DEFAULT_INDEX_NAME,
    generate_embeddings,
    _get_search_credentials,
)

logger = logging.getLogger("worker.rag.retriever")


def search(
    query: str,
    index_name: str = DEFAULT_INDEX_NAME,
    top: int = 5,
    mode: str = "hybrid",
    source_filter: Optional[str] = None,
    source_type_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search the index using keyword, vector, or hybrid mode.

    Args:
        query: Search query text
        index_name: Target index name
        top: Number of results to return
        mode: "keyword", "vector", or "hybrid"
        source_filter: Optional filter on source field
        source_type_filter: Optional filter on source_type field

    Returns:
        List of result dicts with id, content, title, source, score, etc.
    """
    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    from azure.core.credentials import AzureKeyCredential

    endpoint, api_key = _get_search_credentials()
    client = SearchClient(endpoint, index_name, AzureKeyCredential(api_key))

    # Build filter expression (escape single quotes per OData spec)
    filters = []
    if source_filter:
        safe_source = str(source_filter).replace("'", "''")
        filters.append(f"source eq '{safe_source}'")
    if source_type_filter:
        safe_type = str(source_type_filter).replace("'", "''")
        filters.append(f"source_type eq '{safe_type}'")
    filter_expr = " and ".join(filters) if filters else None

    # Build search kwargs
    kwargs: Dict[str, Any] = {
        "top": top,
        "select": ["id", "content", "title", "source", "source_type", "chunk_index"],
    }
    if filter_expr:
        kwargs["filter"] = filter_expr

    if mode in ("vector", "hybrid"):
        query_embedding = generate_embeddings([query])[0]
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top,
            fields="content_vector",
        )
        kwargs["vector_queries"] = [vector_query]

    if mode == "vector":
        # Pure vector: no text query
        search_text = None
    else:
        # keyword or hybrid
        search_text = query

    results = client.search(search_text=search_text, **kwargs)

    output = []
    for result in results:
        output.append({
            "id": result["id"],
            "content": result["content"],
            "title": result.get("title", ""),
            "source": result.get("source", ""),
            "source_type": result.get("source_type", ""),
            "chunk_index": result.get("chunk_index", 0),
            "score": result.get("@search.score", 0.0),
            "reranker_score": result.get("@search.reranker_score"),
        })

    logger.info(
        "Search '%s' (mode=%s, index=%s) returned %d results",
        query[:60], mode, index_name, len(output),
    )
    return output
