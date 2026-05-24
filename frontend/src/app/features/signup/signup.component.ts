import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ThemeService } from '../../core/services/theme.service';
import { ThemePickerComponent } from '../../shared/components/theme-picker.component';
import {
  BillingInterval,
  LAUNCH_COUNTRIES,
  LaunchCountry,
  PlanTier,
  PriceCatalogue,
  SignupApiResponse,
  SignupService,
} from './signup.service';

/**
 * SignupComponent — single-component, signal-driven multi-step signup.
 *
 * Steps:
 *   1. Account — email, password, firm name, country  → POST /auth/signup
 *   2. Plan    — Starter / Growth / Pro × monthly|annual (next commit)
 *   3. Card    — Stripe Elements + start-trial         (next commit)
 *
 * State machine lives in `step()`; we keep all form state local so a back-nav
 * never loses what the user typed.  Resilient to a mid-flow refresh too: the
 * backend signup is idempotent on email (per auth.py docstring).
 *
 * Per issue #115 — no signup path exists today; this unblocks pilot launch.
 */
@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, ThemePickerComponent],
  template: `
    <div class="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <!-- Header — keep parity with landing so the user feels they're in the same product -->
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
          <a routerLink="/" class="text-sm text-slate-400 hover:text-slate-200 transition-colors">
            Cancel
          </a>
        </div>
      </header>

      <!-- Step indicator -->
      <div class="px-8 py-6">
        <ol class="flex items-center justify-center gap-3 text-xs text-slate-400" aria-label="Signup steps">
          @for (s of stepLabels; track s.idx) {
            <li class="flex items-center gap-3">
              <span
                class="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-medium border"
                [class.bg-accent]="step() === s.idx"
                [class.text-accent-on]="step() === s.idx"
                [class.border-accent]="step() === s.idx"
                [class.bg-slate-800]="step() !== s.idx"
                [class.border-slate-700]="step() !== s.idx && step() < s.idx"
                [class.border-accent-light]="step() > s.idx"
                [class.text-accent-light]="step() > s.idx"
                [attr.aria-current]="step() === s.idx ? 'step' : null"
              >
                {{ step() > s.idx ? '✓' : s.idx }}
              </span>
              <span [class.text-slate-100]="step() === s.idx">{{ s.label }}</span>
              @if (s.idx < 3) {
                <span class="w-8 h-px bg-slate-700"></span>
              }
            </li>
          }
        </ol>
      </div>

      <main class="flex-1 px-8 pb-12 flex justify-center">
        <div class="w-full max-w-md">
          @switch (step()) {
            @case (1) { <ng-container *ngTemplateOutlet="accountStep" /> }
            @case (2) { <ng-container *ngTemplateOutlet="planStep" /> }
            @case (3) { <ng-container *ngTemplateOutlet="cardStep" /> }
          }
        </div>
      </main>

      <footer class="px-8 py-4 border-t border-slate-800 text-slate-500 text-xs text-center">
        14-day trial · Cancel anytime · Card kept on file via Stripe
      </footer>
    </div>

    <!-- ── Step 1 · Account ───────────────────────────────────────────────── -->
    <ng-template #accountStep>
      <h1 class="text-2xl font-semibold mb-1">Create your firm</h1>
      <p class="text-slate-400 text-sm mb-6">
        Two minutes. We'll provision your tenant and you'll pick a plan next.
      </p>

      <form [formGroup]="accountForm" (ngSubmit)="submitAccount()" class="space-y-4" novalidate>
        <!-- Firm name -->
        <div>
          <label for="firm" class="block text-xs uppercase tracking-wider text-slate-400 mb-1.5">
            Firm name
          </label>
          <input
            id="firm"
            type="text"
            formControlName="tenant_name"
            autocomplete="organization"
            placeholder="Acme Advisory LLC"
            class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm
                   text-slate-100 placeholder-slate-500
                   focus:outline-none focus:border-accent focus:shadow-accent-ring"
          />
          @if (shouldShowError('tenant_name')) {
            <p class="text-xs text-red-400 mt-1">
              Firm name must be 2–100 characters.
            </p>
          }
        </div>

        <!-- Email -->
        <div>
          <label for="email" class="block text-xs uppercase tracking-wider text-slate-400 mb-1.5">
            Work email
          </label>
          <input
            id="email"
            type="email"
            formControlName="email"
            autocomplete="email"
            placeholder="you@firm.com"
            class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm
                   text-slate-100 placeholder-slate-500
                   focus:outline-none focus:border-accent focus:shadow-accent-ring"
          />
          @if (shouldShowError('email')) {
            <p class="text-xs text-red-400 mt-1">Enter a valid email address.</p>
          }
        </div>

        <!-- Password + strength meter -->
        <div>
          <label for="password" class="block text-xs uppercase tracking-wider text-slate-400 mb-1.5">
            Password
          </label>
          <input
            id="password"
            type="password"
            formControlName="password"
            autocomplete="new-password"
            placeholder="At least 8 characters"
            class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm
                   text-slate-100 placeholder-slate-500
                   focus:outline-none focus:border-accent focus:shadow-accent-ring"
          />
          <!-- Strength meter — purely client-side hint, real check is server-side -->
          <div class="flex items-center gap-1.5 mt-2" aria-hidden="true">
            @for (i of [1,2,3,4]; track i) {
              <div
                class="h-1 flex-1 rounded-full transition-colors"
                [class.bg-slate-700]="passwordStrength() < i"
                [class.bg-red-500]="passwordStrength() >= i && passwordStrength() <= 1"
                [class.bg-amber-500]="passwordStrength() >= i && passwordStrength() === 2"
                [class.bg-accent-light]="passwordStrength() >= i && passwordStrength() === 3"
                [class.bg-accent]="passwordStrength() >= i && passwordStrength() >= 4"
              ></div>
            }
          </div>
          <p class="text-xs mt-1.5" [class.text-slate-500]="passwordStrength() < 3" [class.text-accent-light]="passwordStrength() >= 3">
            {{ passwordStrengthLabel() }}
          </p>
          @if (shouldShowError('password')) {
            <p class="text-xs text-red-400 mt-1">Password must be at least 8 characters.</p>
          }
        </div>

        <!-- Country -->
        <div>
          <label for="country" class="block text-xs uppercase tracking-wider text-slate-400 mb-1.5">
            Country
          </label>
          <select
            id="country"
            formControlName="country"
            class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm
                   text-slate-100
                   focus:outline-none focus:border-accent focus:shadow-accent-ring"
          >
            @for (c of countries; track c.code) {
              <option [value]="c.code">{{ c.label }} · {{ c.currency }}</option>
            }
          </select>
          <p class="text-xs text-slate-500 mt-1">
            Sets your base currency and tax jurisdiction.
          </p>
        </div>

        <!-- Server error (signup rejection / network) -->
        @if (serverError()) {
          <div
            role="alert"
            class="text-sm text-red-300 bg-red-900/30 border border-red-800/60 rounded-lg px-3 py-2"
          >
            {{ serverError() }}
          </div>
        }

        <button
          type="submit"
          [disabled]="submitting() || accountForm.invalid"
          class="w-full inline-flex items-center justify-center gap-2
                 bg-accent hover:bg-accent-hover text-accent-on font-medium
                 px-4 py-2.5 rounded-lg transition-colors text-sm
                 disabled:opacity-50 disabled:cursor-not-allowed shadow-accent-ring"
        >
          @if (submitting()) {
            <span class="w-4 h-4 border-2 border-current border-r-transparent rounded-full animate-spin" aria-hidden="true"></span>
            Creating your firm…
          } @else {
            Continue to plan
          }
        </button>

        <p class="text-xs text-slate-500 text-center">
          By continuing you agree to the
          <a class="text-slate-300 hover:text-white underline" href="#" target="_blank" rel="noopener">terms</a>
          and
          <a class="text-slate-300 hover:text-white underline" href="#" target="_blank" rel="noopener">privacy notice</a>.
        </p>
      </form>
    </ng-template>

    <!-- ── Step 2 · Plan ───────────────────────────────────────────────────── -->
    <ng-template #planStep>
      <h1 class="text-2xl font-semibold mb-1">Pick a plan</h1>
      <p class="text-slate-400 text-sm mb-6">
        14-day trial on any plan. We'll only charge after the trial ends —
        cancel anytime from settings.
      </p>

      @if (loadingPrices()) {
        <div class="flex items-center justify-center py-12" role="status" aria-label="Loading plans">
          <span class="w-6 h-6 border-2 border-accent border-r-transparent rounded-full animate-spin" aria-hidden="true"></span>
        </div>
      } @else if (pricesError()) {
        <div role="alert" class="text-sm text-red-300 bg-red-900/30 border border-red-800/60 rounded-lg px-3 py-3 mb-4">
          {{ pricesError() }}
          <button type="button" (click)="loadPrices()" class="ml-2 underline">Retry</button>
        </div>
      } @else if (prices() !== null) {
        <!-- Billing interval toggle -->
        <div class="flex items-center justify-center mb-5">
          <div role="radiogroup" aria-label="Billing interval" class="inline-flex bg-slate-800 border border-slate-700 rounded-lg p-1 text-xs">
            <button
              type="button"
              role="radio"
              [attr.aria-checked]="interval() === 'monthly'"
              (click)="interval.set('monthly')"
              [class.bg-slate-700]="interval() === 'monthly'"
              [class.text-slate-100]="interval() === 'monthly'"
              [class.text-slate-400]="interval() !== 'monthly'"
              class="px-3 py-1.5 rounded-md transition-colors"
            >
              Monthly
            </button>
            <button
              type="button"
              role="radio"
              [attr.aria-checked]="interval() === 'annual'"
              (click)="interval.set('annual')"
              [class.bg-slate-700]="interval() === 'annual'"
              [class.text-slate-100]="interval() === 'annual'"
              [class.text-slate-400]="interval() !== 'annual'"
              class="px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5"
            >
              Annual
              <span class="text-[10px] text-accent-light bg-accent-subtle px-1.5 py-0.5 rounded">2 mo free</span>
            </button>
          </div>
        </div>

        <!-- Plan tiles -->
        <div class="space-y-3" role="radiogroup" aria-label="Plan tier">
          @for (plan of planList(); track plan.tier) {
            <button
              type="button"
              role="radio"
              [attr.aria-checked]="selectedTier() === plan.tier"
              [disabled]="!plan.priceId"
              (click)="selectTier(plan.tier)"
              [class]="planTileClass(plan)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-semibold text-slate-100 capitalize">{{ plan.tier }}</span>
                    @if (plan.recommended) {
                      <span class="text-[10px] uppercase tracking-wider bg-accent text-accent-on px-1.5 py-0.5 rounded">
                        Recommended
                      </span>
                    }
                  </div>
                  <p class="text-xs text-slate-400 mt-1">{{ plan.summary }}</p>
                </div>
                <div class="text-right shrink-0">
                  @if (plan.priceId) {
                    <div class="text-base font-semibold text-slate-50">
                      {{ prices()?.currency }} <span class="text-slate-300 text-xs">/ {{ interval() === 'monthly' ? 'mo' : 'yr' }}</span>
                    </div>
                    <div class="text-[11px] text-slate-500" title="Stripe price id">
                      {{ plan.priceId | slice:0:14 }}…
                    </div>
                  } @else {
                    <div class="text-xs text-slate-500">Not available in {{ prices()?.currency }}</div>
                  }
                </div>
              </div>
            </button>
          }
        </div>

        @if (serverError()) {
          <div role="alert" class="mt-4 text-sm text-red-300 bg-red-900/30 border border-red-800/60 rounded-lg px-3 py-2">
            {{ serverError() }}
          </div>
        }

        <div class="flex items-center justify-between gap-3 mt-6">
          <button
            type="button"
            (click)="step.set(1)"
            class="text-sm text-slate-400 hover:text-slate-200"
          >
            ← Back
          </button>
          <button
            type="button"
            [disabled]="!canAdvanceFromPlan()"
            (click)="advanceToCard()"
            class="inline-flex items-center justify-center gap-2
                   bg-accent hover:bg-accent-hover text-accent-on font-medium
                   px-4 py-2.5 rounded-lg transition-colors text-sm
                   disabled:opacity-50 disabled:cursor-not-allowed shadow-accent-ring"
          >
            Continue to card →
          </button>
        </div>
      }
    </ng-template>

    <!-- ── Step 3 · Card (next commit) ─────────────────────────────────────── -->
    <ng-template #cardStep>
      <h1 class="text-2xl font-semibold mb-1">Confirm your card</h1>
      <p class="text-slate-400 text-sm mb-6">
        Coming next commit. Stripe Elements + start-trial wiring.
      </p>
    </ng-template>
  `,
})
export class SignupComponent {
  protected themeSvc = inject(ThemeService);
  private fb = inject(FormBuilder);
  private signupSvc = inject(SignupService);
  private router = inject(Router);

