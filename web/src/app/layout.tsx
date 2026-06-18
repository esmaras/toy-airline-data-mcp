import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClearPath — Airline Data Assistant",
  description: "Southwest Airlines operational data assistant powered by ClearPath",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}
