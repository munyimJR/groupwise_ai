"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

/** Keep legacy bookmarks useful after removing the sensitive dynamics surface. */
export default function DynamicsRedirect() {
  const { groupId } = useParams<{ groupId: string }>();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/g/${groupId}/balances`);
  }, [groupId, router]);

  return <p className="p-6 text-sm text-ink-muted">Opening balances…</p>;
}
