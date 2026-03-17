export const apiBaseUrl =
  process.env.NEXT_PUBLIC_ATLAS_CONSOLE_API_BASE_URL ??
  process.env.ATLAS_CONSOLE_API_BASE_URL ??
  "http://127.0.0.1:8000";
