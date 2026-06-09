import json
import os
import re
from datetime import date
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv

from .parser import ParsedItem, ParsedReceipt


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env", override=True)


def extract_receipt_from_image(
    image_bytes: bytes,
    mime_type: str | None = None,
) -> tuple[str, ParsedReceipt]:
    """Extract structured receipt data using Gemini."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Create a valid Gemini API key in Google AI Studio, "
            "put it in backend/.env, and restart the backend."
        )

    try:
        from google import genai
        from google.genai import errors, types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed. Run `pip install -r requirements.txt` "
            "from the backend directory."
        ) from exc

    gemini_image_bytes, gemini_mime_type = prepare_image_for_gemini(image_bytes, mime_type)
    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=gemini_image_bytes, mime_type=gemini_mime_type),
                GEMINI_RECEIPT_PROMPT,
            ],
        )
    except errors.APIError as exc:
        raise RuntimeError(gemini_api_error_message(exc)) from exc
    except Exception as exc:
        raise RuntimeError(gemini_request_error_message(exc)) from exc

    raw_response = response.text or ""
    data = parse_gemini_json(raw_response)
    parsed = parsed_receipt_from_gemini_data(data)
    return receipt_text_from_parsed_receipt(parsed), parsed


def gemini_config_status() -> dict[str, str | bool | int]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    return {
        "has_api_key": bool(api_key),
        "api_key_length": len(api_key),
        "api_key_prefix": api_key[:6] if api_key else "",
        "api_key_suffix": api_key[-4:] if api_key else "",
        "model": model,
    }


GEMINI_RECEIPT_PROMPT = """Extract grocery receipt data from this image.

Return only valid JSON with this exact shape:
{
  "store_name": string | null,
  "store_location_text": string | null,
  "purchased_at": "YYYY-MM-DD" | null,
  "items": [
    {
      "name": string,
      "quantity": string | null,
      "unit": string | null,
      "unit_price": number | null,
      "unit_price_unit": string | null,
      "price": number,
      "source_line": string | null
    }
  ]
}

Rules:
- Do not include phone numbers.
- Ignore subtotal, total, tax, bottle deposit, environmental fee, bag fee, payment, change, and return policy lines.
- For weighted produce, quantity is the purchased weight and unit_price is the receipt's price per unit.
- For count pricing like "3 @ $0.69", quantity is "3", unit is "ct", unit_price is 0.69, and price is the final line total after discounts.
- Keep abbreviated item names as seen if uncertain.
- If a value is unclear, use null rather than guessing.
"""


def prepare_image_for_gemini(
    image_bytes: bytes,
    mime_type: str | None,
) -> tuple[bytes, str]:
    normalized_mime_type = (mime_type or "").split(";")[0].lower()
    if normalized_mime_type in {"image/jpeg", "image/png", "image/webp"}:
        return image_bytes, normalized_mime_type

    try:
        from PIL import Image
        from pillow_heif import register_heif_opener

        register_heif_opener()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        output = BytesIO()
        image.save(output, format="JPEG", quality=92)
        return output.getvalue(), "image/jpeg"
    except Exception:
        if normalized_mime_type.startswith("image/"):
            return image_bytes, normalized_mime_type
        return image_bytes, "image/jpeg"


def gemini_api_error_message(exc: Exception) -> str:
    message = str(exc)
    if "API_KEY_INVALID" in message or "API key not valid" in message:
        return (
            "Gemini rejected GEMINI_API_KEY as invalid. Replace the value in backend/.env "
            "with a valid Google AI Studio API key, then restart the backend."
        )
    if "PERMISSION_DENIED" in message:
        return "Gemini API permission denied. Check that the API key has access to the Gemini API."
    if "RESOURCE_EXHAUSTED" in message:
        return "Gemini API quota exceeded or rate limited. Try again later or check billing/quota."
    return f"Gemini OCR request failed: {message}"


def gemini_request_error_message(exc: Exception) -> str:
    message = str(exc)
    if "nodename nor servname provided" in message or "Name or service not known" in message:
        return (
            "Could not reach the Gemini API host. Check your internet connection, DNS, "
            "VPN/proxy settings, and that generativelanguage.googleapis.com is reachable."
        )
    if "timed out" in message.lower():
        return "Gemini OCR request timed out. Try again or use a smaller receipt image."
    return f"Gemini OCR request failed before a response was returned: {message}"


def parse_gemini_json(raw_response: str) -> dict:
    stripped = raw_response.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini did not return valid receipt JSON.") from exc

    if not isinstance(data, dict):
        raise RuntimeError("Gemini receipt response was not a JSON object.")
    return data


def parsed_receipt_from_gemini_data(data: dict) -> ParsedReceipt:
    items = []
    for raw_item in data.get("items") or []:
        if not isinstance(raw_item, dict):
            continue
        name = clean_string(raw_item.get("name"))
        price = clean_float(raw_item.get("price"))
        if not name or price is None:
            continue

        items.append(
            ParsedItem(
                line=clean_string(raw_item.get("source_line")) or name,
                name=name,
                quantity=clean_optional_string(raw_item.get("quantity")),
                unit=clean_optional_string(raw_item.get("unit")),
                unit_price=clean_float(raw_item.get("unit_price")),
                unit_price_unit=clean_optional_string(raw_item.get("unit_price_unit")),
                price=price,
            )
        )

    return ParsedReceipt(
        store_name=clean_string(data.get("store_name")) or "Unknown Store",
        store_location_text=clean_optional_string(data.get("store_location_text")),
        purchased_at=clean_date(data.get("purchased_at")),
        items=items,
    )


def receipt_text_from_parsed_receipt(parsed: ParsedReceipt) -> str:
    lines = [parsed.store_name]
    if parsed.store_location_text:
        lines.append(parsed.store_location_text)
    if parsed.purchased_at:
        lines.append(parsed.purchased_at.isoformat())
    for item in parsed.items:
        lines.append(item.line or f"{item.name} {item.price:.2f}")
    return "\n".join(lines)


def clean_string(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def clean_optional_string(value) -> str | None:
    cleaned = clean_string(value)
    return cleaned or None


def clean_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_date(value) -> date | None:
    cleaned = clean_string(value)
    if not cleaned:
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        return None