  protected readonly countries = LAUNCH_COUNTRIES;
  protected readonly stepLabels = [
    { idx: 1, label: 'Account' },
    { idx: 2, label: 'Plan' },
    { idx: 3, label: 'Card' },
  ];

  /** Active step (1-indexed). Drives the @switch above. */
  protected step = signal<1 | 2 | 3>(1);

  /** Submission spinner state — disables the CTA so users don't double-submit. */
  protected submitting = signal(false);

  /** Last server-side error message, shown in the inline alert above the CTA. */
  protected serverError = signal<string | null>(null);

  /**
   * Tenant id + SetupIntent client_secret carried across steps.
   * Set on successful step-1 submission and consumed by step 3.
   */
  protected signupResult = signal<SignupApiResponse | null>(null);

  // ── Step 2 state ────────────────────────────────────────────────────────
  protected loadingPrices = signal(false);
  protected pricesError = signal<string | null>(null);
  protected prices = signal<PriceCatalogue | null>(null);
  protected interval = signal<BillingInterval>('monthly');
  protected selectedTier = signal<PlanTier>('growth'); // recommended default

  /** Per-tier metadata that's UI-only (copy, recommended flag). */
  private readonly tierMeta: Record<PlanTier, { summary: string; recommended: boolean }> = {
    starter: {
      summary: '1 owner · 10 invoices/mo · core agents at L2',
      recommended: false,
    },
    growth: {
      summary: 'Up to 5 seats · unlimited invoices · agent autonomy promotion',
      recommended: true,
    },
    pro: {
      summary: 'Unlimited seats · multi-entity · priority support · L3 auto-eligible',
      recommended: false,
    },
  };

