"use client";

import { FormEvent, useState } from "react";
import { AlertTriangle, BarChart3 } from "lucide-react";
import { CompareResult, SearchResult, compareItems, formatMoney } from "@/lib/api";

export default function ComparePage() {
  const [name, setName] = useState("");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCompare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;

    setError(null);

    try {
      setResult(await compareItems(name.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    }
  }

  const hasUnreliableComparisons =
    result?.by_store.some((store) => !store.comparison_reliable) ?? false;

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Compare prices by store</h1>
          <p>
            Compare by unit price when quantity and unit are available. Rows with missing
            units fall back to total item price.
          </p>
        </div>
      </section>

      <form className="form-row" onSubmit={handleCompare}>
        <input
          aria-label="Item to compare"
          type="text"
          placeholder="Eggs, spinach, oats..."
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button type="submit">
          <BarChart3 size={18} aria-hidden="true" />
          Compare
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {result ? (
        <div className="stack">
          {hasUnreliableComparisons ? (
            <p className="comparison-warning">
              <AlertTriangle size={18} aria-hidden="true" />
              Some stores are compared by total price because quantity or unit data is
              missing. Those comparisons may be unreliable.
            </p>
          ) : null}

          <section className="summary-grid">
            {result.by_store.length === 0 ? (
              <p className="empty-state">No stores found for that item.</p>
            ) : (
              result.by_store.map((store) => (
                <article className="stat" key={store.store_name}>
                  <span>{store.store_name}</span>
                  <strong>{formatComparisonPrice(store)}</strong>
                  <p className={store.comparison_reliable ? "muted" : "error"}>
                    {store.comparison_reliable
                      ? `Lowest ${formatMoney(store.lowest_price)} total`
                      : store.comparison_warning}
                  </p>
                </article>
              ))
            )}
          </section>

          <ComparisonTable results={result.matches} />
        </div>
      ) : null}
    </div>
  );
}

function ComparisonTable({ results }: { results: SearchResult[] }) {
  if (results.length === 0) {
    return <p className="empty-state">No matching grocery prices yet.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Quantity</th>
            <th>Store</th>
            <th>Date</th>
            <th className="numeric">Total</th>
            <th className="numeric">Comparable price</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.item_id}>
              <td>{result.name}</td>
              <td>{formatQuantity(result.quantity, result.unit)}</td>
              <td>{result.store_name}</td>
              <td>{result.purchased_at ?? "-"}</td>
              <td className="numeric">{formatMoney(result.price)}</td>
              <td className="numeric">
                <span className={result.comparison_reliable ? "" : "unreliable-price"}>
                  {formatItemComparison(result)}
                </span>
                {!result.comparison_reliable ? (
                  <small className="comparison-note">{result.comparison_warning}</small>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatComparisonPrice(store: CompareResult["by_store"][number]): string {
  if (store.lowest_unit_price !== null && store.lowest_unit_price_label) {
    return `${formatMoney(store.lowest_unit_price)} ${store.lowest_unit_price_label}`;
  }
  return `${formatMoney(store.comparison_price)} total`;
}

function formatItemComparison(result: SearchResult): string {
  if (result.unit_price !== null && result.unit_price_label) {
    return `${formatMoney(result.unit_price)} ${result.unit_price_label}`;
  }
  return `${formatMoney(result.price)} total`;
}

function formatQuantity(quantity: number | null, unit: string | null): string {
  if (quantity === null && !unit) return "-";
  return [quantity, unit].filter(Boolean).join(" ");
}
