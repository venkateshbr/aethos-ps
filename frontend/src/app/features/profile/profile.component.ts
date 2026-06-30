import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { SupabaseService } from '../../core/services/supabase.service';
import { ChangePasswordComponent } from '../settings/change-password.component';

interface OrgProfile {
  tenant_id: string;
  email: string;
  org_name: string;
  country: string;
  plan_tier: string;
  status: string;
  trial_ends_at: string | null;
  member_since: string;
}

const COUNTRY_NAMES: Record<string, string> = {
  US: 'United States', GB: 'United Kingdom', SG: 'Singapore',
  IN: 'India', AU: 'Australia',
};

const PLAN_LABELS: Record<string, string> = {
  starter: 'Starter', growth: 'Growth', pro: 'Pro',
};

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, MatIconModule, ChangePasswordComponent],
  template: `
    <div class="min-h-full bg-surface-base p-6">
      <h1 class="text-2xl font-semibold text-text-primary mb-1">Account</h1>
      <p class="text-sm text-text-muted mb-8">Your profile, organisation and security settings.</p>

      <div class="max-w-2xl space-y-6">
        @if (auth.mustChangePassword()) {
          <div class="rounded-lg border border-accent/40 bg-accent/10 px-4 py-3 text-sm text-accent-light" role="alert">
            Change your initial password to continue using Aethos.
          </div>
        }

        <!-- ── Organisation details ──────────────────────────────────── -->
        <section aria-labelledby="org-heading">
          <h2 id="org-heading" class="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3">
            Organisation
          </h2>

          @if (loading()) {
            <div class="bg-surface-raised border border-border-default rounded-lg p-6 animate-pulse space-y-3">
              <div class="h-4 bg-surface w-1/3 rounded"></div>
              <div class="h-4 bg-surface w-1/2 rounded"></div>
            </div>
          } @else if (profile()) {
            <div class="bg-surface-raised border border-border-default rounded-lg divide-y divide-border-default">

              <div class="flex items-center justify-between px-5 py-3.5">
                <span class="text-xs text-text-muted w-32 flex-none">Firm name</span>
                <span class="text-sm text-text-primary font-medium flex-1">{{ profile()!.org_name }}</span>
              </div>

              <div class="flex items-center justify-between px-5 py-3.5">
                <span class="text-xs text-text-muted w-32 flex-none">Email</span>
                <span class="text-sm text-text-primary flex-1">{{ profile()!.email }}</span>
              </div>

              <div class="flex items-center justify-between px-5 py-3.5">
                <span class="text-xs text-text-muted w-32 flex-none">Country</span>
                <span class="text-sm text-text-primary flex-1">{{ countryName() }}</span>
              </div>

              <div class="flex items-center justify-between px-5 py-3.5">
                <span class="text-xs text-text-muted w-32 flex-none">Plan</span>
                <span class="text-sm flex-1">
                  <span class="inline-flex items-center gap-1.5">
                    <span class="text-text-primary font-medium">{{ planLabel() }}</span>
                    <span [class]="statusChipClass()">{{ profile()!.status }}</span>
                  </span>
                </span>
              </div>

              @if (profile()!.trial_ends_at) {
                <div class="flex items-center justify-between px-5 py-3.5">
                  <span class="text-xs text-text-muted w-32 flex-none">Trial ends</span>
                  <span class="text-sm text-text-primary flex-1">{{ trialEnds() }}</span>
                </div>
              }

              <div class="flex items-center justify-between px-5 py-3.5">
                <span class="text-xs text-text-muted w-32 flex-none">Member since</span>
                <span class="text-sm text-text-muted flex-1">{{ profile()!.member_since }}</span>
              </div>

            </div>
          } @else if (error()) {
            <p class="text-sm text-confidence-low">{{ error() }}</p>
          }
        </section>

        <!-- ── Change password ───────────────────────────────────────── -->
        <section aria-labelledby="security-heading">
          <h2 id="security-heading" class="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3">
            Security
          </h2>
          <app-change-password />
        </section>

        <!-- ── Danger zone ───────────────────────────────────────────── -->
        <section aria-labelledby="danger-heading">
          <h2 id="danger-heading" class="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3">
            Session
          </h2>
          <div class="bg-surface-raised border border-border-default rounded-lg p-5 flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-text-primary">Sign out</p>
              <p class="text-xs text-text-muted mt-0.5">You'll need to sign in again to access Aethos.</p>
            </div>
            <button
              (click)="logout()"
              class="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded bg-confidence-low/10 hover:bg-confidence-low/20 text-confidence-low border border-confidence-low/30 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low"
            >
              <mat-icon style="font-size:1rem;width:1rem;height:1rem;">logout</mat-icon>
              Sign out
            </button>
          </div>
        </section>

      </div>
    </div>
  `,
})
export class ProfileComponent implements OnInit {
  private http    = inject(HttpClient);
  protected auth  = inject(AuthService);
  private router  = inject(Router);
  private supa    = inject(SupabaseService);

  protected loading = signal(true);
  protected profile = signal<OrgProfile | null>(null);
  protected error   = signal<string | null>(null);

  ngOnInit() { this.load(); }

  private async load() {
    try {
      const data = await firstValueFrom(
        this.http.get<OrgProfile>('/api/v1/billing/profile')
      );
      this.profile.set(data);
    } catch {
      this.error.set('Could not load profile. Please refresh.');
    } finally {
      this.loading.set(false);
    }
  }

  protected countryName() {
    return COUNTRY_NAMES[this.profile()?.country ?? ''] ?? this.profile()?.country ?? '';
  }

  protected planLabel() {
    return PLAN_LABELS[this.profile()?.plan_tier ?? ''] ?? this.profile()?.plan_tier ?? '';
  }

  protected trialEnds() {
    const d = this.profile()?.trial_ends_at;
    if (!d) return '';
    return new Date(d).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  }

  protected statusChipClass() {
    const s = this.profile()?.status ?? '';
    if (s === 'trialing') return 'text-xs px-2 py-0.5 rounded bg-confidence-med/15 text-confidence-med';
    if (s === 'active')   return 'text-xs px-2 py-0.5 rounded bg-confidence-high/15 text-confidence-high';
    return 'text-xs px-2 py-0.5 rounded bg-surface text-text-muted';
  }

  protected async logout() {
    await this.supa.client.auth.signOut().catch(() => {});
    this.auth.clearToken();
    this.router.navigate(['/login']);
  }
}
