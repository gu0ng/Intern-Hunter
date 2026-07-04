from io import BytesIO

from pypdf import PdfReader


class PdfExtractionError(RuntimeError):
    pass


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF upload before sending it to an LLM parser."""
    if not pdf_bytes:
        raise PdfExtractionError("Uploaded PDF is empty.")
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
    except Exception as exc:
        raise PdfExtractionError(f"Failed to extract PDF text: {exc}") from exc

    text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
    if not text:
        raise PdfExtractionError("No selectable text was extracted from the PDF. Scanned PDFs need OCR support.")
    return text
