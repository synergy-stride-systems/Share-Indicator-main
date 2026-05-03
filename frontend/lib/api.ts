export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:4000";
export const SCAN_BASE_URL = process.env.NEXT_PUBLIC_SCAN_BASE_URL || "http://localhost:5000";

export const apiUrl = (path: string) => `${API_BASE_URL}${path}`;
export const scanUrl = (path: string) => `${SCAN_BASE_URL}${path}`;
