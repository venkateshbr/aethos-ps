import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
  RevenueRow,
  TrialBalanceReport,
  TrialBalanceLine,
} from '../../core/services/reports.service';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, FormsModule, MatTabsModule, MatTableModule, MatIconModule, MoneyPipe],
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
            @defer (on immediate) {
              @if (revLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (revError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Revenue', retry: loadRevenue.bind(this) }" />
              } @else if (revRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'revenue data' }" />
              } @else {
                <div class="overflow-x-auto rounded-lg border border-border-default">
                  <table mat-table [dataSource]="revRows()" class="w-full bg-surface-raised">
                    <ng-container matColumnDef="engagement_id">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Engagement</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">{{ row.engagement_name ?? row.engagement_id }}</td>
                    </ng-container>
                    <ng-container matColumnDef="total_invoiced">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Total Invoiced</th>
                      <td mat-cell *matCellDef="let row" class="text-accent-light text-sm font-mono font-bold text-right tabular-nums">{{ row.total_invoiced | money }}</td>
                    </ng-container>
                    <tr mat-header-row *matHeaderRowDef="revColumns" class="bg-surface-base/50"></tr>
                    <tr mat-row *matRowDef="let row; columns: revColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
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
        <!-- ── Trial Balance ──────────────────────────────────────────────── -->
        <mat-tab label="Trial Balance">
          <div class="pt-4">
            <!-- Period picker -->
            <div class="flex items-center gap-3 mb-6">
              <label class="text-slate-400 text-sm" for="tb-period">As of period</label>
              <input
                id="tb-period"
                type="month"
                [(ngModel)]="tbPeriod"
                (change)="loadTrialBalance()"
                class="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                aria-label="Select period for trial balance"
              />
              <button
                type="button"
                (click)="tbPeriod = ''; loadTrialBalance()"
                class="text-slate-400 text-sm hover:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 rounded"
              >All time</button>
            </div>

            @defer (on viewport) {
              @if (tbLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (tbError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Trial Balance', retry: loadTrialBalance.bind(this) }" />
              } @else if (!tbData() || tbData()!.lines.length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'trial balance data' }" />
              } @else {
                <!-- Balanced indicator -->
                <div class="mb-4 flex items-center gap-2 text-sm">
                  @if (tbData()!.is_balanced) {
                    <span class="text-green-400" role="status">&#10003; Balanced &mdash; DR equals CR</span>
                  } @else {
                    <span class="text-red-400" role="alert">&#9888; Out of balance &mdash; contact support</span>
                  }
                  <span class="text-slate-500">&middot; Generated {{ tbData()!.generated_at | date:'short' }}</span>
                </div>

                <!-- Trial balance table -->
                <div class="overflow-x-auto rounded-lg border border-border-default">
                  <table class="w-full text-sm bg-surface-raised" aria-label="Trial Balance">
                    <thead>
                      <tr class="text-slate-400 border-b border-slate-700 bg-surface-base/50">
                        <th scope="col" class="text-left py-3 px-4 text-xs uppercase tracking-wide w-20">Code</th>
                        <th scope="col" class="text-left py-3 px-4 text-xs uppercase tracking-wide">Account</th>
                        <th scope="col" class="text-left py-3 px-4 text-xs uppercase tracking-wide w-28">Type</th>
                        <th scope="col" class="text-right py-3 px-4 text-xs uppercase tracking-wide w-36">Debit (DR)</th>
                        <th scope="col" class="text-right py-3 px-4 text-xs uppercase tracking-wide w-36">Credit (CR)</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (line of tbData()!.lines; track line.account_code) {
                        <tr class="border-b border-slate-800 hover:bg-slate-800/40 transition-colors">
                          <td class="py-2.5 px-4 text-slate-400 font-mono text-xs">{{ line.account_code }}</td>
                          <td class="py-2.5 px-4 text-slate-200">{{ line.account_name }}</td>
                          <td class="py-2.5 px-4">
                            <span [class]="tbAccountTypeBadgeClass(line.account_type)">
                              {{ line.account_type }}
                            </span>
                          </td>
                          <td class="py-2.5 px-4 text-right font-mono text-slate-200 tabular-nums">
                            {{ line.total_dr !== '0.00' ? (line.total_dr | money) : '&mdash;' }}
                          </td>
                          <td class="py-2.5 px-4 text-right font-mono text-slate-200 tabular-nums">
                            {{ line.total_cr !== '0.00' ? (line.total_cr | money) : '&mdash;' }}
                          </td>
                        </tr>
                      }
                    </tbody>
                    <tfoot>
                      <tr class="border-t-2 border-slate-600 font-semibold text-slate-200 bg-surface-base/30">
                        <td colspan="3" class="py-3 px-4 text-text-muted uppercase text-xs tracking-wide">Total</td>
                        <td class="py-3 px-4 text-right font-mono tabular-nums">{{ tbData()!.grand_total_dr | money }}</td>
                        <td class="py-3 px-4 text-right font-mono tabular-nums">{{ tbData()!.grand_total_cr | money }}</td>
                      </tr>
                    </tfoot>
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

  // Revenue
  revLoading = signal(false);
  revError = signal(false);
  revRows = signal<RevenueRow[]>([]);

  // Trial Balance
  tbLoading = signal(false);
  tbError = signal(false);
  tbData = signal<TrialBalanceReport | null>(null);
  tbPeriod = (() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  })();

  readonly pnlColumns = ['project_name', 'revenue', 'direct_cost', 'gross_margin', 'gross_margin_pct'];
  readonly utilColumns = ['employee_id', 'total_hours', 'billable_hours', 'utilization_pct'];
  readonly wipColumns = ['project_name', 'unbilled_hours', 'avg_rate', 'wip_value'];
  readonly revColumns = ['engagement_id', 'total_invoiced'];

  ngOnInit(): void {
    this.loadAr();
    this.loadAp();
    this.loadPnl();
    this.loadUtil();
    this.loadWip();
    this.loadRevenue();
    this.loadTrialBalance();
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

  loadRevenue(): void {
    this.revLoading.set(true);
    this.revError.set(false);
    this.svc.getRevenueByEngagement().subscribe({
      next: rows => { this.revRows.set(rows); this.revLoading.set(false); },
      error: () => { this.revError.set(true); this.revLoading.set(false); },
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

  loadTrialBalance(): void {
    this.tbLoading.set(true);
    this.tbError.set(false);
    this.svc.getTrialBalance(this.tbPeriod || undefined).subscribe({
      next: data => { this.tbData.set(data); this.tbLoading.set(false); },
      error: () => { this.tbError.set(true); this.tbLoading.set(false); },
    });
  }

  tbAccountTypeBadgeClass(type: string): string {
    const base = 'inline-block px-2 py-0.5 rounded text-xs font-medium capitalize';
    switch (type) {
      case 'asset':     return `${base} bg-blue-500/20 text-blue-300`;
      case 'liability': return `${base} bg-red-500/20 text-red-300`;
      case 'equity':    return `${base} bg-purple-500/20 text-purple-300`;
      case 'revenue':   return `${base} bg-emerald-500/20 text-emerald-300`;
      case 'expense':   return `${base} bg-amber-500/20 text-amber-300`;
      default:          return `${base} bg-surface text-text-muted`;
    }
  }
}
