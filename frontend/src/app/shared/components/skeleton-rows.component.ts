import { Component, input, computed } from '@angular/core';

/**
 * SkeletonRowsComponent — animated loading skeleton for list/table pages.
 * Renders `count` placeholder rows with a pulse animation.
 */
@Component({
  selector: 'app-skeleton-rows',
  standalone: true,
  template: `
    <div
      class="rounded-lg overflow-hidden border border-border-default animate-pulse"
      aria-busy="true"
      [attr.aria-label]="ariaLabel()"
    >
      @for (row of rows(); track row) {
        <div class="flex gap-4 px-4 py-3 border-b border-border-subtle last:border-0 bg-surface-raised">
          <div class="h-4 bg-surface rounded w-24"></div>
          <div class="h-4 bg-surface rounded w-32"></div>
          <div class="h-4 bg-surface rounded w-20"></div>
          <div class="h-4 bg-surface rounded flex-1"></div>
          <div class="h-4 bg-surface rounded w-16"></div>
        </div>
      }
    </div>
  `,
})
export class SkeletonRowsComponent {
  count     = input<number>(4);
  ariaLabel = input<string>('Loading…');

  rows = computed(() => Array.from({ length: this.count() }, (_, i) => i));
}
