"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "./api";
import type { Attendee } from "./types";

const STORAGE_KEY = "atlas:auth:attendee";

interface AuthState {
  attendee: Attendee | null;
  ready: boolean;
}

interface AuthContextValue extends AuthState {
  signIn: (email: string) => Promise<Attendee>;
  signUp: (input: {
    email: string;
    name: string;
    company?: string;
    role?: string;
  }) => Promise<Attendee>;
  signOut: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStored(): Attendee | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Attendee;
    if (parsed?.attendee_id && parsed?.email) return parsed;
    return null;
  } catch {
    return null;
  }
}

function writeStored(attendee: Attendee | null) {
  if (typeof window === "undefined") return;
  if (attendee) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(attendee));
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    attendee: null,
    ready: false,
  });

  useEffect(() => {
    const stored = readStored();
    if (!stored) {
      setState({ attendee: null, ready: true });
      return;
    }
    let cancelled = false;
    api
      .getAttendee(stored.attendee_id)
      .then((fresh) => {
        if (cancelled) return;
        writeStored(fresh);
        setState({ attendee: fresh, ready: true });
      })
      .catch(() => {
        if (cancelled) return;
        writeStored(null);
        setState({ attendee: null, ready: true });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string) => {
    const attendee = await api.loginAttendee(email);
    writeStored(attendee);
    setState({ attendee, ready: true });
    return attendee;
  }, []);

  const signUp = useCallback(
    async (input: {
      email: string;
      name: string;
      company?: string;
      role?: string;
    }) => {
      const attendee = await api.createAttendee(input);
      writeStored(attendee);
      setState({ attendee, ready: true });
      return attendee;
    },
    []
  );

  const signOut = useCallback(() => {
    writeStored(null);
    setState({ attendee: null, ready: true });
  }, []);

  const refresh = useCallback(async () => {
    const current = state.attendee;
    if (!current) return;
    try {
      const fresh = await api.getAttendee(current.attendee_id);
      writeStored(fresh);
      setState({ attendee: fresh, ready: true });
    } catch {
      writeStored(null);
      setState({ attendee: null, ready: true });
    }
  }, [state.attendee]);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, signIn, signUp, signOut, refresh }),
    [state, signIn, signUp, signOut, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
