const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "cars_jwt";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export interface Car {
  id: number;
  brand: string;
  model: string;
  year: number;
  price: number;
  color: string;
  link: string;
  total_price?: number | null;
  transmission?: string | null;
  title?: string | null;
  mileage_km?: number | null;
  mileage_display?: string | null;
  body_type?: string | null;
}

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const res = await fetch(`${API_URL}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Login failed");
  }
  return res.json();
}

export type CarsSortBy =
  | "id"
  | "brand"
  | "model"
  | "year"
  | "price"
  | "total_price"
  | "updated_at"
  | "mileage_km"
  | "body_type";
export type CarsOrder = "asc" | "desc";

export interface CarsFilters {
  brand?: string;
  model?: string;
  color?: string;
  year_min?: number;
  year_max?: number;
  price_min?: number;
  price_max?: number;
  body_type?: string;
  transmission?: string;
  mileage_max_km?: number;
  drive_type?: string;
  engine_type?: string;
  q?: string;
}

export interface GetCarsParams {
  skip?: number;
  limit?: number;
  sort_by?: CarsSortBy;
  order?: CarsOrder;
  brand?: string;
  model?: string;
  color?: string;
  year_min?: number;
  year_max?: number;
  price_min?: number;
  price_max?: number;
  body_type?: string;
  transmission?: string;
  mileage_max_km?: number;
  drive_type?: string;
  engine_type?: string;
  q?: string;
}

export interface ParsedSearchParams {
  brand?: string;
  model?: string;
  color?: string;
  year_min?: number;
  year_max?: number;
  price_max_rub?: number;
  transmission?: string;
  mileage_max_km?: number;
  body_type?: string;
  drive_type?: string;
  engine_type?: string;
}

export async function parseSearchQuery(token: string, q: string): Promise<ParsedSearchParams> {
  const res = await fetch(`${API_URL}/api/cars/parse-query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ q: q.trim() }),
  });
  if (!res.ok) return {};
  const data = await res.json();
  return data && typeof data === "object" ? data : {};
}

export async function getCars(token: string, params?: GetCarsParams): Promise<Car[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.sort_by) sp.set("sort_by", params.sort_by);
  if (params?.order) sp.set("order", params.order);
  if (params?.brand != null && params.brand !== "") sp.set("brand", params.brand);
  if (params?.model != null && params.model !== "") sp.set("model", params.model);
  if (params?.color != null && params.color !== "") sp.set("color", params.color);
  if (params?.year_min != null) sp.set("year_min", String(params.year_min));
  if (params?.year_max != null) sp.set("year_max", String(params.year_max));
  if (params?.price_min != null) sp.set("price_min", String(params.price_min));
  if (params?.price_max != null) sp.set("price_max", String(params.price_max));
  if (params?.body_type != null && params.body_type !== "") sp.set("body_type", params.body_type);
  if (params?.transmission != null && params.transmission !== "") sp.set("transmission", params.transmission);
  if (params?.mileage_max_km != null) sp.set("mileage_max_km", String(params.mileage_max_km));
  if (params?.drive_type != null && params.drive_type !== "") sp.set("drive_type", params.drive_type);
  if (params?.engine_type != null && params.engine_type !== "") sp.set("engine_type", params.engine_type);
  if (params?.q != null && params.q !== "") sp.set("q", params.q);
  const queryString = sp.toString();
  const url = queryString ? `${API_URL}/api/cars?${queryString}` : `${API_URL}/api/cars`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new ApiError("Failed to fetch cars", res.status);
  return res.json();
}

export interface FilterOptions {
  brands: string[];
  body_types: string[];
  transmissions: string[];
  year_min: number;
  year_max: number;
  price_min: number;
  price_max: number;
}

export async function getFilterOptions(token: string): Promise<FilterOptions> {
  const res = await fetch(`${API_URL}/api/cars/filter-options`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new ApiError("Failed to fetch filter options", res.status);
  return res.json();
}

export async function getCarsCount(token: string, filters?: CarsFilters): Promise<{ total: number }> {
  const sp = new URLSearchParams();
  if (filters?.brand != null && filters.brand !== "") sp.set("brand", filters.brand);
  if (filters?.model != null && filters.model !== "") sp.set("model", filters.model);
  if (filters?.color != null && filters.color !== "") sp.set("color", filters.color);
  if (filters?.year_min != null) sp.set("year_min", String(filters.year_min));
  if (filters?.year_max != null) sp.set("year_max", String(filters.year_max));
  if (filters?.price_min != null) sp.set("price_min", String(filters.price_min));
  if (filters?.price_max != null) sp.set("price_max", String(filters.price_max));
  if (filters?.body_type != null && filters.body_type !== "") sp.set("body_type", filters.body_type);
  if (filters?.transmission != null && filters.transmission !== "") sp.set("transmission", filters.transmission);
  if (filters?.mileage_max_km != null) sp.set("mileage_max_km", String(filters.mileage_max_km));
  if (filters?.drive_type != null && filters.drive_type !== "") sp.set("drive_type", filters.drive_type);
  if (filters?.engine_type != null && filters.engine_type !== "") sp.set("engine_type", filters.engine_type);
  if (filters?.q != null && filters.q !== "") sp.set("q", filters.q);
  const queryString = sp.toString();
  const url = queryString ? `${API_URL}/api/cars/count?${queryString}` : `${API_URL}/api/cars/count`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new ApiError("Failed to fetch count", res.status);
  return res.json();
}

export async function getRates(token: string): Promise<{ jpy_rub: number }> {
  const res = await fetch(`${API_URL}/api/rates`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new ApiError("Failed to fetch rates", res.status);
  return res.json();
}
