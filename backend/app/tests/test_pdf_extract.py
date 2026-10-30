import io

import pytest
from reportlab.pdfgen import canvas

from app.services.pdf_extract import MAX_PDF_BYTES, PdfExtractionError, extract_text_from_pdf


def _make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 700, text)
    c.save()
    return buf.getvalue()


def test_extracts_text_from_real_pdf():
    pdf_bytes = _make_pdf("Jane Doe - Senior Engineer at Acme")
    text = extract_text_from_pdf(pdf_bytes)
    assert "Jane Doe" in text


def test_rejects_empty_file():
    with pytest.raises(PdfExtractionError, match="Empty"):
        extract_text_from_pdf(b"")


def test_rejects_oversized_file():
    with pytest.raises(PdfExtractionError, match="exceeds"):
        extract_text_from_pdf(b"0" * (MAX_PDF_BYTES + 1))


def test_rejects_non_pdf_bytes():
    with pytest.raises(PdfExtractionError, match="Could not parse"):
        extract_text_from_pdf(b"not a real pdf")
