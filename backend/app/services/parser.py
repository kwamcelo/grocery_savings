import re
from dataclasses import dataclass
from datetime import date, datetime


PRICE_PATTERN = re.compile(
    r"(?P<name>.*?)(?P<price>\$?\d+(?:[.,]\d{2}))\s*(?:[A-Z]{1,3})?\s*$"
)
DATE_PATTERNS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y")
SKIP_WORDS = {
    "bottle deposit",
    "change",
    "debit",
    "env. fee",
    "gst",
    "mastercard",
    "multiple item",
    "pst",
    "ps",
    "subtotal",
    "sub total",
    "tax",
    "total",
    "visa",
    "vitsu",
}
STREET_PATTERN = re.compile(
    r"\b\d{1,6}\s+.+\b(st|street|ave|avenue|rd|road|dr|drive|blvd|boulevard|way|lane|ln|hwy|highway)\b",
    re.I,
)
POSTAL_PATTERN = re.compile(
    r"\b([A-Z]\d[A-Z]\s?\d[A-Z]\d|\d{5}(?:-\d{4})?)\b",
    re.I,
)


@dataclass
class ParsedItem:
    line: str
    name: str
    quantity: str | None
    unit: str | None
    unit_price: float | None
    unit_price_unit: str | None
    price: float


@dataclass
class ParsedReceipt:
    store_name: str
    store_location_text: str | None
    purchased_at: date | None
    items: list[ParsedItem]


