"""
pdf_parser.py — O16.2 sub-task 047

Parser de PDFs AECO usando Azure Document Intelligence prebuilt-layout.
Lee un blob desde `stumbralagentsprod/crudos/aeco/raw/{source_type}/{doc_id}.pdf`,
lo manda a DI, chunkea párrafo-aware y escribe JSONL en
`stumbralagentsprod/crudos/aeco/parsed/{source_type}/{doc_id}.chunks.jsonl`.

Idempotente: skip si el output existe con el mismo `parser_version`, salvo `--force`.

Auth: DefaultAzureCredential
    - Local: az login (usuario con `Cognitive Services User` + `Storage Blob Data Contributor`)
    - Container Apps Job: UAMI `uami-umbral-agents-prod` (RBAC ya asignado en O16.1)

Uso CLI:
    python -m scripts.aeco_kb.pdf_parser \\
        --blob-path aeco/raw/buildingsmart/IFC4.3.2.0-sample.pdf \\
        --source-type buildingsmart --jurisdiction intl \\
        --doc-type spec --version IFC4.3.2.0 --lang es

Variables de entorno (override blob path para Container Apps Job):
    DI_ENDPOINT              (default: https://di-umbral-prod.cognitiveservices.azure.com/)
    STORAGE_ACCOUNT          (default: stumbralagentsprod)
    INPUT_CONTAINER          (default: crudos)
    OUTPUT_CONTAINER         (default: crudos)
    INPUT_BLOB_PATH          (override de --blob-path)
    SOURCE_TYPE, JURISDICTION, DOC_TYPE, VERSION, LANG, SOURCE_URL
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Iterator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aeco-pdf-parser")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARSER_VERSION = "v1.0.0"  # Bump cuando cambie chunking o DI model
DI_MODEL_ID = "prebuilt-layout"  # Lockeado en task 047 §D7

DEFAULT_DI_ENDPOINT = "https://di-umbral-prod.cognitiveservices.azure.com/"
DEFAULT_STORAGE_ACCOUNT = "stumbralagentsprod"
DEFAULT_INPUT_CONTAINER = "crudos"
DEFAULT_OUTPUT_CONTAINER = "crudos"

# Chunking targets (aproximado por whitespace tokens, NO tiktoken)
TOKEN_TARGET_MIN = 50
TOKEN_TARGET_MAX = 800
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
SUPPORTED_RAW_EXTENSIONS = {".pdf", ".html", ".htm", ".txt", ".exp", ".md"}
TEXT_RAW_EXTENSIONS = {".html", ".htm", ".txt", ".exp", ".md"}
SOURCE_DEFAULTS = {
    "buildingsmart": {"jurisdiction": "intl", "doc_type": "spec", "lang": "en"},
    "minvu": {"jurisdiction": "cl", "doc_type": "regulation", "lang": "es"},
    "iram": {"jurisdiction": "ar", "doc_type": "regulation", "lang": "es"},
    "nmx": {"jurisdiction": "mx", "doc_type": "regulation", "lang": "es"},
}


# ---------------------------------------------------------------------------
# Chunk model — alineado con schema del índice (task 046)
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    id: str
    content: str
    source_url: str | None
    source_type: str
    jurisdiction: str
    doc_type: str
    version: str | None
    lang: str
    valid_from: str | None
    valid_to: str | None
    chunk_id: int
    parent_doc_id: str
    kb_version: str | None  # Lo setea 049 al publicar
    # Metadata propia del parser (no va al índice — separamos al serializar)
    parser_version: str = field(default=PARSER_VERSION)
    parser_metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Token estimation (heuristic)
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Aproximación rápida: words * 1.3 (no tiktoken)."""
    return int(len(text.split()) * 1.3)


# ---------------------------------------------------------------------------
# Chunking strategy (task 047 §D8)
# ---------------------------------------------------------------------------


