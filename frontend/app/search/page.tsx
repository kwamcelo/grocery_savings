"use client";

import { FormEvent, useState } from "react";
import { Search } from "lucide-react";
import { ResultTable } from "@/components/ResultTable";
import { SearchResult, searchItems } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;

    setError(null);
    setHasSearched(true);

    try {
      setResults(await searchItems(query.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  }

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Search item prices</h1>
          <p>Find historical prices from uploaded receipts by grocery item name.</p>
        </div>
      </section>

      <form className="form-row" onSubmit={handleSearch}>
        <input
          aria-label="Item search"
          type="search"
          placeholder="Milk, bananas, eggs..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit">
          <Search size={18} aria-hidden="true" />
          Search
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}
      {hasSearched ? <ResultTable results={results} /> : null}
    </div>
  );
}
