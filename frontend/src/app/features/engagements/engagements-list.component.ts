import { Component, inject, signal, OnInit } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { Router } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { EngagementService, EngagementSummary } from '../../core/services/engagement.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { userMessageForError } from '../../core/utils/error-message';

function formatBillingArrangement(arrangement: string): string {
  const map: Record<string, string> = {
    time_and_materials: 'T&M',
    fixed_fee: 'Fixed',
    retainer: 'Retainer',
    milestone: 'Milestone',
    capped_tm: 'Capped T&M',
  };
  return map[arrangement] ?? arrangement;
}

@Component({
  selector: 'app-engagements-list',
  standalone: true,
  imports: [
    TitleCasePipe,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MoneyPipe,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Page header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Engagements</h1>
          <p class="text-sm text-text-muted mt-1">All client engagements across your firm</p>
        </div>
        <button
          mat-flat-button
          class="bg-accent hover:bg-accent text-accent-on rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Create new engagement"
          (click)="openCreateForm()"
        >
          <mat-icon>add</mat-icon>
          New engagement
        </button>
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="rounded-lg overflow-hidden border border-border-default" aria-label="Loading engagements" aria-busy="true">
          @for (row of [1, 2, 3]; track row) {
            <div class="flex gap-4 px-4 py-3 border-b border-border-subtle last:border-0">
              <div class="h-4 bg-surface-raised animate-pulse rounded w-1/4"></div>
              <div class="h-4 bg-surface-raised animate-pulse rounded w-1/6"></div>
              <div class="h-4 bg-surface-raised animate-pulse rounded w-1/8"></div>
              <div class="h-4 bg-surface-raised animate-pulse rounded w-1/6"></div>
              <div class="h-4 bg-surface-raised animate-pulse rounded w-1/12"></div>
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !error() && engagements().length === 0) {
        <div class="rounded-lg border border-border-default bg-surface-raised px-6 py-12 text-center">
          <mat-icon class="text-4xl text-text-disabled mb-4 block">work_outline</mat-icon>
          <p class="text-text-secondary text-sm leading-relaxed mb-4">
            No engagements yet. Start by uploading an engagement letter or creating one manually.
          </p>
          <button
            mat-stroked-button
            class="border-border-strong text-text-secondary hover:border-border-strong hover:text-text-primary rounded"
            aria-label="Create your first engagement"
            (click)="openCreateForm()"
          >
            <mat-icon>add</mat-icon>
            Create engagement
          </button>
        </div>
      }

      <!-- Table -->
      @if (!loading() && !error() && engagements().length > 0) {
        <div class="rounded-lg overflow-hidden border border-border-default">
          <table
            mat-table
            [dataSource]="engagements()"
            class="w-full bg-surface-base"
            aria-label="Engagements"
          >
            <!-- Name column -->
            <ng-container matColumnDef="name">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Name
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium px-4 py-3 border-b border-border-subtle">
                <button
                  class="text-left hover:text-accent-light transition-colors focus-visible:outline-none focus-visible:underline"
                  (click)="openDetail(row.id)"
                  [attr.aria-label]="'Open engagement ' + row.name"
                >
                  {{ row.name }}
                </button>
              </td>
            </ng-container>

            <!-- Client column -->
            <ng-container matColumnDef="client">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Client
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle">
                {{ row.client_name ?? '—' }}
              </td>
            </ng-container>

            <!-- Billing type column -->
            <ng-container matColumnDef="billing">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Billing
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm px-4 py-3 border-b border-border-subtle">
                {{ formatBilling(row.billing_arrangement) }}
              </td>
            </ng-container>

            <!-- Currency column -->
            <ng-container matColumnDef="currency">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Currency
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-muted text-sm font-mono px-4 py-3 border-b border-border-subtle">
                {{ row.currency }}
              </td>
            </ng-container>

            <!-- Value column -->
            <ng-container matColumnDef="value">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3 text-right">
                Value
              </th>
              <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono px-4 py-3 border-b border-border-subtle text-right tabular-nums">
                {{ row.total_value | money: row.currency }}
              </td>
            </ng-container>

            <!-- Status column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs font-medium uppercase tracking-wide bg-surface-raised border-b border-border-default px-4 py-3">
                Status
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                  [class]="statusClass(row.status)"
                  [attr.aria-label]="'Status: ' + row.status"
                >
                  <span class="w-1.5 h-1.5 rounded-full" [class]="statusDotClass(row.status)"></span>
                  {{ row.status | titlecase }}
                </span>
              </td>
            </ng-container>

            <!-- Actions column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef class="bg-surface-raised border-b border-border-default px-4 py-3 w-12">
                <span class="sr-only">Actions</span>
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-border-subtle">
                <button
                  mat-icon-button
                  class="text-text-muted hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                  [matTooltip]="'Open engagement'"
                  (click)="openDetail(row.id)"
                  [attr.aria-label]="'Open ' + row.name"
                >
                  <mat-icon class="text-base">chevron_right</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr
              mat-row
              *matRowDef="let row; columns: displayedColumns"
              class="hover:bg-surface-raised transition-colors cursor-pointer"
              (click)="openDetail(row.id)"
              [attr.aria-label]="'Engagement: ' + row.name"
            ></tr>
          </table>
        </div>

        <p class="text-xs text-text-disabled mt-3">{{ engagements().length }} engagement{{ engagements().length !== 1 ? 's' : '' }}</p>
      }
    </div>

    <!-- Create engagement slide-in panel -->
    @if (showCreateForm()) {
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/50 z-40"
        (click)="closeCreateForm()"
        aria-hidden="true"
      ></div>
      <!-- Panel -->
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-engagement-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="create-engagement-title" class="text-base font-semibold text-text-primary">New engagement</h2>
          <button
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeCreateForm()"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <form
          [formGroup]="createForm"
          (ngSubmit)="submitCreate()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >
          <!-- Name -->
          <div>
            <label for="eng-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Name *</label>
            <input
              id="eng-name"
              type="text"
              formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. Q3 Advisory — Acme Corp"
            />
            @if (createForm.controls.name.touched && createForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1">Name is required.</p>
            }
          </div>

          <!-- Billing arrangement -->
          <div>
            <label for="eng-billing" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Billing arrangement *</label>
            <select
              id="eng-billing"
              formControlName="billing_arrangement"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="">Select…</option>
              <option value="time_and_materials">Time &amp; Materials</option>
              <option value="fixed_fee">Fixed Fee</option>
              <option value="retainer">Retainer</option>
              <option value="milestone">Milestone</option>
              <option value="capped_tm">Capped T&amp;M</option>
            </select>
            @if (createForm.controls.billing_arrangement.touched && createForm.controls.billing_arrangement.errors) {
              <p class="text-xs text-confidence-low mt-1">Billing arrangement is required.</p>
            }
          </div>

          <!-- Currency -->
          <div>
            <label for="eng-currency" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Currency *</label>
            <select
              id="eng-currency"
              formControlName="currency"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="">Select…</option>
              <option value="USD">USD — US Dollar</option>
              <option value="GBP">GBP — British Pound</option>
              <option value="SGD">SGD — Singapore Dollar</option>
              <option value="INR">INR — Indian Rupee</option>
              <option value="AUD">AUD — Australian Dollar</option>
            </select>
            @if (createForm.controls.currency.touched && createForm.controls.currency.errors) {
              <p class="text-xs text-confidence-low mt-1">Currency is required.</p>
            }
          </div>

          <!-- Total value -->
          <div>
            <label for="eng-value" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Total value</label>
            <input
              id="eng-value"
              type="text"
              formControlName="total_value"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
              placeholder="e.g. 25000.00"
            />
            <p class="text-xs text-text-muted mt-1">Optional. Enter as a decimal number.</p>
          </div>

          @if (createError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
              {{ createError() }}
            </div>
          }
        </form>

        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeCreateForm()"
          >
            Cancel
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="createForm.invalid || creating()"
            (click)="submitCreate()"
          >
            @if (creating()) { Creating… } @else { Create engagement }
          </button>
        </div>
      </aside>
    }
  `,
  styles: [`
    :host { display: block; }

    /* Override Material table background to match dark theme */
    ::ng-deep .mat-mdc-table {
      background: transparent !important;
    }
    ::ng-deep .mat-mdc-header-row,
    ::ng-deep .mat-mdc-row {
      background: transparent !important;
    }
    ::ng-deep .mat-mdc-cell,
    ::ng-deep .mat-mdc-header-cell {
      border-bottom: none !important;
    }
  `],
})
export class EngagementsListComponent implements OnInit {
  private engagementService = inject(EngagementService);
  private router = inject(Router);
  private fb = inject(FormBuilder);

  loading = signal(true);
  error = signal<string | null>(null);
  engagements = signal<EngagementSummary[]>([]);

  // Create form state
  showCreateForm = signal(false);
  creating = signal(false);
  createError = signal<string | null>(null);
  createForm = this.fb.nonNullable.group({
    name:                ['', [Validators.required]],
    billing_arrangement: ['', [Validators.required]],
    currency:            ['', [Validators.required]],
    total_value:         [''],
  });

  displayedColumns = ['name', 'client', 'billing', 'currency', 'value', 'status', 'actions'];

  ngOnInit(): void {
    this.engagementService.getEngagements().subscribe({
      next: (res) => {
        this.engagements.set(res);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        // #113: pick copy by status code (session-expired vs. service-down).
        this.error.set(userMessageForError(err, 'Engagements'));
        this.loading.set(false);
      },
    });
  }

  formatBilling(arrangement: string): string {
    return formatBillingArrangement(arrangement);
  }

  statusClass(status: string): string {
    switch (status) {
      case 'active':    return 'bg-accent/15 text-accent-light';
      case 'draft':     return 'bg-confidence-med/10 text-confidence-med';
      case 'completed': return 'bg-surface-raised text-text-muted';
      case 'cancelled': return 'bg-confidence-low/10 text-confidence-low';
      default:          return 'bg-surface-raised text-text-muted';
    }
  }

  statusDotClass(status: string): string {
    switch (status) {
      case 'active':    return 'bg-emerald-400';
      case 'draft':     return 'bg-amber-400';
      case 'completed': return 'bg-slate-400';
      case 'cancelled': return 'bg-red-400';
      default:          return 'bg-slate-400';
    }
  }

  openDetail(id: string): void {
    this.router.navigate(['/app/engagements', id]);
  }

  openCreateForm(): void {
    this.createForm.reset({ name: '', billing_arrangement: '', currency: '', total_value: '' });
    this.createError.set(null);
    this.showCreateForm.set(true);
  }

  closeCreateForm(): void {
    this.showCreateForm.set(false);
  }

  submitCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    this.creating.set(true);
    this.createError.set(null);
    const v = this.createForm.getRawValue();
    this.engagementService.createEngagement({
      name:                v.name,
      client_id:           '', // optional — will be set later in the engagement detail
      billing_arrangement: v.billing_arrangement,
      currency:            v.currency,
      total_value:         v.total_value || null,
    }).subscribe({
      next: (newEng) => {
        this.engagements.update(list => [newEng as unknown as EngagementSummary, ...list]);
        this.creating.set(false);
        this.closeCreateForm();
      },
      error: (err: { status?: number; error?: { detail?: string } }) => {
        this.creating.set(false);
        const detail = err?.error?.detail;
        this.createError.set(
          typeof detail === 'string' ? detail : 'Could not create engagement. Please try again.'
        );
      },
    });
  }
}
