"""OCR tasks for scanned/image PDFs."""

import io
import tempfile
from pathlib import Path

import structlog
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

from main import app
from shared.config import load_ocr_config

logger = structlog.get_logger()


def check_ocr_needed(
    text: str,
    file_size: int,
    page_count: int,
) -> bool:
    """Check if OCR is needed based on extraction results.

    Args:
        text: Extracted text
        file_size: File size in bytes
        page_count: Number of pages

    Returns:
        True if OCR should be run
    """
    config = load_ocr_config()

    if not config.enabled:
        return False

    if config.mode != "fallback_only":
        return True

    # Calculate metrics
    char_count = len(text)
    avg_chars_per_page = char_count / max(page_count, 1)
    text_ratio = char_count / max(file_size, 1)

    needs_ocr = (
        avg_chars_per_page < config.thresholds.min_chars_per_page
        or text_ratio < config.thresholds.min_text_ratio
    )

    logger.debug(
        "OCR check",
        char_count=char_count,
        avg_chars_per_page=avg_chars_per_page,
        text_ratio=text_ratio,
        needs_ocr=needs_ocr,
    )

    return needs_ocr


def preprocess_image(image: Image.Image, config) -> Image.Image:
    """Preprocess image for better OCR results.

    Args:
        image: PIL Image
        config: OCR config

    Returns:
        Preprocessed image
    """
    preprocessing = config.preprocessing

    # Convert to grayscale
    if preprocessing.grayscale:
        image = image.convert("L")

    # Apply thresholding
    if preprocessing.threshold:
        image = image.point(lambda x: 0 if x < 128 else 255)

    return image


@app.task(bind=True, name="tasks.ocr.ocr_document")
def ocr_document(self, file_path: str) -> dict:
    """Run OCR on a PDF document.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dict with OCR text, page count, and confidence
    """
    config = load_ocr_config()
    tesseract_config = config.tesseract

    logger.info("Running OCR on document", file_path=file_path)

    try:
        # Convert PDF pages to images
        images = convert_from_path(
            file_path,
            dpi=tesseract_config.dpi,
        )

        page_texts = []
        confidences = []

        for i, image in enumerate(images):
            logger.debug("Processing page", page=i + 1, total=len(images))

            # Preprocess
            processed = preprocess_image(image, config)

            # Run OCR with detailed output
            ocr_data = pytesseract.image_to_data(
                processed,
                lang=tesseract_config.lang,
                config=f"--psm {tesseract_config.psm} --oem {tesseract_config.oem}",
                output_type=pytesseract.Output.DICT,
            )

            # Extract text and calculate confidence
            words = []
            page_confidences = []

            for j, conf in enumerate(ocr_data["conf"]):
                if conf != -1:  # -1 means no confidence (non-text)
                    conf_value = int(conf)
                    if conf_value >= config.output.min_confidence:
                        words.append(ocr_data["text"][j])
                        page_confidences.append(conf_value)

            page_text = " ".join(words)
            page_texts.append(page_text)

            if page_confidences:
                confidences.append(sum(page_confidences) / len(page_confidences))

        # Calculate overall confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Combine with page markers
        full_text_parts = []
        for i, text in enumerate(page_texts):
            full_text_parts.append(f"[PAGE {i + 1}]\n{text}")

        return {
            "text": "\n\n".join(full_text_parts),
            "page_count": len(images),
            "page_texts": page_texts,
            "confidence": avg_confidence,
            "is_ocr": True,
        }

    except Exception as e:
        logger.error("OCR failed", error=str(e), file_path=file_path)
        raise


@app.task(bind=True, name="tasks.ocr.ocr_image")
def ocr_image(self, image_path: str) -> dict:
    """Run OCR on a single image file.

    Args:
        image_path: Path to the image file

    Returns:
        Dict with OCR text and confidence
    """
    config = load_ocr_config()
    tesseract_config = config.tesseract

    logger.info("Running OCR on image", image_path=image_path)

    try:
        image = Image.open(image_path)
        processed = preprocess_image(image, config)

        # Run OCR
        ocr_data = pytesseract.image_to_data(
            processed,
            lang=tesseract_config.lang,
            config=f"--psm {tesseract_config.psm} --oem {tesseract_config.oem}",
            output_type=pytesseract.Output.DICT,
        )

        words = []
        confidences = []

        for i, conf in enumerate(ocr_data["conf"]):
            if conf != -1:
                conf_value = int(conf)
                if conf_value >= config.output.min_confidence:
                    words.append(ocr_data["text"][i])
                    confidences.append(conf_value)

        text = " ".join(words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "text": text,
            "page_count": 1,
            "page_texts": [text],
            "confidence": avg_confidence,
            "is_ocr": True,
        }

    except Exception as e:
        logger.error("Image OCR failed", error=str(e), image_path=image_path)
        raise
