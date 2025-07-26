"use client";
import React, { createContext, useContext, useState, useCallback } from "react";

interface SyncContextType {
  lastSync: number;
  triggerSync: () => void;
}

const SyncContext = createContext<SyncContextType | undefined>(undefined);

export const SyncProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lastSync, setLastSync] = useState(Date.now());

  const triggerSync = useCallback(() => {
    setLastSync(Date.now());
  }, []);

  return (
    <SyncContext.Provider value={{ lastSync, triggerSync }}>
      {children}
    </SyncContext.Provider>
  );
};

export function useSync() {
  const ctx = useContext(SyncContext);
  if (!ctx) throw new Error("useSync must be used within a SyncProvider");
  return ctx;
}
