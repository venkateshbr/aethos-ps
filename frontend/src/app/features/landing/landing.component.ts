import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-screen bg-surface-base text-text-primary flex flex-col overflow-hidden">
      <header class="px-5 py-5 border-b border-border-subtle md:px-8 flex items-center justify-between bg-surface-base/90 backdrop-blur sticky top-0 z-30">
        <a routerLink="/" aria-label="Aethos — agentic ERP for professional services">
          <img
            [src]="themeSvc.meta().lockupSrc"
            [alt]="'Aethos — agentic ERP for professional services (' + themeSvc.meta().label + ')'"
            class="h-10 w-auto"
          />
        </a>
        <nav aria-label="Primary navigation" class="flex items-center gap-2 sm:gap-5">
          <a href="#platform" class="hidden rounded-md px-2 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:inline-flex">Platform</a>
          <a href="#proof" class="hidden rounded-md px-2 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:inline-flex">Proof</a>
          <a
            routerLink="/login"
            class="rounded-md px-2 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >Sign in</a>
          <a
            routerLink="/signup"
            class="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-on shadow-accent-ring transition-colors hover:bg-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >Start trial</a>
        </nav>
      </header>

      <main class="flex-1">
        <section class="relative px-5 py-16 md:px-8 md:py-24">
          <div class="pointer-events-none absolute inset-x-0 top-0 -z-0 mx-auto h-96 max-w-5xl rounded-full bg-accent/10 blur-3xl"></div>
          <div class="relative mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
            <div>
              <div class="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-border-default bg-surface-base/60 text-xs text-text-secondary">
                <span class="w-1.5 h-1.5 rounded-full bg-accent shadow-accent-ring"></span>
                Private beta · Agentic ERP · US · UK · SG · IN · AU
              </div>
              <h1 class="max-w-4xl text-4xl font-bold tracking-tight mb-6 sm:text-5xl md:text-6xl">
                The agentic ERP for professional services firms.
              </h1>
              <p class="max-w-2xl text-text-muted text-base mb-8 leading-relaxed md:text-lg">
                Aethos runs the full services back office — opportunity and engagement-to-cash, procure-to-pay,
                project delivery, time, expenses, record-to-report, and close — with AI agents that draft work,
                explain decisions, and wait for human approval before posting.
              </p>
              <div class="flex flex-col gap-3 sm:flex-row">
                <a
                  routerLink="/signup"
                  class="inline-flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-8 py-3 rounded-lg transition-colors text-sm shadow-accent-ring focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
                >
                  Start a 14-day trial
                </a>
                <a
                  href="#platform"
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-border-default bg-surface-raised/70 px-8 py-3 text-sm font-medium text-text-primary transition-colors hover:border-accent/70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
                >
                  Explore the platform
                </a>
              </div>
              <p class="text-text-muted text-xs mt-4">Built for consulting, advisory, accounting, agencies, law firms, and dev shops.</p>
            </div>

            <div class="rounded-3xl border border-border-default bg-surface-raised/80 p-4 shadow-2xl shadow-black/30 backdrop-blur">
              <div class="rounded-2xl border border-border-subtle bg-surface-base p-5">
                <div class="mb-5 flex items-center justify-between border-b border-border-subtle pb-4">
                  <div>
                    <p class="text-xs uppercase tracking-[0.25em] text-text-muted">Aethos command center</p>
                    <h2 class="mt-1 text-xl font-semibold">Month-end cockpit</h2>
                  </div>
                  <span class="rounded-full bg-accent/15 px-3 py-1 text-xs font-medium text-accent-light">L2 approval mode</span>
                </div>
                <div class="space-y-3">
                  <article class="rounded-xl border border-border-default bg-surface-raised p-4">
                    <div class="flex items-start justify-between gap-4">
                      <div>
                        <p class="text-sm font-semibold">Vendor invoice matched to PO-1048</p>
                        <p class="mt-1 text-xs text-text-muted">Procure-to-pay agent found a 3-way match and drafted AP journal lines.</p>
                      </div>
                      <span class="text-xs text-accent-light">98%</span>
                    </div>
                  </article>
                  <article class="rounded-xl border border-border-default bg-surface-raised p-4">
                    <div class="flex items-start justify-between gap-4">
                      <div>
                        <p class="text-sm font-semibold">Revenue recognition release ready</p>
                        <p class="mt-1 text-xs text-text-muted">Record-to-report agent prepared deferred revenue release for September close.</p>
                      </div>
                      <span class="text-xs text-accent-light">Approve</span>
                    </div>
                  </article>
                  <article class="rounded-xl border border-border-default bg-surface-raised p-4">
                    <div class="flex items-start justify-between gap-4">
                      <div>
                        <p class="text-sm font-semibold">Draft invoice for Meridian Advisory</p>
                        <p class="mt-1 text-xs text-text-muted">Engagement-to-cash agent combined approved time, expenses, and milestone terms.</p>
                      </div>
                      <span class="text-xs text-accent-light">$42.8k</span>
                    </div>
                  </article>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="border-y border-border-subtle bg-surface-raised/40 px-5 py-6 md:px-8" aria-label="Platform outcomes">
          <div class="mx-auto grid max-w-7xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div class="rounded-2xl border border-border-subtle bg-surface-base/70 p-5">
              <p class="text-2xl font-semibold">6</p>
              <p class="mt-1 text-sm text-text-muted">ERP workstreams unified in one agentic platform</p>
            </div>
            <div class="rounded-2xl border border-border-subtle bg-surface-base/70 p-5">
              <p class="text-2xl font-semibold">5</p>
              <p class="mt-1 text-sm text-text-muted">launch markets with multi-currency operations</p>
            </div>
            <div class="rounded-2xl border border-border-subtle bg-surface-base/70 p-5">
              <p class="text-2xl font-semibold">L2 → L3</p>
              <p class="mt-1 text-sm text-text-muted">human-in-the-loop now, controlled autonomy later</p>
            </div>
            <div class="rounded-2xl border border-border-subtle bg-surface-base/70 p-5">
              <p class="text-2xl font-semibold">GAAP</p>
              <p class="mt-1 text-sm text-text-muted">balanced double-entry journals underneath every workflow</p>
            </div>
          </div>
        </section>

        <section id="platform" class="px-5 py-16 md:px-8 md:py-24">
          <div class="mx-auto max-w-7xl">
            <div class="max-w-3xl">
              <p class="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-accent-light">Actual platform</p>
              <h2 class="text-3xl font-semibold tracking-tight md:text-4xl">Beyond engagement-to-cash: the operating system for services finance.</h2>
              <p class="mt-4 text-text-muted">Aethos keeps the familiar ERP controls, then replaces spreadsheet handoffs with agents, documents, approvals, and explainable posting suggestions.</p>
            </div>
            <div class="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Opportunity to cash</p>
                <h3 class="text-xl font-semibold">Engagements, projects, billing, AR</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">Turn proposals and engagement letters into clients, projects, rate cards, invoices, payment links, and receivables.</p>
              </article>
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Procure-to-pay</p>
                <h3 class="text-xl font-semibold">Vendors, POs, bills, approvals, pay runs</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">Upload vendor invoices, match project costs, draft AP journals, and create controlled payment batches with export safeguards.</p>
              </article>
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Record-to-report</p>
                <h3 class="text-xl font-semibold">GL, reporting, close, audit trail</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">Run journals, period close tasks, revenue recognition, FX remeasurement, management reports, and traceable approvals.</p>
              </article>
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Project delivery</p>
                <h3 class="text-xl font-semibold">Time, expenses, WIP, margins</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">See project health from approved time, reimbursable expenses, budgets, retainers, and delivery margin signals.</p>
              </article>
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Agent controls</p>
                <h3 class="text-xl font-semibold">Copilot plus HITL inbox</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">Chat, upload documents, review every proposed mutation, and promote autonomy only when confidence history earns it.</p>
              </article>
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Multi-market core</p>
                <h3 class="text-xl font-semibold">Currency, tax, payments</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">Operate across USD, GBP, SGD, INR, and AUD with tax seeds, Stripe billing, payment links, and tenant-scoped controls.</p>
              </article>
            </div>
          </div>
        </section>

        <section class="px-5 py-16 md:px-8 md:py-24 bg-surface-raised/30">
          <div class="mx-auto max-w-7xl">
            <div class="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
              <div>
                <p class="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-accent-light">How work flows</p>
                <h2 class="text-3xl font-semibold tracking-tight md:text-4xl">Agents draft. Finance approves. Aethos posts.</h2>
                <p class="mt-4 text-text-muted">Every workflow follows the same operating pattern: ingest the work, propose the accounting treatment, route the approval, then post a balanced journal.</p>
              </div>
              <div class="grid gap-4 md:grid-cols-2">
                <div class="rounded-2xl border border-border-default bg-surface-base p-5">
                  <span class="text-xs text-accent-light">01</span>
                  <h3 class="mt-2 font-semibold">Ingest</h3>
                  <p class="mt-2 text-sm text-text-muted">Chat requests, PDFs, receipts, vendor invoices, time sheets, bank events.</p>
                </div>
                <div class="rounded-2xl border border-border-default bg-surface-base p-5">
                  <span class="text-xs text-accent-light">02</span>
                  <h3 class="mt-2 font-semibold">Reason</h3>
                  <p class="mt-2 text-sm text-text-muted">Agents extract facts, apply ERP policy, and prepare traceable suggestions.</p>
                </div>
                <div class="rounded-2xl border border-border-default bg-surface-base p-5">
                  <span class="text-xs text-accent-light">03</span>
                  <h3 class="mt-2 font-semibold">Approve</h3>
                  <p class="mt-2 text-sm text-text-muted">Human-in-the-loop inbox shows confidence, source evidence, and impact.</p>
                </div>
                <div class="rounded-2xl border border-border-default bg-surface-base p-5">
                  <span class="text-xs text-accent-light">04</span>
                  <h3 class="mt-2 font-semibold">Post</h3>
                  <p class="mt-2 text-sm text-text-muted">Balanced double-entry records, immutable postings, and reporting-ready data.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="proof" class="px-5 py-16 md:px-8 md:py-24">
          <div class="mx-auto max-w-7xl">
            <div class="max-w-3xl">
              <p class="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-accent-light">Customer proof</p>
              <h2 class="text-3xl font-semibold tracking-tight md:text-4xl">Representative beta scenarios from firms Aethos is built for.</h2>
              <p class="mt-4 text-text-muted">Representative examples for beta positioning; names and metrics are illustrative until design partners approve public references.</p>
            </div>
            <div class="mt-10 grid gap-5 lg:grid-cols-3">
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Case study</p>
                <h3 class="mt-3 text-xl font-semibold">Meridian Advisory Group</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">A 42-person consulting firm used Aethos to connect retainers, expenses, AP bills, and close journals in one cockpit.</p>
                <p class="mt-5 text-2xl font-semibold">32% faster close</p>
              </article>
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Case study</p>
                <h3 class="mt-3 text-xl font-semibold">Northstar Digital Studio</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">A design and engineering agency replaced manual invoice prep with agent-drafted billing from approved time and milestone terms.</p>
                <p class="mt-5 text-2xl font-semibold">18 hours saved / month</p>
              </article>
              <article class="rounded-2xl border border-border-default bg-surface-raised/70 p-6">
                <p class="text-xs font-semibold uppercase tracking-[0.24em] text-accent-light">Case study</p>
                <h3 class="mt-3 text-xl font-semibold">Cedar Ledger Partners</h3>
                <p class="mt-3 text-sm leading-6 text-text-muted">A boutique accounting practice piloted record-to-report agents for recurring journals, FX checks, and review-ready audit trails.</p>
                <p class="mt-5 text-2xl font-semibold">91% suggestions accepted</p>
              </article>
            </div>

            <div class="mt-8 grid gap-5 md:grid-cols-3" aria-label="Client testimonials">
              <blockquote class="rounded-2xl border border-border-subtle bg-surface-base/70 p-6">
                <p class="text-sm leading-6 text-text-secondary">“Aethos feels like an ERP controller sitting beside our team — it drafts the work, but we keep the final say.”</p>
                <footer class="mt-4 text-xs text-text-muted">Priya S. · COO, advisory firm</footer>
              </blockquote>
              <blockquote class="rounded-2xl border border-border-subtle bg-surface-base/70 p-6">
                <p class="text-sm leading-6 text-text-secondary">“The procure-to-pay flow finally connects vendor bills to client projects without another spreadsheet.”</p>
                <footer class="mt-4 text-xs text-text-muted">James L. · Finance Lead, digital agency</footer>
              </blockquote>
              <blockquote class="rounded-2xl border border-border-subtle bg-surface-base/70 p-6">
                <p class="text-sm leading-6 text-text-secondary">“Record-to-report used to be a checklist in docs. Now the close work is visible, reviewable, and auditable.”</p>
                <footer class="mt-4 text-xs text-text-muted">Amelia R. · Partner, accounting practice</footer>
              </blockquote>
            </div>
          </div>
        </section>

        <section class="px-5 pb-16 md:px-8 md:pb-24">
          <div class="mx-auto max-w-7xl rounded-3xl border border-border-default bg-accent/10 p-8 text-center md:p-12">
            <p class="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-accent-light">Ready for beta teams</p>
            <h2 class="mx-auto max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">Bring your services ERP, agents, approvals, and accounting controls into one workspace.</h2>
            <p class="mx-auto mt-4 max-w-2xl text-text-muted">Start with the workflows you need now, then expand across procure-to-pay, record-to-report, and delivery operations as your firm scales.</p>
            <a
              routerLink="/signup"
              class="mt-8 inline-flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-8 py-3 rounded-lg transition-colors text-sm shadow-accent-ring focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
            >
              Start free trial
            </a>
          </div>
        </section>
      </main>

      <footer class="px-5 py-4 md:px-8 flex flex-col gap-3 border-t border-border-subtle text-text-muted text-xs sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2">
          <span class="lockup-mark inline-block w-2.5 h-2.5 bg-accent rounded-[1.5px]"></span>
          <span>Aethos &middot; agentic ERP for professional services</span>
        </div>
        <div>&copy; 2026 Aethos</div>
      </footer>
    </div>
  `,
})
export class LandingComponent {
  protected themeSvc = inject(ThemeService);
}
