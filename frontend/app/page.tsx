import Link from "next/link";
import { BarChart3, Search, Upload } from "lucide-react";

export default function HomePage() {
  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Grocery Savings</h1>
          <p>
            Turn grocery receipts into a personal price list, then check where your
            regular items cost less.
          </p>
        </div>
        <Link className="button" href="/upload">
          <Upload size={18} aria-hidden="true" />
          Upload receipt
        </Link>
      </section>

      <section className="panel">
        <h2>What would you like to do?</h2>
        <p className="muted">
          Add a new receipt, look up an item you buy often, or compare prices
          between stores.
        </p>
        <div className="actions">
          <Link className="button secondary" href="/upload">
            <Upload size={18} aria-hidden="true" />
            Add receipt
          </Link>
          <Link className="button secondary" href="/search">
            <Search size={18} aria-hidden="true" />
            Find an item
          </Link>
          <Link className="button secondary" href="/compare">
            <BarChart3 size={18} aria-hidden="true" />
            Compare prices
          </Link>
        </div>
      </section>

    </div>
  );
}