def chunk_paragraphs(paragraphs: list[str], headings: dict[int, str]) -> Iterator[str]:
    """
    Estrategia párrafo-aware:
    - Si párrafo > TOKEN_TARGET_MAX: split por sentencia + recombine.
    - Si párrafo < TOKEN_TARGET_MIN: merge con siguiente.
    - Heading inmediatamente anterior se prepend como contexto markdown.
    """
    buffer = ""
    buffer_tokens = 0
    for idx, raw in enumerate(paragraphs):
        text = raw.strip()
        if not text:
            continue

        prefix = ""
        heading = headings.get(idx)
        if heading:
            prefix = f"## {heading.strip()}\n\n"

        tokens = estimate_tokens(text)

        if tokens > TOKEN_TARGET_MAX:
            # Flush buffer first
            if buffer:
                yield buffer.strip()
                buffer = ""
                buffer_tokens = 0
            # Split por sentencia
            sentences = SENTENCE_SPLIT_RE.split(text)
            cur = prefix
            cur_tokens = estimate_tokens(prefix)
            for sent in sentences:
                s_tok = estimate_tokens(sent)
                if cur_tokens + s_tok > TOKEN_TARGET_MAX and cur.strip():
                    yield cur.strip()
                    cur = ""
                    cur_tokens = 0
                cur = (cur + " " + sent).strip() if cur else sent
                cur_tokens += s_tok
            if cur.strip():
                yield cur.strip()
            continue

        # Párrafo cabe — buffer logic
        candidate = (buffer + "\n\n" + prefix + text).strip() if buffer else (prefix + text)
        candidate_tokens = buffer_tokens + tokens + estimate_tokens(prefix)
        if candidate_tokens >= TOKEN_TARGET_MIN and candidate_tokens <= TOKEN_TARGET_MAX:
            yield candidate
            buffer = ""
            buffer_tokens = 0
        elif candidate_tokens > TOKEN_TARGET_MAX:
            # Buffer + nuevo párrafo se pasaron — flush buffer y arrancar nuevo
            if buffer:
                yield buffer.strip()
            buffer = prefix + text
            buffer_tokens = tokens + estimate_tokens(prefix)
        else:
            # Sigue chico — acumular
            buffer = candidate
            buffer_tokens = candidate_tokens

    if buffer.strip():
        yield buffer.strip()


# ---------------------------------------------------------------------------
# Text/HTML parsing and DI invocation
# ---------------------------------------------------------------------------


class _HTMLTextExtractor(HTMLParser):
    """Small stdlib-only HTML text extractor for standards pages."""

    block_tags = {
        "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
        "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5",
        "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre",
        "section", "table", "td", "th", "tr", "ul",
    }
    skip_tags = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        tag = tag.lower()
        if tag in self.skip_tags:
            self._skip_depth += 1
            return
        if self._skip_depth == 0 and tag in self.block_tags:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth == 0 and tag in self.block_tags:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def _html_to_text(raw: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    parser.close()
    return parser.text()


def _split_text_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    blocks = [
        re.sub(r"\n+", "\n", block).strip()
        for block in re.split(r"\n\s*\n+", text)
    ]
    return [
        block
        for block in blocks
        if len(block.split()) >= 3 or (block and len(block) <= 120 and not block.endswith("."))
    ]


def parse_text_bytes(content: bytes, blob_path: str) -> tuple[list[str], dict[int, str], list[str]]:
    """Parse HTML/text raw docs without Azure Document Intelligence."""
    raw = content.decode("utf-8", errors="ignore")
    suffix = PurePosixPath(blob_path).suffix.lower()
    text = _html_to_text(raw) if suffix in {".html", ".htm"} else raw
    paragraphs = _split_text_blocks(text)
    log.info("Text parser extracted %d blocks from %s", len(paragraphs), blob_path)
    return paragraphs, {}, []


def is_supported_raw_blob(blob_path: str) -> bool:
    return PurePosixPath(blob_path).suffix.lower() in SUPPORTED_RAW_EXTENSIONS


def is_text_raw_blob(blob_path: str) -> bool:
    return PurePosixPath(blob_path).suffix.lower() in TEXT_RAW_EXTENSIONS


def default_lang_from_env() -> str | None:
    for name in ("AECO_LANG", "DOC_LANG", "LANG"):
        value = os.environ.get(name, "").strip()
        if re.fullmatch(r"[a-z]{2}", value, flags=re.IGNORECASE):
            return value.lower()
    return None


def parse_pdf_with_di(
    pdf_bytes: bytes,
    di_endpoint: str,
    credential,
) -> tuple[list[str], dict[int, str], list[str]]:
    """
    Invoca DI prebuilt-layout. Devuelve:
      - paragraphs: lista de strings (en reading order)
      - headings: dict {paragraph_index: heading_text} para párrafos que vienen después de un heading
      - tables_md: tablas serializadas a markdown (1 por entrada)
    """
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

    client = DocumentIntelligenceClient(endpoint=di_endpoint, credential=credential)
    log.info("Submitting PDF (%d bytes) to DI %s", len(pdf_bytes), DI_MODEL_ID)
    poller = client.begin_analyze_document(
        model_id=DI_MODEL_ID,
        body=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
    )
    result = poller.result()

    paragraphs: list[str] = []
    headings: dict[int, str] = {}
    last_heading: str | None = None

    for para in result.paragraphs or []:
        text = (para.content or "").strip()
        if not text:
            continue
        role = getattr(para, "role", None)
        if role in ("title", "sectionHeading", "pageHeader"):
            last_heading = text
            continue
        if last_heading:
            headings[len(paragraphs)] = last_heading
            last_heading = None
        paragraphs.append(text)

    tables_md: list[str] = []
    for tbl in result.tables or []:
        try:
            tables_md.append(_table_to_markdown(tbl))
        except Exception as exc:  # pragma: no cover — defensive
            log.warning("Failed to serialize table: %s", exc)

    log.info(
        "DI parsed: %d paragraphs, %d headings, %d tables",
        len(paragraphs),
        len(headings),
        len(tables_md),
    )
    return paragraphs, headings, tables_md


def _table_to_markdown(table) -> str:
    """Serializa una tabla DI a markdown."""
    rows = max(c.row_index for c in table.cells) + 1
    cols = max(c.column_index for c in table.cells) + 1
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    for cell in table.cells:
        grid[cell.row_index][cell.column_index] = (cell.content or "").replace("|", "\\|").strip()
    if not rows:
        return ""
    header = "| " + " | ".join(grid[0]) + " |"
    sep = "| " + " | ".join(["---"] * cols) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in grid[1:])
    return "\n".join([header, sep, body]).strip()


