"use client";
import { SyncProvider } from "../lib/syncContext";
import { UserProvider } from "../lib/userContext";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <SyncProvider>
      <UserProvider>
        {children}
      </UserProvider>
    </SyncProvider>
  );
}
