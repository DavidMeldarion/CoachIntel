import '../styles/globals.css';
import { SpeedInsights } from "@vercel/speed-insights/next"
import { Analytics } from "@vercel/analytics/react"
import NavbarServer from '../components/NavbarServer';
import { SyncProvider } from '../lib/syncContext';
import ClientLayout from './ClientLayout';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50">
        <ClientLayout>
          <SyncProvider>
            <NavbarServer />
            {children}
            <SpeedInsights />
            <Analytics />
          </SyncProvider>
        </ClientLayout>
      </body>
    </html>
  );
}
