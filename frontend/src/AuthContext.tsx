import React, { createContext, useContext, useEffect, useState } from "react";
import { getTenantHost, setTenantHost as persistTenantHost } from "./utils/tenant";

type AuthContextType = {
  tenantHost: string | null;
  setTenantHost: (h: string | null) => void;
};

const DEFAULT: AuthContextType = {
  tenantHost: null,
  setTenantHost: () => {},
};

export const AuthContext = createContext<AuthContextType>(DEFAULT);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [tenantHost, setTenantHostState] = useState<string | null>(null);

  useEffect(() => {
    setTenantHostState(getTenantHost());
  }, []);

  const setTenantHost = (h: string | null) => {
    persistTenantHost(h);
    setTenantHostState(h);
  };

  return (
    <AuthContext.Provider value={{ tenantHost, setTenantHost }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
