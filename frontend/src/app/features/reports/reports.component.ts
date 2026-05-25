import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import {
  ReportsService,
  AgingReport,
  PnlRow,
  UtilRow,
  WipRow,
} from '../../core/services/reports.service';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, MatTabsModule, MatTableModule, MatIconModule, MoneyPipe],
  template: `
    <div class="min-h-full bg-surface-base p-6">
      <h1 class="text-2xl font-semibold text-text-primary mb-6">Reports</h1>

      <mat-tab-group
        animationDuration="150ms"
        class="reports-tabs"
      >
        <!-- ── AR Aging ──────────────────────────────────────────────────── -->
        <mat-tab label="AR Aging">
          <div class="pt-4">
            @defer (on viewport) {
              @if (arLoading()) {
                <ng-container *ngTemplateOutlet="agingSkeleton" />
              } @else if (arError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'AR Aging', retry: loadAr.bind(this) }" />
              } @else if (!arData()) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'AR aging data' }" />
              } @else {
                <ng-container *ngTemplateOutlet="agingCards; context: { $implicit: arData()! }" />
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="agingSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="agingSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- ── AP Aging ──────────────────────────────────────────────────── -->
        <mat-tab label="AP Aging">
          <div class="pt-4">
            @defer (on viewport) {
              @if (apLoading()) {
                <ng-container *ngTemplateOutlet="agingSkeleton" />
              } @else if (apError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'AP Aging', retry: loadAp.bind(this) }" />
              } @else if (!apData()) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'AP aging data' }" />
              } @else {
                <ng-container *ngTemplateOutlet="agingCards; context: { $implicit: apData()! }" />
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="agingSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="agingSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- ── Project P&L ────────────────────────────────────────────── -->
        <mat-tab label="Project P&L">
          <div class="pt-4">
            @defer (on viewport) {
              @if (pnlLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (pnlError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Project P&L', retry: loadPnl.bind(this) }" />
              } @else if (pnlRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'P&L data' }" />
              } @else {
                <div class="overflow-x-auto rounded-lg border border-border-default">
                  <table mat-table [dataSource]="pnlRows()" class="w-full bg-surface-raised">
                    <ng-container matColumnDef="project_name">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Project</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">{{ row.project_name }}</td>
                    </ng-container>
                    <ng-container matColumnDef="revenue">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Revenue</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono">{{ row.revenue | money: row.currency }}</td>
                    </ng-container>
                    <ng-container matColumnDef="direct_cost">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Direct Cost</th>
                      <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm font-mono">{{ row.direct_cost | money: row.currency }}</td>
                    </ng-container>
                    <ng-container matColumnDef="gross_margin">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Gross Margin</th>
                      <td mat-cell *matCellDef="let row" class="text-sm font-mono font-medium" [class]="marginAmountClass(row.gross_margin_pct)">{{ row.gross_margin | money: row.currency }}</td>
                    </ng-container>
                    <ng-container matColumnDef="gross_margin_pct">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Margin %</th>
                      <td mat-cell *matCellDef="let row">
                        <span [class]="marginPctClass(row.gross_margin_pct)">
                          {{ row.gross_margin_pct.toFixed(1) }}%
                        </span>
                      </td>
                    </ng-container>
                    <tr mat-header-row *matHeaderRowDef="pnlColumns" class="bg-surface-base/50"></tr>
                    <tr mat-row *matRowDef="let row; columns: pnlColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
                  </table>
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- ── Utilization ────────────────────────────────────────────── -->
        <mat-tab label="Utilization">
          <div class="pt-4">
            @defer (on viewport) {
              @if (utilLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (utilError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Utilization', retry: loadUtil.bind(this) }" />
              } @else if (utilRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'utilization data' }" />
              } @else {
                <div class="overflow-x-auto rounded-lg border border-border-default">
                  <table mat-table [dataSource]="utilRows()" class="w-full bg-surface-raised">
                    <ng-container matColumnDef="employee_id">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Employee</th>
                      <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm font-mono">{{ row.employee_id }}</td>
                    </ng-container>
                    <ng-container matColumnDef="total_hours">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Total Hours</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono">{{ row.total_hours }}</td>
                    </ng-container>
                    <ng-container matColumnDef="billable_hours">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Billable Hours</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono">{{ row.billable_hours }}</td>
                    </ng-container>
                    <ng-container matColumnDef="utilization_pct">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Util %</th>
                      <td mat-cell *matCellDef="let row">
                        <span [class]="utilChipClass(row.utilization_pct)">
                          {{ row.utilization_pct.toFixed(1) }}%
                        </span>
                      </td>
                    </ng-container>
                    <tr mat-header-row *matHeaderRowDef="utilColumns" class="bg-surface-base/50"></tr>
                    <tr mat-row *matRowDef="let row; columns: utilColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
                  </table>
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- ── WIP ────────────────────────────────────────────────────── -->
        <mat-tab label="WIP">
          <div class="pt-4">
            @defer (on viewport) {
              @if (wipLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (wipError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'WIP', retry: loadWip.bind(this) }" />
              } @else if (wipRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'WIP data' }" />
              } @else {
                <div class="overflow-x-auto rounded-lg border border-border-default">
                  <table mat-table [dataSource]="wipRows()" class="w-full bg-surface-raised">
                    <ng-container matColumnDef="project_name">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Project</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">{{ row.project_name }}</td>
                    </ng-container>
                    <ng-container matColumnDef="unbilled_hours">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Unbilled Hours</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono">{{ row.unbilled_hours }}</td>
                    </ng-container>
                    <ng-container matColumnDef="avg_rate">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Avg Rate</th>
                      <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm font-mono">{{ row.avg_rate | money }}/h</td>
                    </ng-container>
                    <ng-container matColumnDef="wip_value">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">WIP Value</th>
                      <td mat-cell *matCellDef="let row" class="text-accent-light text-sm font-mono font-bold">{{ row.wip_value | money }}</td>
                    </ng-container>
                    <tr mat-header-row *matHeaderRowDef="wipColumns" class="bg-surface-base/50"></tr>
                    <tr mat-row *matRowDef="let row; columns: wipColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
                  </table>
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- ── Revenue ────────────────────────────────────────────────── -->
        <mat-tab label="Revenue">
          <div class="pt-4">
            <div class="flex flex-col items-center justify-center h-64 text-center bg-surface-raised rounded-lg border border-border-default">
              <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;" aria-hidden="true">bar_chart</mat-icon>
              <p class="text-text-muted font-medium">Revenue by Engagement</p>
              <p class="text-text-disabled text-sm mt-1">Coming in the next release</p>
            </div>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>

    <!-- ── Shared templates ─────────────────────────────────────────────── -->

    <!-- Aging metric cards -->
    <ng-template #agingCards let-data>
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-6">
        <div class="bg-surface-raised border border-border-default rounded-lg p-4">
          <p class="text-xs text-text-muted uppercase tracking-wide mb-1">0–30 days</p>
          <p class="text-xl font-bold text-text-primary font-mono">{{ data['0_30'] | money }}</p>
        </div>
        <div class="bg-surface-raised border border-confidence-med/40/50 rounded-lg p-4">
          <p class="text-xs text-confidence-med uppercase tracking-wide mb-1">31–60 days</p>
          <p class="text-xl font-bold text-confidence-med font-mono">{{ data['31_60'] | money }}</p>
        </div>
        <div class="bg-surface-raised border border-orange-700/50 rounded-lg p-4">
          <p class="text-xs text-orange-400 uppercase tracking-wide mb-1">61–90 days</p>
          <p class="text-xl font-bold text-orange-400 font-mono">{{ data['61_90'] | money }}</p>
        </div>
        <div class="bg-surface-raised border border-red-700/50 rounded-lg p-4">
          <p class="text-xs text-confidence-low uppercase tracking-wide mb-1">90+ days</p>
          <p class="text-xl font-bold text-confidence-low font-mono">{{ data['over_90'] | money }}</p>
        </div>
      </div>
      <div class="bg-surface-raised border border-border-default rounded-lg p-4 flex items-center justify-between">
        <p class="text-sm text-text-muted uppercase tracking-wide font-medium">Total Outstanding</p>
        <p class="text-3xl font-bold text-text-primary font-mono">{{ data.total | money }}</p>
      </div>
    </ng-template>

    <!-- Aging skeleton -->
    <ng-template #agingSkeleton>
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-6 animate-pulse">
        @for (i of [1, 2, 3, 4]; track i) {
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <div class="h-3 bg-surface rounded w-16 mb-2"></div>
            <div class="h-6 bg-surface rounded w-24"></div>
          </div>
        }
      </div>
      <div class="bg-surface-raised border border-border-default rounded-lg p-4 animate-pulse">
        <div class="h-8 bg-surface rounded w-40"></div>
      </div>
    </ng-template>

    <!-- Table skeleton -->
    <ng-template #tableSkeleton>
      <div class="rounded-lg border border-border-default overflow-hidden animate-pulse">
        <div class="h-10 bg-surface-base/50 border-b border-border-default"></div>
        @for (i of [1, 2, 3, 4, 5]; track i) {
          <div class="h-12 border-b border-border-default/50 bg-surface-raised flex items-center px-4 gap-4">
            <div class="h-3 bg-surface rounded w-32"></div>
            <div class="h-3 bg-surface rounded w-20"></div>
            <div class="h-3 bg-surface rounded w-20"></div>
            <div class="h-3 bg-surface rounded w-16"></div>
          </div>
        }
      </div>
    </ng-template>

    <!-- Empty state -->
    <ng-template #emptyState let-label>
      <div class="flex flex-col items-center justify-center h-64 text-center bg-surface-raised rounded-lg border border-border-default">
        <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;" aria-hidden="true">inbox</mat-icon>
        <p class="text-text-muted font-medium">No {{ label }} available</p>
        <p class="text-text-disabled text-sm mt-1">Data will appear once transactions are recorded</p>
      </div>
    </ng-template>

    <!-- Error state -->
    <ng-template #errorState let-label let-retry="retry">
      <div class="flex flex-col items-center justify-center h-64 text-center bg-surface-raised rounded-lg border border-border-default" role="alert">
        <mat-icon class="text-confidence-low mb-3" style="font-size:2rem;width:2rem;height:2rem;">error_outline</mat-icon>
        <p class="text-text-secondary font-medium">Failed to load {{ label }}</p>
        <p class="text-text-disabled text-sm mt-1 mb-4">Something went wrong. Please try again.</p>
        @if (retry) {
          <button
            (click)="retry()"
            class="px-4 py-2 text-xs font-medium rounded bg-surface hover:bg-surface-raised text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
          >Retry</button>
        }
      </div>
    </ng-template>
  `,
  styles: [`
    :host { display: block; }

    ::ng-deep .reports-tabs .mat-mdc-tab-header {
      border-bottom: 1px solid rgb(51 65 85); /* slate-700 */
    }
    ::ng-deep .reports-tabs .mat-mdc-tab-body-wrapper {
      padding-top: 0;
    }
    ::ng-deep .reports-tabs .mdc-tab__text-label {
      color: rgb(148 163 184); /* slate-400 */
      font-size: 0.875rem;
    }
    ::ng-deep .reports-tabs .mdc-tab--active .mdc-tab__text-label {
      color: rgb(248 250 252); /* slate-50 */
    }
    ::ng-deep .reports-tabs .mdc-tab-indicator__content--underline {
      border-color: rgb(99 102 241); /* indigo-500 */
    }
    ::ng-deep .reports-tabs .mat-mdc-table {
      background: transparent;
    }
    ::ng-deep .reports-tabs .mat-mdc-header-row {
      background: rgb(15 23 42 / 0.5); /* slate-900/50 */
    }
    ::ng-deep .reports-tabs .mat-mdc-header-cell,
    ::ng-deep .reports-tabs .mat-mdc-cell {
      border-bottom-color: rgb(51 65 85 / 0.7); /* slate-700/70 */
      padding: 0.75rem 1rem;
    }
    ::ng-deep .reports-tabs .mat-mdc-row:last-child .mat-mdc-cell {
      border-bottom: none;
    }
  `],
})
export class ReportsComponent implements OnInit {
  private svc = inject(ReportsService);

