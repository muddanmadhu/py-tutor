/**
 * Static content access.
 *
 * Reads the JSON tree that `tools/export_static.py` pre-rendered from the real
 * API, so these documents have exactly the shapes in `@/api/types`. Everything
 * is fetched relative to `BASE_URL` so it works from a project sub-path
 * (`/py-tutor/`) as well as from a domain root.
 */

const ROOT = `${import.meta.env.BASE_URL}content`;

/** Content is immutable per deploy, so nothing needs fetching twice. */
const cache = new Map<string, Promise<unknown>>();

export class ContentError extends Error {
  constructor(
    public readonly path: string,
    public readonly status: number,
  ) {
    super(
      status === 404
        ? 'That page is not part of this build of the curriculum.'
        : 'Could not load the curriculum. Check your connection and reload.',
    );
    this.name = 'ContentError';
  }
}

/** Fetch and cache one exported document. */
export function load<T>(path: string): Promise<T> {
  const existing = cache.get(path);
  if (existing) return existing as Promise<T>;

  const pending = fetch(`${ROOT}/${path}`).then(async (response) => {
    if (!response.ok) {
      // Do not cache a failure: a 404 is permanent but a network blip is not,
      // and keeping the rejection would make the whole session unrecoverable.
      cache.delete(path);
      throw new ContentError(path, response.status);
    }
    return response.json();
  });

  cache.set(path, pending);
  return pending as Promise<T>;
}

/** Fetch a document, or `null` if this build does not contain it. */
export async function loadOptional<T>(path: string): Promise<T | null> {
  try {
    return await load<T>(path);
  } catch (error) {
    if (error instanceof ContentError && error.status === 404) return null;
    throw error;
  }
}
