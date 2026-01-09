"""E2E test for W-2 document pipeline."""

from pathlib import Path

import pytest


@pytest.mark.skipif(
    not Path("tests/golden/w2_sample.pdf").exists(),
    reason="W-2 sample PDF not found in tests/golden/",
)
class TestW2Pipeline:
    """End-to-end tests for W-2 document processing."""

    def test_w2_extraction(self, sample_w2_path: Path):
        """Test that W-2 text extraction works."""
        # Import here to avoid issues if dependencies not installed
        from services.worker.tasks.extract import extract_pdf

        result = extract_pdf(str(sample_w2_path))

        assert result["page_count"] >= 1
        assert len(result["text"]) > 0
        assert len(result["page_texts"]) == result["page_count"]

    def test_w2_canonicalization(self, sample_w2_path: Path):
        """Test W-2 canonicalization."""
        from services.worker.tasks.extract import extract_pdf
        from services.worker.tasks.canonicalize import canonicalize_document

        # Extract first
        extract_result = extract_pdf(str(sample_w2_path))

        # Then canonicalize
        canonical_result = canonicalize_document(
            extract_result["page_texts"],
            is_ocr=False,
        )

        assert len(canonical_result["text"]) > 0
        assert len(canonical_result["page_texts"]) == extract_result["page_count"]

    def test_w2_chunking_and_embedding(self, sample_w2_path: Path):
        """Test W-2 chunking and embedding."""
        from services.worker.tasks.extract import extract_pdf
        from services.worker.tasks.canonicalize import canonicalize_document
        from services.worker.tasks.embed import chunk_and_embed

        # Extract and canonicalize
        extract_result = extract_pdf(str(sample_w2_path))
        canonical_result = canonicalize_document(
            extract_result["page_texts"],
            is_ocr=False,
        )

        # Chunk and embed
        embed_result = chunk_and_embed(
            canonical_result["text"],
            canonical_result["page_texts"],
            is_ocr=False,
        )

        assert len(embed_result["chunks"]) > 0
        assert embed_result["model"] is not None
        assert embed_result["dimension"] > 0

        # Check each chunk has an embedding
        for chunk in embed_result["chunks"]:
            assert "embedding" in chunk
            assert len(chunk["embedding"]) == embed_result["dimension"]
            assert chunk["page_start"] >= 1
            assert chunk["page_end"] >= chunk["page_start"]

    def test_w2_searchable_after_ingestion(self, sample_w2_path: Path, db_session):
        """Test that W-2 is searchable after full pipeline."""
        # This test requires the full ingestion to run
        # and would search for employer name or wages
        pytest.skip("Full ingestion test requires running worker")
