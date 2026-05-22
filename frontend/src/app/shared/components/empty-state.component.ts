import { Component, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/**
 * EmptyStateComponent — consistent empty state for all list pages.
 * Shows an icon, a heading, a sub-message, and an optional CTA button.
 */
@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="rounded-lg border border-slate-700 bg-slate-800 px-4 py-12 text-center">
      <mat-icon
        class="text-4xl text-slate-500 mb-3 block"
        style="font-size:2.5rem;width:2.5rem;height:2.5rem;"
        aria-hidden="true"
      >{{ icon() }}</mat-icon>
      <p class="text-slate-300 font-medium mb-1">{{ heading() }}</p>
      <p class="text-slate-500 text-sm">{{ message() }}</p>
    </div>
  `,
})
export class EmptyStateComponent {
  icon    = input<string>('inbox');
  heading = input<string>('Nothing here yet');
  message = input<string>('Items will appear here once added.');
}
