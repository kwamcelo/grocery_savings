"use client";

import Link from "next/link";
import { BarChart3, LogOut, ReceiptText, Search, Upload, UserRound } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";

const links = [
  { href: "/", label: "Home", icon: ReceiptText },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/search", label: "Search", icon: Search },
  { href: "/compare", label: "Compare", icon: BarChart3 },
];

export function AppNav() {
  const { user, signOut } = useAuth();

  return (
    <header className="app-header">
      <Link className="brand" href="/">
        Grocery Savings
      </Link>
      <nav className="nav-links" aria-label="Main navigation">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <Link key={link.href} href={link.href}>
              <Icon size={18} aria-hidden="true" />
              <span>{link.label}</span>
            </Link>
          );
        })}
        {user ? (
          <button className="nav-auth-button" type="button" onClick={signOut}>
            <LogOut size={18} aria-hidden="true" />
            <span>Sign out</span>
          </button>
        ) : (
          <Link href="/account">
            <UserRound size={18} aria-hidden="true" />
            <span>Account</span>
          </Link>
        )}
      </nav>
    </header>
  );
}
