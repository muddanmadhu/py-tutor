/** Authentication state, shared through context. */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { ApiError, tokens } from '@/api/client';
import { auth } from '@/api/endpoints';
import type { User } from '@/api/types';
import {
  clearSession,
  firebaseEnabled,
  hasSession,
  signIn as firebaseSignIn,
  signUp as firebaseSignUp,
} from '@/state/firebase';

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    email: string;
    password: string;
    display_name: string;
    declared_level?: string;
    goal?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/** Whether any credential is stored, under whichever scheme is configured. */
function hasCredentials(): boolean {
  return firebaseEnabled ? hasSession() : Boolean(tokens.access);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!hasCredentials()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await auth.me());
    } catch (error) {
      // A 401 here means the stored credential is dead; anything else is
      // transient and should not silently log the learner out mid-session.
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
        tokens.clear();
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    if (firebaseEnabled) {
      // Firebase issues the credential; the account row is provisioned by the
      // API the first time it sees the token, so `me()` is what tells us who
      // we are rather than the sign-in response.
      await firebaseSignIn(email, password);
      setUser(await auth.me());
      return;
    }
    const response = await auth.login({ email, password });
    tokens.set(response.tokens.access_token, response.tokens.refresh_token);
    setUser(response.user);
  }, []);

  const register = useCallback<AuthState['register']>(async (input) => {
    if (firebaseEnabled) {
      await firebaseSignUp(input.email, input.password, input.display_name);
      const created = await auth.me();
      // Firebase holds only the credential, so the learning profile fields go
      // to our API as a follow-up rather than being part of sign-up.
      setUser(
        input.declared_level || input.goal
          ? await auth.updateProfile({
              display_name: input.display_name,
              declared_level: input.declared_level,
              goal: input.goal,
            })
          : created,
      );
      return;
    }
    const response = await auth.register(input);
    tokens.set(response.tokens.access_token, response.tokens.refresh_token);
    setUser(response.user);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    tokens.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// The hook lives beside its provider so callers have one import. That costs
// fast-refresh granularity for this file only, which is a fair trade.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}
