/** Route table and auth gating. */

import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { ReactElement } from 'react';

import { AppLayout } from '@/components/AppLayout';
import { Spinner } from '@/components/ui';
import { STATIC_MODE } from '@/api/endpoints';
import { LoginPage, RegisterPage } from '@/pages/AuthPages';
import { DashboardPage } from '@/pages/DashboardPage';
import { ExercisePage, PracticePage } from '@/pages/ExercisePages';
import { LearnPage, LessonPage } from '@/pages/LearnPages';
import { ProjectPage, ProjectsPage } from '@/pages/ProjectPages';
import {
  CodeLabPage,
  InterviewPage,
  ProgressPage,
  ReferenceEntryPage,
  ReferencePage,
  SettingsPage,
  TutorPage,
} from '@/pages/ToolPages';
import { useAuth } from '@/state/auth';

/**
 * Gate a route behind sign-in.
 *
 * In the static build there are no accounts — the local profile always exists —
 * so this waits for it to load and then lets everyone through. The redirect only
 * happens in the API-backed build, which does have real sign-in.
 */
function RequireAuth({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="center-page">
        <Spinner label={STATIC_MODE ? 'Loading your progress' : 'Signing you in'} />
      </div>
    );
  }
  if (!user && !STATIC_MODE) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="learn" element={<LearnPage />} />
        <Route path="learn/:slug" element={<LessonPage />} />
        <Route path="practice" element={<PracticePage />} />
        <Route path="practice/:slug" element={<ExercisePage />} />
        <Route path="challenges" element={<PracticePage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:slug" element={<ProjectPage />} />
        <Route path="reference" element={<ReferencePage />} />
        <Route path="reference/:key" element={<ReferenceEntryPage />} />
        <Route path="lab" element={<CodeLabPage />} />
        {/* Not in the navigation: the tab was removed because the static build has
            no model to talk to. The route stays reachable by URL, so the
            definition-of-done suite and any bookmark still work. */}
        <Route path="tutor" element={<TutorPage />} />
        <Route path="interview" element={<InterviewPage />} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

/**
 * Reference keys contain dots (``list.append``) but never slashes, so a plain
 * dynamic segment matches them; no splat route is needed.
 */
function NotFound() {
  return (
    <div className="empty">
      <h1>Page not found</h1>
      <p>
        Nothing lives at this address. <Link to="/">Back to the dashboard</Link>.
      </p>
    </div>
  );
}
