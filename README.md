# Grocery Receipt Price Tracker

A local full-stack app for uploading grocery receipt images, extracting receipt text, storing item prices, and comparing prices across stores.

## Stack

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, Python
- Database: SQLite for local development
- ORM: SQLAlchemy
- OCR: Tesseract via `pytesseract` when enabled, with placeholder OCR available by default

## Project Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- db.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   `-- services/
|   |       |-- ocr.py
|   |       `-- parser.py
|   |-- data/
|   |-- requirements.txt
|   `-- .env.example
|-- frontend/
|   |-- app/
|   |   |-- page.tsx
|   |   |-- upload/page.tsx
|   |   |-- search/page.tsx
|   |   `-- compare/page.tsx
|   |-- components/
|   |-- lib/
|   |-- package.json
|   `-- .env.local.example
`-- README.md
```

## Backend Setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

Useful endpoints:

- `GET /health`
- `POST /receipts/upload`
- `GET /receipts`
- `GET /items/search?q=milk`
- `GET /items/compare?name=milk`

SQLite is created automatically at `backend/data/grocery_tracker.db`.

## OCR Setup

Placeholder OCR is enabled by default so the app works before Tesseract is installed. To use real OCR:

1. Install the Tesseract binary.
   - macOS: `brew install tesseract`
   - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
2. Set `USE_TESSERACT=true` in `backend/.env`.
3. Restart the FastAPI server.

Receipt parsing is intentionally simple in this scaffold. It detects the first likely store line, common date formats, and item lines ending in a price.

## Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The app runs at `http://localhost:3000`.

Pages included:

- `/` dashboard with recent receipts and totals
- `/upload` image upload and extracted item preview
- `/search` item price search
- `/compare` price comparison by store

## Local Development Flow

1. Start the backend with `uvicorn app.main:app --reload`.
2. Start the frontend with `npm run dev`.
3. Open `http://localhost:3000`.
4. Upload any image while placeholder OCR is enabled. The backend will store a sample receipt.
5. Search for `milk`, `eggs`, or `bananas` to verify the end-to-end flow.

## Next Steps

- Add migrations with Alembic before schema changes become frequent.
- Improve receipt parsing with store-specific rules and confidence scores.
- Store uploaded image files or object storage references.
- Add user accounts if receipts should be private per user.
- Add tests for parser edge cases and API endpoints.
