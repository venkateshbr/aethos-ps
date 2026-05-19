import { Component, input, output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ConfidenceChipComponent } from '../../../shared/components/confidence-chip.component';

export interface BillExtractedPayload {
  vendor_name: string;
  invoice_number: string | null;
  total: string;
  currency: string;
  line_count: number | null;
  due_date: string | null;
  confidence: string;
}

@Component({
  selector: 'app-bill-extracted-card',
  standalone: true,
  imports: [MatIconModule, MoneyPipe, ConfidenceChipComponent],
  template: `
    <div [class]="cardClass()" role="article" aria-label="Vendor bill: {{ payload().vendor_name }}">

      <!-- Card header -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-indigo-400 text-sm" aria-hidden="true">&#10022;</span>
        <span class="text-xs text-slate-400 font-medium uppercase tracking-wide">Vendor Bill</span>
        <app-confidence-chip [confidence]="payload().confidence" />
        @if (streaming()) {
          <div
            class="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"
            aria-hidden="true"
          ></div>
        }
      </div>

      <!-- Vendor + invoice number -->
      <p class="text-sm font-semibold text-slate-100 mb-1">
        {{ payload().vendor_name || 'Unknown Vendor' }}
      </p>
      @if (payload().invoice_number) {
        <p class="text-xs text-slate-500 mb-3 font-mono">
          Invoice {{ payload().invoice_number }}
        </p>
      }

      <!-- Detail grid -->
      <div class="grid grid-cols-3 gap-3 text-xs mb-4">
        <div>
          <div class="text-slate-500 mb-0.5">Total</div>
          <div class="text-slate-200 font-mono">
            {{ payload().total | money:payload().currency }}
          </div>
        </div>
        @if (payload().line_count != null) {
          <div>
            <div class="text-slate-500 mb-0.5">Lines</div>
            <div class="text-slate-200">{{ payload().line_count }}</div>
          </div>
        }
        @if (payload().due_date) {
          <div>
            <div class="text-slate-500 mb-0.5">Due</div>
            <div class="text-slate-200">{{ payload().due_date }}</div>
          </div>
        }
      </div>

      <!-- Actions -->
      @if (!streaming() && hitlTaskId()) {
        <div class="flex gap-2 pt-3 border-t border-slate-700">
          <button
            (click)="onApprove.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
            aria-label="Approve vendor bill"
          >
            Approve
          </button>
          <button
            (click)="onEdit.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded border border-slate-600 text-slate-300 hover:border-slate-500 hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
            aria-label="Edit vendor bill"
          >
            Edit
          </button>
          <button
            (click)="onReject.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded text-red-400 hover:text-red-300 hover:bg-red-950 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
            aria-label="Reject vendor bill"
          >
            Reject
          </button>
        </div>
      }
    </div>
  `,
})
export class BillExtractedCardComponent {
  payload    = input.required<BillExtractedPayload>();
  hitlTaskId = input<string | null>(null);
  streaming  = input(false);

  onApprove = output<void>();
  onEdit    = output<void>();
  onReject  = output<void>();

  cardClass(): string {
    const base = 'rounded-lg border p-4 my-2 transition-all';
    return this.streaming()
      ? `${base} border-indigo-500/50 bg-slate-800 shadow-[0_0_12px_rgba(99,102,241,0.08)]`
      : `${base} border-slate-600 bg-slate-800`;
  }
}
