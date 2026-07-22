import { Component, inject, signal, OnInit } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

export interface RateCardLine {
  role: string;
  rate: string;           // decimal string, e.g. "250.00"
  service_line: string | null;
}

export interface RateCard {
  id: string;
  name: string;
  currency: string;
  effective_date: string; // ISO date
  lines: RateCardLine[];
}

const SERVICE_LINES = ['accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other'] as const;
const CURRENCIES = ['USD', 'GBP', 'SGD', 'INR', 'AUD'] as const;

@Component({
  selector: 'app-rate-cards',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">
      <div class="flex items-center justify-between px-6 py-4 border-b border-border-default">
        <div class="flex items-center gap-2">
          <mat-icon class="text-indigo-400">request_quote</mat-icon>
          <h3 class="text-base font-semibold text-text-primary">Rate Cards</h3>
        </div>
        <button
          type="button"
          (click)="openAddPanel()"
          class="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-1.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Add new rate card"
        >
          <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
          Add Rate Card
        </button>
      </div>

      @if (loading()) {
        <div class="divide-y divide-border-default animate-pulse" aria-busy="true" aria-label="Loading rate cards">
          @for (i of [1, 2]; track i) {
            <div class="flex items-center gap-4 px-6 py-4">
              <div class="h-4 bg-surface rounded w-1/3"></div>
              <div class="h-4 bg-surface rounded w-16"></div>
              <div class="h-4 bg-surface rounded w-24"></div>
            </div>
          }
        </div>
      }

      @if (loadError() && !loading()) {
        <div class="px-6 py-4 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Failed to load rate cards. <button type="button" class="underline hover:no-underline ml-1" (click)="load()">Retry</button>
        </div>
      }

      @if (!loading() && !loadError() && cards().length === 0) {
        <div class="px-6 py-10 text-center">
          <mat-icon class="text-3xl text-text-disabled mb-2 block">request_quote</mat-icon>
          <p class="text-sm text-text-muted">No rate cards yet. Create one to price engagements by role.</p>
        </div>
      }

      @if (!loading() && !loadError() && cards().length > 0) {
        <ul class="divide-y divide-border-default">
          @for (card of cards(); track card.id) {
            <li class="px-6 py-4">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-medium text-text-primary">{{ card.name }}</p>
                  <p class="text-xs text-text-muted mt-0.5">
                    {{ card.currency }} · effective {{ card.effective_date }} ·
                    {{ card.lines.length }} {{ card.lines.length === 1 ? 'role' : 'roles' }}
                  </p>
                </div>
                <button
                  type="button"
                  (click)="toggleExpanded(card.id)"
                  class="text-xs text-accent-light hover:text-text-secondary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded px-1"
                  [attr.aria-expanded]="expanded() === card.id"
                  [attr.aria-label]="(expanded() === card.id ? 'Hide' : 'Show') + ' roles for ' + card.name"
                >
                  {{ expanded() === card.id ? 'Hide roles' : 'Show roles' }}
                </button>
              </div>
              @if (expanded() === card.id) {
                <table class="w-full text-xs mt-3" aria-label="Rate card roles">
                  <thead>
                    <tr class="text-text-muted uppercase tracking-wide">
                      <th scope="col" class="text-left py-1">Role</th>
                      <th scope="col" class="text-left py-1">Service line</th>
                      <th scope="col" class="text-right py-1">Rate</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-subtle">
                    @for (line of card.lines; track line.role) {
                      <tr>
                        <td class="py-1.5 text-text-secondary">{{ line.role }}</td>
                        <td class="py-1.5 text-text-muted">{{ line.service_line || '—' }}</td>
                        <td class="py-1.5 text-text-primary font-mono tabular-nums text-right">
                          {{ card.currency }} {{ line.rate }}
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              }
            </li>
          }
        </ul>
      }
    </div>

    @if (showAddPanel()) {
      <div class="fixed inset-0 bg-black/50 z-40" (click)="closeAddPanel()" aria-hidden="true"></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-lg bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-rate-card-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="add-rate-card-title" class="text-base font-semibold text-text-primary">Add Rate Card</h2>
          <button
            type="button"
            (click)="closeAddPanel()"
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <form [formGroup]="addForm" (ngSubmit)="submitAdd()" class="flex-1 overflow-y-auto px-6 py-5 space-y-5" novalidate>
          <div>
            <label for="rc-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Name *</label>
            <input
              id="rc-name"
              type="text"
              formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. FY26 Standard Rates"
            />
            @if (addForm.controls.name.touched && addForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1">Name is required.</p>
            }
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="rc-currency" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Currency *</label>
              <select
                id="rc-currency"
                formControlName="currency"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              >
                @for (c of currencies; track c) {
                  <option [value]="c">{{ c }}</option>
                }
              </select>
            </div>
            <div>
              <label for="rc-effective" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Effective date *</label>
              <input
                id="rc-effective"
                type="date"
                formControlName="effective_date"
                class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              />
              @if (addForm.controls.effective_date.touched && addForm.controls.effective_date.errors) {
                <p class="text-xs text-confidence-low mt-1">Effective date is required.</p>
              }
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs uppercase tracking-wide text-text-muted">Roles &amp; rates *</span>
              <button
                type="button"
                (click)="addLine()"
                class="inline-flex items-center gap-1 text-xs text-accent-light hover:text-text-secondary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded px-1"
              >
                <mat-icon class="leading-none" style="font-size:0.9rem;width:0.9rem;height:0.9rem;">add</mat-icon>
                Add role
              </button>
            </div>
            <div class="space-y-2" formArrayName="lines">
              @for (line of lines.controls; track line; let i = $index) {
                <div class="grid grid-cols-[1fr_1fr_auto_auto] gap-2 items-start" [formGroupName]="i">
                  <input
                    type="text"
                    formControlName="role"
                    class="px-2 py-1.5 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                    [attr.aria-label]="'Role for line ' + (i + 1)"
                    placeholder="Role (e.g. Partner)"
                  />
                  <select
                    formControlName="service_line"
                    class="px-2 py-1.5 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                    [attr.aria-label]="'Service line for line ' + (i + 1)"
                  >
                    <option value="">(none)</option>
                    @for (sl of serviceLines; track sl) {
                      <option [value]="sl">{{ sl }}</option>
                    }
                  </select>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    formControlName="rate"
                    class="w-24 px-2 py-1.5 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
                    [attr.aria-label]="'Rate for line ' + (i + 1)"
                    placeholder="Rate"
                  />
                  <button
                    type="button"
                    (click)="removeLine(i)"
                    [disabled]="lines.length === 1"
                    class="p-1.5 text-text-muted hover:text-confidence-low disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                    [attr.aria-label]="'Remove line ' + (i + 1)"
                  >
                    <mat-icon style="font-size:1.05rem;width:1.05rem;height:1.05rem;">delete_outline</mat-icon>
                  </button>
                </div>
              }
            </div>
          </div>

          @if (addError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
              {{ addError() }}
            </div>
          }
        </form>

        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeAddPanel()"
          >
            Cancel
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="addForm.invalid || saving()"
            (click)="submitAdd()"
          >
            @if (saving()) { Saving… } @else { Add Rate Card }
          </button>
        </div>
      </aside>
    }
  `,
  styles: [':host { display: block; }'],
})
export class RateCardsComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  readonly serviceLines = SERVICE_LINES;
  readonly currencies = CURRENCIES;

  loading = signal(true);
  loadError = signal(false);
  cards = signal<RateCard[]>([]);
  expanded = signal<string | null>(null);

  showAddPanel = signal(false);
  saving = signal(false);
  addError = signal<string | null>(null);

  addForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    currency: ['USD', [Validators.required]],
    effective_date: ['', [Validators.required]],
    lines: this.fb.array([this.newLine()]),
  });

  get lines(): FormArray {
    return this.addForm.get('lines') as FormArray;
  }

  private newLine() {
    return this.fb.nonNullable.group({
      role: ['', [Validators.required]],
      rate: [null as number | null, [Validators.required, Validators.min(0)]],
      service_line: [''],
    });
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<RateCard[]>('/api/v1/rate-cards').subscribe({
      next: (data) => {
        this.cards.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  toggleExpanded(id: string): void {
    this.expanded.update(current => (current === id ? null : id));
  }

  addLine(): void {
    this.lines.push(this.newLine());
  }

  removeLine(index: number): void {
    if (this.lines.length > 1) this.lines.removeAt(index);
  }

  openAddPanel(): void {
    this.addForm.reset({ name: '', currency: 'USD', effective_date: '' });
    this.lines.clear();
    this.lines.push(this.newLine());
    this.addError.set(null);
    this.showAddPanel.set(true);
  }

  closeAddPanel(): void {
    this.showAddPanel.set(false);
  }

  submitAdd(): void {
    if (this.addForm.invalid) {
      this.addForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.addError.set(null);
    const v = this.addForm.getRawValue();
    this.http.post<RateCard>('/api/v1/rate-cards', {
      name: v.name,
      currency: v.currency,
      effective_date: v.effective_date,
      lines: v.lines.map(line => ({
        role: line.role,
        rate: String(line.rate),
        service_line: line.service_line || null,
      })),
    }).subscribe({
      next: (created) => {
        this.cards.update(list => [...list, created]);
        this.saving.set(false);
        this.closeAddPanel();
      },
      error: (err: { error?: { detail?: unknown } }) => {
        this.saving.set(false);
        const detail = err?.error?.detail;
        this.addError.set(typeof detail === 'string' ? detail : 'Could not save the rate card. Please try again.');
      },
    });
  }
}
