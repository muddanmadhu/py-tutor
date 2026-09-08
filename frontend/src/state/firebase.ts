/**
 * Firebase Authentication over its REST API.
 *
 * Deliberately not the `firebase` npm SDK. The SDK is ~200 kB gzipped and
 * brings an initialisation lifecycle, where all this application needs is
 * "exchange a password for an ID token, and keep that token fresh". The REST
 * endpoints do exactly that with no dependency, which also keeps the Pages
 * bundle small.
 *
 * The trade-off is federated sign-in: Google/GitHub popups need the SDK's OAuth
 * flow, so this module supports email and password only. Adding the SDK later
 * means replacing this file, not the callers — everything outside it goes
 * through `getIdToken()`.
 *
 * The web API key is public. It identifies the project and is safe in a client
 * bundle; what protects accounts is Firebase's own rate limiting and the
 * server verifying the resulting token's signature.
 */

const API_KEY = import.meta.env.VITE_FIREBASE_API_KEY as string | undefined;
const PROJECT_ID = import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined;

const IDENTITY_URL = 'https://identitytoolkit.googleapis.com/v1/accounts';
const TOKEN_URL = 'https://securetoken.googleapis.com/v1/token';

const SESSION_KEY = 'pyforge.firebase_session';
/** Refresh this far before actual expiry, so a request never races the clock. */
const REFRESH_SKEW_MS = 60_000;

/** Whether this build is configured to authenticate through Firebase. */
export const firebaseEnabled = Boolean(API_KEY && PROJECT_ID);

interface Session {
  idToken: string;
  refreshToken: string;
  /** Epoch milliseconds. */
  expiresAt: number;
}

/** Firebase returns machine-readable codes; these are the ones worth rewording. */
const MESSAGES: Record<string, string> = {
  EMAIL_EXISTS: 'An account with that email already exists.',
  EMAIL_NOT_FOUND: 'Email or password is incorrect.',
  INVALID_PASSWORD: 'Email or password is incorrect.',
  INVALID_LOGIN_CREDENTIALS: 'Email or password is incorrect.',
  INVALID_EMAIL: 'That does not look like a valid email address.',
  USER_DISABLED: 'This account has been disabled.',
  WEAK_PASSWORD: 'Password must be at least 6 characters.',
  TOO_MANY_ATTEMPTS_TRY_LATER: 'Too many attempts. Please wait a moment and try again.',
  OPERATION_NOT_ALLOWED: 'Email and password sign-in is not enabled for this project.',
};

export class FirebaseAuthError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'FirebaseAuthError';
  }
}

function readSession(): Session | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Session;
    return parsed.refreshToken ? parsed : null;
  } catch {
    // A corrupted entry is indistinguishable from no session, and clearing it
    // is kinder than failing every request until the learner clears storage.
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

function writeSession(session: Session): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

async function callIdentity(method: string, body: Record<string, unknown>) {
  const response = await fetch(`${IDENTITY_URL}:${method}?key=${API_KEY}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    // Firebase packs the code and a detail into one string, e.g.
    // "WEAK_PASSWORD : Password should be at least 6 characters".
    const code = String(payload?.error?.message ?? 'UNKNOWN').split(' :')[0] ?? 'UNKNOWN';
    throw new FirebaseAuthError(code, MESSAGES[code] ?? 'Sign in failed. Please try again.');
  }
  return payload as {
    idToken: string;
    refreshToken: string;
    expiresIn: string;
    localId: string;
    email: string;
    displayName?: string;
  };
}

function persist(result: { idToken: string; refreshToken: string; expiresIn: string }): void {
  writeSession({
    idToken: result.idToken,
    refreshToken: result.refreshToken,
    expiresAt: Date.now() + Number(result.expiresIn) * 1000,
  });
}

/** Create an account and start a session. */
export async function signUp(
  email: string,
  password: string,
  displayName: string,
): Promise<void> {
  const result = await callIdentity('signUp', { email, password, returnSecureToken: true });
  persist(result);
  if (displayName.trim()) {
    // Best-effort: the account exists either way, and the server falls back to
    // the local part of the email when no display name is set.
    await callIdentity('update', {
      idToken: result.idToken,
      displayName: displayName.trim(),
      returnSecureToken: false,
    }).catch(() => undefined);
  }
}

/** Exchange email and password for a session. */
export async function signIn(email: string, password: string): Promise<void> {
  persist(await callIdentity('signInWithPassword', { email, password, returnSecureToken: true }));
}

let refreshInFlight: Promise<string | null> | null = null;

/** Trade the refresh token for a new ID token. Concurrent callers share one attempt. */
async function refresh(session: Session): Promise<string | null> {
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${TOKEN_URL}?key=${API_KEY}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          refresh_token: session.refreshToken,
        }),
      });
      if (!response.ok) {
        // The refresh token is revoked or expired: the session is genuinely over.
        clearSession();
        return null;
      }
      const body = await response.json();
      writeSession({
        idToken: body.id_token,
        refreshToken: body.refresh_token,
        expiresAt: Date.now() + Number(body.expires_in) * 1000,
      });
      return body.id_token as string;
    } catch {
      // A network blip must not sign the learner out; the next call retries.
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/**
 * The current ID token, refreshed if it is close to expiring.
 *
 * Returns `null` when there is no session, which callers should treat as
 * "signed out" rather than as an error.
 */
export async function getIdToken(): Promise<string | null> {
  const session = readSession();
  if (!session) return null;
  if (Date.now() < session.expiresAt - REFRESH_SKEW_MS) return session.idToken;
  return refresh(session);
}

/** Whether a session exists locally, without validating it against Firebase. */
export function hasSession(): boolean {
  return readSession() !== null;
}
