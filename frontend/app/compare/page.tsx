"use client";

import { FormEvent, useState } from "react";
import { AlertTriangle, BarChart3 } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { CompareResult, SearchResult, compareItems, formatMoney } from "@/lib/api";

export default function ComparePage() {
  const [name, setName] = useState("");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const { user, isLoading } = useAuth();

  async function handleCompare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Enter an item name to compare.");
      return;
    }

    setError(null);
    setIsComparing(true);

    try {
      setResult(await compareItems(name.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    } finally {
      setIsComparing(false);
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
            See which store has the better price for an item you buy.
          </p>
        </div>
      </section>

      {!isLoading && !user ? (
        <section className="panel stack">
          <p className="muted">Sign in to compare saved prices.</p>
          <Link className="button" href="/account">
            Go to account
          </Link>
        </section>
      ) : null}

      {user ? (
      <form className="form-row" onSubmit={handleCompare}>
        <input
          aria-label="Item to compare"
          type="text"
          placeholder="Eggs, spinach, oats..."
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button disabled={isComparing} type="submit">
          <BarChart3 size={18} aria-hidden="true" />
          {isComparing ? "Comparing..." : "Compare"}
        </button>
      </form>
      ) : null}

      {error ? <p className="error">{error}</p> : null}

      {isComparing ? <p className="muted">Checking prices...</p> : null}

      {result && !isComparing ? (
        <div className="stack">
          {hasUnreliableComparisons ? (
            <p className="comparison-warning">
              <AlertTriangle size={18} aria-hidden="true" />
              Some prices may be harder to compare because the receipt was missing
              size or weight details.
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
                      : "Check the item details before comparing."}
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
            <th className="numeric">Price per unit</th>
            <th className="numeric">Total</th>
            <th className="numeric">Best comparison</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.item_id}>
              <td data-label="Item">{result.name}</td>
              <td data-label="Quantity">{formatQuantity(result.quantity, result.unit)}</td>
              <td data-label="Store">{result.store_name}</td>
              <td data-label="Date">{result.purchased_at ?? "-"}</td>
              <td data-label="Price per unit" className="numeric">{formatSourceUnitPrice(result)}</td>
              <td data-label="Total" className="numeric">{formatMoney(result.price)}</td>
              <td data-label="Best comparison" className="numeric">
                <span className={result.comparison_reliable ? "" : "unreliable-price"}>
                  {formatItemComparison(result)}
                </span>
                {!result.comparison_reliable ? (
                  <small className="comparison-note">Missing size or weight details</small>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatSourceUnitPrice(result: SearchResult): string {
  if (result.source_unit_price !== null && result.source_unit_price_unit) {
    return `${formatMoney(result.source_unit_price)} / ${result.source_unit_price_unit}`;
  }
  return "-";
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