  /**
   * Combined list of plans with their currently-selected interval's price id
   * resolved from the catalogue. Drives the @for tile loop in step 2.
   */
  protected planList = computed(() => {
    const cat = this.prices();
    if (!cat) return [];
    const order: PlanTier[] = ['starter', 'growth', 'pro'];
    return order.map((tier) => {
      const entry = cat.plans.find((p) => p.tier === tier);
      const priceId =
        entry == null
          ? null
          : this.interval() === 'monthly'
            ? entry.monthly_id
            : entry.annual_id;
      return {
        tier,
        priceId,
        summary: this.tierMeta[tier].summary,
        recommended: this.tierMeta[tier].recommended,
      };
    });
  });

  /** Resolved Stripe price_id for the current (tier, interval) selection. */
  protected selectedPriceId = computed<string | null>(() => {
    const cat = this.prices();
    if (!cat) return null;
    const entry = cat.plans.find((p) => p.tier === this.selectedTier());
    if (!entry) return null;
    return this.interval() === 'monthly' ? entry.monthly_id : entry.annual_id;
  });

  protected canAdvanceFromPlan = computed(() => this.selectedPriceId() !== null);

  /** Reactive form — typed via FormBuilder.group. */
  protected accountForm = this.fb.nonNullable.group({
    tenant_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    country: ['US' as LaunchCountry, [Validators.required]],
  });

