"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { createClient } from "@/lib/supabase/client";

export function AppTopbar({ email }: { email: string | null }) {
  const { theme, setTheme } = useTheme();

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    window.location.href = "/login";
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--stroke-muted)] bg-[var(--surface-container)] px-4">
      <SidebarTrigger className="icon-tertiary hover:icon-secondary" />
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full icon-tertiary hover:bg-[var(--surface-raised-x2)] hover:icon-secondary"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <Sun size={16} strokeWidth={1.75} className="dark:hidden" />
          <Moon size={16} strokeWidth={1.75} className="hidden dark:block" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="gap-2">
              <Avatar className="h-6 w-6">
                <AvatarFallback>{(email ?? "?")[0]?.toUpperCase()}</AvatarFallback>
              </Avatar>
              <span className="text-sm text-[var(--text-tertiary)]">{email ?? "Account"}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={signOut}>Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
