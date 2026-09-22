"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/schemes", label: "Course schemes" },
  { href: "/timetables", label: "Timetables" },
  { href: "/build-timetable", label: "Build timetable" },
  { href: "/teachers", label: "Teachers" },
  { href: "/dashboard", label: "Stats overview" },
];

export function SiteHeader() {
  // Top bar on every page: the logo leads home, and the links cover the sections that work
  // today. On a phone the links drop onto their own row instead of overflowing.
  const pathname = usePathname();

  return (
    <header className="border-b border-content/10 bg-card">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-1 px-4 py-2 sm:px-6">
        <Link href="/" className="flex min-h-11 items-center gap-2 font-semibold text-content">
          <Image src="/imcs-logo.png" alt="" width={32} height={32} />
          IMCS Scheduler
        </Link>
        <nav aria-label="Main" className="flex flex-wrap gap-1 text-sm">
          {NAV_LINKS.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-11 items-center rounded-lg px-3 font-medium ${
                  active ? "bg-primary text-white" : "text-content/70 hover:bg-content/5 hover:text-content"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
