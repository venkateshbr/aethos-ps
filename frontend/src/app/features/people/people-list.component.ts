import { Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/**
 * Placeholder people / team view — see clients-list.component.ts for context.
 * The real People surface (team members, roles, billable rates, time-off)
 * lands in a follow-up ticket.
 */
@Component({
  selector: 'app-people-list',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <section class="h-full flex flex-col bg-slate-900 text-slate-100">
      <header class="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <h1 class="text-lg font-semibold text-slate-50">People</h1>
      </header>
      <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
        <mat-icon
          class="text-slate-500 mb-3"
          style="font-size:2.5rem;width:2.5rem;height:2.5rem;"
          aria-hidden="true"
        >badge</mat-icon>
        <p class="text-slate-300 font-medium">People view coming soon</p>
        <p class="text-slate-500 text-sm mt-1 max-w-md">
          Manage team members, billable rates, and roles. For the pilot,
          add teammates via Settings &rsaquo; Members.
        </p>
      </div>
    </section>
  `,
})
export class PeopleListComponent {}
