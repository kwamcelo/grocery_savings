import re
from dataclasses import dataclass
from datetime import date, datetime


PRICE_PATTERN = re.compile(r"(?P<name>.*?)(?P<price>\$?\d+(?:[.,]\d{2}))\s*$")
DATE_PATTERNS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y")
SKIP_WORDS = {"subtotal", "total", "tax", "visa", "mastercard", "debit", "change"}


@dataclass
class ParsedItem:
    name: str
    quantity: str | None
    price: float


@dataclass
class ParsedReceipt:
    store_name: str
    purchased_at: date | None
    items: list[ParsedItem]


def parse_receipt_text(raw_text: str) -> ParsedReceipt:
    lines = [normalize_line(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    purchased_at = next((parsed for line in lines if (parsed := parse_date(line))), None)
    store_name = infer_store_name(lines)
    items = [item for line in lines if (item := parse_item_line(line))]

    return ParsedReceipt(store_name=store_name, purchased_at=purchased_at, items=items)


def normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


def infer_store_name(lines: list[str]) -> str:
    for line in lines[:5]:
        if not parse_date(line) and not PRICE_PATTERN.search(line):
            return line
    return "Unknown Store"


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

    quantity = infer_quantity(raw_name)
    return ParsedItem(name=clean_item_name(raw_name), quantity=quantity, price=price)


def infer_quantity(raw_name: str) -> str | None:
    match = re.search(r"\b(\d+(?:\.\d+)?\s?(?:kg|g|lb|lbs|oz|l|ml|ct|x))\b", raw_name, re.I)
    return match.group(1) if match else None


def clean_item_name(raw_name: str) -> str:
    return re.sub(r"\s+", " ", raw_name).strip().title()
