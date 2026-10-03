"use client";

import { Loader2, PlayCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export function DemoButton({ size = "lg", variant = "default", label = "Explore the live demo", className }: { size?: "lg" | "default"; variant?: "default" | "blue" | "outline"; label?: string; className?: string }) {
  const { startDemo } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function go() {
    setBusy(true);
    // Free hosting tiers sleep when idle; explain why the very first start can take a while.
    const slow = setTimeout(
      () => toast.info("Waking up the AI service…", { description: "On free hosting the first start can take up to a minute. Your private sandbox is being generated.", duration: 15000 }),
      6000,
    );
    try {
      const first = await startDemo();
      router.push(first ? `/g/${first}` : "/groups");
    } catch (e) {
      toast.error((e as Error).message || "Couldn't start the demo. Please try again.");
      setBusy(false);
    } finally {
      clearTimeout(slow);
    }
  }

  return (
    <Button size={size} variant={variant} onClick={go} disabled={busy} className={className}>
      {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <PlayCircle className="size-4" aria-hidden />}
      {busy ? "Preparing your private demo…" : label}
    </Button>
  );
}
