import os
from io import BytesIO
from shutil import which


PLACEHOLDER_RECEIPT_TEXT = """Fresh Market
123 Main St Vancouver BC V6B 1A1
604-555-0101
2026-06-01
Bananas 1.24
Milk 2L 5.49
Eggs dozen 4.79
Spinach 3.29
"""


def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract receipt text.

    OCR_PROVIDER=tesseract is the default for local development.
    Set OCR_PROVIDER=placeholder only when you intentionally want demo text.
    """
    provider = os.getenv("OCR_PROVIDER", "tesseract").strip().lower()
    if provider == "placeholder":
        return os.getenv("PLACEHOLDER_OCR_TEXT", PLACEHOLDER_RECEIPT_TEXT)
    if provider != "tesseract":
        raise RuntimeError(f"Unsupported OCR_PROVIDER '{provider}'. Use 'tesseract' or 'placeholder'.")

    if not which("tesseract"):
        raise RuntimeError(
            "Tesseract is not installed or is not on PATH. Install it with "
            "`brew install tesseract`, then restart the backend. To use demo text "
            "instead, set OCR_PROVIDER=placeholder."
        )

    try:
        from PIL import Image
        from pillow_heif import register_heif_opener
        import pytesseract

        register_heif_opener()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return pytesseract.image_to_string(image)
    except Exception as exc:
        raise RuntimeError(
            "Tesseract OCR failed. Confirm the tesseract binary is installed "
            "and that the uploaded image format is supported."
        ) from exc
