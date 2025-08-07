import '../styles/globals.css';
import { SpeedInsights } from "@vercel/speed-insights/next"
import { Analytics } from "@vercel/analytics/react"
import Navbar from '../components/Navbar';
import { SyncProvider } from '../lib/syncContext';
import ClientLayout from './ClientLayout';
import Providers from '../components/Providers';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50">
        <Providers>
          <ClientLayout>
            <SyncProvider>
              <Navbar />
              {children}
              <SpeedInsights />
              <Analytics />
            </SyncProvider>
          </ClientLayout>
        </Providers>
      </body>
    </html>
  );
}