  // ── Password strength heuristic (0–4) — purely a UI nudge ────────────────
  protected passwordStrength = computed(() => {
    const v = this.accountForm.controls.password.value ?? '';
    if (!v) return 0;
    let score = 0;
    if (v.length >= 8) score += 1;
    if (v.length >= 12) score += 1;
    if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score += 1;
    if (/[0-9]/.test(v) && /[^A-Za-z0-9]/.test(v)) score += 1;
    return score;
  });

  protected passwordStrengthLabel = computed(() => {
    const s = this.passwordStrength();
    if (s === 0) return 'Use at least 8 characters.';
    if (s <= 1) return 'Weak — add length or a symbol.';
    if (s === 2) return 'OK — mix in case and a number.';
    if (s === 3) return 'Good.';
    return 'Strong.';
  });

  /**
   * Should we show the field-level error block for a given control?
   * Pattern: only after the user has interacted (dirty || touched) and
   * the control is invalid. Avoids showing red text the moment the page loads.
   */
  protected shouldShowError(name: keyof typeof this.accountForm.controls): boolean {
    const ctrl = this.accountForm.controls[name];
    return ctrl.invalid && (ctrl.dirty || ctrl.touched);
  }

  /** Submit page 1 → POST /auth/signup → mint JWT → advance to plan picker. */
  protected async submitAccount(): Promise<void> {
    if (this.accountForm.invalid) {
      this.accountForm.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.serverError.set(null);

    const raw = this.accountForm.getRawValue();
    try {
      const resp = await this.signupSvc.signupAndSignIn({
        email: raw.email.trim().toLowerCase(),
        password: raw.password,
        tenant_name: raw.tenant_name.trim(),
        country: raw.country,
        plan_tier: 'starter', // can be re-picked in step 2; backend defaults to starter
      });
      this.signupResult.set(resp);
      this.step.set(2);
      // Fire-and-forget price catalogue load — needs the JWT from signin above.
      void this.loadPrices();
    } catch (err: unknown) {
      this.serverError.set(this.friendlyError(err));
    } finally {
      this.submitting.set(false);
    }
  }

  /** Step 2 — fetch the price catalogue from the backend. Auto-runs on entering the step. */
  protected async loadPrices(): Promise<void> {
    this.loadingPrices.set(true);
    this.pricesError.set(null);
    try {
      const cat = await this.signupSvc.fetchPrices();
      this.prices.set(cat);
      // Snap selectedTier to 'growth' if it's available, otherwise the first
      // tier that has a price for the current interval.
      if (!this.selectedPriceId()) {
        const firstAvailable = this.planList().find((p) => p.priceId !== null);
        if (firstAvailable) this.selectedTier.set(firstAvailable.tier);
      }
    } catch (err: unknown) {
      this.pricesError.set(
        this.friendlyError(err) || 'Could not load plans. Please try again.',
      );
    } finally {
      this.loadingPrices.set(false);
    }
  }

  /**
   * Resolve the class string for a plan tile. Kept in TS (not template) because
   * Angular's [class.foo] binding doesn't accept Tailwind variant prefixes like
   * `hover:` or arbitrary opacity suffixes (`bg-slate-800/60`) — those fail the
   * template lexer.
   */
  protected planTileClass(plan: { tier: PlanTier; priceId: string | null }): string {
    const base =
      'w-full text-left rounded-lg border px-4 py-3 transition-colors block ' +
      'disabled:opacity-40 disabled:cursor-not-allowed';
    if (this.selectedTier() === plan.tier) {
      return `${base} border-accent shadow-accent-ring bg-slate-800`;
    }
    const hover = plan.priceId ? ' hover:border-slate-600' : '';
    return `${base} border-slate-700 bg-slate-800/60${hover}`;
  }

  /** Tile click — only select if a price_id exists for this (tier, interval). */
  protected selectTier(tier: PlanTier): void {
    const plan = this.planList().find((p) => p.tier === tier);
    if (plan?.priceId) this.selectedTier.set(tier);
  }

  /** Advance from plan → card step. Card-step Stripe wiring lands in commit 3. */
  protected advanceToCard(): void {
    this.serverError.set(null);
    if (this.canAdvanceFromPlan()) {
      this.step.set(3);
    }
  }

  /**
   * Map backend / Supabase errors to a user-facing message.
   * We never surface raw vendor strings (see auth.py _auth_error_to_http for
   * the backend's matching mapping).
   */
  private friendlyError(err: unknown): string {
    // HttpErrorResponse shape — backend sends { detail: "…" } on 4xx/5xx.
    const e = err as { status?: number; error?: { detail?: string }; message?: string };
    if (typeof e?.status === 'number') {
      const detail = e.error?.detail;
      if (e.status === 409) return detail || 'Email already registered. Try signing in instead.';
      if (e.status === 422) return detail || 'Please check your details and try again.';
      if (e.status === 429) return 'Too many signup attempts. Please wait a moment and try again.';
      if (e.status === 503) return 'Signup is temporarily unavailable. Please try again later.';
      if (e.status >= 500) return 'Something went wrong on our end. Please try again.';
      return detail || 'Could not complete signup.';
    }
    return e?.message || 'Could not complete signup. Please try again.';
  }
}
