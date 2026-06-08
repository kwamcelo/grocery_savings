import Link from "next/link";
import { BarChart3, ReceiptText, Search, Upload } from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", icon: ReceiptText },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/search", label: "Search", icon: Search },
  { href: "/compare", label: "Compare", icon: BarChart3 },
];

export function AppNav() {
  return (
    <header className="app-header">
      <Link className="brand" href="/">
        Receipt Prices
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
      </nav>
    </header>
  );
}
