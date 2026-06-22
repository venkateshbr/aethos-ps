import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { startWith } from 'rxjs';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SupabaseService } from '../../core/services/supabase.service';

/**
 * ChangePasswordComponent — Account / Security section of settings.
 *
 * Per issue #118. Frontend-only flow (no backend endpoint needed):
 *
 *   1. Re-authenticate with `signInWithPassword(email, current_password)` to
 *      verify the user actually knows the current password. This is the
 *      security gate — without it, a stolen session could change the password
 *      without the original owner's knowledge.
 *   2. On success, `supabase.auth.updateUser({ password: new_password })`
 *      mutates the password on the existing session.
 *   3. Show success; clear form.
 *
 * Email is pulled from the active Supabase session (the user is signed in or
 * the parent route guard wouldn't have let them get here).
 */
@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg p-6">
      <h3 class="text-sm font-semibold text-text-primary mb-1">Change password</h3>
      <p class="text-xs text-text-muted mb-5">
        You'll need to enter your current password to confirm the change.
      </p>

      <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4 max-w-md" novalidate>

        <div>
          <label for="current_password" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
            Current password
          </label>
          <input
            id="current_password"
            type="password"
            formControlName="current_password"
            autocomplete="current-password"
            class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
          />
        </div>

        <div>
          <label for="new_password" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
            New password
          </label>
          <input
            id="new_password"
            type="password"
            formControlName="new_password"
            autocomplete="new-password"
            minlength="8"
            class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
          />
          @if (newPwd().length > 0) {
            <div class="mt-2 flex items-center gap-2">
              <div class="flex-1 h-1 bg-surface rounded overflow-hidden">
                <div
                  class="h-full transition-all"
                  [style.width.%]="strengthPct()"
                  [class]="strengthBarClass()"
                ></div>
              </div>
              <span class="text-xs text-text-muted w-16 text-right">{{ strengthLabel() }}</span>
            </div>
          }
          @if (form.controls.new_password.touched && form.controls.new_password.errors?.['minlength']) {
            <p class="text-xs text-confidence-low mt-1">Password must be at least 8 characters.</p>
          }
        </div>

        <div>
          <label for="confirm_password" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
            Confirm new password
          </label>
          <input
            id="confirm_password"
            type="password"
            formControlName="confirm_password"
            autocomplete="new-password"
            class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
          />
          @if (form.controls.confirm_password.touched && form.errors?.['mismatch']) {
            <p class="text-xs text-confidence-low mt-1">Passwords don't match.</p>
          }
        </div>

        @if (error()) {
          <p role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
            {{ error() }}
          </p>
        }
        @if (success()) {
          <p role="status" class="text-sm text-accent-light bg-accent/10 border border-accent/40 rounded px-3 py-2">
            Password updated. Use your new password the next time you sign in.
          </p>
        }

        <div class="flex justify-end pt-2">
          <button
            type="submit"
            [disabled]="!canSubmit()"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            @if (submitting()) { Updating… } @else { Update password }
          </button>
        </div>
      </form>
    </div>
  `,
})
export class ChangePasswordComponent {
  private fb = inject(FormBuilder);
  private router = inject(Router);
  private auth = inject(AuthService);
  private supabaseSvc = inject(SupabaseService);

  protected form = this.fb.nonNullable.group(
    {
      current_password: ['', [Validators.required]],
      new_password: ['', [Validators.required, Validators.minLength(8)]],
      confirm_password: ['', [Validators.required]],
    },
    { validators: [matchPasswordsValidator()] },
  );

  protected submitting = signal(false);
  protected error = signal<string | null>(null);
  protected success = signal(false);
  private formStatus = toSignal(this.form.statusChanges.pipe(startWith(this.form.status)), {
    initialValue: this.form.status,
  });
  private newPasswordValue = toSignal(
    this.form.controls.new_password.valueChanges.pipe(startWith(this.form.controls.new_password.value)),
    { initialValue: this.form.controls.new_password.value },
  );

  protected canSubmit = computed(() => this.formStatus() === 'VALID' && !this.submitting());

  /** Reactive new-password value for the strength meter. */
  protected newPwd = computed(() => this.newPasswordValue() || '');
  protected strengthPct = computed(() => Math.min(100, scorePassword(this.newPwd()) * 25));
  protected strengthLabel = computed(() => {
    const s = scorePassword(this.newPwd());
    return ['weak', 'okay', 'good', 'strong'][Math.max(0, Math.min(3, s - 1))] ?? 'weak';
  });
  protected strengthBarClass = computed(() => {
    const s = scorePassword(this.newPwd());
    if (s <= 1) return 'bg-confidence-low';
    if (s === 2) return 'bg-confidence-med';
    return 'bg-accent';
  });

  async submit(): Promise<void> {
    this.error.set(null);
    this.success.set(false);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    try {
      const { current_password, new_password } = this.form.getRawValue();

      // 1. Pull the active user's email from the Supabase session
      const session = await this.supabaseSvc.client.auth.getSession();
      const email = session.data.session?.user?.email;
      if (!email) {
        this.error.set('Your session is missing an email. Please sign in again.');
        this.auth.clearToken();
        this.router.navigate(['/login']);
        return;
      }

      // 2. Verify current password by re-authenticating
      const verify = await this.supabaseSvc.client.auth.signInWithPassword({
        email,
        password: current_password,
      });
      if (verify.error) {
        this.error.set('Current password is incorrect.');
        return;
      }

      // 3. Update password on the active session
      const update = await this.supabaseSvc.client.auth.updateUser({ password: new_password });
      if (update.error) {
        this.error.set(this.translateUpdateError(update.error.message, (update.error as { code?: string }).code));
        return;
      }

      // 4. Refresh the in-memory token from the verify response (signInWithPassword
      //    returns a new session — keep AuthService in sync so the next request
      //    uses the latest access token).
      const newToken = verify.data.session?.access_token;
      if (newToken) {
        this.auth.setToken(newToken);
      }

      this.success.set(true);
      this.form.reset({ current_password: '', new_password: '', confirm_password: '' });
    } catch {
      this.error.set('Could not reach the authentication server. Check your connection and try again.');
    } finally {
      this.submitting.set(false);
    }
  }

  private translateUpdateError(message: string, code?: string): string {
    const lower = (message || '').toLowerCase();
    if (code === 'weak_password' || lower.includes('weak')) {
      return 'New password is too weak. Use 8+ characters with a mix of letters and numbers.';
    }
    if (code === 'session_expired' || lower.includes('jwt expired')) {
      return 'Your session expired. Please sign in again.';
    }
    if (code === 'same_password' || lower.includes('different')) {
      return 'New password must be different from the current one.';
    }
    return message || 'Could not update password. Try again.';
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

/** Validator: confirm_password must match new_password. */
function matchPasswordsValidator() {
  return (group: import('@angular/forms').AbstractControl) => {
    const a = group.get('new_password')?.value;
    const b = group.get('confirm_password')?.value;
    return a && b && a !== b ? { mismatch: true } : null;
  };
}

/** Rough password strength score 0-4 (length + variety). Used for the bar/label. */
function scorePassword(p: string): number {
  if (!p) return 0;
  let score = 0;
  if (p.length >= 8) score++;
  if (p.length >= 12) score++;
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) score++;
  if (/\d/.test(p) && /[^A-Za-z0-9]/.test(p)) score++;
  return score;
}
