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
  ProjectHealthRow,
  CapacityRow,
  BacklogForecastRow,
  MilestoneRiskRow,
  ClientProfitabilityRow,
  ClientGroupProfitabilityRow,
  SegmentProfitabilityRow,
  PracticeDashboardRow,
  PricingStaffingRecommendation,
  ScopeChangeAdvisorRow,
  ActionQueueItem,
  ActionQueueRole,
  UtilRow,
  WipRow,
  RevenueRow,
  TrialBalanceReport,
  TrialBalanceLine,
  BalanceSheetReport,
  CashFlowReport,
  IncomeStatementReport,
  RetainedEarningsRollForwardReport,
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
        (selectedTabChange)="onTabChanged($event.index)"
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

        <!-- Project Health -->
        <mat-tab label="Project Health">
          <div class="pt-4">
            @defer (on viewport) {
              @if (healthLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (healthError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Project Health', retry: loadProjectHealth.bind(this) }" />
              } @else if (healthRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'project health data' }" />
              } @else {
                <div class="overflow-x-auto rounded-lg border border-border-default">
                  <table mat-table [dataSource]="healthRows()" class="w-full bg-surface-raised">
                    <ng-container matColumnDef="project_name">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Project</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">
                        {{ row.project_name }}
                        <div class="text-xs text-text-muted">{{ serviceLineLabel(row.service_line) }}</div>
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="risk_level">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Risk</th>
                      <td mat-cell *matCellDef="let row">
                        <span [class]="riskChipClass(row.risk_level)">{{ labelize(row.risk_level) }}</span>
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="health_score">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Score</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.health_score }}</td>
                    </ng-container>
                    <ng-container matColumnDef="drivers">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Drivers</th>
                      <td mat-cell *matCellDef="let row" class="text-sm text-text-secondary">
                        @if (row.drivers.length === 0) {
                          <span class="text-text-muted">No active drivers</span>
                        } @else {
                          <div class="flex flex-wrap gap-1.5">
                            @for (driver of row.drivers.slice(0, 3); track driver.code) {
                              <span class="rounded bg-surface-base border border-border-subtle px-2 py-0.5 text-xs">
                                {{ driver.label }}
                              </span>
                            }
                            @if (row.drivers.length > 3) {
                              <span class="text-xs text-text-muted">+{{ row.drivers.length - 3 }}</span>
                            }
                          </div>
                        }
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="recommended_actions">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Next action</th>
                      <td mat-cell *matCellDef="let row" class="text-sm text-text-secondary max-w-md">
                        {{ firstText(row.recommended_actions) || 'Continue monitoring.' }}
                      </td>
                    </ng-container>
                    <tr mat-header-row *matHeaderRowDef="healthColumns" class="bg-surface-base/50"></tr>
                    <tr mat-row *matRowDef="let row; columns: healthColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
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

        <!-- Capacity -->
        <mat-tab label="Capacity">
          <div class="pt-4">
            @defer (on viewport) {
              @if (capacityLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (capacityError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Capacity Planning', retry: loadCapacity.bind(this) }" />
              } @else if (capacityRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'capacity data' }" />
              } @else {
                <div class="overflow-x-auto rounded-lg border border-border-default">
                  <table mat-table [dataSource]="capacityRows()" class="w-full bg-surface-raised">
                    <ng-container matColumnDef="employee_name">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Employee</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">
                        {{ row.employee_name }}
                        <div class="text-xs text-text-muted">{{ serviceLineLabel(row.practice_area || 'unclassified') }}</div>
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="capacity_hours">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Capacity</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.capacity_hours }}</td>
                    </ng-container>
                    <ng-container matColumnDef="logged_hours">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Logged</th>
                      <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.logged_hours }}</td>
                    </ng-container>
                    <ng-container matColumnDef="utilization_pct">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Util</th>
                      <td mat-cell *matCellDef="let row" class="text-right">
                        <span [class]="utilChipClass(row.utilization_pct)">{{ row.utilization_pct.toFixed(1) }}%</span>
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="target_billable_utilization_pct">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Billable Target</th>
                      <td mat-cell *matCellDef="let row" class="text-right text-sm">
                        <span class="font-mono text-text-primary">{{ row.billable_utilization_pct.toFixed(1) }}%</span>
                        <span class="text-text-muted"> / {{ row.target_billable_utilization_pct.toFixed(1) }}%</span>
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="capacity_status">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Status</th>
                      <td mat-cell *matCellDef="let row">
                        <span [class]="capacityChipClass(row.capacity_status)">{{ labelize(row.capacity_status) }}</span>
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="recommended_action">
                      <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Action</th>
                      <td mat-cell *matCellDef="let row" class="text-sm text-text-secondary max-w-md">{{ row.recommended_action }}</td>
                    </ng-container>
                    <tr mat-header-row *matHeaderRowDef="capacityColumns" class="bg-surface-base/50"></tr>
                    <tr mat-row *matRowDef="let row; columns: capacityColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
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

        <!-- Backlog Forecast -->
        <mat-tab label="Backlog">
          <div class="pt-4 space-y-5">
            @defer (on viewport) {
              @if (backlogLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (backlogError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Backlog Forecast', retry: loadBacklog.bind(this) }" />
              } @else {
                <section>
                  <h2 class="mb-3 text-sm font-semibold text-text-primary">Engagement Backlog</h2>
                  @if (backlogRows().length === 0) {
                    <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'backlog forecast data' }" />
                  } @else {
                    <div class="overflow-x-auto rounded-lg border border-border-default">
                      <table mat-table [dataSource]="backlogRows()" class="w-full bg-surface-raised">
                        <ng-container matColumnDef="engagement_name">
                          <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Engagement</th>
                          <td mat-cell *matCellDef="let row" class="text-sm">
                            <div class="font-medium text-text-primary">{{ row.engagement_name }}</div>
                            <div class="text-xs text-text-muted">{{ row.client_name ?? 'No client' }} · {{ serviceLineLabel(row.service_line) }}</div>
                          </td>
                        </ng-container>
                        <ng-container matColumnDef="risk_level">
                          <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Risk</th>
                          <td mat-cell *matCellDef="let row">
                            <span [class]="riskChipClass(row.risk_level)">{{ labelize(row.risk_level) }}</span>
                          </td>
                        </ng-container>
                        <ng-container matColumnDef="contracted_value">
                          <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Contract</th>
                          <td mat-cell *matCellDef="let row" class="text-right font-mono text-sm text-text-primary tabular-nums">{{ row.contracted_value | money: row.currency }}</td>
                        </ng-container>
                        <ng-container matColumnDef="recognized_backlog">
                          <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Backlog</th>
                          <td mat-cell *matCellDef="let row" class="text-right font-mono text-sm text-text-primary tabular-nums">{{ row.recognized_backlog | money: row.currency }}</td>
                        </ng-container>
                        <ng-container matColumnDef="unbilled_wip">
                          <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">WIP</th>
                          <td mat-cell *matCellDef="let row" class="text-right font-mono text-sm text-text-secondary tabular-nums">{{ row.unbilled_wip | money: row.currency }}</td>
                        </ng-container>
                        <ng-container matColumnDef="next_milestone_due_date">
                          <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Next Due</th>
                          <td mat-cell *matCellDef="let row" class="text-sm text-text-secondary">{{ row.next_milestone_due_date ?? '—' }}</td>
                        </ng-container>
                        <ng-container matColumnDef="recommended_action">
                          <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Action</th>
                          <td mat-cell *matCellDef="let row" class="text-sm text-text-secondary">{{ row.recommended_action }}</td>
                        </ng-container>
                        <tr mat-header-row *matHeaderRowDef="backlogColumns" class="bg-surface-base/50"></tr>
                        <tr mat-row *matRowDef="let row; columns: backlogColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
                      </table>
                    </div>
                  }
                </section>

                <section>
                  <h2 class="mb-3 text-sm font-semibold text-text-primary">Milestone Risk</h2>
                  @if (milestoneRows().length === 0) {
                    <div class="rounded-lg border border-border-default bg-surface-raised p-4 text-sm text-text-muted">
                      No overdue or near-due milestones.
                    </div>
                  } @else {
                    <div class="space-y-3">
                      @for (row of milestoneRows(); track row.milestone_id) {
                        <article class="rounded-lg border border-border-default bg-surface-raised p-4">
                          <div class="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <div class="flex flex-wrap items-center gap-2">
                                <h3 class="text-sm font-semibold text-text-primary">{{ row.milestone_name }}</h3>
                                <span [class]="riskChipClass(row.risk_level)">{{ labelize(row.risk_level) }}</span>
                              </div>
                              <p class="mt-1 text-xs text-text-muted">{{ row.project_name }} · {{ serviceLineLabel(row.service_line) }}</p>
                            </div>
                            <div class="text-right">
                              <p class="text-sm font-mono text-text-primary">{{ row.due_date }}</p>
                              <p class="text-xs text-text-muted">{{ milestoneDueLabel(row.days_until_due) }}</p>
                            </div>
                          </div>
                          <p class="mt-3 text-sm text-text-secondary">{{ row.recommended_action }}</p>
                        </article>
                      }
                    </div>
                  }
                </section>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- Profitability -->
        <mat-tab label="Profitability">
          <div class="pt-4 space-y-8">
            @defer (on viewport) {
              <section aria-labelledby="client-profitability-heading">
                <div class="flex items-center justify-between mb-3">
                  <h2 id="client-profitability-heading" class="text-sm font-semibold text-text-primary">Client profitability</h2>
                  <button type="button" class="text-xs text-accent-light hover:underline" (click)="loadProfitability()">Refresh</button>
                </div>
                @if (clientProfitLoading()) {
                  <ng-container *ngTemplateOutlet="tableSkeleton" />
                } @else if (clientProfitError()) {
                  <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Client Profitability', retry: loadProfitability.bind(this) }" />
                } @else if (clientProfitRows().length === 0) {
                  <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'client profitability data' }" />
                } @else {
                  <div class="overflow-x-auto rounded-lg border border-border-default">
                    <table mat-table [dataSource]="clientProfitRows()" class="w-full bg-surface-raised">
                      <ng-container matColumnDef="client_name">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Client</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">
                          {{ row.client_name }}
                          <div class="text-xs text-text-muted">{{ row.service_lines.join(', ') || 'Unclassified' }}</div>
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="revenue">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Revenue</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.revenue | money: (row.currency || 'USD') }}</td>
                      </ng-container>
                      <ng-container matColumnDef="total_cost">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Cost</th>
                        <td mat-cell *matCellDef="let row" class="text-text-secondary text-sm font-mono text-right">{{ row.total_cost | money: (row.currency || 'USD') }}</td>
                      </ng-container>
                      <ng-container matColumnDef="gross_margin_pct">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Margin</th>
                        <td mat-cell *matCellDef="let row" class="text-right">
                          <span [class]="profitabilityChipClass(row.profitability_status)">{{ row.gross_margin_pct.toFixed(1) }}%</span>
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="recommended_action">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Action</th>
                        <td mat-cell *matCellDef="let row" class="text-sm text-text-secondary max-w-md">{{ row.recommended_action }}</td>
                      </ng-container>
                      <tr mat-header-row *matHeaderRowDef="profitColumns" class="bg-surface-base/50"></tr>
                      <tr mat-row *matRowDef="let row; columns: profitColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
                    </table>
                  </div>
                }
              </section>

              <section aria-labelledby="group-profitability-heading">
                <h2 id="group-profitability-heading" class="text-sm font-semibold text-text-primary mb-3">Client group rollups</h2>
                @if (groupProfitLoading()) {
                  <ng-container *ngTemplateOutlet="tableSkeleton" />
                } @else if (groupProfitError()) {
                  <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Client Group Profitability', retry: loadGroupProfitability.bind(this) }" />
                } @else if (groupProfitRows().length === 0) {
                  <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'client group profitability data' }" />
                } @else {
                  <div class="overflow-x-auto rounded-lg border border-border-default">
                    <table mat-table [dataSource]="groupProfitRows()" class="w-full bg-surface-raised">
                      <ng-container matColumnDef="client_group_name">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Group</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">
                          {{ row.client_group_name }}
                          <div class="text-xs text-text-muted">{{ labelize(row.group_type) }} · {{ row.member_count }} members</div>
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="revenue">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Revenue</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.revenue | money: (row.currency || 'USD') }}</td>
                      </ng-container>
                      <ng-container matColumnDef="gross_margin">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Margin</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.gross_margin | money: (row.currency || 'USD') }}</td>
                      </ng-container>
                      <ng-container matColumnDef="gross_margin_pct">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Margin %</th>
                        <td mat-cell *matCellDef="let row" class="text-right">
                          <span [class]="profitabilityChipClass(row.profitability_status)">{{ row.gross_margin_pct.toFixed(1) }}%</span>
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="recommended_action">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Action</th>
                        <td mat-cell *matCellDef="let row" class="text-sm text-text-secondary max-w-md">{{ row.recommended_action }}</td>
                      </ng-container>
                      <tr mat-header-row *matHeaderRowDef="groupProfitColumns" class="bg-surface-base/50"></tr>
                      <tr mat-row *matRowDef="let row; columns: groupProfitColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
                    </table>
                  </div>
                }
              </section>

              <section aria-labelledby="segment-profitability-heading">
                <h2 id="segment-profitability-heading" class="text-sm font-semibold text-text-primary mb-3">Service-line segments</h2>
                @if (segmentProfitLoading()) {
                  <ng-container *ngTemplateOutlet="tableSkeleton" />
                } @else if (segmentProfitError()) {
                  <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Segment Profitability', retry: loadSegmentProfitability.bind(this) }" />
                } @else if (segmentProfitRows().length === 0) {
                  <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'segment profitability data' }" />
                } @else {
                  <div class="overflow-x-auto rounded-lg border border-border-default">
                    <table mat-table [dataSource]="segmentProfitRows()" class="w-full bg-surface-raised">
                      <ng-container matColumnDef="segment_label">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide">Segment</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-medium">{{ row.segment_label }}</td>
                      </ng-container>
                      <ng-container matColumnDef="revenue">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Revenue</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.revenue | money: (row.currency || 'USD') }}</td>
                      </ng-container>
                      <ng-container matColumnDef="gross_margin_pct">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Margin</th>
                        <td mat-cell *matCellDef="let row" class="text-right">
                          <span [class]="profitabilityChipClass(row.profitability_status)">{{ row.gross_margin_pct.toFixed(1) }}%</span>
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="client_count">
                        <th mat-header-cell *matHeaderCellDef class="text-text-muted text-xs uppercase tracking-wide text-right">Clients</th>
                        <td mat-cell *matCellDef="let row" class="text-text-primary text-sm font-mono text-right">{{ row.client_count }}</td>
                      </ng-container>
                      <tr mat-header-row *matHeaderRowDef="segmentColumns" class="bg-surface-base/50"></tr>
                      <tr mat-row *matRowDef="let row; columns: segmentColumns;" class="border-border-default hover:bg-surface/40 transition-colors"></tr>
                    </table>
                  </div>
                }
              </section>
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- Practice -->
        <mat-tab label="Practice">
          <div class="pt-4">
            @defer (on viewport) {
              @if (practiceLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (practiceError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Practice Dashboard', retry: loadPracticeDashboard.bind(this) }" />
              } @else if (practiceRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'practice dashboard data' }" />
              } @else {
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  @for (row of practiceRows(); track row.practice_key) {
                    <article class="rounded-lg border border-border-default bg-surface-raised p-4">
                      <div class="flex items-start justify-between gap-3">
                        <div>
                          <h2 class="text-sm font-semibold text-text-primary">{{ row.practice_label }}</h2>
                          <p class="text-xs text-text-muted mt-1">
                            {{ row.client_count }} clients · {{ row.project_count }} projects · {{ row.employee_count }} employees
                          </p>
                        </div>
                        <span [class]="profitabilityChipClass(row.profitability_status)">{{ labelize(row.profitability_status) }}</span>
                      </div>
                      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                        <div>
                          <p class="text-xs text-text-muted uppercase tracking-wide">Revenue</p>
                          <p class="text-sm text-text-primary font-mono">{{ row.revenue | money }}</p>
                        </div>
                        <div>
                          <p class="text-xs text-text-muted uppercase tracking-wide">Margin</p>
                          <p class="text-sm text-text-primary font-mono">{{ row.gross_margin_pct.toFixed(1) }}%</p>
                        </div>
                        <div>
                          <p class="text-xs text-text-muted uppercase tracking-wide">Health</p>
                          <p class="text-sm text-text-primary font-mono">{{ row.avg_project_health_score ?? '—' }}</p>
                        </div>
                        <div>
                          <p class="text-xs text-text-muted uppercase tracking-wide">Util</p>
                          <p class="text-sm text-text-primary font-mono">{{ row.avg_utilization_pct.toFixed(1) }}%</p>
                        </div>
                      </div>
                      @if (row.recommended_actions.length) {
                        <p class="mt-4 text-sm text-text-secondary">{{ row.recommended_actions[0] }}</p>
                      }
                    </article>
                  }
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- Recommendations -->
        <mat-tab label="Recommendations">
          <div class="pt-4">
            @defer (on viewport) {
              @if (recommendationsLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (recommendationsError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Recommendations', retry: loadRecommendations.bind(this) }" />
              } @else if (recommendationRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'pricing and staffing recommendations' }" />
              } @else {
                <div class="space-y-3">
                  @for (row of recommendationRows(); track row.recommendation_id) {
                    <article class="rounded-lg border border-border-default bg-surface-raised p-4">
                      <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div class="flex items-center gap-2 flex-wrap">
                            <h2 class="text-sm font-semibold text-text-primary">{{ row.entity_name }}</h2>
                            <span [class]="priorityChipClass(row.priority)">{{ labelize(row.priority) }}</span>
                            <span class="rounded bg-surface-base border border-border-subtle px-2 py-0.5 text-xs text-text-muted">{{ labelize(row.recommendation_type) }}</span>
                          </div>
                          @if (row.service_line) {
                            <p class="text-xs text-text-muted mt-1">{{ serviceLineLabel(row.service_line) }}</p>
                          }
                        </div>
                        <span class="text-xs text-text-muted">{{ labelize(row.entity_type) }}</span>
                      </div>
                      <p class="mt-3 text-sm text-text-secondary">{{ row.recommended_action }}</p>
                      @if (row.evidence.length) {
                        <ul class="mt-3 space-y-1 text-sm text-text-muted">
                          @for (evidence of row.evidence.slice(0, 3); track evidence) {
                            <li>{{ evidence }}</li>
                          }
                        </ul>
                      }
                    </article>
                  }
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- Action Queue -->
        <mat-tab label="Action Queue">
          <div class="pt-4 space-y-4">
            <div class="flex flex-wrap gap-2">
              @for (role of actionQueueRoles; track role.value) {
                <button
                  type="button"
                  (click)="setActionQueueRole(role.value)"
                  [class]="queueRoleButtonClass(role.value)"
                >
                  {{ role.label }}
                </button>
              }
            </div>

            @defer (on viewport) {
              @if (actionQueueLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (actionQueueError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Action Queue', retry: loadActionQueue.bind(this) }" />
              } @else if (actionQueueRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'action queue' }" />
              } @else {
                <div class="space-y-3">
                  @for (row of actionQueueRows(); track row.id) {
                    <article class="rounded-lg border border-border-default bg-surface-raised p-4">
                      <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div class="flex flex-wrap items-center gap-2">
                            <h2 class="text-sm font-semibold text-text-primary">{{ row.entity_name }}</h2>
                            <span [class]="priorityChipClass(row.priority)">{{ labelize(row.priority) }}</span>
                            <span class="rounded bg-surface-base border border-border-subtle px-2 py-0.5 text-xs text-text-muted">{{ roleLabel(row.role) }}</span>
                          </div>
                          <p class="mt-1 text-xs text-text-muted">
                            {{ labelize(row.source_type) }} · {{ labelize(row.entity_type) }}
                          </p>
                        </div>
                        @if (row.service_line) {
                          <span class="rounded bg-indigo-500/10 px-2 py-0.5 text-xs text-indigo-300">{{ serviceLineLabel(row.service_line) }}</span>
                        }
                      </div>
                      <p class="mt-3 text-sm text-text-primary">{{ row.summary }}</p>
                      <p class="mt-2 text-sm text-text-secondary">{{ row.recommended_action }}</p>
                      @if (row.evidence.length) {
                        <ul class="mt-3 space-y-1 text-sm text-text-muted">
                          @for (evidence of row.evidence.slice(0, 3); track evidence) {
                            <li>{{ evidence }}</li>
                          }
                        </ul>
                      }
                    </article>
                  }
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- Scope Advisor -->
        <mat-tab label="Scope Advisor">
          <div class="pt-4">
            @defer (on viewport) {
              @if (scopeLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (scopeError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Scope Advisor', retry: loadScopeAdvisor.bind(this) }" />
              } @else if (scopeRows().length === 0) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'scope advisor data' }" />
              } @else {
                <div class="space-y-3">
                  @for (row of scopeRows(); track row.advisor_id) {
                    <article class="rounded-lg border border-border-default bg-surface-raised p-4">
                      <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h2 class="text-sm font-semibold text-text-primary">{{ row.project_name }}</h2>
                          <p class="text-xs text-text-muted mt-1">{{ serviceLineLabel(row.service_line) }} · {{ labelize(row.billing_arrangement || 'unknown') }}</p>
                        </div>
                        <div class="flex items-center gap-2">
                          <span [class]="riskChipClass(row.risk_level)">{{ labelize(row.risk_level) }}</span>
                          <span [class]="confidenceChipClass(row.confidence)">{{ labelize(row.confidence) }} confidence</span>
                        </div>
                      </div>
                      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
                        <div>
                          <p class="text-xs text-text-muted uppercase tracking-wide">Health score</p>
                          <p class="text-sm text-text-primary font-mono">{{ row.health_score }}</p>
                        </div>
                        <div>
                          <p class="text-xs text-text-muted uppercase tracking-wide">Fee adjustment</p>
                          <p class="text-sm text-text-primary font-mono">{{ row.suggested_fee_adjustment | money }}</p>
                        </div>
                        <div>
                          <p class="text-xs text-text-muted uppercase tracking-wide">Comparables</p>
                          <p class="text-sm text-text-primary font-mono">{{ row.comparable_projects.length }}</p>
                        </div>
                      </div>
                      <p class="mt-3 text-sm text-text-secondary">{{ row.recommended_action }}</p>
                      @if (row.scope_signals.length) {
                        <div class="mt-3 flex flex-wrap gap-1.5">
                          @for (signal of row.scope_signals; track signal) {
                            <span class="rounded bg-surface-base border border-border-subtle px-2 py-0.5 text-xs text-text-muted">{{ labelize(signal) }}</span>
                          }
                        </div>
                      }
                    </article>
                  }
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

        <!-- ── Balance Sheet ─────────────────────────────────────────────── -->
        <mat-tab label="Balance Sheet">
          <div class="pt-4 space-y-4">
            <ng-container *ngTemplateOutlet="statementPeriodPicker" />

            @defer (on viewport) {
              @if (balanceSheetLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (balanceSheetError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Balance Sheet', retry: loadBalanceSheet.bind(this) }" />
              } @else if (!balanceSheetData()) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'balance sheet data' }" />
              } @else {
                <div class="grid gap-4 md:grid-cols-4">
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Assets', value: balanceSheetData()!.total_assets }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Liabilities', value: balanceSheetData()!.total_liabilities }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Equity', value: balanceSheetData()!.total_equity }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'L + E', value: balanceSheetData()!.liabilities_and_equity }" />
                </div>
                <div class="text-sm">
                  @if (balanceSheetData()!.is_balanced) {
                    <span class="text-accent-light" role="status">&#10003; Balance sheet balances</span>
                  } @else {
                    <span class="text-confidence-low" role="alert">&#9888; Balance sheet does not balance</span>
                  }
                </div>
                @if (retainedEarningsLoading()) {
                  <ng-container *ngTemplateOutlet="tableSkeleton" />
                } @else if (retainedEarningsError()) {
                  <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Retained Earnings', retry: loadRetainedEarnings.bind(this) }" />
                } @else if (retainedEarningsData()) {
                  <div>
                    <h3 class="text-sm font-semibold text-text-primary">Retained earnings roll-forward</h3>
                    <p class="text-xs text-text-muted mb-3">{{ retainedEarningsData()!.previous_period }} to {{ retainedEarningsData()!.period }}</p>
                    <div class="grid gap-4 md:grid-cols-4">
                    <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Beginning RE', value: retainedEarningsData()!.beginning_retained_earnings }" />
                    <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Net Income', value: retainedEarningsData()!.current_period_net_income }" />
                    <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'RE Activity', value: retainedEarningsData()!.retained_earnings_activity }" />
                    <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Ending RE', value: retainedEarningsData()!.ending_retained_earnings }" />
                    </div>
                  </div>
                }
                <div class="grid gap-4 xl:grid-cols-3">
                  <ng-container *ngTemplateOutlet="statementSection; context: { title: 'Assets', rows: balanceSheetData()!.asset_lines, totalLabel: 'Total Assets', total: balanceSheetData()!.total_assets }" />
                  <ng-container *ngTemplateOutlet="statementSection; context: { title: 'Liabilities', rows: balanceSheetData()!.liability_lines, totalLabel: 'Total Liabilities', total: balanceSheetData()!.total_liabilities }" />
                  <ng-container *ngTemplateOutlet="statementSection; context: { title: 'Equity', rows: balanceSheetData()!.equity_lines, totalLabel: 'Total Equity', total: balanceSheetData()!.total_equity }" />
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- ── Income Statement ──────────────────────────────────────────── -->
        <mat-tab label="Income Statement">
          <div class="pt-4 space-y-4">
            <ng-container *ngTemplateOutlet="statementPeriodPicker" />

            @defer (on viewport) {
              @if (incomeStatementLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (incomeStatementError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Income Statement', retry: loadIncomeStatement.bind(this) }" />
              } @else if (!incomeStatementData()) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'income statement data' }" />
              } @else {
                <div class="grid gap-4 md:grid-cols-3">
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Revenue', value: incomeStatementData()!.total_revenue }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Expenses', value: incomeStatementData()!.total_expenses }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Net Income', value: incomeStatementData()!.net_income }" />
                </div>
                <div class="grid gap-4 lg:grid-cols-2">
                  <ng-container *ngTemplateOutlet="statementSection; context: { title: 'Revenue', rows: incomeStatementData()!.revenue_lines, totalLabel: 'Total Revenue', total: incomeStatementData()!.total_revenue }" />
                  <ng-container *ngTemplateOutlet="statementSection; context: { title: 'Expenses', rows: incomeStatementData()!.expense_lines, totalLabel: 'Total Expenses', total: incomeStatementData()!.total_expenses }" />
                </div>
              }
            } @placeholder {
              <div><ng-container *ngTemplateOutlet="tableSkeleton" /></div>
            } @loading {
              <ng-container *ngTemplateOutlet="tableSkeleton" />
            }
          </div>
        </mat-tab>

        <!-- ── Cash Flow ─────────────────────────────────────────────────── -->
        <mat-tab label="Cash Flow">
          <div class="pt-4 space-y-4">
            <ng-container *ngTemplateOutlet="statementPeriodPicker" />

            @defer (on viewport) {
              @if (cashFlowLoading()) {
                <ng-container *ngTemplateOutlet="tableSkeleton" />
              } @else if (cashFlowError()) {
                <ng-container *ngTemplateOutlet="errorState; context: { $implicit: 'Cash Flow', retry: loadCashFlow.bind(this) }" />
              } @else if (!cashFlowData()) {
                <ng-container *ngTemplateOutlet="emptyState; context: { $implicit: 'cash-flow data' }" />
              } @else {
                <div class="grid gap-4 md:grid-cols-4">
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Operating', value: cashFlowData()!.net_cash_from_operating }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Investing', value: cashFlowData()!.net_cash_from_investing }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Financing', value: cashFlowData()!.net_cash_from_financing }" />
                  <ng-container *ngTemplateOutlet="statementMetric; context: { label: 'Net Change', value: cashFlowData()!.net_change_in_cash }" />
                </div>
                <div class="grid gap-4 lg:grid-cols-3">
                  <ng-container *ngTemplateOutlet="cashFlowSection; context: { title: 'Operating Activities', rows: cashFlowData()!.operating_lines, total: cashFlowData()!.net_cash_from_operating }" />
                  <ng-container *ngTemplateOutlet="cashFlowSection; context: { title: 'Investing Activities', rows: cashFlowData()!.investing_lines, total: cashFlowData()!.net_cash_from_investing }" />
                  <ng-container *ngTemplateOutlet="cashFlowSection; context: { title: 'Financing Activities', rows: cashFlowData()!.financing_lines, total: cashFlowData()!.net_cash_from_financing }" />
                </div>
                <div class="rounded-lg border border-border-default bg-surface-raised p-4 text-sm">
                  <div class="flex items-center justify-between py-1">
                    <span class="text-text-muted">Beginning cash</span>
                    <span class="font-mono text-text-primary tabular-nums">{{ cashFlowData()!.beginning_cash | money }}</span>
                  </div>
                  <div class="flex items-center justify-between py-1">
                    <span class="text-text-muted">Net cash change</span>
                    <span class="font-mono text-text-primary tabular-nums">{{ cashFlowData()!.net_change_in_cash | money }}</span>
                  </div>
                  <div class="mt-2 flex items-center justify-between border-t border-border-subtle pt-3 font-semibold">
                    <span class="text-text-primary">Ending cash</span>
                    <span class="font-mono text-text-primary tabular-nums">{{ cashFlowData()!.ending_cash | money }}</span>
                  </div>
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

    <ng-template #statementPeriodPicker>
      <div class="flex flex-wrap items-center gap-3">
        <label class="text-slate-400 text-sm" for="statement-period">Statement period</label>
        <input
          id="statement-period"
          type="month"
          [(ngModel)]="statementPeriod"
          (change)="loadFinancialStatements()"
          class="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          aria-label="Select period for financial statements"
        />
      </div>
    </ng-template>

    <ng-template #statementMetric let-label="label" let-value="value">
      <div class="rounded-lg border border-border-default bg-surface-raised p-4">
        <p class="text-xs uppercase tracking-wide text-text-muted">{{ label }}</p>
        <p class="mt-1 font-mono text-xl font-semibold text-text-primary tabular-nums">{{ value | money }}</p>
      </div>
    </ng-template>

    <ng-template #statementSection let-title="title" let-rows="rows" let-totalLabel="totalLabel" let-total="total">
      <section class="rounded-lg border border-border-default bg-surface-raised">
        <div class="border-b border-border-subtle px-4 py-3">
          <h2 class="text-sm font-semibold text-text-primary">{{ title }}</h2>
        </div>
        <div class="divide-y divide-border-subtle">
          @if (rows.length === 0) {
            <div class="px-4 py-4 text-sm text-text-muted">No activity</div>
          } @else {
            @for (line of rows; track line.account_code) {
              <div class="grid grid-cols-[4rem_1fr_auto] items-center gap-3 px-4 py-2.5 text-sm">
                <span class="font-mono text-xs text-text-muted">{{ line.account_code }}</span>
                <span class="text-text-secondary">{{ line.account_name }}</span>
                <span class="font-mono text-text-primary tabular-nums">{{ line.amount | money }}</span>
              </div>
            }
          }
        </div>
        <div class="flex items-center justify-between border-t border-border-default px-4 py-3 text-sm font-semibold">
          <span class="text-text-primary">{{ totalLabel }}</span>
          <span class="font-mono text-text-primary tabular-nums">{{ total | money }}</span>
        </div>
      </section>
    </ng-template>

    <ng-template #cashFlowSection let-title="title" let-rows="rows" let-total="total">
      <section class="rounded-lg border border-border-default bg-surface-raised">
        <div class="border-b border-border-subtle px-4 py-3">
          <h2 class="text-sm font-semibold text-text-primary">{{ title }}</h2>
        </div>
        <div class="divide-y divide-border-subtle">
          @if (rows.length === 0) {
            <div class="px-4 py-4 text-sm text-text-muted">No activity</div>
          } @else {
            @for (line of rows; track line.journal_entry_id ?? line.description) {
              <div class="px-4 py-2.5 text-sm">
                <div class="flex items-start justify-between gap-3">
                  <span class="text-text-secondary">{{ line.description }}</span>
                  <span class="font-mono text-text-primary tabular-nums">{{ line.amount | money }}</span>
                </div>
                @if (line.reference_type || line.period) {
                  <p class="mt-1 text-xs text-text-muted">
                    {{ labelize(line.reference_type) }} · {{ line.period }}
                  </p>
                }
              </div>
            }
          }
        </div>
        <div class="flex items-center justify-between border-t border-border-default px-4 py-3 text-sm font-semibold">
          <span class="text-text-primary">Net cash</span>
          <span class="font-mono text-text-primary tabular-nums">{{ total | money }}</span>
        </div>
      </section>
    </ng-template>

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

  // Project health
  healthLoading = signal(false);
  healthError = signal(false);
  healthRows = signal<ProjectHealthRow[]>([]);

  // Capacity planning
  capacityLoading = signal(false);
  capacityError = signal(false);
  capacityRows = signal<CapacityRow[]>([]);

  // Backlog and milestones
  backlogLoading = signal(false);
  backlogError = signal(false);
  backlogRows = signal<BacklogForecastRow[]>([]);
  milestoneRows = signal<MilestoneRiskRow[]>([]);

  // Profitability
  clientProfitLoading = signal(false);
  clientProfitError = signal(false);
  clientProfitRows = signal<ClientProfitabilityRow[]>([]);
  groupProfitLoading = signal(false);
  groupProfitError = signal(false);
  groupProfitRows = signal<ClientGroupProfitabilityRow[]>([]);
  segmentProfitLoading = signal(false);
  segmentProfitError = signal(false);
  segmentProfitRows = signal<SegmentProfitabilityRow[]>([]);

  // Practice dashboard
  practiceLoading = signal(false);
  practiceError = signal(false);
  practiceRows = signal<PracticeDashboardRow[]>([]);

  // Recommendations
  recommendationsLoading = signal(false);
  recommendationsError = signal(false);
  recommendationRows = signal<PricingStaffingRecommendation[]>([]);

  // Action queue
  actionQueueLoading = signal(false);
  actionQueueError = signal(false);
  actionQueueRows = signal<ActionQueueItem[]>([]);
  actionQueueRole = signal<ActionQueueRole>('all');
  readonly actionQueueRoles: { value: ActionQueueRole; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'partner', label: 'Partner' },
    { value: 'finance_manager', label: 'Finance' },
    { value: 'project_manager', label: 'Projects' },
    { value: 'ap_clerk', label: 'AP' },
  ];

  // Scope advisor
  scopeLoading = signal(false);
  scopeError = signal(false);
  scopeRows = signal<ScopeChangeAdvisorRow[]>([]);

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

  // Financial statements
  balanceSheetLoading = signal(false);
  balanceSheetError = signal(false);
  balanceSheetData = signal<BalanceSheetReport | null>(null);
  retainedEarningsLoading = signal(false);
  retainedEarningsError = signal(false);
  retainedEarningsData = signal<RetainedEarningsRollForwardReport | null>(null);
  incomeStatementLoading = signal(false);
  incomeStatementError = signal(false);
  incomeStatementData = signal<IncomeStatementReport | null>(null);
  cashFlowLoading = signal(false);
  cashFlowError = signal(false);
  cashFlowData = signal<CashFlowReport | null>(null);
  statementPeriod = (() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  })();

  // Trial Balance
  tbLoading = signal(false);
  tbError = signal(false);
  tbData = signal<TrialBalanceReport | null>(null);
  tbPeriod = (() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  })();

  readonly pnlColumns = ['project_name', 'revenue', 'direct_cost', 'gross_margin', 'gross_margin_pct'];
  readonly healthColumns = ['project_name', 'risk_level', 'health_score', 'drivers', 'recommended_actions'];
  readonly capacityColumns = ['employee_name', 'capacity_hours', 'logged_hours', 'utilization_pct', 'target_billable_utilization_pct', 'capacity_status', 'recommended_action'];
  readonly backlogColumns = ['engagement_name', 'risk_level', 'contracted_value', 'recognized_backlog', 'unbilled_wip', 'next_milestone_due_date', 'recommended_action'];
  readonly profitColumns = ['client_name', 'revenue', 'total_cost', 'gross_margin_pct', 'recommended_action'];
  readonly groupProfitColumns = ['client_group_name', 'revenue', 'gross_margin', 'gross_margin_pct', 'recommended_action'];
  readonly segmentColumns = ['segment_label', 'revenue', 'gross_margin_pct', 'client_count'];
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
    this.loadFinancialStatements();
    this.loadTrialBalance();
  }

  onTabChanged(index: number): void {
    switch (index) {
      case 3:
        this.loadProjectHealth();
        break;
      case 4:
        this.loadCapacity();
        break;
      case 5:
        this.loadBacklog();
        break;
      case 6:
        this.loadProfitability();
        this.loadGroupProfitability();
        this.loadSegmentProfitability();
        break;
      case 7:
        this.loadPracticeDashboard();
        break;
      case 8:
        this.loadRecommendations();
        break;
      case 9:
        this.loadActionQueue();
        break;
      case 10:
        this.loadScopeAdvisor();
        break;
    }
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

  loadProjectHealth(): void {
    this.healthLoading.set(true);
    this.healthError.set(false);
    this.svc.getProjectHealth().subscribe({
      next: rows => { this.healthRows.set(rows); this.healthLoading.set(false); },
      error: () => { this.healthError.set(true); this.healthLoading.set(false); },
    });
  }

  loadCapacity(): void {
    this.capacityLoading.set(true);
    this.capacityError.set(false);
    this.svc.getCapacityPlanning().subscribe({
      next: rows => { this.capacityRows.set(rows); this.capacityLoading.set(false); },
      error: () => { this.capacityError.set(true); this.capacityLoading.set(false); },
    });
  }

  loadBacklog(): void {
    this.backlogLoading.set(true);
    this.backlogError.set(false);
    this.svc.getBacklogForecast().subscribe({
      next: rows => {
        this.backlogRows.set(rows);
        this.svc.getMilestoneRisk().subscribe({
          next: milestoneRows => {
            this.milestoneRows.set(milestoneRows);
            this.backlogLoading.set(false);
          },
          error: () => {
            this.backlogError.set(true);
            this.backlogLoading.set(false);
          },
        });
      },
      error: () => { this.backlogError.set(true); this.backlogLoading.set(false); },
    });
  }

  loadProfitability(): void {
    this.clientProfitLoading.set(true);
    this.clientProfitError.set(false);
    this.svc.getClientProfitability().subscribe({
      next: rows => { this.clientProfitRows.set(rows); this.clientProfitLoading.set(false); },
      error: () => { this.clientProfitError.set(true); this.clientProfitLoading.set(false); },
    });
  }

  loadGroupProfitability(): void {
    this.groupProfitLoading.set(true);
    this.groupProfitError.set(false);
    this.svc.getClientGroupProfitability().subscribe({
      next: rows => { this.groupProfitRows.set(rows); this.groupProfitLoading.set(false); },
      error: () => { this.groupProfitError.set(true); this.groupProfitLoading.set(false); },
    });
  }

  loadSegmentProfitability(): void {
    this.segmentProfitLoading.set(true);
    this.segmentProfitError.set(false);
    this.svc.getSegmentProfitability().subscribe({
      next: rows => { this.segmentProfitRows.set(rows); this.segmentProfitLoading.set(false); },
      error: () => { this.segmentProfitError.set(true); this.segmentProfitLoading.set(false); },
    });
  }

  loadPracticeDashboard(): void {
    this.practiceLoading.set(true);
    this.practiceError.set(false);
    this.svc.getPracticeDashboard().subscribe({
      next: rows => { this.practiceRows.set(rows); this.practiceLoading.set(false); },
      error: () => { this.practiceError.set(true); this.practiceLoading.set(false); },
    });
  }

  loadRecommendations(): void {
    this.recommendationsLoading.set(true);
    this.recommendationsError.set(false);
    this.svc.getPricingStaffingRecommendations().subscribe({
      next: rows => { this.recommendationRows.set(rows); this.recommendationsLoading.set(false); },
      error: () => { this.recommendationsError.set(true); this.recommendationsLoading.set(false); },
    });
  }

  setActionQueueRole(role: ActionQueueRole): void {
    this.actionQueueRole.set(role);
    this.loadActionQueue();
  }

  loadActionQueue(): void {
    this.actionQueueLoading.set(true);
    this.actionQueueError.set(false);
    this.svc.getActionQueue(this.actionQueueRole()).subscribe({
      next: rows => { this.actionQueueRows.set(rows); this.actionQueueLoading.set(false); },
      error: () => { this.actionQueueError.set(true); this.actionQueueLoading.set(false); },
    });
  }

  loadScopeAdvisor(): void {
    this.scopeLoading.set(true);
    this.scopeError.set(false);
    this.svc.getScopeChangeAdvisor().subscribe({
      next: rows => { this.scopeRows.set(rows); this.scopeLoading.set(false); },
      error: () => { this.scopeError.set(true); this.scopeLoading.set(false); },
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

  loadFinancialStatements(): void {
    this.loadBalanceSheet();
    this.loadRetainedEarnings();
    this.loadIncomeStatement();
    this.loadCashFlow();
  }

  loadBalanceSheet(): void {
    this.balanceSheetLoading.set(true);
    this.balanceSheetError.set(false);
    this.svc.getBalanceSheet(this.statementPeriod || undefined).subscribe({
      next: data => { this.balanceSheetData.set(data); this.balanceSheetLoading.set(false); },
      error: () => { this.balanceSheetError.set(true); this.balanceSheetLoading.set(false); },
    });
  }

  loadRetainedEarnings(): void {
    this.retainedEarningsLoading.set(true);
    this.retainedEarningsError.set(false);
    this.svc.getRetainedEarningsRollForward(this.statementPeriod).subscribe({
      next: data => { this.retainedEarningsData.set(data); this.retainedEarningsLoading.set(false); },
      error: () => { this.retainedEarningsError.set(true); this.retainedEarningsLoading.set(false); },
    });
  }

  loadIncomeStatement(): void {
    this.incomeStatementLoading.set(true);
    this.incomeStatementError.set(false);
    this.svc.getIncomeStatement(this.statementPeriod || undefined).subscribe({
      next: data => { this.incomeStatementData.set(data); this.incomeStatementLoading.set(false); },
      error: () => { this.incomeStatementError.set(true); this.incomeStatementLoading.set(false); },
    });
  }

  loadCashFlow(): void {
    this.cashFlowLoading.set(true);
    this.cashFlowError.set(false);
    this.svc.getCashFlow(this.statementPeriod || undefined).subscribe({
      next: data => { this.cashFlowData.set(data); this.cashFlowLoading.set(false); },
      error: () => { this.cashFlowError.set(true); this.cashFlowLoading.set(false); },
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

  riskChipClass(risk: string): string {
    const base = 'text-xs font-semibold px-2 py-0.5 rounded';
    switch (risk) {
      case 'critical': return `${base} bg-confidence-low/10 text-confidence-low`;
      case 'at_risk': return `${base} bg-orange-500/10 text-orange-300`;
      case 'watch': return `${base} bg-confidence-med/10 text-confidence-med`;
      default: return `${base} bg-accent/15 text-accent-light`;
    }
  }

  capacityChipClass(status: string): string {
    const base = 'text-xs font-semibold px-2 py-0.5 rounded';
    switch (status) {
      case 'overallocated': return `${base} bg-confidence-low/10 text-confidence-low`;
      case 'underutilized': return `${base} bg-confidence-med/10 text-confidence-med`;
      case 'full': return `${base} bg-blue-500/15 text-blue-300`;
      default: return `${base} bg-accent/15 text-accent-light`;
    }
  }

  profitabilityChipClass(status: string): string {
    const base = 'text-xs font-semibold px-2 py-0.5 rounded';
    switch (status) {
      case 'critical': return `${base} bg-confidence-low/10 text-confidence-low`;
      case 'watch': return `${base} bg-confidence-med/10 text-confidence-med`;
      case 'strong': return `${base} bg-accent/15 text-accent-light`;
      default: return `${base} bg-blue-500/15 text-blue-300`;
    }
  }

  priorityChipClass(priority: string): string {
    const base = 'text-xs font-semibold px-2 py-0.5 rounded';
    switch (priority) {
      case 'critical': return `${base} bg-confidence-low/10 text-confidence-low`;
      case 'high': return `${base} bg-orange-500/10 text-orange-300`;
      case 'medium': return `${base} bg-confidence-med/10 text-confidence-med`;
      default: return `${base} bg-surface-base text-text-muted border border-border-subtle`;
    }
  }

  queueRoleButtonClass(role: ActionQueueRole): string {
    const base = 'h-9 rounded border px-3 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent';
    if (this.actionQueueRole() === role) {
      return `${base} border-accent bg-accent/15 text-text-primary`;
    }
    return `${base} border-border-default text-text-secondary hover:border-accent/60 hover:text-text-primary`;
  }

  roleLabel(role: string): string {
    if (role === 'finance_manager') return 'Finance';
    if (role === 'project_manager') return 'Projects';
    if (role === 'ap_clerk') return 'AP';
    return this.labelize(role);
  }

  confidenceChipClass(confidence: string): string {
    const base = 'text-xs font-semibold px-2 py-0.5 rounded';
    switch (confidence) {
      case 'high': return `${base} bg-accent/15 text-accent-light`;
      case 'medium': return `${base} bg-confidence-med/10 text-confidence-med`;
      default: return `${base} bg-surface-base text-text-muted border border-border-subtle`;
    }
  }

  labelize(value: string | null | undefined): string {
    if (!value) return 'Unclassified';
    return value
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  serviceLineLabel(value: string | null | undefined): string {
    const labels: Record<string, string> = {
      accounting: 'Accounting',
      tax: 'Tax',
      cosec: 'Company Secretarial',
      payroll: 'Payroll',
      advisory: 'Advisory',
      other: 'Other',
      unclassified: 'Unclassified',
    };
    return labels[value ?? 'unclassified'] ?? this.labelize(value);
  }

  milestoneDueLabel(daysUntilDue: number): string {
    if (daysUntilDue < 0) {
      return `${Math.abs(daysUntilDue)} days overdue`;
    }
    if (daysUntilDue === 0) return 'Due today';
    return `Due in ${daysUntilDue} days`;
  }

  firstText(values: string[] | null | undefined): string {
    return values?.find(value => value.trim().length > 0) ?? '';
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
