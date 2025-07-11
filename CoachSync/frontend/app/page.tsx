import Link from "next/link";
import "../styles/globals.css";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-8">
      <h1 className="text-4xl font-bold text-blue-700 mb-2">CoachSync</h1>
      <p className="mb-8 text-gray-600">
        AI assistant for personal trainers and fitness coaches
      </p>
      <nav className="flex flex-col gap-4 w-full max-w-xs">
        <Link href="/dashboard" className="btn-primary">
          Dashboard
        </Link>
        <Link href="/upload" className="btn-secondary">
          Upload Coaching Call
        </Link>
        <Link href="/timeline" className="btn-secondary">
          Session Timeline
        </Link>
      </nav>
    </main>
  );
}
