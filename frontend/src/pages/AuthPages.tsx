/** Sign in and registration. */

import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { useAuth } from '@/state/auth';
import { FirebaseAuthError } from '@/state/firebase';

/**
 * Turn a thrown value into something worth showing.
 *
 * Sign-in can fail at either layer — Firebase rejecting the credential, or our
 * API rejecting the resulting token — and both already carry learner-facing
 * wording, so the fallback is only for genuinely unexpected throws.
 */
function authMessage(caught: unknown, fallback: string): string {
  if (caught instanceof FirebaseAuthError || caught instanceof ApiError) return caught.message;
  return fallback;
}

export function LoginPage() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null;
  if (user) return <Navigate to={(location.state as { from?: string })?.from ?? '/'} replace />;

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (caught) {
      setError(authMessage(caught, 'Sign in failed. Please try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="center-page">
      <div className="card auth-card">
        <div className="row" style={{ marginBottom: 'var(--space-5)' }}>
          <span className="brand-mark" aria-hidden>
            Py
          </span>
          <div>
            <h1 style={{ fontSize: '1.3rem', margin: 0 }}>Sign in to PyForge</h1>
            <p className="small muted" style={{ margin: 0 }}>
              Learn Python by writing it.
            </p>
          </div>
        </div>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} noValidate>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="small muted" style={{ marginTop: 'var(--space-4)', marginBottom: 0 }}>
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}

export function RegisterPage() {
  const { user, register, loading } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    display_name: '',
    email: '',
    password: '',
    declared_level: 'beginner',
    goal: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null;
  if (user) return <Navigate to="/" replace />;

  const update = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({
        email: form.email,
        password: form.password,
        display_name: form.display_name,
        declared_level: form.declared_level,
        goal: form.goal || undefined,
      });
      navigate('/', { replace: true });
    } catch (caught) {
      setError(authMessage(caught, 'Registration failed. Please try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="center-page">
      <div className="card auth-card">
        <h1 style={{ fontSize: '1.3rem' }}>Start learning</h1>
        <p className="small muted">
          You will write and run real Python from the first lesson.
        </p>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} noValidate>
          <div className="field">
            <label htmlFor="display_name">Name</label>
            <input
              id="display_name"
              className="input"
              value={form.display_name}
              onChange={update('display_name')}
              autoComplete="name"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="reg-email">Email</label>
            <input
              id="reg-email"
              className="input"
              type="email"
              value={form.email}
              onChange={update('email')}
              autoComplete="email"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="reg-password">Password</label>
            <input
              id="reg-password"
              className="input"
              type="password"
              value={form.password}
              onChange={update('password')}
              autoComplete="new-password"
              minLength={10}
              required
              aria-describedby="password-help"
            />
            <p id="password-help" className="small muted" style={{ margin: '6px 0 0' }}>
              At least 10 characters, mixing letters with digits or symbols.
            </p>
          </div>

          <div className="field">
            <label htmlFor="level">Where are you starting?</label>
            <select
              id="level"
              className="select"
              value={form.declared_level}
              onChange={update('declared_level')}
            >
              <option value="beginner">Completely new to programming</option>
              <option value="intermediate">I can program, but not in Python</option>
              <option value="advanced">I know Python, I want depth</option>
              <option value="professional">I want production and automation skills</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="goal">What do you want to be able to build? (optional)</label>
            <input
              id="goal"
              className="input"
              value={form.goal}
              onChange={update('goal')}
              placeholder="e.g. automate our invoice processing"
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
            {submitting ? 'Creating your account…' : 'Create account'}
          </button>
        </form>

        <p className="small muted" style={{ marginTop: 'var(--space-4)', marginBottom: 0 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
