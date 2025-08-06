"use client";
import { SyncProvider } from "../lib/syncContext";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <SyncProvider>
      {children}
    </SyncProvider>
  );
}
