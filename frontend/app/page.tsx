import Link from "next/link";
import { BarChart3, Search, Upload } from "lucide-react";
import { fetchReceipts, formatMoney, type Receipt } from "@/lib/api";

export default async function DashboardPage() {
  let receipts: Receipt[] = [];
  let loadError = false;

  try {
    receipts = await fetchReceipts();
  } catch {
    loadError = true;
  }

  const itemCount = receipts.reduce((sum, receipt) => sum + receipt.items.length, 0);
  const totalSpend = receipts.reduce(
    (sum, receipt) => sum + receipt.items.reduce((itemSum, item) => itemSum + item.price, 0),
    0,
  );

  return (
    <div className="stack">
      <section className="page-title">
        <div>
          <h1>Grocery receipt price tracker</h1>
          <p>
            Upload receipt images, extract line items, and build a searchable local
            history of prices by store.
          </p>
        </div>
        <Link className="button" href="/upload">
          <Upload size={18} aria-hidden="true" />
          Upload receipt
        </Link>
      </section>

      <section className="grid" aria-label="Receipt statistics">
        <div className="stat">
          <span>Receipts</span>
          <strong>{receipts.length}</strong>
        </div>
        <div className="stat">
          <span>Tracked items</span>
          <strong>{itemCount}</strong>
        </div>
        <div className="stat">
          <span>Indexed spend</span>
          <strong>{formatMoney(totalSpend)}</strong>
        </div>
      </section>

      <section className="panel">
        <h2>Common workflows</h2>
        <div className="actions">
          <Link className="button secondary" href="/search">
            <Search size={18} aria-hidden="true" />
            Search items
          </Link>
          <Link className="button secondary" href="/compare">
            <BarChart3 size={18} aria-hidden="true" />
            Compare stores
          </Link>
        </div>
      </section>

      <section>
        <div className="page-title">
          <div>
            <h1>Recent receipts</h1>
            {loadError ? (
              <p className="error">Start the FastAPI backend to load local receipts.</p>
            ) : (
              <p>Most recent uploads from the SQLite database.</p>
            )}
          </div>
        </div>
        <div className="receipt-list">
          {receipts.length === 0 ? (
            <p className="empty-state">No receipts have been uploaded yet.</p>
          ) : (
            receipts.slice(0, 6).map((receipt) => (
              <article className="receipt-card" key={receipt.id}>
                <header>
                  <div>
                    <h2>{receipt.store_name}</h2>
                    <span className="muted">{receipt.purchased_at ?? "No date parsed"}</span>
                  </div>
                  <strong>
                    {formatMoney(receipt.items.reduce((sum, item) => sum + item.price, 0))}
                  </strong>
                </header>
                <p className="muted">
                  {receipt.items.length} item{receipt.items.length === 1 ? "" : "s"} extracted
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
