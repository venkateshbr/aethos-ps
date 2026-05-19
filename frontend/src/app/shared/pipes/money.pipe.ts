import { Pipe, PipeTransform } from '@angular/core';

/**
 * MoneyPipe — formats API money strings (which are always strings per the Aethos contract)
 * using Intl.NumberFormat. Never uses parseFloat for computation — display only.
 */
@Pipe({ name: 'money', standalone: true })
export class MoneyPipe implements PipeTransform {
  transform(value: string | null | undefined, currency: string = 'USD'): string {
    if (value == null || value === '') return '—';
    // Safe: Number() is used only for display formatting, never for financial computation.
    const amount = Number(value);
    if (isNaN(amount)) return '—';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(amount);
  }
}
