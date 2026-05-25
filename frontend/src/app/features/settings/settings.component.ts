import { Component } from '@angular/core';
import { StripeConnectComponent } from './stripe-connect.component';
import { ChangePasswordComponent } from './change-password.component';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [StripeConnectComponent, ChangePasswordComponent],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Page header -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-text-primary">Settings</h1>
        <p class="text-sm text-text-muted mt-1">Manage your workspace, integrations, and billing preferences.</p>
      </div>

      <!-- Sections -->
      <div class="max-w-2xl space-y-8">

        <!-- Account / Security section (#118) -->
        <section aria-labelledby="account-heading">
          <h2 id="account-heading" class="text-sm font-semibold text-text-muted uppercase tracking-wide mb-3">
            Account &amp; security
          </h2>
          <app-change-password />
        </section>

        <!-- Integrations section -->
        <section aria-labelledby="integrations-heading">
          <h2 id="integrations-heading" class="text-sm font-semibold text-text-muted uppercase tracking-wide mb-3">
            Integrations
          </h2>
          <app-stripe-connect />
        </section>

      </div>
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class SettingsComponent {}
