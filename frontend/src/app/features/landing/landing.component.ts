import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-screen bg-surface-base text-text-primary flex flex-col">
      <header class="px-8 py-5 border-b border-border-subtle flex items-center justify-between">
        <a routerLink="/" aria-label="Aethos — for professional services">
          <img
            [src]="themeSvc.meta().lockupSrc"
            [alt]="'Aethos — for professional services (' + themeSvc.meta().label + ')'"
            class="h-10 w-auto"
          />
        </a>
        <a routerLink="/login" class="text-sm text-text-secondary hover:text-text-primary transition-colors">Sign in</a>
      </header>

      <main class="flex-1 flex items-center justify-center px-8">
        <div class="text-center max-w-2xl">
          <div class="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-border-default bg-surface-base/60 text-xs text-text-secondary">
            <span class="w-1.5 h-1.5 rounded-full bg-accent shadow-accent-ring"></span>
            Now in private beta · US · UK · SG · IN · AU
          </div>
          <h1 class="text-5xl font-bold tracking-tight mb-6">
            Engagement to cash.<br>
            <span class="text-accent-light">Without the forms.</span>
          </h1>
          <p class="text-text-muted text-lg mb-10 leading-relaxed">
            Drop your engagement letter. Aethos extracts, proposes, and posts —
            you approve. GAAP double-entry under the hood. Works for US, UK, Singapore, India, and Australia.
          </p>
          <a
            routerLink="/signup"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-8 py-3 rounded-lg transition-colors text-sm shadow-accent-ring"
          >
            Get started
          </a>
          <p class="text-text-muted text-xs mt-4">14-day trial &middot; No credit card required at signup</p>
        </div>
      </main>

      <footer class="px-8 py-4 border-t border-border-subtle flex items-center justify-between text-text-muted text-xs">
        <div class="flex items-center gap-2">
          <span class="lockup-mark inline-block w-2.5 h-2.5 bg-accent rounded-[1.5px]"></span>
          <span>Aethos &middot; for professional services</span>
        </div>
        <div>&copy; 2026 Aethos</div>
      </footer>
    </div>
  `,
})
export class LandingComponent {
  protected themeSvc = inject(ThemeService);
}
