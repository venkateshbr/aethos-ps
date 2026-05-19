import { Component, input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * ConfidenceChipComponent — displays an agent confidence score (0–1) as a
 * colour-coded percentage chip. Note: parseFloat is used here only for
 * display-formatting of a probability float, NOT for financial computation.
 * All monetary values continue to use MoneyPipe per the Aethos quality gates.
 */
@Component({
  selector: 'app-confidence-chip',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span [class]="chipClass()">
      {{ label() }}
    </span>
  `,
})
export class ConfidenceChipComponent {
  /** Accept "0.78" (API string) or 0.78 (already numeric). */
  confidence = input.required<string | number>();

  private value = computed(() => {
    const v = this.confidence();
    return typeof v === 'string' ? parseFloat(v) : v;
  });

  label = computed(() => `${Math.round(this.value() * 100)}%`);

  chipClass = computed(() => {
    const v = this.value();
    const base = 'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium';
    if (v >= 0.8) return `${base} bg-emerald-900 text-emerald-400`;
    if (v >= 0.5) return `${base} bg-amber-950 text-amber-400`;
    return `${base} bg-red-950 text-red-400`;
  });
}
