"""
Tests for RAG module: indexer, retriever, and task handlers.

All Azure AI Search and embedding calls are mocked.
"""

import pytest
import sys
import types
from unittest.mock import patch, MagicMock, ANY


# ---------------------------------------------------------------------------
# Indexer helpers
# ---------------------------------------------------------------------------


class TestChunkText:
    """Tests for chunk_text helper."""

    def test_empty_text(self):
        from worker.rag.indexer import chunk_text
        assert chunk_text("") == []

    def test_short_text_single_chunk(self):
        from worker.rag.indexer import chunk_text
        result = chunk_text("Hello world", chunk_size=100, overlap=20)
        assert len(result) == 1
        assert result[0] == "Hello world"

    def test_long_text_multiple_chunks(self):
        from worker.rag.indexer import chunk_text
        text = "A" * 2500
        result = chunk_text(text, chunk_size=1000, overlap=200)
        assert len(result) >= 3
        # Each chunk should be at most chunk_size
        for chunk in result:
            assert len(chunk) <= 1000

    def test_overlap_between_chunks(self):
        from worker.rag.indexer import chunk_text
        text = "0123456789" * 30  # 300 chars
        result = chunk_text(text, chunk_size=100, overlap=20)
        # With overlap, later chunks should start before previous ended
        assert len(result) >= 3


class TestMakeDocId:
    """Tests for _make_doc_id helper."""

    def test_deterministic(self):
        from worker.rag.indexer import _make_doc_id
        id1 = _make_doc_id("source.md", 0)
        id2 = _make_doc_id("source.md", 0)
        assert id1 == id2

    def test_different_for_different_chunks(self):
        from worker.rag.indexer import _make_doc_id
        id0 = _make_doc_id("source.md", 0)
        id1 = _make_doc_id("source.md", 1)
        assert id0 != id1

    def test_length(self):
        from worker.rag.indexer import _make_doc_id
        doc_id = _make_doc_id("test", 0)
        assert len(doc_id) == 32  # SHA-256 truncated to 32 hex chars


