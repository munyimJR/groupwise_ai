import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

/** Supabase Auth is used when configured; otherwise GroupWise's own API issues sessions. Only the public anon key is ever used here. */
export const supabaseEnabled = Boolean(url && anonKey);

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (!supabaseEnabled) return null;
  if (!client) {
    client = createClient(url!, anonKey!, { auth: { persistSession: true, autoRefreshToken: true, storageKey: "gw-supabase" } });
  }
  return client;
}
