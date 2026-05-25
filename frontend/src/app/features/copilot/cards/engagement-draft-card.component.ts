import { Component, input, output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { ConfidenceChipComponent } from '../../../shared/components/confidence-chip.component';

export interface EngagementDraftPayload {
  client_name: string;
  billing_arrangement: string;
  currency: string;
  total_value: string | null;
  scope_summary: string;
  confidence: string;
}

@Component({
  selector: 'app-engagement-draft-card',
  standalone: true,
  imports: [MatIconModule, MoneyPipe, ConfidenceChipComponent],
  template: `
    <div [class]="cardClass()" role="article" [attr.aria-label]="'Engagement draft: ' + (payload().client_name)">

      <!-- Card header -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-accent-light text-sm" aria-hidden="true">&#10022;</span>
        <span class="text-xs text-text-muted font-medium uppercase tracking-wide">Engagement Draft</span>
        <app-confidence-chip [confidence]="payload().confidence" />
        @if (streaming()) {
          <div
            class="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"
            aria-label="Streaming"
            aria-hidden="true"
          ></div>
        }
      </div>

      <!-- Client + scope -->
      <p class="text-sm font-semibold text-text-primary mb-1">
        {{ payload().client_name || 'Unknown Client' }}
      </p>
      <p class="text-xs text-text-muted mb-3 leading-relaxed">{{ payload().scope_summary }}</p>

      <!-- Detail grid -->
      <div class="grid grid-cols-3 gap-3 text-xs mb-4">
        <div>
          <div class="text-text-disabled mb-0.5">Billing</div>
          <div class="text-text-primary">{{ formatArrangement(payload().billing_arrangement) }}</div>
        </div>
        <div>
          <div class="text-text-disabled mb-0.5">Currency</div>
          <div class="text-text-primary">{{ payload().currency }}</div>
        </div>
        @if (payload().total_value) {
          <div>
            <div class="text-text-disabled mb-0.5">Value</div>
            <div class="text-text-primary font-mono">
              {{ payload().total_value | money:payload().currency }}
            </div>
          </div>
        }
      </div>

      <!-- Actions — only when not streaming and task ID is present -->
      @if (!streaming() && hitlTaskId()) {
        <div class="flex gap-2 pt-3 border-t border-border-default">
          <button
            (click)="onApprove.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded bg-accent hover:bg-accent text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
            aria-label="Approve engagement draft"
          >
            Approve
          </button>
          <button
            (click)="onEdit.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded border border-border-strong text-text-secondary hover:border-slate-500 hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
            aria-label="Edit engagement draft"
          >
            Edit
          </button>
          <button
            (click)="onReject.emit()"
            class="px-3 py-1.5 text-xs font-medium rounded text-confidence-low hover:text-confidence-low hover:bg-confidence-low/10 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
            aria-label="Reject engagement draft"
          >
            Reject
          </button>
        </div>
      }
    </div>
  `,
})
export class EngagementDraftCardComponent {
  payload    = input.required<EngagementDraftPayload>();
  hitlTaskId = input<string | null>(null);
  streaming  = input(false);

  onApprove = output<void>();
  onEdit    = output<void>();
  onReject  = output<void>();

  cardClass(): string {
    const base = 'rounded-lg border p-4 my-2 transition-all';
    return this.streaming()
      ? `${base} border-accent/50 bg-surface-raised shadow-[0_0_12px_rgba(16,185,129,0.08)]`
      : `${base} border-border-strong bg-surface-raised`;
  }

  formatArrangement(arr: string): string {
    return arr.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}
