"""Embedding generation and storage tasks."""

import re
import uuid
from dataclasses import dataclass

import structlog
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from main import app
from shared.config import load_embeddings_config

logger = structlog.get_logger()

# Global model instance (loaded once per worker)
_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Get or load the embedding model."""
    global _model
    if _model is None:
        config = load_embeddings_config()
        logger.info("Loading embedding model", model=config.model)
        _model = SentenceTransformer(
            config.model,
            device=config.device,
            cache_folder=config.cache_folder,
        )
    return _model


@dataclass
class Chunk:
    """A text chunk with metadata."""

    content: str
    page_start: int
    page_end: int
    chunk_index: int
    section_header: str | None = None


def semantic_chunk(
    text: str,
    page_texts: list[str],
    target_tokens: int = 1000,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    """Split text into semantic chunks with overlap.

    Args:
        text: Full document text
        page_texts: Text per page (for page tracking)
        target_tokens: Target tokens per chunk (approx 4 chars/token)
        overlap_tokens: Overlap between chunks

    Returns:
        List of chunks with metadata
    """
    # Approximate chars per token
    target_chars = target_tokens * 4
    overlap_chars = overlap_tokens * 4

    chunks = []
    chunk_index = 0

    # Split by page markers first
    page_pattern = re.compile(r"\[PAGE (\d+)\]")

    # Track current position in text
    current_pos = 0
    current_page = 1

    while current_pos < len(text):
        # Find end of chunk
        end_pos = min(current_pos + target_chars, len(text))

        # Try to break at paragraph boundary
        if end_pos < len(text):
            # Look for paragraph break near end
            search_start = max(end_pos - 200, current_pos)
            search_region = text[search_start:end_pos + 200]
            para_match = re.search(r"\n\n", search_region)
            if para_match:
                end_pos = search_start + para_match.end()

        # Extract chunk text
        chunk_text = text[current_pos:end_pos].strip()

        if not chunk_text:
            break

        # Find page range for this chunk
        chunk_pages = page_pattern.findall(chunk_text)
        if chunk_pages:
            page_start = int(chunk_pages[0])
            page_end = int(chunk_pages[-1])
        else:
            page_start = current_page
            page_end = current_page

        # Extract section header if present
        section_header = None
        header_match = re.search(r"^#+\s*(.+)$|^([A-Z][A-Z\s]+)$", chunk_text, re.MULTILINE)
        if header_match:
            section_header = (header_match.group(1) or header_match.group(2))[:255]

        chunks.append(
            Chunk(
                content=chunk_text,
                page_start=page_start,
                page_end=page_end,
                chunk_index=chunk_index,
                section_header=section_header,
            )
        )

        chunk_index += 1
        current_page = page_end

        # Move position with overlap
        current_pos = end_pos - overlap_chars

    logger.debug("Created chunks", count=len(chunks))
    return chunks


@app.task(bind=True, name="tasks.embed.embed_chunks")
def embed_chunks(self, chunks_data: list[dict]) -> dict:
    """Generate embeddings for chunks.

    Args:
        chunks_data: List of chunk dicts with 'content' key

    Returns:
        Dict with embeddings list
    """
    config = load_embeddings_config()
    model = get_embedding_model()

    logger.info("Generating embeddings", chunk_count=len(chunks_data))

    texts = [c["content"] for c in chunks_data]

    embeddings = model.encode(
        texts,
        batch_size=config.batch_size,
        normalize_embeddings=config.normalize,
        show_progress_bar=config.show_progress and len(texts) > 10,
    )

    return {
        "embeddings": embeddings.tolist(),
        "model": config.model,
        "dimension": config.dimension,
    }


@app.task(bind=True, name="tasks.embed.chunk_and_embed")
def chunk_and_embed(
    self,
    text: str,
    page_texts: list[str],
    is_ocr: bool = False,
) -> dict:
    """Chunk document and generate embeddings.

    Args:
        text: Full document text
        page_texts: Text per page
        is_ocr: Whether text came from OCR

    Returns:
        Dict with chunks and embeddings
    """
    config = load_embeddings_config()
    model = get_embedding_model()

    # Create chunks
    chunks = semantic_chunk(text, page_texts)

    logger.info(
        "Chunking and embedding",
        chunk_count=len(chunks),
        is_ocr=is_ocr,
    )

    # Generate embeddings
    texts = [c.content for c in chunks]
    embeddings = model.encode(
        texts,
        batch_size=config.batch_size,
        normalize_embeddings=config.normalize,
        show_progress_bar=config.show_progress and len(texts) > 10,
    )

    # Combine chunks with embeddings
    result_chunks = []
    for chunk, embedding in zip(chunks, embeddings):
        result_chunks.append({
            "content": chunk.content,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "chunk_index": chunk.chunk_index,
            "section_header": chunk.section_header,
            "is_ocr": is_ocr,
            "embedding": embedding.tolist(),
            "token_count": len(chunk.content) // 4,  # Approximate
        })

    return {
        "chunks": result_chunks,
        "model": config.model,
        "dimension": config.dimension,
    }
