"use client";

import { FormEvent, useState } from "react";
import { BarChart3 } from "lucide-react";
import { ResultTable } from "@/components/ResultTable";
import { CompareResult, compareItems, formatMoney } from "@/lib/api";

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

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Compare prices by store</h1>
          <p>Review lowest, highest, and average observed prices for an item.</p>
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
          <section className="summary-grid">
            {result.by_store.length === 0 ? (
              <p className="empty-state">No stores found for that item.</p>
            ) : (
              result.by_store.map((store) => (
                <article className="stat" key={store.store_name}>
                  <span>{store.store_name}</span>
                  <strong>{formatMoney(store.average_price)}</strong>
                  <p className="muted">
                    Low {formatMoney(store.lowest_price)} / High{" "}
                    {formatMoney(store.highest_price)} / {store.observations} seen
                  </p>
                </article>
              ))
            )}
          </section>
          <ResultTable results={result.matches} />
        </div>
      ) : null}
    </div>
  );
}
