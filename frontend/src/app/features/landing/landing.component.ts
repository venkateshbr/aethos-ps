import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-screen bg-slate-900 text-slate-100 flex flex-col">

      <!-- Nav -->
      <header class="px-8 py-5 border-b border-slate-800 flex items-center justify-between">
        <div>
          <span class="text-xl font-semibold">Aethos</span>
          <span class="text-slate-400 text-sm ml-2">for professional services</span>
        </div>
        <a routerLink="/app" class="text-sm text-slate-300 hover:text-white transition-colors">Sign in</a>
      </header>

      <main class="flex-1">

        <!-- Hero -->
        <section class="flex items-center justify-center px-8 py-24">
          <div class="text-center max-w-2xl">
            <h1 class="text-5xl font-bold tracking-tight mb-6 leading-tight">
              Engagement to cash.<br>
              <span class="text-emerald-400">Without the forms.</span>
            </h1>
            <p class="text-slate-400 text-lg mb-10 leading-relaxed">
              Drop your engagement letter. Aethos extracts, proposes, and posts —
              you approve. GAAP double-entry under the hood. Works for US, UK, Singapore, India, and Australia.
            </p>
            <a
              routerLink="/signup"
              class="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-medium px-8 py-3 rounded-lg transition-colors text-sm"
            >
              Start your 14-day free trial &rarr;
            </a>
            <p class="text-slate-500 text-xs mt-4">No credit card required to start.</p>
          </div>
        </section>

        <!-- Three features -->
        <section class="px-8 pb-24">
          <div class="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">

            <!-- Feature 1 -->
            <div class="bg-slate-800 border border-slate-700 rounded-xl p-6">
              <div class="w-10 h-10 rounded-lg bg-emerald-900 flex items-center justify-center mb-4">
                <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-3 3-3-3z" />
                </svg>
              </div>
              <h3 class="text-base font-semibold text-slate-100 mb-2">Chat-first, not form-first</h3>
              <p class="text-slate-400 text-sm leading-relaxed">
                Drop a document or describe a transaction in plain English. AI agents extract the structured data and present a proposal — confidence score included.
                You approve in one click; nothing touches the books without your sign-off.
              </p>
            </div>

            <!-- Feature 2 -->
            <div class="bg-slate-800 border border-slate-700 rounded-xl p-6">
              <div class="w-10 h-10 rounded-lg bg-emerald-900 flex items-center justify-center mb-4">
                <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3 class="text-base font-semibold text-slate-100 mb-2">Every billing model, one place</h3>
              <p class="text-slate-400 text-sm leading-relaxed">
                Time and materials, fixed fee, milestone, retainer, and capped T&amp;M — all supported natively on a single engagement.
                Mix billing models across project phases, run retainer-plus-overage arrangements, and generate invoices that reflect exactly what was agreed.
              </p>
            </div>

            <!-- Feature 3 -->
            <div class="bg-slate-800 border border-slate-700 rounded-xl p-6">
              <div class="w-10 h-10 rounded-lg bg-emerald-900 flex items-center justify-center mb-4">
                <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <h3 class="text-base font-semibold text-slate-100 mb-2">Get paid faster with Stripe</h3>
              <p class="text-slate-400 text-sm leading-relaxed">
                Every invoice includes a Stripe Payment Link your client can pay in two clicks — no login required.
                When payment arrives, the AR journal entry posts automatically. Stripe Connect routes funds directly to your firm's bank account.
              </p>
            </div>

          </div>
        </section>

        <!-- Pricing row -->
        <section class="px-8 pb-24 border-t border-slate-800 pt-16">
          <div class="max-w-5xl mx-auto">
            <h2 class="text-2xl font-bold text-center mb-2">Simple, transparent pricing</h2>
            <p class="text-slate-400 text-center text-sm mb-10">14-day free trial on every plan. No credit card required to start.</p>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

              <!-- Starter -->
              <div class="bg-slate-800 border border-slate-700 rounded-xl p-6 flex flex-col">
                <div class="mb-4">
                  <p class="text-xs text-slate-400 uppercase tracking-widest mb-1">Starter</p>
                  <p class="text-3xl font-bold text-slate-100">$29<span class="text-base font-normal text-slate-400">/mo</span></p>
                  <p class="text-xs text-slate-500 mt-1">£25 · S$39 · ₹2,499 · A$45</p>
                </div>
                <p class="text-slate-400 text-sm leading-relaxed flex-1">Solo practitioners and firms up to 5 people who need clean AI-assisted invoicing and a real GL without enterprise complexity.</p>
                <a routerLink="/signup" class="mt-6 block text-center text-sm bg-slate-700 hover:bg-slate-600 text-slate-100 font-medium px-4 py-2 rounded-lg transition-colors">
                  Start free trial
                </a>
              </div>

              <!-- Growth -->
              <div class="bg-slate-800 border border-emerald-500 rounded-xl p-6 flex flex-col relative">
                <div class="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span class="text-xs font-medium bg-emerald-500 text-white px-3 py-1 rounded-full">Most popular</span>
                </div>
                <div class="mb-4">
                  <p class="text-xs text-slate-400 uppercase tracking-widest mb-1">Growth</p>
                  <p class="text-3xl font-bold text-slate-100">$79<span class="text-base font-normal text-slate-400">/mo</span></p>
                  <p class="text-xs text-slate-500 mt-1">£69 · S$109 · ₹6,999 · A$119</p>
                </div>
                <p class="text-slate-400 text-sm leading-relaxed flex-1">Growing firms of 5 to 20 people running multiple concurrent engagements with mixed billing models and a team to coordinate.</p>
                <a routerLink="/signup" class="mt-6 block text-center text-sm bg-emerald-500 hover:bg-emerald-400 text-white font-medium px-4 py-2 rounded-lg transition-colors">
                  Start free trial
                </a>
              </div>

              <!-- Pro -->
              <div class="bg-slate-800 border border-slate-700 rounded-xl p-6 flex flex-col">
                <div class="mb-4">
                  <p class="text-xs text-slate-400 uppercase tracking-widest mb-1">Pro</p>
                  <p class="text-3xl font-bold text-slate-100">$199<span class="text-base font-normal text-slate-400">/mo</span></p>
                  <p class="text-xs text-slate-500 mt-1">£179 · S$279 · ₹17,999 · A$299</p>
                </div>
                <p class="text-slate-400 text-sm leading-relaxed flex-1">Established practices of 20 to 50 people needing full AP workflows, billing-run automation, and advanced agent autonomy controls.</p>
                <a routerLink="/signup" class="mt-6 block text-center text-sm bg-slate-700 hover:bg-slate-600 text-slate-100 font-medium px-4 py-2 rounded-lg transition-colors">
                  Start free trial
                </a>
              </div>

            </div>
          </div>
        </section>

      </main>

      <footer class="px-8 py-4 border-t border-slate-800 text-center text-slate-500 text-xs">
        &copy; 2026 Aethos &middot; Professional Services ERP
      </footer>
    </div>
  `,
})
export class LandingComponent {}
