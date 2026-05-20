import io
from pathlib import Path

import fitz
import pytesseract
from PIL import Image, ImageOps

MAX_PDF_PAGES = 4

# Tesseract language string for Arabic + English
_TESSERACT_LANG = "ara+eng"


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from a CV file.

    Supports:
      - PDF  → reads embedded text layer; falls back to Tesseract OCR if the PDF is a scan
      - JPG / JPEG / PNG → Tesseract OCR with Arabic + English language support

    Raises ValueError for unsupported formats or unreadable files.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return _extract_from_pdf(file_bytes)
    elif suffix in {".jpg", ".jpeg", ".png"}:
        return _extract_from_image(file_bytes)
    else:
        raise ValueError(
            f"Unsupported format '{suffix}'. Accepted: PDF, JPG, JPEG, PNG."
        )


def _extract_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    if doc.page_count > MAX_PDF_PAGES:
        doc.close()
        raise ValueError(
            f"PDF has {doc.page_count} pages. Maximum allowed is {MAX_PDF_PAGES} pages."
        )

    pages_text = [page.get_text("text") for page in doc]
    doc.close()

    full_text = "\n".join(pages_text).strip()

    # If the text layer is nearly empty, the PDF is likely a scan — use OCR
    if len(full_text) < 100:
        return _extract_from_pdf_via_ocr(file_bytes)

    return full_text


def _extract_from_pdf_via_ocr(file_bytes: bytes) -> str:
    """Render each PDF page to an image then run Tesseract OCR on it."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[str] = []

    for page in doc:
        # 200 DPI gives good OCR accuracy without being too slow
        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes(
            "RGB", (pix.width, pix.height), pix.samples
        )
        text = pytesseract.image_to_string(img, lang=_TESSERACT_LANG)
        pages.append(text)

    doc.close()
    return "\n".join(pages)


def _extract_from_image(file_bytes: bytes) -> str:
    """
    Extract text from a JPG/PNG image.
    Pillow normalises the image first (fixes phone-camera EXIF rotation)
    before handing off to Tesseract.
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = ImageOps.exif_transpose(
            img
        )  # fix upside-down phone photos
        img = img.convert("RGB")
    except Exception as exc:
        raise ValueError(f"Could not open image: {exc}") from exc

    return pytesseract.image_to_string(img, lang=_TESSERACT_LANG)
