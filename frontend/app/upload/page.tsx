"use client";

import { FormEvent, useState } from "react";
import { Plus, ReceiptText, Save, Trash2, Upload } from "lucide-react";
import {
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
  price: string;
  source_line: string | null;
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
          unit: "",
          price: String(item.price),
          source_line: item.line,
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
        items: items
          .filter((item) => item.name.trim() && item.price.trim())
          .map((item) => ({
            name: item.name.trim(),
            quantity: item.quantity.trim() || null,
            unit: item.unit.trim() || null,
            price: Number(item.price),
            source_line: item.source_line,
          })),
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
      { name: "", quantity: "", unit: "", price: "", source_line: null },
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