class TestGenerateEmbeddings:
    """Tests for generate_embeddings with mocked HTTP."""

    @patch("worker.rag.indexer.urllib.request.urlopen")
    def test_returns_embeddings_in_order(self, mock_urlopen):
        from worker.rag.indexer import generate_embeddings
        import json
        import os

        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com"
        os.environ["AZURE_OPENAI_API_KEY"] = "test-key"

        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "data": [
                {"index": 1, "embedding": [0.2, 0.3]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = generate_embeddings(["text1", "text2"])
        assert len(result) == 2
        assert result[0] == [0.1, 0.2]  # sorted by index
        assert result[1] == [0.2, 0.3]

    def test_missing_env_raises(self):
        from worker.rag.indexer import generate_embeddings
        import os

        os.environ.pop("AZURE_OPENAI_ENDPOINT", None)
        os.environ.pop("AZURE_OPENAI_API_KEY", None)

        with pytest.raises(EnvironmentError, match="AZURE_OPENAI"):
            generate_embeddings(["test"])


# ---------------------------------------------------------------------------
# Retriever search
# ---------------------------------------------------------------------------


class _FakeVectorizedQuery:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeAzureKeyCredential:
    def __init__(self, key):
        self.key = key


class TestRetrieverSearch:
    @pytest.fixture
    def retriever_setup(self, monkeypatch):
        from worker.rag import retriever

        azure_module = types.ModuleType("azure")
        azure_search_module = types.ModuleType("azure.search")
        azure_documents_module = types.ModuleType("azure.search.documents")
        azure_models_module = types.ModuleType("azure.search.documents.models")
        azure_core_module = types.ModuleType("azure.core")
        azure_credentials_module = types.ModuleType("azure.core.credentials")

        search_client_instance = MagicMock()
        search_client_class = MagicMock(return_value=search_client_instance)

        azure_documents_module.SearchClient = search_client_class
        azure_models_module.VectorizedQuery = _FakeVectorizedQuery
        azure_credentials_module.AzureKeyCredential = _FakeAzureKeyCredential

        azure_module.search = azure_search_module
        azure_search_module.documents = azure_documents_module
        azure_documents_module.models = azure_models_module
        azure_module.core = azure_core_module
        azure_core_module.credentials = azure_credentials_module

        monkeypatch.setitem(sys.modules, "azure", azure_module)
        monkeypatch.setitem(sys.modules, "azure.search", azure_search_module)
        monkeypatch.setitem(sys.modules, "azure.search.documents", azure_documents_module)
        monkeypatch.setitem(sys.modules, "azure.search.documents.models", azure_models_module)
        monkeypatch.setitem(sys.modules, "azure.core", azure_core_module)
        monkeypatch.setitem(sys.modules, "azure.core.credentials", azure_credentials_module)

        mock_creds = MagicMock(return_value=("https://search.example", "secret-key"))
        mock_embeddings = MagicMock(return_value=[[0.1, 0.2, 0.3]])
        monkeypatch.setattr(retriever, "_get_search_credentials", mock_creds)
        monkeypatch.setattr(retriever, "generate_embeddings", mock_embeddings)

        return retriever, search_client_class, search_client_instance, mock_embeddings

    def test_keyword_mode_skips_embeddings_and_maps_defaults(self, retriever_setup):
        retriever, _, search_client_instance, mock_embeddings = retriever_setup
        search_client_instance.search.return_value = [
            {"id": "doc-1", "content": "Result content"},
        ]

        result = retriever.search(query="cement ratio", mode="keyword", top=2)

        assert result == [{
            "id": "doc-1",
            "content": "Result content",
            "title": "",
            "source": "",
            "source_type": "",
            "chunk_index": 0,
            "score": 0.0,
            "reranker_score": None,
        }]
        mock_embeddings.assert_not_called()
        assert search_client_instance.search.call_args.kwargs["search_text"] == "cement ratio"
        assert "vector_queries" not in search_client_instance.search.call_args.kwargs

    def test_vector_mode_uses_vector_query_and_no_search_text(self, retriever_setup):
        retriever, _, search_client_instance, mock_embeddings = retriever_setup
        search_client_instance.search.return_value = []

        retriever.search(query="thermal bridge", mode="vector", top=3)

        mock_embeddings.assert_called_once_with(["thermal bridge"])
        kwargs = search_client_instance.search.call_args.kwargs
        assert kwargs["search_text"] is None
        assert len(kwargs["vector_queries"]) == 1
        vector_query = kwargs["vector_queries"][0]
        assert isinstance(vector_query, _FakeVectorizedQuery)
        assert vector_query.kwargs["k_nearest_neighbors"] == 3
        assert vector_query.kwargs["fields"] == "content_vector"

    def test_hybrid_mode_escapes_odata_filters(self, retriever_setup):
        retriever, _, search_client_instance, mock_embeddings = retriever_setup
        search_client_instance.search.return_value = []

        retriever.search(
            query="spec",
            mode="hybrid",
            source_filter="manual'o",
            source_type_filter="doc's",
        )

        mock_embeddings.assert_called_once_with(["spec"])
        kwargs = search_client_instance.search.call_args.kwargs
        assert kwargs["search_text"] == "spec"
        assert kwargs["filter"] == "source eq 'manual''o' and source_type eq 'doc''s'"


# ---------------------------------------------------------------------------
# Task handlers
# ---------------------------------------------------------------------------


SEARCH_PATCH = "worker.tasks.rag.search"
INDEX_PATCH = "worker.tasks.rag.index_documents"
ENSURE_PATCH = "worker.tasks.rag.ensure_index"
LLM_PATCH = "worker.tasks.rag.handle_llm_generate"


class TestRagEnsureIndex:
    """Tests for handle_rag_ensure_index."""

    @patch(ENSURE_PATCH)
    def test_default_index(self, mock_ensure):
        from worker.tasks.rag import handle_rag_ensure_index

        mock_ensure.return_value = {"index_name": "umbral-knowledge", "fields": 7}
        result = handle_rag_ensure_index({})

        assert result["index_name"] == "umbral-knowledge"
        mock_ensure.assert_called_once()

    @patch(ENSURE_PATCH)
    def test_custom_index_name(self, mock_ensure):
        from worker.tasks.rag import handle_rag_ensure_index

        mock_ensure.return_value = {"index_name": "custom", "fields": 7}
        result = handle_rag_ensure_index({"index_name": "custom"})

        mock_ensure.assert_called_once_with(index_name="custom")


class TestRagIndex:
    """Tests for handle_rag_index."""

    @patch(INDEX_PATCH)
    def test_indexes_documents(self, mock_index):
        from worker.tasks.rag import handle_rag_index

        mock_index.return_value = {
            "indexed": 5, "chunks": 5, "documents": 2, "errors": []
        }

        result = handle_rag_index({
            "documents": [
                {"content": "Hello world", "title": "Test"},
                {"content": "More text", "source": "test.md"},
            ]
        })

        assert result["indexed"] == 5
        mock_index.assert_called_once()

    def test_missing_documents_raises(self):
        from worker.tasks.rag import handle_rag_index

        with pytest.raises(ValueError, match="documents"):
            handle_rag_index({})

    def test_empty_documents_raises(self):
        from worker.tasks.rag import handle_rag_index

        with pytest.raises(ValueError, match="documents"):
            handle_rag_index({"documents": []})


class TestRagSearch:
    """Tests for handle_rag_search."""

    @patch(SEARCH_PATCH)
    def test_basic_search(self, mock_search):
        from worker.tasks.rag import handle_rag_search

        mock_search.return_value = [
            {"id": "1", "content": "Result 1", "title": "T1",
             "source": "s1", "source_type": "file", "chunk_index": 0,
             "score": 0.9, "reranker_score": None},
        ]

        result = handle_rag_search({"query": "test query"})

        assert result["count"] == 1
        assert result["query"] == "test query"
        assert result["mode"] == "hybrid"
        mock_search.assert_called_once_with(query="test query", top=5, mode="hybrid")

    @patch(SEARCH_PATCH)
    def test_search_with_filters(self, mock_search):
        from worker.tasks.rag import handle_rag_search

        mock_search.return_value = []

        handle_rag_search({
            "query": "notion",
            "mode": "vector",
            "top": 10,
            "source_type_filter": "notion",
        })

        mock_search.assert_called_once_with(
            query="notion", top=10, mode="vector",
            source_type_filter="notion",
        )

    def test_empty_query_raises(self):
        from worker.tasks.rag import handle_rag_search

        with pytest.raises(ValueError, match="query"):
            handle_rag_search({"query": ""})

    @patch(SEARCH_PATCH)
    def test_invalid_mode_defaults_hybrid(self, mock_search):
        from worker.tasks.rag import handle_rag_search

        mock_search.return_value = []
        result = handle_rag_search({"query": "test", "mode": "invalid"})
        assert result["mode"] == "hybrid"


class TestRagQuery:
    """Tests for handle_rag_query (search + LLM)."""

    @patch(LLM_PATCH)
    @patch(SEARCH_PATCH)
    def test_basic_rag_query(self, mock_search, mock_llm):
        from worker.tasks.rag import handle_rag_query

        mock_search.return_value = [
            {"id": "1", "content": "Worker runs on port 8088",
             "title": "Architecture", "source": "docs/arch.md",
             "source_type": "file", "chunk_index": 0,
             "score": 0.95, "reranker_score": None},
        ]
        mock_llm.return_value = {
            "text": "El Worker corre en el puerto 8088.",
            "model": "gpt-5.4",
            "usage": {},
        }

        result = handle_rag_query({"question": "¿En qué puerto corre el Worker?"})

        assert "8088" in result["answer"]
        assert result["sources"] == ["docs/arch.md"]
        assert result["search_results"] == 1
        # Verify LLM received the context
        llm_call = mock_llm.call_args[0][0]
        assert "Worker runs on port 8088" in llm_call["system"]
        assert llm_call["temperature"] == 0.3

    @patch(LLM_PATCH)
    @patch(SEARCH_PATCH)
    def test_no_results_still_generates(self, mock_search, mock_llm):
        from worker.tasks.rag import handle_rag_query

        mock_search.return_value = []
        mock_llm.return_value = {
            "text": "No tengo información suficiente.",
            "model": "gpt-5.4",
            "usage": {},
        }

        result = handle_rag_query({"question": "Unknown topic?"})

        assert result["search_results"] == 0
        assert result["sources"] == []
        # LLM should get the "no context" message
        llm_call = mock_llm.call_args[0][0]
        assert "No relevant context found" in llm_call["system"]

    @patch(LLM_PATCH)
    @patch(SEARCH_PATCH)
    def test_deduplicates_sources(self, mock_search, mock_llm):
        from worker.tasks.rag import handle_rag_query

        mock_search.return_value = [
            {"id": "1", "content": "chunk 1", "title": "", "source": "a.md",
             "source_type": "file", "chunk_index": 0, "score": 0.9, "reranker_score": None},
            {"id": "2", "content": "chunk 2", "title": "", "source": "a.md",
             "source_type": "file", "chunk_index": 1, "score": 0.8, "reranker_score": None},
            {"id": "3", "content": "chunk 3", "title": "", "source": "b.md",
             "source_type": "file", "chunk_index": 0, "score": 0.7, "reranker_score": None},
        ]
        mock_llm.return_value = {"text": "Answer", "model": "gpt-5.4", "usage": {}}

        result = handle_rag_query({"question": "test"})

        assert result["sources"] == ["a.md", "b.md"]  # deduplicated, order preserved

    def test_empty_question_raises(self):
        from worker.tasks.rag import handle_rag_query

        with pytest.raises(ValueError, match="question"):
            handle_rag_query({"question": ""})


class TestTaskRegistration:
    """Verify RAG tasks are in TASK_HANDLERS."""

    def test_rag_tasks_registered(self):
        from worker.tasks import TASK_HANDLERS

        rag_tasks = [k for k in TASK_HANDLERS if k.startswith("rag.")]
        assert sorted(rag_tasks) == [
            "rag.ensure_index",
            "rag.index",
            "rag.query",
            "rag.search",
        ]

    def test_total_handler_count(self):
        from worker.tasks import TASK_HANDLERS
        assert len(TASK_HANDLERS) == 102
