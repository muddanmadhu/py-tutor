/** Global search: the top-bar field, its dropdown, and keyboard navigation. */

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { search } from '@/api/endpoints';
import type { SearchHit } from '@/api/types';

export function GlobalSearch() {
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Debounced search: 200 ms is short enough to feel instant and long enough to
  // avoid a request per keystroke.
  useEffect(() => {
    if (query.trim().length < 2) {
      setHits([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const response = await search(query);
        setHits(response.hits);
        setActiveIndex(0);
        setOpen(true);
      } catch {
        setHits([]);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', onClickOutside);
    document.addEventListener('keydown', onShortcut);
    return () => {
      document.removeEventListener('mousedown', onClickOutside);
      document.removeEventListener('keydown', onShortcut);
    };
  }, []);

  const go = (hit: SearchHit) => {
    setOpen(false);
    setQuery('');
    navigate(hit.url);
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (!open || hits.length === 0) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % hits.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + hits.length) % hits.length);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const hit = hits[activeIndex];
      if (hit) go(hit);
    } else if (event.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div className="search-box" ref={containerRef}>
      <label htmlFor="global-search" className="visually-hidden">
        Search lessons, concepts, the Python reference, exercises and projects
      </label>
      <input
        id="global-search"
        ref={inputRef}
        className="input"
        type="search"
        placeholder="Search anything…  (⌘K)"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => hits.length > 0 && setOpen(true)}
        onKeyDown={onKeyDown}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls="search-results"
        aria-autocomplete="list"
      />

      {open && (
        <div className="search-results" id="search-results" role="listbox">
          {hits.length === 0 ? (
            <div className="search-result muted small">No matches for “{query}”</div>
          ) : (
            hits.map((hit, index) => (
              <a
                key={`${hit.kind}-${hit.slug}`}
                href={hit.url}
                role="option"
                aria-selected={index === activeIndex}
                className={`search-result${index === activeIndex ? ' active' : ''}`}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={(event) => {
                  event.preventDefault();
                  go(hit);
                }}
              >
                <div className="row" style={{ gap: 8 }}>
                  <span className="badge">{hit.kind}</span>
                  <strong>{hit.title}</strong>
                </div>
                {hit.snippet && (
                  <div className="small muted" style={{ marginTop: 3 }}>
                    {hit.snippet}
                  </div>
                )}
              </a>
            ))
          )}
        </div>
      )}
    </div>
  );
}
