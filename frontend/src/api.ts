import axios from "axios";
import { getTenantHost } from "./utils/tenant";

const api = axios.create({
  baseURL: "/api/",
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  try {
    const host = getTenantHost();
    if (host) {
      config.headers = config.headers || {};
      // backend expects X-Tenant-Host when running through the multi-tenant detection
      // in tests we also set this header to force tenant resolution without DB lookups
      (config.headers as any)["X-TENANT-HOST"] = host;
    }
  } catch (e) {
    // noop
  }
  return config;
});

export default api;
