import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth';
import { SupabaseService } from '../../core/supabase.service';

function matchingPasswords(control: AbstractControl): ValidationErrors | null {
  return control.get('new_password')?.value === control.get('confirm_password')?.value
    ? null
    : { mismatch: true };
}

@Component({
  selector: 'ts-change-password',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <div class="min-h-screen flex items-center justify-center px-4 bg-surface-base">
      <div class="w-full max-w-md">
        <div class="flex items-center gap-2 justify-center mb-8">
          <span class="inline-block w-5 h-5 bg-accent rounded-[3px]"></span>
          <span class="text-lg font-bold tracking-wide text-text-primary">Aethos Timesheets</span>
        </div>

        <div class="bg-surface border border-border-default rounded-xl p-6 shadow-xl">
          <h1 class="text-xl font-semibold text-text-primary mb-1">Set a new password</h1>
          <p class="text-sm text-text-muted mb-6">
            Your administrator issued a temporary password. Replace it before opening your timesheet.
          </p>

          <form [formGroup]="form" (ngSubmit)="submit()" novalidate class="space-y-4">
            <div>
              <label for="ts-current-password" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Current password
              </label>
              <input
                id="ts-current-password"
                type="password"
                formControlName="current_password"
                autocomplete="current-password"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
            </div>
            <div>
              <label for="ts-new-password" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                New password
              </label>
              <input
                id="ts-new-password"
                type="password"
                formControlName="new_password"
                autocomplete="new-password"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
              @if (form.controls.new_password.touched && form.controls.new_password.errors?.['minlength']) {
                <p class="mt-1 text-xs text-confidence-low">Use at least 8 characters.</p>
              }
            </div>
            <div>
              <label for="ts-confirm-password" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                Confirm new password
              </label>
              <input
                id="ts-confirm-password"
                type="password"
                formControlName="confirm_password"
                autocomplete="new-password"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
              />
              @if (form.controls.confirm_password.touched && form.errors?.['mismatch']) {
                <p class="mt-1 text-xs text-confidence-low">Passwords do not match.</p>
              }
            </div>

            @if (error()) {
              <p role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
                {{ error() }}
              </p>
            }

            <button
              type="submit"
              [disabled]="form.invalid || submitting()"
              class="w-full inline-flex items-center justify-center bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2.5 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              @if (submitting()) { Updating… } @else { Update password }
            </button>
          </form>
        </div>
      </div>
    </div>
  `,
})
export class ChangePasswordComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private router = inject(Router);
  private auth = inject(AuthService);
  private supabase = inject(SupabaseService);

  protected submitting = signal(false);
  protected error = signal<string | null>(null);
  protected form = this.fb.nonNullable.group(
    {
      current_password: ['', Validators.required],
      new_password: ['', [Validators.required, Validators.minLength(8)]],
      confirm_password: ['', Validators.required],
    },
    { validators: matchingPasswords },
  );

  protected async submit(): Promise<void> {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    try {
      const { current_password, new_password } = this.form.getRawValue();
      const session = await this.supabase.client.auth.getSession();
      const email = session.data.session?.user?.email;
      if (!email) throw new Error('session_missing');

      const verified = await this.supabase.client.auth.signInWithPassword({
        email,
        password: current_password,
      });
      if (verified.error || !verified.data.session) {
        this.error.set('Current password is incorrect.');
        return;
      }

      const updated = await this.supabase.client.auth.updateUser({ password: new_password });
      if (updated.error) {
        this.error.set(
          updated.error.message.toLowerCase().includes('different')
            ? 'New password must be different from the temporary password.'
            : 'Could not update the password. Check the requirements and try again.',
        );
        return;
      }

      this.auth.refreshToken(verified.data.session.access_token);
      await firstValueFrom(this.http.post('/api/v1/auth/complete-password-change', {}));
      this.auth.markPasswordChanged();
      await this.router.navigateByUrl('/timesheet');
    } catch {
      this.error.set('Could not complete the password change. Please try again.');
    } finally {
      this.submitting.set(false);
    }
  }
}
