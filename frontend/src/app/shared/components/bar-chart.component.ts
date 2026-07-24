import { Component, computed, input } from '@angular/core';

export interface BarChartDatum {
  label: string;
  value: number;
  /** Optional Tailwind background class for the bar (defaults to the accent). */
  colorClass?: string;
}

/**
 * Dependency-free, CSP-safe horizontal bar chart (no external chart library).
 * Accessible: the group is a labelled img and each bar carries an aria-label
 * with its label + formatted value. Used to give the reports/dashboard a visual
 * primitive beyond tables (#405).
 */
@Component({
  selector: 'app-bar-chart',
  standalone: true,
  imports: [],
  template: `
    <figure class="w-full" role="img" [attr.aria-label]="ariaLabel()">
      @if (title()) {
        <figcaption class="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">
          {{ title() }}
        </figcaption>
      }
      @if (bars().length === 0) {
        <p class="text-sm text-text-disabled py-4 text-center">No data to chart.</p>
      } @else {
        <div class="space-y-2.5">
          @for (bar of bars(); track bar.label) {
            <div class="grid grid-cols-[8rem_1fr_auto] items-center gap-3 text-sm">
              <span class="truncate text-text-secondary" [title]="bar.label">{{ bar.label }}</span>
              <div class="h-5 rounded bg-surface overflow-hidden" aria-hidden="true">
                <div
                  class="h-full rounded transition-[width] duration-500"
                  [class]="bar.colorClass || 'bg-accent'"
                  [style.width.%]="bar.pct"
                ></div>
              </div>
              <span class="font-mono tabular-nums text-text-primary text-right min-w-[6rem]">
                {{ bar.display }}
              </span>
            </div>
          }
        </div>
      }
    </figure>
  `,
  styles: [':host { display: block; }'],
})
export class BarChartComponent {
  data = input.required<BarChartDatum[]>();
  title = input<string>('');
  format = input<'currency' | 'number' | 'percent'>('number');
  currency = input<string>('USD');

  private max = computed(() =>
    Math.max(1, ...this.data().map(d => Math.abs(Number(d.value) || 0))),
  );

  bars = computed(() =>
    this.data().map(d => {
      const value = Number(d.value) || 0;
      return {
        label: d.label,
        colorClass: d.colorClass,
        pct: (Math.abs(value) / this.max()) * 100,
        display: this.formatValue(value),
      };
    }),
  );

  ariaLabel = computed(() => {
    const parts = this.data().map(d => `${d.label}: ${this.formatValue(Number(d.value) || 0)}`);
    return `${this.title() || 'Bar chart'}. ${parts.join(', ')}`;
  });

  private formatValue(value: number): string {
    if (this.format() === 'currency') {
      return `${this.currency()} ${value.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`;
    }
    if (this.format() === 'percent') {
      return `${value.toFixed(1)}%`;
    }
    return value.toLocaleString();
  }
}
