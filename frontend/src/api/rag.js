import { getSession, refreshSession, getValidSession } from "./auth";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function authorizedFetch(path, options = {}) {
  let session = await getValidSession();
  if (!session?.access_token) {
    throw new Error("Please sign in before using Enterprise RAG.");
  }

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${session.access_token}`);

  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Access tokens are short-lived. Refresh once and retry a failed auth
  // request so an otherwise-valid browser session does not surface a 401.
  if (response.status === 401 && session.refresh_token) {
    const refreshed = await refreshSession(session);
    if (refreshed?.access_token) {
      headers.set("Authorization", `Bearer ${refreshed.access_token}`);
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers,
      });
    }
  }

  return response;
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error("Backend unavailable");
  }
  return response.json();
}

export async function uploadDocument(file) {
  if (!(file instanceof File)) {
    throw new Error("Please select a PDF document.");
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("Only PDF documents are supported.");
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await authorizedFetch("/documents", {
    method: "POST",
    body: formData,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || `Upload failed with status ${response.status}`
    );
  }

  return data;
}

export async function queryRAG(query) {
  const response = await authorizedFetch("/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || `Request failed with status ${response.status}`
    );
  }

  return data;
}
