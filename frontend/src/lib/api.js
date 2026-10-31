const BASE = "/api/v1";

/** Every failed request throws this, carrying the backend's {code, detail, fields}. */
export class ApiError extends Error {
  constructor(status, { code, detail, fields } = {}) {
    super(detail || "Something went wrong. Please try again.");
    this.status = status;
    this.code = code || "error";
    this.fields = fields || {};
  }
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function ensureCsrfCookie() {
  if (!readCookie("csrftoken")) {
    await fetch(`${BASE}/auth/csrf`, { credentials: "same-origin" });
  }
  return readCookie("csrftoken");
}

export async function api(path, { method = "GET", body, params } = {}) {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRFToken"] = await ensureCsrfCookie();

  let response;
  try {
    response = await fetch(`${BASE}${path}${query}`, {
      method,
      headers,
      credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, { code: "network_error", detail: "Can't reach the server. Check your connection." });
  }

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data || {});
  return data;
}
