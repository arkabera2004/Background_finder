"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { chanakyaApi } from "@/lib/chanakya-api";

const TABS = [
  { href: "/chanakya", label: "Monthly runs" },
  { href: "/chanakya/schedules", label: "Schedules" },
] as const;

export function ChanakyaSubNav() {
  const pathname = usePathname();
  const [counts, setCounts] = useState<{ runs: number; schedules: number } | null>(null);

  useEffect(() => {
    Promise.all([chanakyaApi.listRuns(), chanakyaApi.listSchedules()])
      .then(([runs, schedules]) => setCounts({ runs: runs.length, schedules: schedules.length }))
      .catch(() => setCounts(null));
  }, []);

  const countFor = (href: (typeof TABS)[number]["href"]) =>
    href === "/chanakya" ? counts?.runs : counts?.schedules;

  return (
    <nav className="flex gap-1 border-b border-[var(--stroke-muted)]" aria-label="Chanakya sections">
      {TABS.map(({ href, label }) => {
        const active = pathname === href;
        const count = countFor(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2 border-b-2 px-3 py-2 text-sm transition-colors",
              active
                ? "border-primary font-medium text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {label}
            {count !== undefined && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                {count}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
