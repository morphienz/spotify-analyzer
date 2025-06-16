export function getApiBaseUrl() {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim() !== "") {
    return envUrl;
  }
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8080`;
}

export const API_BASE_URL = getApiBaseUrl();