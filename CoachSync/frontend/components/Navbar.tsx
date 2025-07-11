import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="w-full flex justify-center gap-8 py-4 bg-white shadow mb-8">
      <Link href="/dashboard" className="text-blue-700 font-semibold hover:underline">Dashboard</Link>
      <Link href="/upload" className="text-blue-700 font-semibold hover:underline">Upload</Link>
      <Link href="/timeline" className="text-blue-700 font-semibold hover:underline">Timeline</Link>
    </nav>
  );
}
