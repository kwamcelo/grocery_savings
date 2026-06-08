import os
from io import BytesIO


PLACEHOLDER_RECEIPT_TEXT = """Fresh Market
2026-06-01
Bananas 1.24
Milk 2L 5.49
Eggs dozen 4.79
Spinach 3.29
"""


def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract receipt text.

    Set USE_TESSERACT=true after installing the Tesseract binary locally.
    The placeholder keeps the API working during local setup and tests.
    """
    if os.getenv("USE_TESSERACT", "").lower() != "true":
        return os.getenv("PLACEHOLDER_OCR_TEXT", PLACEHOLDER_RECEIPT_TEXT)

    try:
        from PIL import Image
        import pytesseract

        image = Image.open(BytesIO(image_bytes))
        return pytesseract.image_to_string(image)
    except Exception as exc:
        raise RuntimeError(
            "Tesseract OCR failed. Confirm the tesseract binary is installed "
            "or unset USE_TESSERACT to use placeholder OCR."
        ) from exc
