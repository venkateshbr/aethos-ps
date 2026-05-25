import { Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/**
 * Placeholder payments view — see clients-list.component.ts for context on
 * why this exists. The real Payments surface (Stripe Connect ledger + manual
 * payment recording) lands in a follow-up ticket.
 */
@Component({
  selector: 'app-payments-list',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <section class="h-full flex flex-col bg-surface-base text-text-primary">
      <header class="px-6 py-4 border-b border-border-default flex items-center justify-between">
        <h1 class="text-lg font-semibold text-text-primary">Payments</h1>
      </header>
      <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
        <mat-icon
          class="text-text-disabled mb-3"
          style="font-size:2.5rem;width:2.5rem;height:2.5rem;"
          aria-hidden="true"
        >account_balance</mat-icon>
        <p class="text-text-secondary font-medium">Payments view coming soon</p>
        <p class="text-text-disabled text-sm mt-1 max-w-md">
          Track received payments, Stripe Connect transfers, and manual
          payment recording. Ships with the billing-cash close in the next release.
        </p>
      </div>
    </section>
  `,
})
export class PaymentsListComponent {}
