const defaultApiBaseUrl = typeof window !== "undefined" && window.location.hostname.includes("azurewebsites.net")
  ? "https://synergyapp-backend-dfg3gbb5ddhddqew.canadacentral-01.azurewebsites.net"
  : "http://localhost:4000";

const defaultScanBaseUrl = process.env.NEXT_PUBLIC_SCAN_BASE_URL || "http://localhost:5000";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || defaultApiBaseUrl;
export const SCAN_BASE_URL = defaultScanBaseUrl;

export const apiUrl = (path: string) => `${API_BASE_URL}${path}`;
export const scanUrl = (path: string) => `${SCAN_BASE_URL}${path}`;
