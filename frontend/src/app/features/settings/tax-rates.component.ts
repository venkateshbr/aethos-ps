import { Component, inject, signal, OnInit } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

export interface TaxRate {
  id: string;
  name: string;
  rate: string;          // decimal string, e.g. "10.00"
  market: string | null; // 'US'|'UK'|'SG'|'IN'|'AU'|null (null = All)
  is_system: boolean;
  is_active: boolean;
}

@Component({
  selector: 'app-tax-rates',
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule, MatIconModule, MatSlideToggleModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-border-default">
        <div class="flex items-center gap-2">
          <mat-icon class="text-indigo-400">percent</mat-icon>
          <h3 class="text-base font-semibold text-text-primary">Tax Rates</h3>
        </div>
        <button
          type="button"
          (click)="openAddPanel()"
          class="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-1.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Add new tax rate"
        >
          <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
          Add Tax Rate
        </button>
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="divide-y divide-border-default animate-pulse" aria-busy="true" aria-label="Loading tax rates">
          @for (i of [1, 2, 3]; track i) {
            <div class="flex items-center gap-4 px-6 py-4">
              <div class="h-4 bg-surface rounded w-1/3"></div>
              <div class="h-4 bg-surface rounded w-16"></div>
              <div class="h-4 bg-surface rounded w-12"></div>
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @if (loadError() && !loading()) {
        <div class="px-6 py-4 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Failed to load tax rates. <button type="button" class="underline hover:no-underline ml-1" (click)="load()">Retry</button>
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !loadError() && rates().length === 0) {
        <div class="px-6 py-10 text-center">
          <mat-icon class="text-3xl text-text-disabled mb-2 block">percent</mat-icon>
          <p class="text-sm text-text-muted">No tax rates configured yet.</p>
        </div>
      }

      <!-- Table -->
      @if (!loading() && !loadError() && rates().length > 0) {
        <div class="overflow-x-auto">
          <table class="w-full text-sm" aria-label="Tax Rates">
            <thead>
              <tr class="text-text-muted text-xs uppercase tracking-wide border-b border-border-default bg-surface-base/50">
                <th scope="col" class="text-left px-6 py-3">Name</th>
                <th scope="col" class="text-left px-6 py-3">Rate</th>
                <th scope="col" class="text-left px-6 py-3">Market</th>
                <th scope="col" class="text-left px-6 py-3">System</th>
                <th scope="col" class="text-left px-6 py-3">Active</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              @for (rate of rates(); track rate.id) {
                <tr class="hover:bg-surface-base/40 transition-colors">
                  <td class="px-6 py-3 text-text-primary font-medium">{{ rate.name }}</td>
                  <td class="px-6 py-3 text-text-secondary font-mono tabular-nums">{{ formatRate(rate.rate) }}%</td>
                  <td class="px-6 py-3">
                    @if (rate.market) {
                      <span class="inline-block px-2 py-0.5 rounded text-xs font-medium bg-indigo-500/20 text-indigo-300">{{ rate.market }}</span>
                    } @else {
                      <span class="text-text-muted text-xs">All</span>
                    }
                  </td>
                  <td class="px-6 py-3">
                    @if (rate.is_system) {
                      <mat-icon
                        class="text-text-muted"
                        style="font-size:1.1rem;width:1.1rem;height:1.1rem;"
                        aria-label="System rate (read-only)"
                        title="System rate — read-only"
                      >lock</mat-icon>
                    } @else {
                      <span class="text-text-disabled text-xs">—</span>
                    }
                  </td>
                  <td class="px-6 py-3">
                    @if (rate.is_system) {
                      <!-- System rates cannot be toggled -->
                      <span
                        class="inline-flex items-center gap-1 text-xs font-medium"
                        [class]="rate.is_active ? 'text-accent-light' : 'text-text-disabled'"
                        aria-label="System rate — active state cannot be changed"
                      >
                        <span
                          class="w-2 h-2 rounded-full"
                          [class]="rate.is_active ? 'bg-emerald-400' : 'bg-slate-600'"
                          aria-hidden="true"
                        ></span>
                        {{ rate.is_active ? 'Active' : 'Inactive' }}
                      </span>
                    } @else {
                      <!-- Custom rates: toggle active state -->
                      <!-- TODO: PATCH /api/v1/tax-rates/{id} endpoint to be implemented by Karya -->
                      <button
                        type="button"
                        [disabled]="toggling() === rate.id"
                        (click)="toggleActive(rate)"
                        class="inline-flex items-center gap-1.5 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded px-1"
                        [class]="rate.is_active ? 'text-accent-light hover:text-text-secondary' : 'text-text-disabled hover:text-text-muted'"
                        [attr.aria-label]="(rate.is_active ? 'Deactivate' : 'Activate') + ' ' + rate.name"
                        [attr.aria-pressed]="rate.is_active"
                      >
                        <span
                          class="w-2 h-2 rounded-full transition-colors"
                          [class]="rate.is_active ? 'bg-emerald-400' : 'bg-slate-600'"
                          aria-hidden="true"
                        ></span>
                        @if (toggling() === rate.id) {
                          <span>Saving…</span>
                        } @else {
                          <span>{{ rate.is_active ? 'Active' : 'Inactive' }}</span>
                        }
                      </button>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>

    <!-- Add Tax Rate slide-in panel -->
    @if (showAddPanel()) {
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/50 z-40"
        (click)="closeAddPanel()"
        aria-hidden="true"
      ></div>
      <!-- Panel -->
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-tax-rate-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="add-tax-rate-title" class="text-base font-semibold text-text-primary">Add Tax Rate</h2>
          <button
            type="button"
            (click)="closeAddPanel()"
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <form
          [formGroup]="addForm"
          (ngSubmit)="submitAdd()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >
          <!-- Name -->
          <div>
            <label for="tr-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Name *</label>
            <input
              id="tr-name"
              type="text"
              formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. GST 10%"
            />
            @if (addForm.controls.name.touched && addForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1">Name is required.</p>
            }
          </div>

          <!-- Rate -->
          <div>
            <label for="tr-rate" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Rate (%) *</label>
            <input
              id="tr-rate"
              type="number"
              min="0"
              max="100"
              step="0.01"
              formControlName="rate"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
              placeholder="e.g. 10.00"
            />
            @if (addForm.controls.rate.touched && addForm.controls.rate.errors) {
              <p class="text-xs text-confidence-low mt-1">Enter a rate between 0 and 100.</p>
            }
          </div>

          <!-- Market -->
          <div>
            <label for="tr-market" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Market</label>
            <select
              id="tr-market"
              formControlName="market"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="">All markets</option>
              <option value="US">US — United States</option>
              <option value="UK">UK — United Kingdom</option>
              <option value="SG">SG — Singapore</option>
              <option value="IN">IN — India</option>
              <option value="AU">AU — Australia</option>
            </select>
          </div>

          <!-- Active toggle -->
          <div class="flex items-center justify-between">
            <label for="tr-active" class="text-sm text-text-primary">Active</label>
            <button
              id="tr-active"
              type="button"
              role="switch"
              [attr.aria-checked]="addForm.controls.is_active.value"
              (click)="addForm.controls.is_active.setValue(!addForm.controls.is_active.value)"
              class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [class]="addForm.controls.is_active.value ? 'bg-accent' : 'bg-slate-700'"
            >
              <span
                class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
                [class]="addForm.controls.is_active.value ? 'translate-x-6' : 'translate-x-1'"
                aria-hidden="true"
              ></span>
            </button>
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
            @if (saving()) { Saving… } @else { Add Tax Rate }
          </button>
        </div>
      </aside>
    }
  `,
  styles: [':host { display: block; }'],
})
export class TaxRatesComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  loading = signal(true);
  loadError = signal(false);
  rates = signal<TaxRate[]>([]);

  // Toggle active state for custom rates
  toggling = signal<string | null>(null);

  // Add panel
  showAddPanel = signal(false);
  saving = signal(false);
  addError = signal<string | null>(null);

  addForm = this.fb.nonNullable.group({
    name:      ['', [Validators.required]],
    rate:      [null as number | null, [Validators.required, Validators.min(0), Validators.max(100)]],
    market:    [''],
    is_active: [true],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<TaxRate[]>('/api/v1/tax-rates').subscribe({
      next: (data) => {
        this.rates.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  formatRate(rate: string): string {
    const n = Number(rate);
    return isNaN(n) ? rate : n.toFixed(2);
  }

  toggleActive(rate: TaxRate): void {
    if (rate.is_system) return;
    this.toggling.set(rate.id);
    // TODO: PATCH /api/v1/tax-rates/{id} endpoint — to be implemented by Karya
    this.http.patch<TaxRate>(`/api/v1/tax-rates/${rate.id}`, { is_active: !rate.is_active }).subscribe({
      next: (updated) => {
        this.rates.update(list => list.map(r => r.id === updated.id ? updated : r));
        this.toggling.set(null);
      },
      error: () => {
        // Silently revert on failure — endpoint may not exist yet
        this.toggling.set(null);
      },
    });
  }

  openAddPanel(): void {
    this.addForm.reset({ name: '', rate: null, market: '', is_active: true });
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
    this.http.post<TaxRate>('/api/v1/tax-rates', {
      name:      v.name,
      rate:      String(v.rate),
      market:    v.market || null,
      is_active: v.is_active,
    }).subscribe({
      next: (created) => {
        this.rates.update(list => [...list, created]);
        this.saving.set(false);
        this.closeAddPanel();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.saving.set(false);
        const detail = err?.error?.detail;
        this.addError.set(typeof detail === 'string' ? detail : 'Could not save tax rate. Please try again.');
      },
    });
  }
}
