import re
from dataclasses import dataclass
from datetime import date, datetime


PRICE_PATTERN = re.compile(r"(?P<name>.*?)(?P<price>\$?\d+(?:[.,]\d{2}))\s*$")
DATE_PATTERNS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y")
SKIP_WORDS = {"subtotal", "total", "tax", "visa", "mastercard", "debit", "change"}
STREET_PATTERN = re.compile(
    r"\b\d{1,6}\s+.+\b(st|street|ave|avenue|rd|road|dr|drive|blvd|boulevard|way|lane|ln|hwy|highway)\b",
    re.I,
)
POSTAL_PATTERN = re.compile(
    r"\b([A-Z]\d[A-Z]\s?\d[A-Z]\d|\d{5}(?:-\d{4})?)\b",
    re.I,
)
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")


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
    store_phone: str | None
    purchased_at: date | None
    items: list[ParsedItem]


def parse_receipt_text(raw_text: str) -> ParsedReceipt:
    lines = [normalize_line(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    purchased_at = next((parsed for line in lines if (parsed := parse_date(line))), None)
    store_name = infer_store_name(lines)
    store_location_text = infer_store_location(lines, store_name)
    store_phone = infer_store_phone(lines)
    items = [item for line in lines if (item := parse_item_line(line))]

    return ParsedReceipt(
        store_name=store_name,
        store_location_text=store_location_text,
        store_phone=store_phone,
        purchased_at=purchased_at,
        items=items,
    )


def normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


def infer_store_name(lines: list[str]) -> str:
    for line in lines[:5]:
        if (
            not parse_date(line)
            and not PRICE_PATTERN.search(line)
            and not looks_like_location_line(line)
        ):
            return line
    return "Unknown Store"


def infer_store_location(lines: list[str], store_name: str) -> str | None:
    location_lines = []
    for line in lines[:10]:
        if line == store_name or parse_date(line) or PRICE_PATTERN.search(line):
            continue
        if PHONE_PATTERN.search(line):
            continue
        if looks_like_location_line(line):
            location_lines.append(line)

    return ", ".join(location_lines) if location_lines else None


def infer_store_phone(lines: list[str]) -> str | None:
    for line in lines[:12]:
        match = PHONE_PATTERN.search(line)
        if match:
            return match.group(0)
    return None


def looks_like_location_line(line: str) -> bool:
    lowered = line.lower()
    return bool(
        STREET_PATTERN.search(line)
        or POSTAL_PATTERN.search(line)
        or PHONE_PATTERN.search(line)
        or re.search(r"\b(suite|unit|vancouver|bc|canada)\b", lowered)
    )


def parse_date(line: str) -> date | None:
    for token in re.split(r"\s+", line):
        cleaned = token.strip(".,")
        for pattern in DATE_PATTERNS:
            try:
                return datetime.strptime(cleaned, pattern).date()
            except ValueError:
                continue
    return None


def parse_item_line(line: str) -> ParsedItem | None:
    lowered = line.lower()
    if any(word in lowered for word in SKIP_WORDS):
        return None

    match = PRICE_PATTERN.match(line.replace(",", "."))
    if not match:
        return None

    raw_name = match.group("name").strip(" -:\t")
    price = float(match.group("price").replace("$", "").replace(",", "."))
    if not raw_name or len(raw_name) < 2:
        return None

    unit_price, unit_price_unit = infer_unit_price(raw_name)
    quantity, unit = infer_quantity(raw_name)
    return ParsedItem(
        line=line,
        name=clean_item_name(raw_name, has_unit_price=unit_price is not None),
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        unit_price_unit=unit_price_unit,
        price=price,
    )


def infer_quantity(raw_name: str) -> tuple[str | None, str | None]:
    match = re.search(r"\b(\d+(?:\.\d+)?\s?(?:kg|g|lb|lbs|oz|l|ml|ct|x))\b", raw_name, re.I)
    if match:
        token = match.group(1)
        parts = re.match(r"(?P<quantity>\d+(?:\.\d+)?)\s?(?P<unit>[a-zA-Z]+)", token)
        if parts:
            return parts.group("quantity"), parts.group("unit").lower()
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
            unit_match.group("unit").lower(),
        )

    count_match = re.search(
        r"\b\d+(?:\.\d+)?\s*@\s*\$?(?P<unit_price>\d+(?:[.,]\d{2}))\b",
        raw_name,
        re.I,
    )
    if count_match:
        return float(count_match.group("unit_price").replace(",", ".")), "ct"

    return None, None


def clean_item_name(raw_name: str, has_unit_price: bool = False) -> str:
    cleaned = raw_name
    if has_unit_price:
        cleaned = re.sub(
            r"\b\d+(?:\.\d+)?\s?(?:kg|g|lb|lbs|oz|l|ml|ct)\b\s*@\s*\$?\d+(?:[.,]\d{2})\s*/\s*[a-zA-Z]+\b",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"\b\d+(?:\.\d+)?\s*@\s*\$?\d+(?:[.,]\d{2}).*$", "", cleaned, flags=re.I)
    return re.sub(r"\s+", " ", cleaned).strip().title()
