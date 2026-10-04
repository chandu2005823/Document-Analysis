import logging
import os
from pathlib import Path

import pymupdf


logger = logging.getLogger(__name__)
MIN_MEANINGFUL_TEXT_CHARS = 20


def _has_meaningful_text(text):
    return sum(character.isalnum() for character in text) >= MIN_MEANINGFUL_TEXT_CHARS


def _ocr_page(page):
    """OCR one PyMuPDF page. Set TESSERACT_CMD to the executable path on Windows."""
    from io import BytesIO

    import pytesseract
    from PIL import Image

    # Example on Windows: set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
    tesseract_cmd = os.environ.get("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    rendered_page = page.get_pixmap(dpi=300)
    with Image.open(BytesIO(rendered_page.tobytes("png"))) as image:
        return pytesseract.image_to_string(image).strip()


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF while preserving page numbers.

    Pages with fewer than 20 alphanumeric text characters use OCR. OCR requires
    pytesseract, Pillow, and the Tesseract executable. On Windows, configure the
    executable with the TESSERACT_CMD environment variable.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    document = pymupdf.open(pdf_path)

    pages = []

    try:
        for page_number, page in enumerate(document, start=1):
            try:
                text = (page.get_text("text") or "").strip()
            except Exception as error:
                logger.warning("Text extraction failed on page %d: %s", page_number, error)
                text = ""

            extraction_method = "text"
            if not _has_meaningful_text(text):
                extraction_method = "ocr"
                try:
                    text = (_ocr_page(page) or "").strip()
                except Exception as error:
                    logger.warning("OCR failed on page %d: %s", page_number, error)
                    text = ""

            pages.append({
                "page_number": page_number,
                "text": text,
                "extraction_method": extraction_method,
            })
    finally:
        document.close()

    return pages


if __name__ == "__main__":

    pdf_file = "data/documents/AUTOSAR_AP_EXP_SWArchitecture.pdf"

    pages = extract_text_from_pdf(pdf_file)

    print(f"Total pages extracted: {len(pages)}")

    for page in pages[:3]:

        print("\n" + "=" * 60)
        print(f"PAGE {page['page_number']}")
        print("=" * 60)

        if page["text"]:
            print(page["text"][:1000])
        else:
            print("[NO TEXT EXTRACTED]")