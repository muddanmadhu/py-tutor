/**
 * Endpoint selection.
 *
 * The app runs in two shapes from one codebase:
 *
 * * **Static** — published to GitHub Pages with no backend. Content comes from
 *   the JSON tree `tools/export_static.py` pre-rendered from the real API,
 *   progress lives in localStorage, and execution, grading and code review run
 *   in Pyodide.
 * * **API-backed** — `run-local.sh` or a hosted deployment, with the full
 *   feature set including the AI tutor, adaptive routing and certifications.
 *
 * Which one is decided at build time by whether an API base URL was configured,
 * because it changes where every read comes from and must not vary per render.
 *
 * The `typeof httpApi` annotation is the load-bearing part: it makes the compiler
 * check that the static implementation still matches the HTTP one, so adding an
 * endpoint to one and forgetting the other is a build failure rather than a
 * blank page for whoever visits the published site.
 */

import * as httpApi from './endpoints.http';
import * as staticApi from './endpoints.static';

/** Whether this build talks to a server. */
export const STATIC_MODE = !import.meta.env.VITE_API_BASE_URL;

const impl: typeof httpApi = STATIC_MODE ? (staticApi as typeof httpApi) : httpApi;

export const auth = impl.auth;
export const curriculum = impl.curriculum;
export const exercises = impl.exercises;
export const execution = impl.execution;
export const progress = impl.progress;
export const projects = impl.projects;
export const tutor = impl.tutor;
export const reference = impl.reference;
export const search = impl.search;
export const codeReview = impl.codeReview;
export const interview = impl.interview;