# ---------------------------------------------------------------------------
# Storage I/O
# ---------------------------------------------------------------------------


def get_blob_service(account: str, credential):
    from azure.storage.blob import BlobServiceClient

    return BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net", credential=credential
    )


def download_blob(account: str, container: str, blob_path: str, credential) -> bytes:
    svc = get_blob_service(account, credential)
    blob = svc.get_blob_client(container=container, blob=blob_path)
    log.info("Downloading blob %s/%s", container, blob_path)
    return blob.download_blob().readall()


def list_raw_blobs(account: str, container: str, source_type: str, credential) -> list[str]:
    svc = get_blob_service(account, credential)
    container_client = svc.get_container_client(container)
    prefix = f"aeco/raw/{source_type}/"
    blob_names: list[str] = []
    for blob in container_client.list_blobs(name_starts_with=prefix):
        if is_supported_raw_blob(blob.name):
            blob_names.append(blob.name)
    blob_names.sort()
    return blob_names


def load_raw_manifest(account: str, container: str, source_type: str, credential) -> dict[str, dict]:
    svc = get_blob_service(account, credential)
    blob = svc.get_blob_client(container=container, blob=f"aeco/raw/_manifest/{source_type}.jsonl")
    if not blob.exists():
        return {}
    raw = blob.download_blob().readall().decode("utf-8", errors="ignore")
    manifest: dict[str, dict] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        doc_id = item.get("doc_id")
        if doc_id:
            manifest[doc_id] = item
    return manifest


