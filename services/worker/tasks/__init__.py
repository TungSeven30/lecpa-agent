"""Celery tasks for document processing pipeline."""

from tasks.ingest import ingest_document
from tasks.extract import extract_pdf, extract_docx, extract_xlsx
from tasks.canonicalize import canonicalize_document
from tasks.ocr import ocr_document, check_ocr_needed
from tasks.embed import embed_chunks

__all__ = [
    "ingest_document",
    "extract_pdf",
    "extract_docx",
    "extract_xlsx",
    "canonicalize_document",
    "ocr_document",
    "check_ocr_needed",
    "embed_chunks",
]
