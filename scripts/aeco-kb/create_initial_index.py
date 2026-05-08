"""
create_initial_index.py — O16.2 sub-task 046

Crea el índice inicial vacío `aeco-kb-es-v<YYYYMMDD>` y el alias estable
`aeco-kb-es-current` apuntando a él en el AI Search service `srch-umbral-kb-prod`.

Idempotente: re-correr no rompe el alias ni el índice (siempre que schema no haya cambiado).

Auth:
    - Local: requiere `az login` activo del usuario con role `Search Service Contributor`.
    - Runtime (Container Apps Job futuro): UAMI `uami-umbral-agents-prod` ya tiene el rol.

Uso:
    python scripts/aeco-kb/create_initial_index.py [--dry-run] [--index-version vYYYYMMDD]

Validación post-deploy:
    az search index show --service-name srch-umbral-kb-prod --resource-group rg-umbral-agents-prod \
        --index-name aeco-kb-es-v20260507
    az search alias show --service-name srch-umbral-kb-prod --resource-group rg-umbral-agents-prod \
        --alias-name aeco-kb-es-current
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from azure.core.exceptions import HttpResponseError, ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchAlias,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)

# ---------------------------------------------------------------------------
# Constants — lockeado en task 045 §D3 + 046
# ---------------------------------------------------------------------------

DEFAULT_SERVICE_NAME = "srch-umbral-kb-prod"
ALIAS_NAME = "aeco-kb-es-current"
INDEX_PREFIX = "aeco-kb-es-"
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small
VECTOR_PROFILE_NAME = "hnsw-cosine"
VECTOR_ALGORITHM_NAME = "hnsw-default"
SEMANTIC_CONFIG_NAME = "default-semantic-cfg"


def build_index(index_name: str) -> SearchIndex:
    """Define el schema completo del índice AECO KB."""

    fields: list[SearchField] = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=False,
            retrievable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            retrievable=True,
            analyzer_name="es.microsoft",
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            retrievable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE_NAME,
        ),
        SimpleField(
            name="source_url",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="source_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True,
        ),
        SimpleField(
            name="jurisdiction",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True,
        ),
        SimpleField(
            name="doc_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True,
        ),
        SimpleField(
            name="version",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="lang",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="valid_from",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
            retrievable=True,
        ),
        SimpleField(
            name="valid_to",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
            retrievable=True,
        ),
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
            retrievable=True,
        ),
        SimpleField(
            name="parent_doc_id",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
        SimpleField(
            name="kb_version",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=VECTOR_ALGORITHM_NAME,
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                    metric=VectorSearchAlgorithmMetric.COSINE,
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE_NAME,
                algorithm_configuration_name=VECTOR_ALGORITHM_NAME,
            )
        ],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG_NAME,
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="source_type"),
                        SemanticField(field_name="jurisdiction"),
                        SemanticField(field_name="doc_type"),
                    ],
                ),
            )
        ]
    )

    return SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def get_endpoint() -> str:
    explicit = os.environ.get("AZURE_SEARCH_ENDPOINT")
    if explicit:
        return explicit.rstrip("/")
    service = os.environ.get("AZURE_SEARCH_SERVICE_NAME", DEFAULT_SERVICE_NAME)
    return f"https://{service}.search.windows.net"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index-version",
        default=f"v{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        help="Sufijo de versión del índice (default: vYYYYMMDD UTC).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo imprime el schema JSON sin tocar Azure.",
    )
    parser.add_argument(
        "--alias-name",
        default=ALIAS_NAME,
        help=f"Nombre del alias estable (default: {ALIAS_NAME}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    index_name = f"{INDEX_PREFIX}{args.index_version}"
    endpoint = get_endpoint()
    index = build_index(index_name)

    if args.dry_run:
        # Serializar schema (mejor esfuerzo) — no toca Azure.
        try:
            schema_dict = index.serialize()  # type: ignore[attr-defined]
        except AttributeError:
            schema_dict = {
                "name": index.name,
                "fields": [f.name for f in index.fields],
                "vector_profile": VECTOR_PROFILE_NAME,
                "semantic_config": SEMANTIC_CONFIG_NAME,
                "embedding_dimensions": EMBEDDING_DIMENSIONS,
            }
        print(json.dumps(schema_dict, indent=2, default=str))
        print(f"\n[dry-run] index={index_name} alias={args.alias_name} endpoint={endpoint}")
        return 0

    print(f"[info] endpoint={endpoint}")
    print(f"[info] index={index_name}")
    print(f"[info] alias={args.alias_name}")

    credential = DefaultAzureCredential()
    client = SearchIndexClient(endpoint=endpoint, credential=credential)

    try:
        result = client.create_or_update_index(index)
        print(f"[ok] index create_or_update → {result.name}")
    except HttpResponseError as exc:
        print(f"[error] index create_or_update falló: {exc.message}", file=sys.stderr)
        return 2

    alias = SearchAlias(name=args.alias_name, indexes=[index_name])
    try:
        client.create_or_update_alias(alias)
        print(f"[ok] alias create_or_update → {args.alias_name} → [{index_name}]")
    except ResourceExistsError as exc:
        # Algunos SDK levantan esto si el alias existe apuntando al mismo target — idempotente OK.
        print(f"[ok] alias ya existente sin cambios: {exc.message}")
    except HttpResponseError as exc:
        print(f"[error] alias create_or_update falló: {exc.message}", file=sys.stderr)
        return 3

    print("\n[done] Validar con:")
    print(
        f"  az search index show --service-name {endpoint.replace('https://', '').split('.')[0]} "
        f"--resource-group rg-umbral-agents-prod --index-name {index_name}"
    )
    print(
        f"  az search alias show --service-name {endpoint.replace('https://', '').split('.')[0]} "
        f"--resource-group rg-umbral-agents-prod --alias-name {args.alias_name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