def upload_jsonl(
    account: str,
    container: str,
    blob_path: str,
    chunks: list[Chunk],
    credential,
    doc_metadata: dict | None = None,
) -> None:
    svc = get_blob_service(account, credential)
    blob = svc.get_blob_client(container=container, blob=blob_path)
    buf = io.StringIO()
    for c in chunks:
        # Strip parser-only fields antes de serializar para el índice
        idx_doc = {k: v for k, v in asdict(c).items() if k not in ("parser_version", "parser_metadata")}
        # Conservar parser_version como header en una linea metadata? No — lo embebemos
        # como sidecar `_meta` campo del primer chunk para idempotencia.
        buf.write(json.dumps(idx_doc, ensure_ascii=False) + "\n")
    # Header line con metadata del parser (primera línea = "_meta")
    meta = {
        "parser_version": PARSER_VERSION,
        "model": DI_MODEL_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if doc_metadata:
        meta.update({k: v for k, v in doc_metadata.items() if v is not None})
    full = json.dumps({"_meta": meta}, ensure_ascii=False) + "\n" + buf.getvalue()
    blob.upload_blob(full.encode("utf-8"), overwrite=True)
    log.info("Uploaded %d chunks → %s/%s", len(chunks), container, blob_path)


def existing_parser_version(
    account: str, container: str, blob_path: str, credential
) -> str | None:
    """Retorna el parser_version del output existente, o None si no existe."""
    svc = get_blob_service(account, credential)
    blob = svc.get_blob_client(container=container, blob=blob_path)
    if not blob.exists():
        return None
    # Bajar solo primera línea (~256 bytes) para chequear _meta
    try:
        head = blob.download_blob(offset=0, length=512).readall().decode("utf-8")
        first_line = head.split("\n", 1)[0]
        meta = json.loads(first_line).get("_meta", {})
        return meta.get("parser_version")
    except Exception as exc:
        log.warning("Could not read existing _meta: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(
    blob_path: str,
    source_type: str,
    jurisdiction: str,
    doc_type: str,
    version: str | None,
    lang: str,
    source_url: str | None,
    valid_from: str | None,
    di_endpoint: str,
    storage_account: str,
    input_container: str,
    output_container: str,
    force: bool,
    dry_run: bool,
) -> int:
    from azure.identity import DefaultAzureCredential

    p = PurePosixPath(blob_path)
    parent_doc_id = p.stem
    output_path = f"aeco/parsed/{source_type}/{parent_doc_id}.chunks.jsonl"

    credential = DefaultAzureCredential()

    if not is_supported_raw_blob(blob_path):
        log.error("Unsupported raw blob extension for %s", blob_path)
        return 2

    if not force:
        existing = existing_parser_version(storage_account, output_container, output_path, credential)
        if existing == PARSER_VERSION:
            log.info("Skip: %s already parsed with %s (use --force to re-parse)", output_path, existing)
            return 0

    pdf_bytes = download_blob(storage_account, input_container, blob_path, credential)

    if is_text_raw_blob(blob_path):
        paragraphs, headings, tables_md = parse_text_bytes(pdf_bytes, blob_path)
    else:
        paragraphs, headings, tables_md = parse_pdf_with_di(pdf_bytes, di_endpoint, credential)

    chunks: list[Chunk] = []
    for idx, text in enumerate(chunk_paragraphs(paragraphs, headings)):
        chunks.append(
            Chunk(
                id=f"{source_type}__{parent_doc_id}__c{idx:04d}",
                content=text,
                source_url=source_url,
                source_type=source_type,
                jurisdiction=jurisdiction,
                doc_type=doc_type,
                version=version,
                lang=lang,
                valid_from=valid_from,
                valid_to=None,
                chunk_id=idx,
                parent_doc_id=parent_doc_id,
                kb_version=None,  # Lo setea 049
            )
        )

    # Tablas como chunks separados al final
    base_chunk_count = len(chunks)
    for tidx, tbl_md in enumerate(tables_md):
        chunks.append(
            Chunk(
                id=f"{source_type}__{parent_doc_id}__t{tidx:04d}",
                content=tbl_md,
                source_url=source_url,
                source_type=source_type,
                jurisdiction=jurisdiction,
                doc_type=doc_type,
                version=version,
                lang=lang,
                valid_from=valid_from,
                valid_to=None,
                chunk_id=base_chunk_count + tidx,
                parent_doc_id=parent_doc_id,
                kb_version=None,
                parser_metadata={"is_table": True},
            )
        )

    log.info("Generated %d chunks (%d text + %d tables)", len(chunks), base_chunk_count, len(tables_md))

    if dry_run:
        for c in chunks[:3]:
            print(json.dumps(asdict(c), ensure_ascii=False, indent=2))
        print(f"\n[dry-run] {len(chunks)} chunks → would upload to {output_container}/{output_path}")
        return 0

    upload_jsonl(
        storage_account,
        output_container,
        output_path,
        chunks,
        credential,
        doc_metadata={
            "doc_id": parent_doc_id,
            "source_url": source_url,
            "source_type": source_type,
            "jurisdiction": jurisdiction,
            "doc_type": doc_type,
            "version": version,
            "lang": lang,
            "valid_from": valid_from,
        },
    )
    return 0


def run_source(
    source_type: str,
    jurisdiction: str,
    doc_type: str,
    version: str | None,
    lang: str,
    di_endpoint: str,
    storage_account: str,
    input_container: str,
    output_container: str,
    force: bool,
    dry_run: bool,
) -> int:
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    blob_paths = list_raw_blobs(storage_account, input_container, source_type, credential)
    if not blob_paths:
        log.error("No supported raw blobs found under aeco/raw/%s/", source_type)
        return 1

    manifest = load_raw_manifest(storage_account, input_container, source_type, credential)
    failures = 0
    for blob_path in blob_paths:
        doc_id = PurePosixPath(blob_path).stem
        item = manifest.get(doc_id, {})
        rc = run(
            blob_path=blob_path,
            source_type=source_type,
            jurisdiction=jurisdiction,
            doc_type=doc_type,
            version=item.get("version") or version,
            lang=item.get("default_lang") or lang,
            source_url=item.get("source_url"),
            valid_from=item.get("valid_from"),
            di_endpoint=di_endpoint,
            storage_account=storage_account,
            input_container=input_container,
            output_container=output_container,
            force=force,
            dry_run=dry_run,
        )
        if rc != 0:
            failures += 1
    return 0 if failures == 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blob-path", default=os.environ.get("INPUT_BLOB_PATH"), help="Ruta del PDF dentro del container input.")
    parser.add_argument("--source-type", default=os.environ.get("SOURCE_TYPE"), choices=["buildingsmart", "minvu", "iram", "nmx"])
    parser.add_argument("--jurisdiction", default=os.environ.get("JURISDICTION"), choices=["intl", "cl", "ar", "mx"])
    parser.add_argument("--doc-type", default=os.environ.get("DOC_TYPE"), choices=["spec", "regulation", "guide"])
    parser.add_argument("--version", default=os.environ.get("VERSION"))
    parser.add_argument("--lang", default=default_lang_from_env())
    parser.add_argument("--source-url", default=os.environ.get("SOURCE_URL"))
    parser.add_argument("--valid-from", default=os.environ.get("VALID_FROM"))
    parser.add_argument("--di-endpoint", default=os.environ.get("DI_ENDPOINT", DEFAULT_DI_ENDPOINT))
    parser.add_argument("--storage-account", default=os.environ.get("STORAGE_ACCOUNT", DEFAULT_STORAGE_ACCOUNT))
    parser.add_argument("--input-container", default=os.environ.get("INPUT_CONTAINER", DEFAULT_INPUT_CONTAINER))
    parser.add_argument("--output-container", default=os.environ.get("OUTPUT_CONTAINER", DEFAULT_OUTPUT_CONTAINER))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    defaults = SOURCE_DEFAULTS.get(args.source_type or "", {})
    args.jurisdiction = args.jurisdiction or defaults.get("jurisdiction")
    args.doc_type = args.doc_type or defaults.get("doc_type")
    args.lang = args.lang or defaults.get("lang") or "es"

    missing = [n for n in ("source_type", "jurisdiction", "doc_type") if not getattr(args, n)]
    if missing:
        parser.error(f"missing required arguments: {missing}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.blob_path:
        return run_source(
            source_type=args.source_type,
            jurisdiction=args.jurisdiction,
            doc_type=args.doc_type,
            version=args.version,
            lang=args.lang,
            di_endpoint=args.di_endpoint,
            storage_account=args.storage_account,
            input_container=args.input_container,
            output_container=args.output_container,
            force=args.force,
            dry_run=args.dry_run,
        )
    return run(
        blob_path=args.blob_path,
        source_type=args.source_type,
        jurisdiction=args.jurisdiction,
        doc_type=args.doc_type,
        version=args.version,
        lang=args.lang,
        source_url=args.source_url,
        valid_from=args.valid_from,
        di_endpoint=args.di_endpoint,
        storage_account=args.storage_account,
        input_container=args.input_container,
        output_container=args.output_container,
        force=args.force,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
