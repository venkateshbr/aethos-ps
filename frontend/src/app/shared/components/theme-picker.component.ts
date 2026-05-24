import { Component, inject, input } from '@angular/core';
import { ThemeService, ThemeId } from '../../core/services/theme.service';

/**
 * ThemePickerComponent — three accent-coloured chips for switching between
 * the slate-emerald / ink-indigo / carbon-amber palettes at runtime.
 *
 * Two intended placements:
 *   - Landing page header — so visitors can preview before signup.
 *   - App shell sidebar footer — so authenticated users can switch in-app.
 *
 * Use the `size` input to compact the chips for tight sidebar slots.
 * The component intentionally doesn't read from CSS theme tokens for its
 * own background — each chip needs to surface the OTHER theme's accent,
 * not the active one. Swatches are sourced from ThemeService.all metadata.
 */
@Component({
  selector: 'app-theme-picker',
  standalone: true,
  template: `
    <div
      class="inline-flex items-center gap-1.5"
      role="radiogroup"
      aria-label="Theme"
    >
      @if (showLabel()) {
        <span class="text-xs text-slate-400 mr-1">Theme</span>
      }
      @for (t of themeSvc.all; track t.id) {
        <button
          type="button"
          role="radio"
          [attr.aria-checked]="themeSvc.theme() === t.id"
          [attr.aria-label]="'Switch theme to ' + t.label"
          [title]="t.label"
          (click)="select(t.id)"
          [class]="chipClass(t.id)"
          [style.--swatch]="t.accentColor"
        >
          <span class="swatch" aria-hidden="true"></span>
          @if (size() !== 'compact') {
            <span class="chip-label">{{ shortLabel(t.id) }}</span>
          }
        </button>
      }
    </div>
  `,
  styles: [`
    :host { display: inline-flex; }
    button {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.25rem 0.5rem;
      border-radius: 0.375rem;
      border: 1px solid var(--t-border-default, #334155);
      background: transparent;
      color: var(--t-text-muted, #94a3b8);
      font-size: 0.7rem;
      line-height: 1rem;
      cursor: pointer;
      transition: border-color 0.15s ease, color 0.15s ease, background-color 0.15s ease;
    }
    button:hover {
      color: var(--t-text-primary, #f8fafc);
      border-color: var(--t-border-strong, #475569);
    }
    button:focus-visible {
      outline: 2px solid var(--t-accent, #10b981);
      outline-offset: 2px;
    }
    button[aria-checked="true"] {
      background: var(--t-bg-surface-raised, #293548);
      color: var(--t-text-primary, #f8fafc);
      border-color: var(--swatch);
    }
    .swatch {
      width: 0.65rem;
      height: 0.65rem;
      border-radius: 9999px;
      background: var(--swatch);
      box-shadow: 0 0 0 1px rgba(255,255,255,0.08) inset;
      flex: none;
    }
    .chip-label {
      letter-spacing: 0.02em;
    }
    /* Compact mode (used in the collapsed sidebar) — swatch only */
    :host(.compact) button,
    button.is-compact {
      padding: 0.25rem;
    }
  `],
})
export class ThemePickerComponent {
  protected themeSvc = inject(ThemeService);

  /** 'default' shows short label next to the swatch; 'compact' is swatch-only. */
  size = input<'default' | 'compact'>('default');

  /** Show the "Theme" prefix label. Off by default for tight placements. */
  showLabel = input<boolean>(false);

  protected select(id: ThemeId): void {
    this.themeSvc.setTheme(id);
  }

  protected chipClass(id: ThemeId): string {
    const compact = this.size() === 'compact' ? ' is-compact' : '';
    return `theme-chip${compact}`;
  }

  protected shortLabel(id: ThemeId): string {
    switch (id) {
      case 'slate-emerald': return 'Slate';
      case 'ink-indigo':    return 'Ink';
      case 'carbon-amber':  return 'Carbon';
    }
  }
}
