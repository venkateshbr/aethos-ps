import { Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/**
 * Placeholder clients list view.
 *
 * The Clients nav item ships before the full feature (engagement → invoice
 * flow). Without this placeholder the sidebar link hits the `**` wildcard
 * and redirects to the landing page — that was the root cause of #112.
 * Real CRUD lives in a follow-up ticket; this exists to make the nav
 * navigable for pilot validation.
 */
@Component({
  selector: 'app-clients-list',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <section class="h-full flex flex-col bg-surface-base text-text-primary">
      <header class="px-6 py-4 border-b border-border-default flex items-center justify-between">
        <h1 class="text-lg font-semibold text-text-primary">Clients</h1>
      </header>
      <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
        <mat-icon
          class="text-text-disabled mb-3"
          style="font-size:2.5rem;width:2.5rem;height:2.5rem;"
          aria-hidden="true"
        >people_outline</mat-icon>
        <p class="text-text-secondary font-medium">Clients view coming soon</p>
        <p class="text-text-disabled text-sm mt-1 max-w-md">
          Clients are derived from your engagements today. A dedicated
          CRM-style list lands in the next release.
        </p>
      </div>
    </section>
  `,
})
export class ClientsListComponent {}
