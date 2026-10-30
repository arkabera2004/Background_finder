import io

import pdfplumber


class PdfExtractionError(ValueError):
    pass


MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB, per project plan


def extract_text_from_pdf(data: bytes) -> str:
    if len(data) > MAX_PDF_BYTES:
        raise PdfExtractionError(f"PDF exceeds {MAX_PDF_BYTES} byte limit")
    if not data:
        raise PdfExtractionError("Empty file")

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:  # noqa: BLE001 - any parse failure is a user-facing extraction error
        raise PdfExtractionError(f"Could not parse PDF: {exc}") from exc

    text = "\n".join(pages_text).strip()
    if not text:
        raise PdfExtractionError("No extractable text found in PDF (scanned image PDFs are not supported)")
    return text
