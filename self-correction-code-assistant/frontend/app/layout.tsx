import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Self-Correction Code Assistant",
  description: "A Loop Engineering workspace for iterative code correction.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
