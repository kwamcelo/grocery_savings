import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Grocery Savings",
  description: "Find better grocery prices from your receipts.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppNav />
          <main>{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