  // AR Aging
  arLoading = signal(false);
  arError = signal(false);
  arData = signal<AgingReport | null>(null);

  // AP Aging
  apLoading = signal(false);
  apError = signal(false);
  apData = signal<AgingReport | null>(null);

  // Project P&L
  pnlLoading = signal(false);
  pnlError = signal(false);
  pnlRows = signal<PnlRow[]>([]);

  // Utilization
  utilLoading = signal(false);
  utilError = signal(false);
  utilRows = signal<UtilRow[]>([]);

  // WIP
  wipLoading = signal(false);
  wipError = signal(false);
  wipRows = signal<WipRow[]>([]);

  readonly pnlColumns = ['project_name', 'revenue', 'direct_cost', 'gross_margin', 'gross_margin_pct'];
  readonly utilColumns = ['employee_id', 'total_hours', 'billable_hours', 'utilization_pct'];
  readonly wipColumns = ['project_name', 'unbilled_hours', 'avg_rate', 'wip_value'];

  ngOnInit(): void {
    this.loadAr();
    this.loadAp();
    this.loadPnl();
    this.loadUtil();
    this.loadWip();
  }

  loadAr(): void {
    this.arLoading.set(true);
    this.arError.set(false);
    this.svc.getArAging().subscribe({
      next: data => { this.arData.set(data); this.arLoading.set(false); },
      error: () => { this.arError.set(true); this.arLoading.set(false); },
    });
  }

