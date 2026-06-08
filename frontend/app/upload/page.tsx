"use client";

import { FormEvent, useState } from "react";
import { ReceiptText, Upload } from "lucide-react";
import { Receipt, formatMoney, uploadReceipt } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setReceipt(null);

    try {
      setReceipt(await uploadReceipt(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Upload a receipt</h1>
          <p>
            The backend will run receipt text through Tesseract when enabled, or through
            placeholder OCR during early local development.
          </p>
        </div>
      </section>

      <form className="upload-box" onSubmit={handleSubmit}>
        <input
          aria-label="Receipt image"
          accept="image/*"
          type="file"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button disabled={!file || isUploading} type="submit">
          <Upload size={18} aria-hidden="true" />
          {isUploading ? "Uploading..." : "Extract receipt"}
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {receipt ? (
        <section className="panel">
          <h2>
            <ReceiptText size={20} aria-hidden="true" /> {receipt.store_name}
          </h2>
          <p className="muted">{receipt.purchased_at ?? "No purchase date parsed"}</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Quantity</th>
                  <th className="numeric">Price</th>
                </tr>
              </thead>
              <tbody>
                {receipt.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{formatQuantity(item.quantity, item.unit)}</td>
                    <td className="numeric">{formatMoney(item.price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function formatQuantity(quantity: number | null, unit: string | null): string {
  if (quantity === null && !unit) return "-";
  return [quantity, unit].filter(Boolean).join(" ");
}
