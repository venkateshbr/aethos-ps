import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ThemeService } from '../../core/services/theme.service';
import { ThemePickerComponent } from '../../shared/components/theme-picker.component';
import {
  LAUNCH_COUNTRIES,
  LaunchCountry,
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

    <!-- ── Step 2 · Plan (next commit) ─────────────────────────────────────── -->
    <ng-template #planStep>
      <h1 class="text-2xl font-semibold mb-1">Pick a plan</h1>
      <p class="text-slate-400 text-sm mb-6">
        Coming next commit. Your firm is created; this step picks a Stripe price.
      </p>
      <button
        type="button"
        (click)="step.set(1)"
        class="text-sm text-slate-400 hover:text-slate-200"
      >
        ← Back
      </button>
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
    } catch (err: unknown) {
      this.serverError.set(this.friendlyError(err));
    } finally {
      this.submitting.set(false);
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
