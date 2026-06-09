# Grocery Savings

A full-stack grocery receipt price tracker. Upload receipt images, review OCR output, normalize product names, and compare grocery prices across stores with unit-price awareness.

## Screenshots

Add screenshots to `docs/screenshots/` before publishing the portfolio page.

| Dashboard | OCR Review | Product Search | Price Compare |
| --- | --- | --- | --- |
| `docs/screenshots/dashboard.png` | `docs/screenshots/ocr-review.png` | `docs/screenshots/search.png` | `docs/screenshots/compare.png` |

## Features

- Receipt image upload with local file storage.
- OCR extraction through Tesseract when enabled, with placeholder OCR for local demos.
- Editable OCR review screen before saving.
- Store name, location, purchase date, item name, purchased quantity, unit, receipt unit price, and total item price capture.
- Normalized products and aliases so `MANGO MX`, `MEX MANGO`, and `MANGOS` can map to `Mexican Mango`.
- Fuzzy product normalization suggestions with confirm/reject controls.
- Product search across normalized product names, aliases, and raw receipt item names.
- Price comparison by store that prefers receipt-provided unit prices, then calculates unit prices from quantity/unit when needed.
- Clear warnings when comparisons fall back to total price because unit-price, quantity, or unit data is missing.
- SQLite seed data for demos and backend tests.

## Stack

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, Python
- Database: SQLite for local development
- ORM: SQLAlchemy
- OCR: Tesseract via `pytesseract`, or placeholder OCR for local demos

## Project Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   |-- seed.py
|   |   |-- migrations.py
|   |   `-- services/
|   |       |-- ocr.py
|   |       |-- parser.py
|   |       `-- storage.py
|   |-- tests/
|   |-- test_receipts/
|   |-- data/
|   |-- requirements.txt
|   `-- .env.example
|-- frontend/
|   |-- app/
|   |-- components/
|   |-- lib/
|   `-- package.json
`-- README.md
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.seed --reset
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

For real local OCR, install the Tesseract binary and keep `OCR_PROVIDER=tesseract`
in `backend/.env`:

```bash
brew install tesseract
```

If `OCR_PROVIDER=placeholder`, uploads intentionally return the demo Fresh Market
text instead of reading the image.

Useful endpoints:

- `GET /health`
- `POST /receipts/upload` for OCR preview
- `POST /receipts` for saving reviewed receipt data
- `GET /products/search?q=Mexican%20mangos`
- `GET /products/{product_id}/price-history`
- `GET /items/compare?name=milk`

## Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The app runs at `http://localhost:3000`.

## Demo Data

Load sample stores, receipts, normalized products, and aliases:

```bash
cd backend
source .venv/bin/activate
python -m app.seed --reset
```

Try these demo queries:

- `Mexican mangos`
- `milk`
- `spinach`
- `bananas`

The `backend/test_receipts/` folder is used by tests for upload coverage when receipt images are present.

## Database Schema

- `stores`: store name and location text.
- `receipts`: uploaded receipt metadata, raw OCR text, purchase date, image path, and `store_id`.
- `receipt_items`: raw item name, total price, purchased quantity, unit, optional receipt unit price, optional receipt unit price unit, purchase date, store, receipt, and normalized product link.
- `normalized_products`: canonical product names such as `Mexican Mango`.
- `product_aliases`: receipt text aliases that map back to normalized products.

## OCR Limitations

OCR quality depends heavily on image quality. Blurry receipts, shadows, rotated images, thermal-paper fading, store-specific formatting, and abbreviated product names can all reduce accuracy. The app intentionally adds a review screen before saving because OCR and receipt parsing should be treated as suggestions, not truth.

The current parser is simple and modular. It looks for:

- a likely store name near the top
- address-like lines
- common purchase date formats
- item lines ending in a price
- simple quantity/unit tokens such as `2L`, `1 lb`, `500g`, or `12 ct`
- receipt-provided unit prices such as `$1.99/lb` or `3 @ $0.69`

## Testing

Run backend tests:

```bash
cd backend
python3 -m pytest
```

Current coverage includes:

- receipt parsing
- saving reviewed receipts
- product search
- unit-aware price comparison
- receipt fixture uploads from `backend/test_receipts/`

Run frontend checks:

```bash
cd frontend
npm run build
```

## Future Improvements

- Replace lightweight SQLite migrations with Alembic.
- Add authentication and per-user receipt ownership.
- Store image files in object storage for production.
- Add receipt image preprocessing before OCR.
- Add store-specific parsing rules and parser confidence scores.
- Add barcode or SKU support for stronger product normalization.
- Add human review queues for uncertain product matches.
- Add charts for price trends over time.
- Add export to CSV.
