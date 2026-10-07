// Talks to the backend. The login token is kept in localStorage.
// VITE_API_URL (build-time) = where the API lives if it is NOT on the same domain (empty on Vercel / local dev).
const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export function getToken() {
  return localStorage.getItem("token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

type Options = { method?: string; body?: unknown; form?: FormData };

export async function api<T = any>(path: string, options: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined = options.form;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  let res: Response;
  try {
    res = await fetch(API_BASE + path, { method: options.method ?? (body ? "POST" : "GET"), headers, body });
  } catch {
    throw new Error("Cannot reach the app. Is the frontend running?");
  }
  // The frontend dev server answers 500/502/504 with no JSON when the backend is not running.
  if ([500, 502, 503, 504].includes(res.status) && !res.headers.get("content-type")?.includes("json")) {
    throw new Error(import.meta.env.DEV ? "The backend is not running. Start it with ./start.sh (see README)."
      : `The server had a problem (error ${res.status}). Check the deployment logs and environment variables.`);
  }
  if (res.status === 401 && !path.startsWith("/api/auth")) {
    setToken(null);
    window.location.href = "/"; // back to the login screen
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : `Error ${res.status}`);
  }
  return data as T;
}

/** Download a file from the backend (needs the login token, so a plain link would not work). */
export async function download(path: string, fileName: string, postBody?: unknown) {
  const headers: Record<string, string> = { Authorization: `Bearer ${getToken()}` };
  if (postBody !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(API_BASE + path, postBody === undefined ? { headers } : { method: "POST", headers, body: JSON.stringify(postBody) });
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? `Error ${res.status}`);
  // The server names the file after your profile (e.g. Jane_Doe_CV_Company.docx); fileName is only the fallback.
  const fromServer = /filename="?([^";]+)"?/.exec(res.headers.get("content-disposition") ?? "")?.[1];
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = fromServer ?? fileName;
  link.click();
  URL.revokeObjectURL(url);
}
