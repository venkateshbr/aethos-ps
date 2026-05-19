import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <header class="px-8 py-5 border-b border-slate-800 flex items-center justify-between">
        <div>
          <span class="text-xl font-semibold">Aethos</span>
          <span class="text-slate-400 text-sm ml-2">for professional services</span>
        </div>
        <a routerLink="/app" class="text-sm text-slate-300 hover:text-white transition-colors">Sign in</a>
      </header>

      <main class="flex-1 flex items-center justify-center px-8">
        <div class="text-center max-w-2xl">
          <h1 class="text-5xl font-bold tracking-tight mb-6">
            Engagement to cash.<br>
            <span class="text-emerald-400">Without the forms.</span>
          </h1>
          <p class="text-slate-400 text-lg mb-10 leading-relaxed">
            Drop your engagement letter. Aethos extracts, proposes, and posts —
            you approve. GAAP double-entry under the hood. Works for US, UK, Singapore, India, and Australia.
          </p>
          <a
            routerLink="/app"
            class="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-medium px-8 py-3 rounded-lg transition-colors text-sm"
          >
            Get started
          </a>
          <p class="text-slate-500 text-xs mt-4">14-day trial &middot; No credit card required at signup</p>
        </div>
      </main>

      <footer class="px-8 py-4 border-t border-slate-800 text-center text-slate-500 text-xs">
        &copy; 2026 Aethos &middot; Professional Services ERP
      </footer>
    </div>
  `,
})
export class LandingComponent {}
