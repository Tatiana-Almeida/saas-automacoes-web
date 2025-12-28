export function normalizeHost(host: string | null | undefined): string | null {
  if (!host) return null;
  try {
    // strip port if present
    const h = host.split(":")[0];
    return h.toLowerCase();
  } catch (e) {
    return host || null;
  }
}

export function getTenantHost(): string | null {
  try {
    const stored = typeof window !== "undefined" && window.sessionStorage
      ? window.sessionStorage.getItem("tenantHost")
      : null;
    if (stored) return normalizeHost(stored);
    if (typeof window !== "undefined" && window.location) {
      return normalizeHost(window.location.hostname);
    }
    return null;
  } catch (e) {
    return null;
  }
}

export function setTenantHost(host: string | null) {
  try {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    if (host) {
      window.sessionStorage.setItem("tenantHost", normalizeHost(host) || "");
    } else {
      window.sessionStorage.removeItem("tenantHost");
    }
  } catch (e) {
    // noop
  }
}
