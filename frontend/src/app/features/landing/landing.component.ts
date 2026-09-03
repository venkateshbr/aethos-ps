import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-screen bg-surface-base text-text-primary flex flex-col">
      <header class="px-5 py-5 border-b border-border-subtle md:px-8 flex items-center justify-between">
        <a routerLink="/" aria-label="Aethos — for professional services">
          <img
            [src]="themeSvc.meta().lockupSrc"
            [alt]="'Aethos — for professional services (' + themeSvc.meta().label + ')'"
            class="h-10 w-auto"
          />
        </a>
        <nav aria-label="Primary navigation" class="flex items-center gap-2 sm:gap-5">
          <a
            routerLink="/login"
            class="rounded-md px-2 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >Sign in</a>
        </nav>
      </header>

      <main class="flex-1">
        <section class="px-5 py-20 md:px-8 md:py-28">
          <div class="mx-auto max-w-3xl text-center">
            <div class="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-border-default bg-surface-base/60 text-xs text-text-secondary">
              <span class="w-1.5 h-1.5 rounded-full bg-accent shadow-accent-ring"></span>
              Now in private beta · US · UK · SG · IN · AU
            </div>
            <h1 class="text-4xl font-bold tracking-tight mb-6 sm:text-5xl md:text-6xl">
              Engagement to cash.<br>
              <span class="text-accent-light">Without the forms.</span>
            </h1>
            <p class="mx-auto max-w-2xl text-text-muted text-base mb-10 leading-relaxed md:text-lg">
              Drop your engagement letter. Aethos extracts, proposes, and posts —
              you approve. GAAP double-entry under the hood. Works for US, UK, Singapore, India, and Australia.
            </p>
            <a
              routerLink="/signup"
              class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-8 py-3 rounded-lg transition-colors text-sm shadow-accent-ring focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
            >
              Get started
            </a>
            <p class="text-text-muted text-xs mt-4">14-day trial &middot; No credit card required at signup</p>
          </div>
        </section>

      </main>

      <footer class="px-5 py-4 md:px-8 flex items-center justify-between text-text-muted text-xs">
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
