"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError, configureApi } from "./api";
import { getSupabase, supabaseEnabled } from "./supabase";
import type { User } from "./types";

type Provider = "local" | "demo" | "supabase";
interface StoredSession {
  token: string;
  provider: Exclude<Provider, "supabase">;
  expires_at: string;
}
interface SessionResponse {
  access_token: string;
  expires_at: string;
  user: User;
  groups?: { id: string; name: string }[];
}

interface AuthState {
  /** "unreachable": a session exists but the API could not be reached (e.g. server waking up). */
  status: "loading" | "authenticated" | "anonymous" | "unreachable";
  user: User | null;
  provider: Provider | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<{ needsConfirmation: boolean }>;
  startDemo: () => Promise<string | null>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);
const STORAGE_KEY = "gw:session";

function readStored(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as StoredSession;
    if (new Date(s.expires_at).getTime() < Date.now()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return s;
  } catch {
    return null;
  }
}

function writeStored(s: StoredSession | null) {
  try {
    localStorage.removeItem("gw:lastGroup"); // never carry navigation state across accounts
    if (s) localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable (private mode) — session lives in memory only */
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [provider, setProvider] = useState<Provider | null>(null);
  const memorySession = useRef<StoredSession | null>(null);

  const clear = useCallback(() => {
    writeStored(null);
    memorySession.current = null;
    setUser(null);
    setProvider(null);
    setStatus("anonymous");
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    configureApi(
      async () => {
        if (memorySession.current) return memorySession.current.token;
        const sb = getSupabase();
        if (sb) {
          const { data } = await sb.auth.getSession();
          return data.session?.access_token ?? null;
        }
        return null;
      },
      () => {
        const wasSignedIn = Boolean(memorySession.current) || provider === "supabase";
        clear();
        getSupabase()?.auth.signOut();
        if (wasSignedIn) router.replace("/login?expired=1");
      },
    );
  }, [clear, provider, router]);

  const loadMe = useCallback(async () => {
    const me = await api<User>("/me");
    setUser(me);
    setStatus("authenticated");
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const stored = readStored();
      if (stored) {
        memorySession.current = stored;
        setProvider(stored.provider);
      } else if (supabaseEnabled) {
        const { data } = await getSupabase()!.auth.getSession();
        if (data.session) setProvider("supabase");
        else {
          if (!cancelled) setStatus("anonymous");
          return;
        }
      } else {
        if (!cancelled) setStatus("anonymous");
        return;
      }
      try {
        await loadMe();
      } catch (e) {
        if (cancelled) return;
        // Only a definite 401 ends the session; outages and cold starts must not log people out.
        if ((e as ApiError).status === 401) clear();
        else setStatus("unreachable");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const adopt = useCallback(
    (res: SessionResponse, p: Exclude<Provider, "supabase">) => {
      const s = { token: res.access_token, provider: p, expires_at: res.expires_at };
      memorySession.current = s;
      writeStored(s);
      queryClient.clear();
      setProvider(p);
      setUser(res.user);
      setStatus("authenticated");
    },
    [queryClient],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      const sb = getSupabase();
      if (sb) {
        const { error } = await sb.auth.signInWithPassword({ email, password });
        if (error) throw new ApiError(401, error.message === "Invalid login credentials" ? "Incorrect email or password." : error.message);
        memorySession.current = null;
        writeStored(null);
        setProvider("supabase");
        await loadMe();
        return;
      }
      adopt(await api<SessionResponse>("/auth/login", { body: { email, password }, auth: false }), "local");
    },
    [adopt, loadMe],
  );

  const signUp = useCallback(
    async (name: string, email: string, password: string) => {
      const sb = getSupabase();
      if (sb) {
        const { data, error } = await sb.auth.signUp({ email, password, options: { data: { display_name: name } } });
        if (error) throw new ApiError(400, error.message);
        if (!data.session) return { needsConfirmation: true };
        setProvider("supabase");
        await loadMe();
        return { needsConfirmation: false };
      }
      adopt(await api<SessionResponse>("/auth/signup", { body: { display_name: name, email, password }, auth: false }), "local");
      return { needsConfirmation: false };
    },
    [adopt, loadMe],
  );

  const startDemo = useCallback(async () => {
    const res = await api<SessionResponse>("/demo/session", { method: "POST", auth: false });
    adopt(res, "demo");
    return res.groups?.[0]?.id ?? null;
  }, [adopt]);

  const signOut = useCallback(async () => {
    if (provider === "supabase") await getSupabase()?.auth.signOut();
    clear();
    router.replace("/");
  }, [clear, provider, router]);

  const value = useMemo<AuthState>(
    () => ({ status, user, provider, signIn, signUp, startDemo, signOut, refreshUser: loadMe }),
    [status, user, provider, signIn, signUp, startDemo, signOut, loadMe],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
