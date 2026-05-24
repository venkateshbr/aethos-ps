import { Injectable, signal } from '@angular/core';

/**
 * ThemeService — runtime palette switcher.
 *
 * The three palettes are defined as `body[data-theme="..."]` scopes in
 * `src/styles.scss`. This service writes the chosen attribute on the
 * <body> element and persists the choice to localStorage so a refresh
 * (or a hard navigation back to the landing page) keeps the user's
 * preferred theme applied.
 *
 * The `:root` fallback in styles.scss is slate-emerald (so a first paint
 * before this service runs still renders a valid palette). The runtime
 * DEFAULT_THEME below is what gets applied as soon as the service
 * constructs — that's the theme an unvisited user lands on.
 *
 * Lockup swap: each theme ships its own SVG lockup. `lockupSrc()` exposes
 * the active asset path so the landing header / app shell can bind it
 * to an <img [src]>.
 */

export type ThemeId = 'slate-emerald' | 'ink-indigo' | 'carbon-amber';

export interface ThemeMeta {
  id: ThemeId;
  label: string;
  accentColor: string;   // shown on the chip swatch
  lockupSrc: string;     // SVG path under /assets
}

const STORAGE_KEY = 'aethos_theme';
// Founder-picked default. Originally slate-emerald (Chitra's recommendation);
// flipped to carbon-amber for the pilot so the warm/boutique direction gets
// real-world exposure before the post-pilot one-theme commit.
const DEFAULT_THEME: ThemeId = 'carbon-amber';

const THEMES: Record<ThemeId, ThemeMeta> = {
  'slate-emerald': {
    id: 'slate-emerald',
    label: 'Slate + Emerald',
    accentColor: '#10b981',
    lockupSrc: '/assets/brand/themes/theme-1-slate-emerald/lockup.svg',
  },
  'ink-indigo': {
    id: 'ink-indigo',
    label: 'Ink + Indigo',
    accentColor: '#818cf8',
    lockupSrc: '/assets/brand/themes/theme-2-ink-indigo/lockup.svg',
  },
  'carbon-amber': {
    id: 'carbon-amber',
    label: 'Carbon + Amber',
    accentColor: '#f5a524',
    lockupSrc: '/assets/brand/themes/theme-3-carbon-amber/lockup.svg',
  },
};

@Injectable({ providedIn: 'root' })
export class ThemeService {
  /** Reactive id of the currently applied theme. */
  private _theme = signal<ThemeId>(this.readPersisted());
  readonly theme = this._theme.asReadonly();

  /** All themes in display order — consumed by the picker UI. */
  readonly all: readonly ThemeMeta[] = Object.values(THEMES);

  constructor() {
    // Apply on construction so the body attribute is set before any
    // child component renders. SSR-safe: guarded by typeof document check.
    this.applyToDom(this._theme());
  }

  /** Switch the active theme — updates DOM, storage, and the signal. */
  setTheme(id: ThemeId): void {
    if (this._theme() === id) return;
    this._theme.set(id);
    this.applyToDom(id);
    this.persist(id);
  }

  /** Synchronous getter for places that can't subscribe to the signal. */
  getTheme(): ThemeId {
    return this._theme();
  }

  /** Metadata (label, accent swatch, lockup src) for the active theme. */
  meta(id?: ThemeId): ThemeMeta {
    return THEMES[id ?? this._theme()];
  }

  // ── Internal helpers ───────────────────────────────────────────────

  private applyToDom(id: ThemeId): void {
    if (typeof document === 'undefined') return;
    document.body.setAttribute('data-theme', id);
  }

  private persist(id: ThemeId): void {
    if (typeof localStorage === 'undefined') return;
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // Storage quota / privacy mode — non-fatal.
    }
  }

  private readPersisted(): ThemeId {
    if (typeof localStorage === 'undefined') return DEFAULT_THEME;
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'slate-emerald' || raw === 'ink-indigo' || raw === 'carbon-amber') {
      return raw;
    }
    return DEFAULT_THEME;
  }
}
