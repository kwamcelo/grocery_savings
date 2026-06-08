"use client";

import { FormEvent, useState } from "react";
import { Search } from "lucide-react";
import {
  ProductPriceHistory,
  ProductSearchCandidate,
  fetchProductPriceHistory,
  formatMoney,
  searchProducts,
} from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<ProductSearchCandidate[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [history, setHistory] = useState<ProductPriceHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;

    setError(null);
    setHasSearched(true);
    setHistory(null);
    setSelectedProductId(null);

    try {
      setCandidates(await searchProducts(query.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  }

  async function handleSelectProduct(product: ProductSearchCandidate) {
    setSelectedProductId(product.product_id);
    setIsLoadingHistory(true);
    setError(null);

    try {
      setHistory(await fetchProductPriceHistory(product.product_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load product prices");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Search product prices</h1>
          <p>
            Search normalized product names and raw receipt item names, then compare
            store prices for the selected product.
          </p>
        </div>
      </section>

      <form className="form-row" onSubmit={handleSearch}>
        <input
          aria-label="Product search"
          type="search"
          placeholder="Mexican mangos, milk, bananas..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit">
          <Search size={18} aria-hidden="true" />
          Search
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {hasSearched ? (
        <section className="stack">
          <h2>Matching products</h2>
          {candidates.length === 0 ? (
            <p className="empty-state">No matching products found.</p>
          ) : (
            <div className="product-candidates">
              {candidates.map((candidate) => (
                <button
                  className={
                    selectedProductId === candidate.product_id
                      ? "product-candidate selected"
                      : "product-candidate"
                  }
                  key={candidate.product_id}
                  type="button"
                  onClick={() => handleSelectProduct(candidate)}
                >
                  <span>
                    <strong>{candidate.name}</strong>
                    {candidate.category ? <small>{candidate.category}</small> : null}
                  </span>
                  <span className="candidate-prices">
                    <strong>
                      Recent{" "}
                      {candidate.most_recent_observed_price === null
                        ? "-"
                        : formatMoney(candidate.most_recent_observed_price)}
                    </strong>
                    <small>
                      Low{" "}
                      {candidate.lowest_observed_price === null
                        ? "-"
                        : formatMoney(candidate.lowest_observed_price)}
                      {candidate.last_purchased_at ? ` / ${candidate.last_purchased_at}` : ""}
                    </small>
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {isLoadingHistory ? <p className="muted">Loading store prices...</p> : null}

      {history ? (
        <section className="stack">
          <div className="page-title compact">
            <div>
              <h1>{history.product_name}</h1>
              <p>Stores sorted from lowest observed price to highest.</p>
            </div>
          </div>

          {history.stores.length === 0 ? (
            <p className="empty-state">No purchases saved for this product yet.</p>
          ) : (
            <div className="store-price-groups">
              {history.stores.map((store) => (
                <article className="store-price-group" key={store.store_id}>
                  <header>
                    <div>
                      <h2>{store.store_name}</h2>
                      <p className="muted">
                        Last purchased {store.last_purchased_at ?? "-"}
                      </p>
                    </div>
                    <div className="store-price-metrics">
                      <span>
                        Most recent
                        <strong>{formatMoney(store.most_recent_observed_price)}</strong>
                      </span>
                      <span>
                        Lowest
                        <strong>{formatMoney(store.lowest_observed_price)}</strong>
                      </span>
                    </div>
                  </header>

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Raw item</th>
                          <th>Quantity</th>
                          <th>Date</th>
                          <th className="numeric">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {store.purchases.map((purchase) => (
                          <tr key={purchase.item_id}>
                            <td>{purchase.raw_item_name}</td>
                            <td>{formatQuantity(purchase.quantity, purchase.unit)}</td>
                            <td>{purchase.purchased_at ?? "-"}</td>
                            <td className="numeric">{formatMoney(purchase.price)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}

function formatQuantity(quantity: number | null, unit: string | null): string {
  if (quantity === null && !unit) return "-";
  return [quantity, unit].filter(Boolean).join(" ");
}
