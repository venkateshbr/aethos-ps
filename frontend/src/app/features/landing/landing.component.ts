import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../core/services/theme.service';
import { ThemePickerComponent } from '../../shared/components/theme-picker.component';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink, ThemePickerComponent],
  template: `
    <div class="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <header class="px-8 py-5 border-b border-slate-800 flex items-center justify-between">
        <a routerLink="/" aria-label="Aethos — for professional services">
          <img
            [src]="themeSvc.meta().lockupSrc"
            [alt]="'Aethos — for professional services (' + themeSvc.meta().label + ')'"
            class="h-10 w-auto"
          />
        </a>
        <div class="flex items-center gap-5">
          <app-theme-picker />
          <a routerLink="/login" class="text-sm text-slate-300 hover:text-white transition-colors">Sign in</a>
        </div>
      </header>

      <main class="flex-1 flex items-center justify-center px-8">
        <div class="text-center max-w-2xl">
          <div class="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-slate-700 bg-slate-900/60 text-xs text-slate-300">
            <span class="w-1.5 h-1.5 rounded-full bg-accent shadow-accent-ring"></span>
            Now in private beta · US · UK · SG · IN · AU
          </div>
          <h1 class="text-5xl font-bold tracking-tight mb-6">
            Engagement to cash.<br>
            <span class="text-accent-light">Without the forms.</span>
          </h1>
          <p class="text-slate-400 text-lg mb-10 leading-relaxed">
            Drop your engagement letter. Aethos extracts, proposes, and posts —
            you approve. GAAP double-entry under the hood. Works for US, UK, Singapore, India, and Australia.
          </p>
          <a
            routerLink="/signup"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-8 py-3 rounded-lg transition-colors text-sm shadow-accent-ring"
          >
            Get started
          </a>
          <p class="text-slate-500 text-xs mt-4">14-day trial &middot; No credit card required at signup</p>
        </div>
      </main>

      <footer class="px-8 py-4 border-t border-slate-800 flex items-center justify-between text-slate-500 text-xs">
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
