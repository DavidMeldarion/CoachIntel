import '../styles/globals.css';
import { SpeedInsights } from "@vercel/speed-insights/next"
import { Analytics } from "@vercel/analytics/react"
import Navbar from '../components/Navbar';
import { SyncProvider } from '../lib/syncContext';
import ClientLayout from './ClientLayout';
import Providers from '../components/Providers';
import { authOptions } from "../lib/auth";
import { getServerSession } from "next-auth";

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);
  return (
    <html lang="en">
  <body className="bg-gray-50 font-sans text-slate-900">
        <Providers session={session}>
          <ClientLayout>
            <Navbar />
            {children}
            <SpeedInsights />
            <Analytics />
          </ClientLayout>
        </Providers>
      </body>
    </html>
  );
}
