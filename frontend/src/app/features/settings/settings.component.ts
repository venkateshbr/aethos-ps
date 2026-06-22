import { Component } from '@angular/core';
import { StripeConnectComponent } from './stripe-connect.component';
import { ChangePasswordComponent } from './change-password.component';
import { TaxRatesComponent } from './tax-rates.component';
import { AutonomyComponent } from './autonomy.component';
import { ServicesComponent } from './services.component';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [StripeConnectComponent, ChangePasswordComponent, TaxRatesComponent, AutonomyComponent, ServicesComponent],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Page header -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-text-primary">Settings</h1>
        <p class="text-sm text-text-muted mt-1">Manage your workspace, integrations, and billing preferences.</p>
      </div>

      <!-- Sections -->
      <div class="max-w-3xl space-y-8">

        <!-- Services & Products section (#237) -->
        <section aria-labelledby="services-heading">
          <h2 id="services-heading" class="text-sm font-semibold text-text-muted uppercase tracking-wide mb-3">
            Services &amp; Products
          </h2>
          <app-services />
        </section>

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

        <!-- Tax Rates section -->
        <section aria-labelledby="tax-rates-heading">
          <h2 id="tax-rates-heading" class="text-sm font-semibold text-text-muted uppercase tracking-wide mb-3">
            Tax Rates
          </h2>
          <app-tax-rates />
        </section>

        <!-- Autonomy section (#209) -->
        <section aria-labelledby="autonomy-heading">
          <h2 id="autonomy-heading" class="text-sm font-semibold text-text-muted uppercase tracking-wide mb-3">
            Agent Autonomy
          </h2>
          <app-autonomy />
        </section>

      </div>
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class SettingsComponent {}
