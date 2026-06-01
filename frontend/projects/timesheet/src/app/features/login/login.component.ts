import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../../core/auth';
import { SupabaseService } from '../../core/supabase.service';

@Component({
  selector: 'ts-login',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="min-h-screen flex items-center justify-center px-4 bg-surface-base">
      <div class="w-full max-w-sm">
        <div class="flex items-center gap-2 justify-center mb-8">
          <span class="inline-block w-5 h-5 bg-accent rounded-[3px]"></span>
          <span class="text-lg font-bold tracking-wide text-text-primary">Aethos Timesheets</span>
        </div>

        <div class="bg-surface border border-border-default rounded-xl p-6 shadow-xl">
          <h1 class="text-xl font-semibold text-text-primary mb-1">Sign in</h1>
          <p class="text-sm text-text-muted mb-6">Log the hours you worked on your projects.</p>

          <form [formGroup]="form" (ngSubmit)="submit()" novalidate class="space-y-4">
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Email</label>
              <input type="email" formControlName="email" autocomplete="username"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
            <div>
              <label class="block text-xs uppercase tracking-wide text-text-muted mb-2">Password</label>
              <input type="password" formControlName="password" autocomplete="current-password"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent" />
            </div>
            @if (error()) {
              <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">{{ error() }}</div>
            }
            <button type="submit" [disabled]="form.invalid || loading()"
              class="w-full inline-flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2.5 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed">
              @if (loading()) { Signing in… } @else { Sign in }
            </button>
          </form>
        </div>
      </div>
    </div>
  `,
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private supa = inject(SupabaseService);
  private auth = inject(AuthService);
  private router = inject(Router);

  loading = signal(false);
  error = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  async submit(): Promise<void> {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.error.set(null);
    const { email, password } = this.form.getRawValue();
    const { data, error } = await this.supa.client.auth.signInWithPassword({ email, password });
    if (error || !data.session) {
      this.error.set('Invalid email or password.');
      this.loading.set(false);
      return;
    }
    const token = data.session.access_token;
    const userId = data.session.user?.id;
    // Resolve tenant via the self-read policy (migration 0020).
    const { data: memberships, error: memErr } = await this.supa.client
      .from('tenant_users')
      .select('tenant_id')
      .eq('user_id', userId)
      .is('deleted_at', null)
      .limit(1);
    if (memErr || !memberships?.length) {
      this.error.set('No organisation is linked to this account. Contact your administrator.');
      this.loading.set(false);
      return;
    }
    this.auth.setSession(token, memberships[0].tenant_id as string);
    await this.router.navigateByUrl('/timesheet');
  }
}
