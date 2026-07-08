export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? API_URL.replace(/^http/, "ws") + "/ws/live";

export async function fetchCases(limit = 50) {
  const res = await fetch(`${API_URL}/api/cases?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch cases: ${res.status}`);
  return res.json();
}
