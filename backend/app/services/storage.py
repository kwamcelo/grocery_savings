from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from ..db import BASE_DIR


UPLOAD_DIR = BASE_DIR / "data" / "uploads"
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}


def save_upload(file: UploadFile, image_bytes: bytes) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        suffix = ".jpg"

    destination = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    destination.write_bytes(image_bytes)
    return destination