def parse_receipt_text(raw_text: str) -> ParsedReceipt:
    lines = [normalize_line(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    purchased_at = next((parsed for line in lines if (parsed := parse_date(line))), None)
    store_name = infer_store_name(lines)
    store_location_text = infer_store_location(lines, store_name)
    items = parse_item_lines(lines)

    return ParsedReceipt(
        store_name=store_name,
        store_location_text=store_location_text,
        purchased_at=purchased_at,
        items=items,
    )


def parse_item_lines(lines: list[str]) -> list[ParsedItem]:
    items = []
    pending_name: str | None = None

    for line in lines:
        item = parse_item_line(line, fallback_name=pending_name)
        if item:
            items.append(item)
            pending_name = None
            continue

        if is_possible_continuation_name(line) and should_update_pending_name(pending_name, line):
            pending_name = line

    return items


def normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


def infer_store_name(lines: list[str]) -> str:
    for line in reversed(lines):
        match = re.search(r"shopping at\s+(?P<store>.+)$", line, re.I)
        if match:
            return normalize_store_name(match.group("store"))

    for line in lines[:5]:
        if (
            not parse_date(line)
            and not PRICE_PATTERN.search(line)
            and not looks_like_location_line(line)
            and not looks_like_noise_line(line)
        ):
            return normalize_store_name(line)
    return "Unknown Store"


def infer_store_location(lines: list[str], store_name: str) -> str | None:
    location_lines = []
    for line in lines[:10]:
        if line == store_name or parse_date(line) or PRICE_PATTERN.search(line):
            continue
        if looks_like_location_line(line):
            location_lines.append(line)

    return ", ".join(location_lines) if location_lines else None


def looks_like_location_line(line: str) -> bool:
    lowered = line.lower()
    return bool(
        STREET_PATTERN.search(line)
        or POSTAL_PATTERN.search(line)
        or re.search(r"\b(suite|unit|vancouver|bc|canada)\b", lowered)
    )


def looks_like_noise_line(line: str) -> bool:
    alpha_count = sum(character.isalpha() for character in line)
    if alpha_count < 3:
        return True
    meaningful_count = sum(character.isalnum() or character.isspace() for character in line)
    return meaningful_count / max(len(line), 1) < 0.65


def normalize_store_name(store_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 &'’-]+", " ", store_name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" '’")
    return cleaned or "Unknown Store"


def parse_date(line: str) -> date | None:
    for token in re.split(r"\s+", line):
        cleaned = token.strip(".,")
        for pattern in DATE_PATTERNS:
            try:
                return datetime.strptime(cleaned, pattern).date()
            except ValueError:
                continue
    return None


def parse_item_line(line: str, fallback_name: str | None = None) -> ParsedItem | None:
    lowered = line.lower()
    if any(word in lowered for word in SKIP_WORDS):
        return None

    match = PRICE_PATTERN.match(line.replace(",", "."))
    if not match:
        return None

    raw_name = match.group("name").strip(" -:\t")
    price = float(match.group("price").replace("$", "").replace(",", "."))
    if not raw_name and not fallback_name:
        return None

    unit_price, unit_price_unit = infer_unit_price(raw_name)
    quantity, unit = infer_quantity(raw_name)
    unit_price = correct_ocr_unit_price(unit_price, quantity, price)
    item_name = fallback_name if fallback_name and is_price_detail_line(raw_name) else raw_name
    if not item_name or len(item_name) < 2:
        return None

    return ParsedItem(
        line=line,
        name=clean_item_name(item_name, has_unit_price=unit_price is not None),
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        unit_price_unit=unit_price_unit,
        price=price,
    )


def is_possible_continuation_name(line: str) -> bool:
    lowered = line.lower()
    if (
        parse_date(line)
        or PRICE_PATTERN.search(line)
        or looks_like_location_line(line)
        or looks_like_noise_line(line)
        or any(word in lowered for word in SKIP_WORDS)
        or "@" in line
    ):
        return False

    return any(character.isalpha() for character in line)


def should_update_pending_name(current: str | None, candidate: str) -> bool:
    if current is None:
        return True
    return not looks_like_weak_item_name(candidate)


def looks_like_weak_item_name(line: str) -> bool:
    if re.search(r"[\]\[{}|]", line):
        return True

    words = re.findall(r"[A-Za-z]+", line)
    if not words:
        return True

    if len(words) <= 3 and all(len(word) <= 3 for word in words):
        return True

    digit_count = sum(character.isdigit() for character in line)
    alpha_count = sum(character.isalpha() for character in line)
    return digit_count > alpha_count


def is_price_detail_line(raw_name: str) -> bool:
    return bool(
        re.match(r"^\d+(?:\.\d+)?\s?(?:kg|g|lb|lbs|ib|ibs|oz|l|ml|ct)\b", raw_name, re.I)
        or re.match(r"^\d+(?:\.\d+)?\s*@", raw_name)
    )


def infer_quantity(raw_name: str) -> tuple[str | None, str | None]:
    match = re.search(r"\b(\d+(?:\.\d+)?\s?(?:kg|g|lb|lbs|ib|ibs|oz|l|ml|ct|x))\b", raw_name, re.I)
    if match:
        token = match.group(1)
        parts = re.match(r"(?P<quantity>\d+(?:\.\d+)?)\s?(?P<unit>[a-zA-Z]+)", token)
        if parts:
            return parts.group("quantity"), normalize_ocr_unit(parts.group("unit"))
        return token, None

    count_match = re.search(r"\b(?P<quantity>\d+(?:\.\d+)?)\s*@\s*\$?\d+(?:[.,]\d{2})\b", raw_name)
    if count_match:
        return count_match.group("quantity"), "ct"

    return None, None


def infer_unit_price(raw_name: str) -> tuple[float | None, str | None]:
    unit_match = re.search(
        r"@\s*\$?(?P<unit_price>\d+(?:[.,]\d{2}))\s*/\s*(?P<unit>[a-zA-Z]+)\b",
        raw_name,
        re.I,
    )
    if unit_match:
        return (
            float(unit_match.group("unit_price").replace(",", ".")),
            normalize_ocr_unit(unit_match.group("unit")),
        )

    count_match = re.search(
        r"\b\d+(?:\.\d+)?\s*@\s*\$?(?P<unit_price>\d+(?:[.,]\d{2}))\b",
        raw_name,
        re.I,
    )
    if count_match:
        return float(count_match.group("unit_price").replace(",", ".")), "ct"

    return None, None


def correct_ocr_unit_price(
    unit_price: float | None,
    quantity: str | None,
    total_price: float,
) -> float | None:
    if unit_price is None or quantity is None:
        return unit_price

    try:
        quantity_value = float(quantity)
    except ValueError:
        return unit_price

    if quantity_value <= 0 or unit_price * quantity_value <= total_price * 3:
        return unit_price

    unit_price_text = f"{unit_price:.2f}"
    integer_part, decimal_part = unit_price_text.split(".", 1)
    while len(integer_part) > 1:
        integer_part = integer_part[1:]
        candidate = float(f"{integer_part}.{decimal_part}")
        if candidate > 0 and candidate * quantity_value <= total_price * 3:
            return candidate

    return unit_price


def normalize_ocr_unit(unit: str) -> str:
    normalized = unit.lower()
    return {"ib": "lb", "ibs": "lbs"}.get(normalized, normalized)


def clean_item_name(raw_name: str, has_unit_price: bool = False) -> str:
    cleaned = raw_name
    if has_unit_price:
        cleaned = re.sub(
            r"\b\d+(?:\.\d+)?\s?(?:kg|g|lb|lbs|ib|ibs|oz|l|ml|ct)\b\s*@\s*\$?\d+(?:[.,]\d{2})\s*/\s*[a-zA-Z]+\b",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*@\s*\$?\d+(?:[.,]\d{2}).*$", "", cleaned, flags=re.I)
    return re.sub(r"\s+", " ", cleaned).strip().title()
