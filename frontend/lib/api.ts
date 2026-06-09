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
  unit_price: number | null;
  unit_price_unit: string | null;
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
  unit: string | null;
  unit_price: number | null;
  unit_price_unit: string | null;
  price: number;
  normalization_suggestion: NormalizationSuggestion | null;
};

export type NormalizationSuggestion = {
  product_id: number;
  product_name: string;
  score: number;
  matched_on: string;
  auto_match: boolean;
};

export type ParsedReceipt = {
  store_name: string;
  store_location_text: string | null;
  purchased_at: string | null;
  items: ParsedReceiptItem[];
};

export type ReceiptPreviewResponse = {
  image_path: string;
  original_filename: string | null;
  extracted_text: string;
  parsed: ParsedReceipt;
};

export type CorrectedReceiptItem = {
  name: string;
  price: number;
  quantity: string | null;
  unit: string | null;
  unit_price: number | null;
  unit_price_unit: string | null;
  source_line: string | null;
  normalized_product_id: number | null;
  reject_normalization_suggestion: boolean;
};

export type SaveReceiptRequest = {
  store_name: string;
  store_location_text: string | null;
  purchased_at: string | null;
  image_path: string | null;
  original_filename: string | null;
  raw_text: string;
  items: CorrectedReceiptItem[];
};

export type SearchResult = {
  item_id: number;
  raw_item_name: string;
  name: string;
  normalized_product_name: string | null;
  quantity: number | null;
  unit: string | null;
  source_unit_price: number | null;
  source_unit_price_unit: string | null;
  price: number;
  unit_price: number | null;
  unit_price_label: string | null;
  comparison_price: number | null;
  comparison_basis: string;
  comparison_reliable: boolean;
  comparison_warning: string | null;
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
  lowest_unit_price: number | null;
  lowest_unit_price_label: string | null;
  comparison_price: number;
  comparison_basis: string;
  comparison_reliable: boolean;
  comparison_warning: string | null;
};

export type CompareResult = {
  query: string;
  matches: SearchResult[];
  by_store: StorePriceSummary[];
};

export type ProductSearchCandidate = {
  product_id: number;
  name: string;
  category: string | null;
  aliases: string[];
  matched_raw_item_names: string[];
  lowest_observed_price: number | null;
  most_recent_observed_price: number | null;
  last_purchased_at: string | null;
};

export type ProductPurchaseRecord = {
  item_id: number;
  receipt_id: number;
  raw_item_name: string;
  price: number;
  unit_price: number | null;
  unit_price_unit: string | null;
  quantity: number | null;
  unit: string | null;
  purchased_at: string | null;
};

export type ProductStorePriceGroup = {
  store_id: number;
  store_name: string;
  lowest_observed_price: number;
  most_recent_observed_price: number;
  last_purchased_at: string | null;
  purchases: ProductPurchaseRecord[];
};

export type ProductPriceHistory = {
  product_id: number;
  product_name: string;
  stores: ProductStorePriceGroup[];
};

export async function previewReceipt(file: File): Promise<ReceiptPreviewResponse> {
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

export async function saveReceipt(payload: SaveReceiptRequest): Promise<Receipt> {
  const response = await fetch(`${API_URL}/receipts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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

export async function searchProducts(query: string): Promise<ProductSearchCandidate[]> {
  const response = await fetch(`${API_URL}/products/search?q=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error("Unable to search products");
  }
  return response.json();
}

export async function fetchProductPriceHistory(productId: number): Promise<ProductPriceHistory> {
  const response = await fetch(`${API_URL}/products/${productId}/price-history`);
  if (!response.ok) {
    throw new Error("Unable to load product price history");
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
