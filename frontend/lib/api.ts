export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ReceiptItem = {
  id: number;
  receipt_id: number;
  store_id: number;
  normalized_product_id: number | null;
  raw_item_name: string;
  name: string;
  normalized_product_name: string | null;
  quantity: number | null;
  unit: string | null;
  price: number;
  purchased_at: string | null;
};

export type Receipt = {
  id: number;
  store_id: number;
  store_name: string;
  purchased_at: string | null;
  original_filename: string | null;
  image_path: string | null;
  raw_text: string;
  created_at: string;
  items: ReceiptItem[];
};

export type ParsedReceiptItem = {
  line: string;
  name: string;
  quantity: string | null;
  price: number;
};

export type ParsedReceipt = {
  store_name: string;
  store_location_text: string | null;
  store_phone: string | null;
  purchased_at: string | null;
  items: ParsedReceiptItem[];
};

export type ReceiptUploadResponse = {
  receipt: Receipt;
  image_path: string;
  extracted_text: string;
  parsed: ParsedReceipt;
};

export type SearchResult = {
  item_id: number;
  raw_item_name: string;
  name: string;
  normalized_product_name: string | null;
  quantity: number | null;
  unit: string | null;
  price: number;
  store_id: number;
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

export async function uploadReceipt(file: File): Promise<ReceiptUploadResponse> {
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
