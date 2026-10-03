import { WifiOff } from "lucide-react";

import { LogoMark } from "@/components/brand/logo";

export const metadata = { title: "Offline" };

export default function OfflinePage() {
  return (
    <div className="grid min-h-dvh place-items-center bg-surface px-4">
      <div className="max-w-sm text-center">
        <LogoMark className="mx-auto size-14" />
        <WifiOff className="mx-auto mt-6 size-6 text-ink-muted" aria-hidden />
        <h1 className="mt-2 text-xl font-extrabold text-ink">You&apos;re offline</h1>
        <p className="mt-1 text-sm text-ink-muted">
          GroupWise needs a connection to show your group&apos;s latest balances and insights. Financial data is never stored offline on this device.
        </p>
      </div>
    </div>
  );
}
