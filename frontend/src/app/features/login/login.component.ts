import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { ThemePickerComponent } from '../../shared/components/theme-picker.component';

/**
 * LoginComponent — sign in for returning pilot tenants.
 *
 * Per issue #119. No backend endpoint involved: we hit Supabase Auth
 * directly via @supabase/supabase-js (same pattern Rupa used in signup —
 * see `SignupService.signupAndSignIn`). The Supabase anon key is
 * publishable-safe; RLS + Prahari's tenant-membership dependency
 * (`backend/app/core/tenant.py`, #90 fix) enforce isolation server-side.
 *
 * Out of scope (Founder deferred):
 *   - Password reset flow
 *   - 2FA / passkeys
 *   - Magic-link login
 *   - RBAC enforcement (already handled by tenant-membership dep)
 */
@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, ThemePickerComponent],
  template: `
    <div class="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <!-- Header — mirror landing for visual continuity -->
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
          <a routerLink="/signup" class="text-sm text-slate-300 hover:text-white transition-colors">
            Create account
          </a>
        </div>
      </header>

      <main class="flex-1 flex items-center justify-center px-8 py-10">
        <div class="w-full max-w-md">
          <h1 class="text-3xl font-semibold text-slate-50 mb-2">Sign in</h1>
          <p class="text-sm text-slate-400 mb-8">
            Welcome back to Aethos.
          </p>

          <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-5" novalidate>

            <!-- Email -->
            <div>
              <label for="email" class="block text-xs uppercase tracking-wide text-slate-400 mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                formControlName="email"
                autocomplete="email"
                class="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
                placeholder="you@firm.com"
              />
              @if (form.controls.email.touched && form.controls.email.errors) {
                <p class="text-xs text-red-400 mt-1">Enter a valid email.</p>
              }
            </div>

            <!-- Password -->
            <div>
              <label for="password" class="block text-xs uppercase tracking-wide text-slate-400 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                formControlName="password"
                autocomplete="current-password"
                class="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
            </div>

            <!-- Error / submit -->
            @if (error()) {
              <p role="alert" class="text-sm text-red-400 bg-red-950 border border-red-900 rounded px-3 py-2">
                {{ error() }}
              </p>
            }

            <button
              type="submit"
              [disabled]="form.invalid || submitting()"
              class="w-full inline-flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-6 py-2.5 rounded transition-colors text-sm shadow-accent-ring disabled:opacity-60 disabled:cursor-not-allowed"
            >
              @if (submitting()) { Signing in… } @else { Sign in }
            </button>
          </form>

          <p class="text-center text-sm text-slate-400 mt-8">
            New here?
            <a routerLink="/signup" class="text-accent-light hover:text-accent font-medium">
              Get started
            </a>
          </p>
        </div>
      </main>

      <footer class="px-8 py-4 border-t border-slate-800 text-center text-xs text-slate-500">
        Aethos · for professional services · &copy; 2026
      </footer>
    </div>
  `,
})
export class LoginComponent {
  protected themeSvc = inject(ThemeService);
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private auth = inject(AuthService);

  protected form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  protected submitting = signal(false);
  protected error = signal<string | null>(null);

  /** Lazy Supabase client (same approach as SignupService). */
  private _supabase: SupabaseClient | null = null;
  private supabase(): SupabaseClient {
    if (!this._supabase) {
      this._supabase = createClient(environment.supabaseUrl, environment.supabaseAnonKey);
    }
    return this._supabase;
  }

  async submit(): Promise<void> {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    try {
      const { email, password } = this.form.getRawValue();
      const { data, error } = await this.supabase().auth.signInWithPassword({ email, password });
      if (error) {
        this.error.set(this.translateError(error.message, (error as { code?: string }).code));
        return;
      }
      const token = data.session?.access_token;
      if (!token) {
        this.error.set('Sign-in succeeded but no session was issued. Please reload and try again.');
        return;
      }
      this.auth.setToken(token);
      this.router.navigate(['/app/copilot']);
    } catch (err) {
      this.error.set('Could not reach the authentication server. Check your connection and try again.');
    } finally {
      this.submitting.set(false);
    }
  }

  /** Map Supabase Auth errors to user-facing copy. */
  private translateError(message: string, code?: string): string {
    const lower = (message || '').toLowerCase();
    if (code === 'invalid_credentials' || lower.includes('invalid login credentials')) {
      return 'Email or password is incorrect.';
    }
    if (code === 'email_not_confirmed' || lower.includes('email not confirmed')) {
      return 'Please confirm your email before signing in.';
    }
    if (code === 'over_request_rate_limit' || lower.includes('rate limit')) {
      return 'Too many attempts. Please wait a moment and try again.';
    }
    return message || 'Could not sign you in. Try again.';
  }
}
