const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || "").replace(/\/$/, "");
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";
const SESSION_KEY = "enterprise-rag-session";

function requireConfig() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("Supabase frontend configuration is missing.");
  }
}

export function getSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveSession(session) {
  if (session?.access_token) {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } else {
    sessionStorage.removeItem(SESSION_KEY);
  }
}

export async function signIn(email, password) {
  requireConfig();

  const response = await fetch(
    `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
    {
      method: "POST",
      headers: {
        apikey: SUPABASE_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok || !data.access_token) {
    throw new Error(
      data.error_description || data.msg || data.message || "Sign-in failed."
    );
  }

  saveSession(data);
  return data;
}

export function signOut() {
  saveSession(null);
}

export async function refreshSession(session = getSession()) {
  if (!session?.refresh_token) return null;
  requireConfig();

  const response = await fetch(
    `${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`,
    {
      method: "POST",
      headers: {
        apikey: SUPABASE_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    }
  );

  if (!response.ok) {
    saveSession(null);
    return null;
  }

  const data = await response.json();
  if (!data.access_token) {
    saveSession(null);
    return null;
  }

  saveSession(data);
  return data;
}

export async function getValidSession() {
  const current = getSession();
  if (!current?.access_token) return null;

  const expiresAtMs = Number(current.expires_at || 0) * 1000;
  const expiresInMs = Number(current.expires_in || 0) * 1000;
  const now = Date.now();

  // Refresh when the token is expired or within the next 60 seconds.
  const effectiveExpiry = expiresAtMs || (expiresInMs ? now + expiresInMs : 0);
  if (effectiveExpiry && effectiveExpiry <= now + 60_000) {
    return refreshSession(current);
  }

  return current;
}

export function getAccessToken() {
  return getSession()?.access_token || null;
}
