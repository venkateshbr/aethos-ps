import { Component, input, output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ConfidenceChipComponent } from '../../../shared/components/confidence-chip.component';

export interface ExpenseExtractedPayload {
  vendor: string;
  amount: string;
  currency: string;
  category: string;
  expense_date: string | null;
  description: string | null;
  confidence: string;
}

@Component({
  selector: 'app-expense-extracted-card',
  standalone: true,
  imports: [MatIconModule, MoneyPipe, ConfidenceChipComponent],
  template: `
    <div [class]="cardClass()" role="article" [attr.aria-label]="'Expense: ' + (payload().vendor)">

      <!-- Card header -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-amber-400 text-sm" aria-hidden="true">&#10022;</span>
        <span class="text-xs text-slate-400 font-medium uppercase tracking-wide">Expense Extracted</span>
        <app-confidence-chip [confidence]="payload().confidence" />
        @if (streaming()) {
          <div
            class="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"
            aria-hidden="true"
          ></div>
        }
      </div>

      <!-- Vendor + description -->
      <p class="text-sm font-semibold text-slate-100 mb-1">
        {{ payload().vendor || 'Unknown Vendor' }}
      </p>
      @if (payload().description) {
        <p class="text-xs text-slate-400 mb-3 leading-relaxed">{{ payload().description }}</p>
      }

      <!-- Detail grid -->
      <div class="grid grid-cols-3 gap-3 text-xs mb-4">
        <div>
          <div class="text-slate-500 mb-0.5">Amount</div>
          <div class="text-slate-200 font-mono">
            {{ payload().amount | money:payload().currency }}
          </div>
        </div>
        <div>
          <div class="text-slate-500 mb-0.5">Category</div>
          <div class="text-slate-200">{{ payload().category }}</div>
        </div>
        @if (payload().expense_date) {
          <div>
            <div class="text-slate-500 mb-0.5">Date</div>
            <div class="text-slate-200">{{ payload().expense_date }}</div>
          </div>
        }
      </div>

      <!-- Actions -->
      @if (!streaming() && hitlTaskId()) {
        <div class="flex gap-2 pt-3 border-t border-slate-700">
          <button
            (click)="onApprove.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
            aria-label="Approve expense"
          >
            Approve
          </button>
          <button
            (click)="onEdit.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded border border-slate-600 text-slate-300 hover:border-slate-500 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
            aria-label="Edit expense"
          >
            Edit
          </button>
          <button
            (click)="onReject.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded text-red-400 hover:text-red-300 hover:bg-red-950 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
            aria-label="Reject expense"
          >
            Reject
          </button>
        </div>
      }
    </div>
  `,
})
export class ExpenseExtractedCardComponent {
  payload    = input.required<ExpenseExtractedPayload>();
  hitlTaskId = input<string | null>(null);
  streaming  = input(false);

  onApprove = output<void>();
  onEdit    = output<void>();
  onReject  = output<void>();

  cardClass(): string {
    const base = 'rounded-lg border p-4 my-2 transition-all';
    return this.streaming()
      ? `${base} border-amber-500/50 bg-slate-800 shadow-[0_0_12px_rgba(245,158,11,0.08)]`
      : `${base} border-slate-600 bg-slate-800`;
  }
}
