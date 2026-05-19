import { Component, inject, signal, OnInit } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { Router } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { EngagementService, EngagementSummary } from '../../core/services/engagement.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';

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
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MoneyPipe,
  ],
  template: `
    <div class="p-6 bg-slate-900 min-h-full">
      <!-- Page header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-slate-50">Engagements</h1>
          <p class="text-sm text-slate-400 mt-1">All client engagements across your firm</p>
        </div>
        <button
          mat-flat-button
          class="bg-emerald-500 hover:bg-emerald-600 text-white rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
          aria-label="Create new engagement"
        >
          <mat-icon>add</mat-icon>
          New engagement
        </button>
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="rounded-lg overflow-hidden border border-slate-700" aria-label="Loading engagements" aria-busy="true">
          @for (row of [1, 2, 3]; track row) {
            <div class="flex gap-4 px-4 py-3 border-b border-slate-800 last:border-0">
              <div class="h-4 bg-slate-800 animate-pulse rounded w-1/4"></div>
              <div class="h-4 bg-slate-800 animate-pulse rounded w-1/6"></div>
              <div class="h-4 bg-slate-800 animate-pulse rounded w-1/8"></div>
              <div class="h-4 bg-slate-800 animate-pulse rounded w-1/6"></div>
              <div class="h-4 bg-slate-800 animate-pulse rounded w-1/12"></div>
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-400" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Something went wrong loading engagements. Please try again.
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !error() && engagements().length === 0) {
        <div class="rounded-lg border border-slate-700 bg-slate-800 px-6 py-12 text-center">
          <mat-icon class="text-4xl text-slate-500 mb-4 block">work_outline</mat-icon>
          <p class="text-slate-300 text-sm leading-relaxed mb-4">
            No engagements yet. Start by uploading an engagement letter or creating one manually.
          </p>
          <button
            mat-stroked-button
            class="border-slate-600 text-slate-300 hover:border-slate-400 hover:text-slate-100 rounded"
            aria-label="Create your first engagement"
          >
            <mat-icon>add</mat-icon>
            Create engagement
          </button>
        </div>
      }

      <!-- Table -->
      @if (!loading() && !error() && engagements().length > 0) {
        <div class="rounded-lg overflow-hidden border border-slate-700">
          <table
            mat-table
            [dataSource]="engagements()"
            class="w-full bg-slate-900"
            aria-label="Engagements"
          >
            <!-- Name column -->
            <ng-container matColumnDef="name">
              <th mat-header-cell *matHeaderCellDef class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Name
              </th>
              <td mat-cell *matCellDef="let row" class="text-slate-50 text-sm font-medium px-4 py-3 border-b border-slate-800">
                <button
                  class="text-left hover:text-emerald-400 transition-colors focus-visible:outline-none focus-visible:underline"
                  (click)="openDetail(row.id)"
                  [attr.aria-label]="'Open engagement ' + row.name"
                >
                  {{ row.name }}
                </button>
              </td>
            </ng-container>

            <!-- Client column -->
            <ng-container matColumnDef="client">
              <th mat-header-cell *matHeaderCellDef class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Client
              </th>
              <td mat-cell *matCellDef="let row" class="text-slate-300 text-sm px-4 py-3 border-b border-slate-800">
                {{ row.client_name ?? '—' }}
              </td>
            </ng-container>

            <!-- Billing type column -->
            <ng-container matColumnDef="billing">
              <th mat-header-cell *matHeaderCellDef class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Billing
              </th>
              <td mat-cell *matCellDef="let row" class="text-slate-300 text-sm px-4 py-3 border-b border-slate-800">
                {{ formatBilling(row.billing_arrangement) }}
              </td>
            </ng-container>

            <!-- Currency column -->
            <ng-container matColumnDef="currency">
              <th mat-header-cell *matHeaderCellDef class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Currency
              </th>
              <td mat-cell *matCellDef="let row" class="text-slate-400 text-sm font-mono px-4 py-3 border-b border-slate-800">
                {{ row.currency }}
              </td>
            </ng-container>

            <!-- Value column -->
            <ng-container matColumnDef="value">
              <th mat-header-cell *matHeaderCellDef class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3 text-right">
                Value
              </th>
              <td mat-cell *matCellDef="let row" class="text-slate-50 text-sm font-mono px-4 py-3 border-b border-slate-800 text-right tabular-nums">
                {{ row.total_value | money: row.currency }}
              </td>
            </ng-container>

            <!-- Status column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef class="text-slate-400 text-xs font-medium uppercase tracking-wide bg-slate-800 border-b border-slate-700 px-4 py-3">
                Status
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-slate-800">
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
              <th mat-header-cell *matHeaderCellDef class="bg-slate-800 border-b border-slate-700 px-4 py-3 w-12">
                <span class="sr-only">Actions</span>
              </th>
              <td mat-cell *matCellDef="let row" class="px-4 py-3 border-b border-slate-800">
                <button
                  mat-icon-button
                  class="text-slate-400 hover:text-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
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
              class="hover:bg-slate-800 transition-colors cursor-pointer"
              (click)="openDetail(row.id)"
              [attr.aria-label]="'Engagement: ' + row.name"
            ></tr>
          </table>
        </div>

        <p class="text-xs text-slate-500 mt-3">{{ engagements().length }} engagement{{ engagements().length !== 1 ? 's' : '' }}</p>
      }
    </div>
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

  loading = signal(true);
  error = signal<string | null>(null);
  engagements = signal<EngagementSummary[]>([]);

  displayedColumns = ['name', 'client', 'billing', 'currency', 'value', 'status', 'actions'];

  ngOnInit(): void {
    this.engagementService.getEngagements().subscribe({
      next: (res) => {
        this.engagements.set(res.items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load');
        this.loading.set(false);
      },
    });
  }

  formatBilling(arrangement: string): string {
    return formatBillingArrangement(arrangement);
  }

  statusClass(status: string): string {
    switch (status) {
      case 'active':    return 'bg-emerald-900 text-emerald-400';
      case 'draft':     return 'bg-amber-950 text-amber-400';
      case 'completed': return 'bg-slate-800 text-slate-400';
      case 'cancelled': return 'bg-red-950 text-red-400';
      default:          return 'bg-slate-800 text-slate-400';
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
}
