"""
Tasks: RAG (Retrieval-Augmented Generation) with Azure AI Search.

- rag.index: Index documents into Azure AI Search with vector embeddings.
- rag.search: Hybrid search (keyword + vector) against the index.
- rag.query: Search + LLM-synthesized answer from retrieved context.
- rag.ensure_index: Create or update the index schema.

All tasks require AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY.
Embedding tasks require AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from worker.rag.indexer import ensure_index, index_documents
from worker.rag.retriever import search
from .llm import handle_llm_generate

logger = logging.getLogger("worker.tasks.rag")

RAG_SYSTEM_PROMPT = (
    "You are a knowledgeable assistant. Answer the user's question using ONLY "
    "the provided context. If the context doesn't contain enough information, "
    "say so clearly — do not fabricate information.\n\n"
    "Respond in the same language as the question.\n\n"
    "Context:\n{context}"
)


def handle_rag_ensure_index(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create or update the search index schema.

    Input:
        index_name (str, optional): Index name (default: umbral-knowledge).

    Returns:
        {"index_name": "...", "fields": N}
    """
    index_name = str(input_data.get("index_name", "")).strip() or None
    kwargs: Dict[str, Any] = {}
    if index_name:
        kwargs["index_name"] = index_name
    return ensure_index(**kwargs)


def handle_rag_index(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Index documents into Azure AI Search with embeddings.

    Input:
        documents (list[dict], required): List of documents to index.
            Each document: {content, title?, source?, source_type?}
        index_name (str, optional): Target index (default: umbral-knowledge).
        chunk_size (int, optional): Characters per chunk (default: 1000).
        chunk_overlap (int, optional): Overlap between chunks (default: 200).

    Returns:
        {"indexed": N, "chunks": N, "documents": N, "errors": [...]}
    """
    documents = input_data.get("documents")
    if not documents or not isinstance(documents, list):
        raise ValueError("'documents' is required and must be a non-empty list")

    index_name = str(input_data.get("index_name", "")).strip() or None
    chunk_size = int(input_data.get("chunk_size", 1000))
    chunk_overlap = int(input_data.get("chunk_overlap", 200))

    kwargs: Dict[str, Any] = {
        "documents": documents,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    if index_name:
        kwargs["index_name"] = index_name

    return index_documents(**kwargs)


def handle_rag_search(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hybrid search against the Azure AI Search index.

    Input:
        query (str, required): Search query.
        top (int, optional): Number of results (default: 5, max: 20).
        mode (str, optional): "keyword", "vector", or "hybrid" (default: "hybrid").
        index_name (str, optional): Target index (default: umbral-knowledge).
        source_filter (str, optional): Filter by source field.
        source_type_filter (str, optional): Filter by source_type field.

    Returns:
        {"results": [...], "count": N, "query": "...", "mode": "..."}
    """
    query = str(input_data.get("query", "")).strip()
    if not query:
        raise ValueError("'query' is required and cannot be empty")

    top = min(int(input_data.get("top", 5)), 20)
    mode = str(input_data.get("mode", "hybrid")).strip()
    if mode not in ("keyword", "vector", "hybrid"):
        mode = "hybrid"

    index_name = str(input_data.get("index_name", "")).strip() or None
    source_filter = input_data.get("source_filter")
    source_type_filter = input_data.get("source_type_filter")

    kwargs: Dict[str, Any] = {
        "query": query,
        "top": top,
        "mode": mode,
    }
    if index_name:
        kwargs["index_name"] = index_name
    if source_filter:
        kwargs["source_filter"] = str(source_filter)
    if source_type_filter:
        kwargs["source_type_filter"] = str(source_type_filter)

    results = search(**kwargs)
    return {
        "results": results,
        "count": len(results),
        "query": query,
        "mode": mode,
    }


def handle_rag_query(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    RAG query: search for context + generate answer with LLM.

    Input:
        question (str, required): Natural language question.
        top (int, optional): Number of context chunks to retrieve (default: 5).
        mode (str, optional): Search mode — "keyword"|"vector"|"hybrid" (default: "hybrid").
        model (str, optional): LLM model for answer generation (default: azure_foundry).
        index_name (str, optional): Target index (default: umbral-knowledge).
        source_filter (str, optional): Filter by source.
        source_type_filter (str, optional): Filter by source_type.
        max_tokens (int, optional): Max tokens for LLM answer (default: 1024).

    Returns:
        {"answer": "...", "sources": [...], "model": "...", "search_results": N}
    """
    question = str(input_data.get("question", "")).strip()
    if not question:
        raise ValueError("'question' is required and cannot be empty")

    top = min(int(input_data.get("top", 5)), 20)
    mode = str(input_data.get("mode", "hybrid")).strip()
    if mode not in ("keyword", "vector", "hybrid"):
        mode = "hybrid"
    model = str(input_data.get("model", "azure_foundry")).strip()
    max_tokens = int(input_data.get("max_tokens", 1024))

    index_name = str(input_data.get("index_name", "")).strip() or None
    source_filter = input_data.get("source_filter")
    source_type_filter = input_data.get("source_type_filter")

    # Step 1: Retrieve context
    search_kwargs: Dict[str, Any] = {
        "query": question,
        "top": top,
        "mode": mode,
    }
    if index_name:
        search_kwargs["index_name"] = index_name
    if source_filter:
        search_kwargs["source_filter"] = str(source_filter)
    if source_type_filter:
        search_kwargs["source_type_filter"] = str(source_type_filter)

    results = search(**search_kwargs)

    # Step 2: Build context from results
    context_parts = []
    sources = []
    for r in results:
        context_parts.append(
            f"[Source: {r['source']}]\n{r['content']}"
        )
        if r["source"] not in sources:
            sources.append(r["source"])

    context = "\n\n---\n\n".join(context_parts) if context_parts else "(No relevant context found)"

    # Step 3: Generate answer
    llm_result = handle_llm_generate({
        "prompt": question,
        "system": RAG_SYSTEM_PROMPT.format(context=context),
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    })

    return {
        "answer": llm_result.get("text", ""),
        "sources": sources,
        "model": llm_result.get("model", model),
        "search_results": len(results),
    }