  loadAp(): void {
    this.apLoading.set(true);
    this.apError.set(false);
    this.svc.getApAging().subscribe({
      next: data => { this.apData.set(data); this.apLoading.set(false); },
      error: () => { this.apError.set(true); this.apLoading.set(false); },
    });
  }

  loadPnl(): void {
    this.pnlLoading.set(true);
    this.pnlError.set(false);
    this.svc.getProjectPnl().subscribe({
      next: rows => { this.pnlRows.set(rows); this.pnlLoading.set(false); },
      error: () => { this.pnlError.set(true); this.pnlLoading.set(false); },
    });
  }

  loadUtil(): void {
    this.utilLoading.set(true);
    this.utilError.set(false);
    this.svc.getUtilization().subscribe({
      next: rows => { this.utilRows.set(rows); this.utilLoading.set(false); },
      error: () => { this.utilError.set(true); this.utilLoading.set(false); },
    });
  }

  loadWip(): void {
    this.wipLoading.set(true);
    this.wipError.set(false);
    this.svc.getWip().subscribe({
      next: rows => { this.wipRows.set(rows); this.wipLoading.set(false); },
      error: () => { this.wipError.set(true); this.wipLoading.set(false); },
    });
  }

  marginAmountClass(pct: number): string {
    if (pct > 30) return 'text-accent-light';
    if (pct >= 10) return 'text-confidence-med';
    return 'text-confidence-low';
  }

  marginPctClass(pct: number): string {
    const base = 'text-xs font-semibold px-2 py-0.5 rounded';
    if (pct > 30) return `${base} bg-accent/15 text-accent-light`;
    if (pct >= 10) return `${base} bg-confidence-med/10 text-confidence-med`;
    return `${base} bg-confidence-low/10 text-confidence-low`;
  }

  utilChipClass(pct: number): string {
    const base = 'text-xs font-semibold px-2 py-0.5 rounded';
    if (pct > 70) return `${base} bg-accent/15 text-accent-light`;
    if (pct >= 50) return `${base} bg-confidence-med/10 text-confidence-med`;
    return `${base} bg-confidence-low/10 text-confidence-low`;
  }
}
