export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ReceiptItem = {
  id: number;
  receipt_id: number;
  name: string;
  quantity: string | null;
  price: number;
};

export type Receipt = {
  id: number;
  store_name: string;
  purchased_at: string | null;
  original_filename: string | null;
  raw_text: string;
  created_at: string;
  items: ReceiptItem[];
};

export type SearchResult = {
  item_id: number;
  name: string;
  quantity: string | null;
  price: number;
  store_name: string;
  purchased_at: string | null;
  receipt_id: number;
};

export type StorePriceSummary = {
  store_name: string;
  lowest_price: number;
  highest_price: number;
  average_price: number;
  observations: number;
};

export type CompareResult = {
  query: string;
  matches: SearchResult[];
  by_store: StorePriceSummary[];
};

export async function uploadReceipt(file: File): Promise<Receipt> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_URL}/receipts/upload`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json();
}

export async function fetchReceipts(): Promise<Receipt[]> {
  const response = await fetch(`${API_URL}/receipts`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load receipts");
  }
  return response.json();
}

export async function searchItems(query: string): Promise<SearchResult[]> {
  const response = await fetch(`${API_URL}/items/search?q=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error("Unable to search items");
  }
  return response.json();
}

export async function compareItems(name: string): Promise<CompareResult> {
  const response = await fetch(`${API_URL}/items/compare?name=${encodeURIComponent(name)}`);
  if (!response.ok) {
    throw new Error("Unable to compare prices");
  }
  return response.json();
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}
