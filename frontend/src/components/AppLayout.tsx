/** The application shell: header, navigation and the main content region. */

import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';

import { GlobalSearch } from '@/components/GlobalSearch';
import { useAuth } from '@/state/auth';
import { useTheme } from '@/state/theme';

const PRIMARY_NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/learn', label: 'Learn' },
  { to: '/practice', label: 'Practice' },
  { to: '/challenges', label: 'Challenges' },
  { to: '/projects', label: 'Projects' },
];

const TOOLS_NAV = [
  { to: '/reference', label: 'Python Reference' },
  { to: '/lab', label: 'Code Lab' },
  { to: '/interview', label: 'Interview Prep' },
];

const ACCOUNT_NAV = [
  { to: '/progress', label: 'Progress' },
  { to: '/settings', label: 'Settings' },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const location = useLocation();

  // The Code Lab and project IDE want the full width.
  const wide = location.pathname.startsWith('/lab') || location.pathname.startsWith('/projects/');

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden>
            Py
          </span>
          PyForge
        </Link>

        <GlobalSearch />

        <div className="grow" />

        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={toggle}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>

        {user && (
          <>
            <span className="badge badge-accent" title="Experience points">
              {user.xp} XP
            </span>
            {user.streak_days > 0 && (
              <span className="badge badge-warning" title="Learning streak">
                {user.streak_days}-day streak
              </span>
            )}
            <span className="small muted">{user.display_name}</span>
            <button type="button" className="btn btn-sm" onClick={logout}>
              Sign out
            </button>
          </>
        )}
      </header>

      <div className="app-body">
        <nav className="app-sidebar" aria-label="Main navigation">
          {PRIMARY_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}

          <div className="nav-section">Tools</div>
          {TOOLS_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}

          <div className="nav-section">You</div>
          {ACCOUNT_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <main id="main-content" className={`app-main${wide ? ' is-wide' : ''}`} tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
