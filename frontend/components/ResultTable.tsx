import { SearchResult, formatMoney } from "@/lib/api";

type ResultTableProps = {
  results: SearchResult[];
};

export function ResultTable({ results }: ResultTableProps) {
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
            <th className="numeric">Price</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.item_id}>
              <td>{result.name}</td>
              <td>{result.quantity ?? "-"}</td>
              <td>{result.store_name}</td>
              <td>{result.purchased_at ?? "-"}</td>
              <td className="numeric">{formatMoney(result.price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
