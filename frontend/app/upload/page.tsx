"use client";

import { FormEvent, useState } from "react";
import { Plus, ReceiptText, Save, Trash2, Upload } from "lucide-react";
import {
  NormalizationSuggestion,
  Receipt,
  ReceiptPreviewResponse,
  formatMoney,
  previewReceipt,
  saveReceipt,
} from "@/lib/api";

type ReviewItem = {
  name: string;
  quantity: string;
  unit: string;
  unitPrice: string;
  unitPriceUnit: string;
  price: string;
  source_line: string | null;
  suggestion: NormalizationSuggestion | null;
  confirmed_product_id: number | null;
  rejected_suggestion: boolean;
};

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ReceiptPreviewResponse | null>(null);
  const [storeName, setStoreName] = useState("");
  const [storeLocation, setStoreLocation] = useState("");
  const [storePhone, setStorePhone] = useState("");
  const [purchasedAt, setPurchasedAt] = useState("");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [savedReceipt, setSavedReceipt] = useState<Receipt | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setPreview(null);
    setSavedReceipt(null);

    try {
      const result = await previewReceipt(file);
      setPreview(result);
      setStoreName(result.parsed.store_name);
      setStoreLocation(result.parsed.store_location_text ?? "");
      setStorePhone(result.parsed.store_phone ?? "");
      setPurchasedAt(result.parsed.purchased_at ?? "");
      setItems(
        result.parsed.items.map((item) => ({
          name: item.name,
          quantity: item.quantity ?? "",
          unit: item.unit ?? "",
          unitPrice: item.unit_price === null ? "" : String(item.unit_price),
          unitPriceUnit: item.unit_price_unit ?? "",
          price: String(item.price),
          source_line: item.line,
          suggestion: item.normalization_suggestion,
          confirmed_product_id: item.normalization_suggestion?.auto_match
            ? item.normalization_suggestion.product_id
            : null,
          rejected_suggestion: false,
        })),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSave() {
    if (!preview) return;

    if (!storeName.trim()) {
      setError("Store name is required before saving.");
      return;
    }

    const correctedItems = items
      .filter((item) => item.name.trim() && item.price.trim())
      .map((item) => ({
        name: item.name.trim(),
        quantity: item.quantity.trim() || null,
        unit: item.unit.trim() || null,
        unit_price: item.unitPrice.trim() ? Number(item.unitPrice) : null,
        unit_price_unit: item.unitPriceUnit.trim() || null,
        price: Number(item.price),
        source_line: item.source_line,
        normalized_product_id: item.confirmed_product_id,
        reject_normalization_suggestion: item.rejected_suggestion,
      }));

    if (correctedItems.length === 0) {
      setError("Add at least one item with a name and price before saving.");
      return;
    }

    if (
      correctedItems.some(
        (item) =>
          !Number.isFinite(item.price) ||
          item.price < 0 ||
          (item.unit_price !== null && (!Number.isFinite(item.unit_price) || item.unit_price < 0)),
      )
    ) {
      setError("Each item price and unit price must be valid non-negative numbers.");
      return;
    }

    if (
      correctedItems.some(
        (item) => item.unit_price !== null && !item.unit_price_unit && !item.unit,
      )
    ) {
      setError("Unit price needs a unit, such as lb, kg, L, ml, or ct.");
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const receipt = await saveReceipt({
        store_name: storeName,
        store_location_text: storeLocation || null,
        store_phone: storePhone || null,
        purchased_at: purchasedAt || null,
        image_path: preview.image_path,
        original_filename: preview.original_filename,
        raw_text: preview.extracted_text,
        items: correctedItems,
      });
      setSavedReceipt(receipt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  }

  function updateItem(index: number, patch: Partial<ReviewItem>) {
    setItems((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    );
  }

  function removeItem(index: number) {
    setItems((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  function addItem() {
    setItems((current) => [
      ...current,
      {
        name: "",
        quantity: "",
        unit: "",
        unitPrice: "",
        unitPriceUnit: "",
        price: "",
        source_line: null,
        suggestion: null,
        confirmed_product_id: null,
        rejected_suggestion: false,
      },
    ]);
  }

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Upload a receipt</h1>
          <p>
            Upload an image, review the OCR result, correct any item details, then save
            the final receipt to the database.
          </p>
        </div>
      </section>

      <form className="upload-box" onSubmit={handleUpload}>
        <input
          aria-label="Receipt image"
          accept="image/*"
          type="file"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button disabled={!file || isUploading} type="submit">
          <Upload size={18} aria-hidden="true" />
          {isUploading ? "Extracting..." : "Extract receipt"}
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {preview ? (
        <section className="panel stack">
          <header>
            <h2>
              <ReceiptText size={20} aria-hidden="true" /> Review receipt
            </h2>
            <p className="muted">Saved image: {preview.image_path}</p>
          </header>

          <div className="review-grid">
            <label>
              Store name
              <input
                value={storeName}
                onChange={(event) => setStoreName(event.target.value)}
              />
            </label>
            <label>
              Purchase date
              <input
                type="date"
                value={purchasedAt}
                onChange={(event) => setPurchasedAt(event.target.value)}
              />
            </label>
            <label>
              Store location
              <input
                value={storeLocation}
                onChange={(event) => setStoreLocation(event.target.value)}
              />
            </label>
            <label>
              Store phone
              <input
                value={storePhone}
                onChange={(event) => setStorePhone(event.target.value)}
              />
            </label>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Item name</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>Receipt unit price</th>
                  <th>Unit price unit</th>
                  <th>Suggested product</th>
                  <th className="numeric">Price</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr key={`${item.source_line ?? "manual"}-${index}`}>
                    <td>
                      <input
                        className="table-input"
                        value={item.name}
                        onChange={(event) => updateItem(index, { name: event.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        className="table-input"
                        value={item.quantity}
                        onChange={(event) =>
                          updateItem(index, { quantity: event.target.value })
                        }
                      />
                    </td>
                    <td>
                      <input
                        className="table-input"
                        value={item.unit}
                        onChange={(event) => updateItem(index, { unit: event.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        className="table-input numeric"
                        min="0"
                        step="0.01"
                        type="number"
                        value={item.unitPrice}
                        onChange={(event) => updateItem(index, { unitPrice: event.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        className="table-input"
                        placeholder={item.unit || "lb"}
                        value={item.unitPriceUnit}
                        onChange={(event) =>
                          updateItem(index, { unitPriceUnit: event.target.value })
                        }
                      />
                    </td>
                    <td>{renderSuggestion(item, index, updateItem)}</td>
                    <td>
                      <input
                        className="table-input numeric"
                        min="0"
                        step="0.01"
                        type="number"
                        value={item.price}
                        onChange={(event) => updateItem(index, { price: event.target.value })}
                      />
                    </td>
                    <td className="numeric">
                      <button
                        aria-label="Remove item"
                        className="icon-button"
                        type="button"
                        onClick={() => removeItem(index)}
                      >
                        <Trash2 size={16} aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="actions">
            <button className="secondary" type="button" onClick={addItem}>
              <Plus size={18} aria-hidden="true" />
              Add item
            </button>
            <button disabled={isSaving || !storeName || items.length === 0} type="button" onClick={handleSave}>
              <Save size={18} aria-hidden="true" />
              {isSaving ? "Saving..." : "Save Receipt"}
            </button>
          </div>

          {savedReceipt ? (
            <p className="save-status">
              Saved receipt #{savedReceipt.id} with {savedReceipt.items.length} item
              {savedReceipt.items.length === 1 ? "" : "s"} totaling{" "}
              {formatMoney(savedReceipt.items.reduce((sum, item) => sum + item.price, 0))}.
            </p>
          ) : null}

          <h3>Extracted text</h3>
          <pre className="ocr-text">{preview.extracted_text}</pre>
        </section>
      ) : null}
    </div>
  );
}

function renderSuggestion(
  item: ReviewItem,
  index: number,
  updateItem: (index: number, patch: Partial<ReviewItem>) => void,
) {
  if (!item.suggestion) {
    return <span className="muted">No suggestion</span>;
  }

  if (item.rejected_suggestion) {
    return (
      <div className="suggestion-cell">
        <span className="muted">Rejected</span>
        <button
          className="secondary mini-button"
          type="button"
          onClick={() =>
            updateItem(index, {
              rejected_suggestion: false,
              confirmed_product_id: null,
            })
          }
        >
          Undo
        </button>
      </div>
    );
  }

  const confirmed = item.confirmed_product_id === item.suggestion.product_id;

  return (
    <div className={confirmed ? "suggestion-cell confirmed" : "suggestion-cell"}>
      <span>
        <strong>{item.suggestion.product_name}</strong>
        <small>
          {Math.round(item.suggestion.score * 100)}% match on "{item.suggestion.matched_on}"
        </small>
      </span>
      <span className="suggestion-actions">
        <button
          className={confirmed ? "mini-button" : "secondary mini-button"}
          type="button"
          onClick={() =>
            updateItem(index, {
              confirmed_product_id: item.suggestion?.product_id ?? null,
              rejected_suggestion: false,
            })
          }
        >
          {confirmed ? "Confirmed" : "Confirm"}
        </button>
        <button
          className="secondary mini-button"
          type="button"
          onClick={() =>
            updateItem(index, {
              confirmed_product_id: null,
              rejected_suggestion: true,
            })
          }
        >
          Reject
        </button>
      </span>
    </div>
  );
}
