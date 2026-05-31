import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { SupabaseService } from '../../core/services/supabase.service';

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
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <div class="min-h-screen bg-surface-base text-text-primary flex flex-col">
      <!-- Header — mirror landing for visual continuity -->
      <header class="px-8 py-5 border-b border-border-subtle flex items-center justify-between">
        <a routerLink="/" aria-label="Aethos — for professional services">
          <img
            [src]="themeSvc.meta().lockupSrc"
            [alt]="'Aethos — for professional services (' + themeSvc.meta().label + ')'"
            class="h-10 w-auto"
          />
        </a>
        <a routerLink="/signup" class="text-sm text-text-secondary hover:text-text-primary transition-colors">
          Create account
        </a>
      </header>

      <main class="flex-1 flex items-center justify-center px-8 py-10">
        <div class="w-full max-w-md">
          <h1 class="text-3xl font-semibold text-text-primary mb-2">Sign in</h1>
          <p class="text-sm text-text-muted mb-8">
            Welcome back to Aethos.
          </p>

          <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-5" novalidate>

            <!-- Email -->
            <div>
              <label for="email" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                formControlName="email"
                autocomplete="email"
                class="w-full px-3 py-2 bg-surface border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
                placeholder="you@firm.com"
              />
              @if (form.controls.email.touched && form.controls.email.errors) {
                <p class="text-xs text-confidence-low mt-1">Enter a valid email.</p>
              }
            </div>

            <!-- Password -->
            <div>
              <label for="password" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                formControlName="password"
                autocomplete="current-password"
                class="w-full px-3 py-2 bg-surface border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
            </div>

            <!-- Error / submit -->
            @if (error()) {
              <p role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
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

          <p class="text-center text-sm text-text-muted mt-8">
            New here?
            <a routerLink="/signup" class="text-accent-light hover:text-accent font-medium">
              Get started
            </a>
          </p>
        </div>
      </main>

      <footer class="px-8 py-4 border-t border-border-subtle text-center text-xs text-text-muted">
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
  private supabaseSvc = inject(SupabaseService);

  protected form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  protected submitting = signal(false);
  protected error = signal<string | null>(null);

  async submit(): Promise<void> {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    try {
      const { email, password } = this.form.getRawValue();
      const { data, error } = await this.supabaseSvc.client.auth.signInWithPassword({ email, password });
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

      // Resolve which tenant this user belongs to so the auth interceptor can
      // attach X-Tenant-ID on subsequent calls. RLS on tenant_users (migration
      // 0001) lets the authenticated user read only their own membership rows.
      const userId = data.session?.user?.id;
      if (userId) {
        const { data: memberships, error: membershipErr } = await this.supabaseSvc.client
          .from('tenant_users')
          .select('tenant_id')
          .eq('user_id', userId)
          .is('deleted_at', null)
          .limit(1);
        if (membershipErr || !memberships?.length) {
          this.error.set('Sign-in succeeded but no tenant is associated with this account. Contact support.');
          this.auth.clearToken();
          return;
        }
        this.auth.setTenantId(memberships[0].tenant_id);
      }

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
