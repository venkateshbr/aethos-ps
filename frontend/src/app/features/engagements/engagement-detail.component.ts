import { Component, computed, inject, signal, OnInit } from '@angular/core';
import { CommonModule, DatePipe, DecimalPipe, TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { firstValueFrom } from 'rxjs';

import { EngagementService, EngagementDetail, EngagementFinancialSummary } from '../../core/services/engagement.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { ProjectsListComponent } from '../projects/projects-list.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';
import { userMessageForError } from '../../core/utils/error-message';

/** Minimal unbilled-time row used to drive the invoice draft picker. */
interface UnbilledTimeEntry {
  id: string;
  project_id: string;
  employee_id: string;
  date: string;
  hours: string;
  description: string;
  billing_status: string;
}

interface ProjectMeta {
  id: string;
  name: string;
  code?: string | null;
}

interface AssignmentMeta {
  project_id: string;
  employee_id: string;
  override_rate: string | null;
  employee_name?: string | null;
}

interface EmployeeMeta {
  id: string;
  first_name: string;
  last_name: string;
  default_bill_rate?: string | number | null;
}

@Component({
  selector: 'app-engagement-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    DatePipe,
    DecimalPipe,
    TitleCasePipe,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MoneyPipe,
    ProjectsListComponent,
    SourceDocumentLinkComponent,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Back nav -->
      <button
        mat-button
        class="text-text-muted hover:text-text-primary mb-4 -ml-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
        (click)="goBack()"
        aria-label="Back to engagements"
      >
        <mat-icon>arrow_back</mat-icon>
        Engagements
      </button>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="animate-pulse" aria-busy="true" aria-label="Loading engagement">
          <div class="h-8 bg-surface-raised rounded w-1/3 mb-3"></div>
          <div class="h-4 bg-surface-raised rounded w-1/5 mb-6"></div>
          <div class="grid grid-cols-2 gap-4">
            @for (item of [1,2,3,4,5,6]; track item) {
              <div class="bg-surface-raised rounded p-4 h-16"></div>
            }
          </div>
        </div>
      }

      <!-- Error state -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- Detail content -->
      @if (!loading() && !error() && engagement()) {
        <!-- Header -->
        <div class="flex items-start justify-between mb-6">
          <div>
            <h1 class="text-2xl font-bold text-text-primary">{{ engagement()!.name }}</h1>
            <p class="text-sm text-text-muted mt-1">{{ engagement()!.client_name ?? 'Client' }}</p>
            @if (engagement()!.source_document_id) {
              <div class="mt-2">
                <app-source-document-link [documentId]="engagement()!.source_document_id!" />
              </div>
            }
          </div>
          <div class="flex items-center gap-3">
            <button
              type="button"
              class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              (click)="openInvoiceDrawer()"
              aria-label="Draft an invoice for this engagement"
            >
              <mat-icon class="text-base leading-none">receipt</mat-icon>
              Draft invoice
            </button>
            <span
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
              [class]="statusClass(engagement()!.status)"
              [attr.aria-label]="'Status: ' + engagement()!.status"
            >
              <span class="w-1.5 h-1.5 rounded-full" [class]="statusDotClass(engagement()!.status)"></span>
              {{ engagement()!.status | titlecase }}
            </span>
          </div>
        </div>

        <!-- Financial summary (#242) -->
        @if (financialSummary()) {
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <!-- Total Value -->
            <div class="bg-surface-raised rounded-lg p-4 border border-border-default">
              <div class="text-xs text-text-muted uppercase tracking-wide mb-1">Total Value</div>
              <div class="text-lg font-semibold text-text-primary font-mono">
                {{ financialSummary()!.total_value ? (financialSummary()!.total_value! | money: financialSummary()!.currency) : '—' }}
              </div>
            </div>
            <!-- Billed to Date -->
            <div class="bg-surface-raised rounded-lg p-4 border border-border-default">
              <div class="text-xs text-text-muted uppercase tracking-wide mb-1">Billed to Date</div>
              <div class="text-lg font-semibold text-accent-light font-mono">
                {{ financialSummary()!.billed_to_date | money: financialSummary()!.currency }}
              </div>
              @if (financialSummary()!.billed_pct !== null) {
                <div class="mt-1 text-xs text-text-muted">{{ financialSummary()!.billed_pct | number:'1.0-0' }}% of total</div>
                <div class="mt-1 h-1 bg-surface-base rounded-full overflow-hidden">
                  <div class="h-full bg-accent rounded-full transition-all" [style.width.%]="financialSummary()!.billed_pct"></div>
                </div>
              }
            </div>
            <!-- WIP (Unbilled) -->
            <div class="bg-surface-raised rounded-lg p-4 border border-border-default">
              <div class="text-xs text-text-muted uppercase tracking-wide mb-1">WIP (Unbilled)</div>
              <div class="text-lg font-semibold text-confidence-med font-mono">
                {{ financialSummary()!.wip_value | money: financialSummary()!.currency }}
              </div>
              <div class="mt-1 text-xs text-text-muted">{{ financialSummary()!.wip_hours | number:'1.0-1' }} hrs</div>
            </div>
            <!-- Remaining -->
            <div class="bg-surface-raised rounded-lg p-4 border border-border-default">
              <div class="text-xs text-text-muted uppercase tracking-wide mb-1">Remaining</div>
              <div class="text-lg font-semibold text-text-primary font-mono">
                {{ financialSummary()!.remaining_value ? (financialSummary()!.remaining_value! | money: financialSummary()!.currency) : '—' }}
              </div>
              <div class="mt-1 text-xs text-text-muted">{{ financialSummary()!.invoice_count }} invoice(s) sent</div>
            </div>
          </div>
        }

        <!-- Key metrics grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Billing Arrangement</dt>
            <dd class="text-text-primary text-sm font-medium">{{ formatBilling(engagement()!.billing_arrangement) }}</dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Currency</dt>
            <dd class="text-text-primary text-sm font-mono font-medium">{{ engagement()!.currency }}</dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Total Value</dt>
            <dd class="text-text-primary text-sm font-mono font-medium tabular-nums">
              {{ engagement()!.total_value | money: engagement()!.currency }}
            </dd>
          </div>
          @if (engagement()!.start_date) {
            <div class="bg-surface-raised border border-border-default rounded-lg p-4">
              <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Start Date</dt>
              <dd class="text-text-primary text-sm">{{ engagement()!.start_date }}</dd>
            </div>
          }
          @if (engagement()!.end_date) {
            <div class="bg-surface-raised border border-border-default rounded-lg p-4">
              <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">End Date</dt>
              <dd class="text-text-primary text-sm">{{ engagement()!.end_date }}</dd>
            </div>
          }
          @if (engagement()!.rate_card_name) {
            <div class="bg-surface-raised border border-border-default rounded-lg p-4">
              <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Rate Card</dt>
              <dd class="text-text-primary text-sm">{{ engagement()!.rate_card_name }}</dd>
            </div>
          }
        </div>

        @if (engagement()?.description) {
          <div class="mb-6 bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">Scope / Description</dt>
            <dd class="text-sm text-text-secondary leading-relaxed">{{ engagement()!.description }}</dd>
          </div>
        }

        <!-- Projects section -->
        <div class="mt-2">
          <h2 class="text-base font-semibold text-text-primary mb-4">Projects</h2>
          <app-projects-list [engagementId]="engagement()!.id" />
        </div>
      }

      <!-- Draft invoice drawer (#156) -->
      @if (drawerOpen()) {
        <div class="fixed inset-0 z-40 bg-black/50 animate-fade-in" (click)="closeInvoiceDrawer()" aria-hidden="true"></div>
        <aside
          class="fixed right-0 top-0 z-50 h-full w-full max-w-2xl bg-surface-base border-l border-border-default shadow-2xl flex flex-col drawer-slide-in"
          role="dialog" aria-modal="true" aria-labelledby="invoice-drawer-title"
        >
          <!-- Drawer header -->
          <div class="px-6 py-4 border-b border-border-default flex items-center justify-between flex-none">
            <div>
              <h2 id="invoice-drawer-title" class="text-base font-semibold text-text-primary">Draft invoice</h2>
              <p class="text-xs text-text-muted mt-0.5">
                {{ engagement()?.name }} · {{ engagement()?.currency }}
              </p>
            </div>
            <button
              type="button"
              class="text-text-muted hover:text-text-primary rounded p-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              (click)="closeInvoiceDrawer()"
              aria-label="Close invoice drawer"
            ><mat-icon>close</mat-icon></button>
          </div>

          <!-- Drawer body -->
          <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            <!-- Dates -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label for="inv-issue-date" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Issue date</label>
                <input id="inv-issue-date" type="date" [(ngModel)]="issueDate" name="inv-issue-date"
                  class="w-full px-3 py-2 bg-surface border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm" />
              </div>
              <div>
                <label for="inv-due-date" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Due date</label>
                <input id="inv-due-date" type="date" [(ngModel)]="dueDate" name="inv-due-date"
                  class="w-full px-3 py-2 bg-surface border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm" />
              </div>
            </div>

            <!-- Unbilled time picker -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-xs uppercase tracking-wide text-text-muted">Unbilled time entries</h3>
                @if (unbilledEntries().length > 0) {
                  <button type="button" class="text-xs text-accent-light hover:text-accent"
                    (click)="toggleSelectAll()">
                    {{ allSelected() ? 'Clear' : 'Select all' }}
                  </button>
                }
              </div>

              @if (loadingEntries()) {
                <div class="flex items-center justify-center py-6">
                  <div class="w-5 h-5 rounded-full border-2 border-accent border-t-transparent animate-spin" aria-label="Loading time entries"></div>
                </div>
              } @else if (unbilledEntries().length === 0) {
                <p class="text-sm text-text-muted bg-surface border border-border-default rounded px-3 py-3">
                  No unbilled time entries for this engagement yet.
                  <a routerLink="/app/time" class="text-accent-light hover:text-accent underline">Log time</a> first.
                </p>
              } @else {
                <ul class="space-y-2">
                  @for (entry of unbilledEntries(); track entry.id) {
                    <li class="bg-surface border border-border-default rounded-lg px-3 py-2 flex items-start gap-3">
                      <input
                        type="checkbox"
                        [id]="'te-' + entry.id"
                        [checked]="isSelected(entry.id)"
                        (change)="toggleEntry(entry.id)"
                        class="mt-1 w-4 h-4 rounded border-border-strong bg-surface text-accent focus:ring-accent"
                      />
                      <label [for]="'te-' + entry.id" class="flex-1 min-w-0 cursor-pointer">
                        <p class="text-sm text-text-primary truncate">
                          {{ entry.description || '(no description)' }}
                        </p>
                        <p class="text-xs text-text-muted mt-0.5">
                          {{ entry.date | date:'mediumDate' }} · {{ projectLabel(entry.project_id) }} · {{ employeeLabel(entry.employee_id) }} · {{ entry.hours }}h &#64; {{ rateFor(entry) }}/h
                        </p>
                      </label>
                      <span class="text-sm font-medium font-mono tabular-nums text-text-primary flex-none">
                        {{ lineAmount(entry) | money: engagement()!.currency }}
                      </span>
                    </li>
                  }
                </ul>
              }
            </div>

            <!-- Optional extra line -->
            <div>
              <label class="flex items-center gap-2 text-xs uppercase tracking-wide text-text-muted mb-2">
                <input type="checkbox" [ngModel]="includeExtra()" (ngModelChange)="includeExtra.set($event)" name="inv-extra-on"
                  class="w-4 h-4 rounded border-border-strong bg-surface text-accent focus:ring-accent" />
                Add a manual line
              </label>
              @if (includeExtra()) {
                <div class="grid grid-cols-12 gap-2">
                  <input type="text" placeholder="Description" [ngModel]="extraDescription()" (ngModelChange)="extraDescription.set($event)" name="inv-extra-desc"
                    class="col-span-7 px-3 py-2 bg-surface border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent" />
                  <input type="number" min="0" step="0.01" placeholder="Qty" [ngModel]="extraQty()" (ngModelChange)="extraQty.set($event)" name="inv-extra-qty"
                    class="col-span-2 px-3 py-2 bg-surface border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent" />
                  <input type="number" min="0" step="0.01" placeholder="Unit price" [ngModel]="extraUnitPrice()" (ngModelChange)="extraUnitPrice.set($event)" name="inv-extra-price"
                    class="col-span-3 px-3 py-2 bg-surface border border-border-default rounded text-text-primary text-sm focus:outline-none focus:border-accent" />
                </div>
              }
            </div>

            <!-- Totals -->
            <div class="border-t border-border-default pt-4 flex items-center justify-between">
              <span class="text-sm text-text-muted">Subtotal</span>
              <span class="text-base font-semibold font-mono tabular-nums text-text-primary">
                {{ subtotal() | money: engagement()!.currency }}
              </span>
            </div>

            <!-- Error -->
            @if (drawerError()) {
              <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
                {{ drawerError() }}
              </div>
            }
          </div>

          <!-- Drawer footer -->
          <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
            <button type="button"
              class="px-4 py-2 text-sm text-text-muted hover:text-text-primary rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              (click)="closeInvoiceDrawer()" [disabled]="submitting()">Cancel</button>
            <button type="button"
              class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [disabled]="!canSubmit() || submitting()"
              (click)="submitDraft()">
              @if (submitting()) { Drafting… } @else { Create draft invoice }
            </button>
          </div>
        </aside>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
    .animate-fade-in { animation: fade-in 0.15s ease-out; }
    @keyframes drawer-slide-in {
      from { transform: translateX(100%); }
      to   { transform: translateX(0); }
    }
    .drawer-slide-in { animation: drawer-slide-in 0.2s ease-out; }
  `],
})
export class EngagementDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private engagementService = inject(EngagementService);
  private http = inject(HttpClient);

  loading = signal(true);
  error = signal<string | null>(null);
  engagement = signal<EngagementDetail | null>(null);

  /** Financial summary — loaded separately; fails silently (#242). */
  financialSummary = signal<EngagementFinancialSummary | null>(null);

  // -------- Invoice drawer state (#156) --------
  drawerOpen = signal(false);
  loadingEntries = signal(false);
  unbilledEntries = signal<UnbilledTimeEntry[]>([]);
  selectedIds = signal<Set<string>>(new Set());
  projects = signal<ProjectMeta[]>([]);
  assignments = signal<AssignmentMeta[]>([]);
  employees = signal<EmployeeMeta[]>([]);
  submitting = signal(false);
  drawerError = signal<string | null>(null);

  // Form fields — signals so computed() tracks them correctly
  issueDate = this.todayIso();
  dueDate = this.thirtyDaysIso();
  includeExtra = signal(false);
  extraDescription = signal('');
  extraQty = signal<number | string>('');
  extraUnitPrice = signal<number | string>('');

  allSelected = computed(() => {
    const list = this.unbilledEntries();
    return list.length > 0 && list.every(e => this.selectedIds().has(e.id));
  });

  subtotal = computed(() => {
    let sum = 0;
    for (const e of this.unbilledEntries()) {
      if (this.selectedIds().has(e.id)) sum += this.lineAmountNumeric(e);
    }
    if (this.includeExtra()) {
      const q = Number(this.extraQty() ?? 0);
      const p = Number(this.extraUnitPrice() ?? 0);
      if (Number.isFinite(q) && Number.isFinite(p)) sum += q * p;
    }
    return sum.toFixed(2);
  });

  canSubmit = computed(() => {
    if (this.selectedIds().size > 0) return true;
    if (this.includeExtra()) {
      const q = Number(this.extraQty() ?? 0);
      const p = Number(this.extraUnitPrice() ?? 0);
      const desc = String(this.extraDescription() ?? '').trim();
      return desc.length > 0 && q > 0 && p >= 0;
    }
    return false;
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.router.navigate(['/app/engagements']);
      return;
    }
    this.engagementService.getEngagement(id).subscribe({
      next: (data) => {
        this.engagement.set(data);
        this.loading.set(false);
      },
      error: (err: unknown) => {
        // #113: per-status-code copy.
        this.error.set(userMessageForError(err, 'Engagement'));
        this.loading.set(false);
      },
    });

    // Load financial summary independently — fail silently; it's an enhancement (#242).
    this.engagementService.getEngagementFinancialSummary(id).subscribe({
      next: s => this.financialSummary.set(s),
      error: () => {}, // intentional: summary is non-blocking
    });
  }

  goBack(): void {
    this.router.navigate(['/app/engagements']);
  }

  formatBilling(arrangement: string): string {
    const map: Record<string, string> = {
      time_and_materials: 'T&M',
      fixed_fee: 'Fixed',
      retainer: 'Retainer',
      milestone: 'Milestone',
      capped_tm: 'Capped T&M',
    };
    return map[arrangement] ?? arrangement;
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

  // ----------------------------------------------------------------------
  // Invoice drawer (#156)
  // ----------------------------------------------------------------------

  openInvoiceDrawer(): void {
    const eng = this.engagement();
    if (!eng) return;
    this.drawerOpen.set(true);
    this.drawerError.set(null);
    this.selectedIds.set(new Set());
    this.includeExtra.set(false);
    this.extraDescription.set('');
    this.extraQty.set('');
    this.extraUnitPrice.set('');
    this.issueDate = this.todayIso();
    this.dueDate = this.thirtyDaysIso();
    void this.loadDrawerData(eng.id);
  }

  closeInvoiceDrawer(): void {
    if (this.submitting()) return;
    this.drawerOpen.set(false);
  }

  /**
   * Load projects → assignments (per project) → unbilled time entries scoped
   * to those projects. Engagement → projects is the only available path; the
   * /time-entries API does not yet filter by engagement_id directly.
   */
  private async loadDrawerData(engagementId: string): Promise<void> {
    this.loadingEntries.set(true);
    try {
      const projects = await firstValueFrom(
        this.http.get<ProjectMeta[]>(`/api/v1/projects?engagement_id=${engagementId}`),
      );
      this.projects.set(projects);

      const empResp = await firstValueFrom(
        this.http.get<{ items: EmployeeMeta[] }>('/api/v1/employees'),
      );
      this.employees.set(empResp.items ?? []);

      const allAssignments: AssignmentMeta[] = [];
      const entriesByProject: UnbilledTimeEntry[][] = [];
      for (const p of projects) {
        const aResp = await firstValueFrom(
          this.http.get<{ items: AssignmentMeta[] }>(`/api/v1/projects/${p.id}/assignments`),
        );
        for (const a of aResp.items ?? []) allAssignments.push({ ...a, project_id: p.id });

        const teResp = await firstValueFrom(
          this.http.get<{ items: UnbilledTimeEntry[] }>(
            `/api/v1/time-entries?project_id=${p.id}&billing_status=unbilled`,
          ),
        );
        entriesByProject.push(teResp.items ?? []);
      }
      this.assignments.set(allAssignments);
      const flat = entriesByProject.flat()
        .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
      this.unbilledEntries.set(flat);
    } catch {
      this.drawerError.set('Could not load unbilled time entries. Please retry.');
    } finally {
      this.loadingEntries.set(false);
    }
  }

  isSelected(id: string): boolean {
    return this.selectedIds().has(id);
  }

  toggleEntry(id: string): void {
    const next = new Set(this.selectedIds());
    if (next.has(id)) next.delete(id);
    else next.add(id);
    this.selectedIds.set(next);
  }

  toggleSelectAll(): void {
    if (this.allSelected()) {
      this.selectedIds.set(new Set());
    } else {
      this.selectedIds.set(new Set(this.unbilledEntries().map(e => e.id)));
    }
  }

  projectLabel(id: string): string {
    const p = this.projects().find(x => x.id === id);
    return p ? (p.code ? `${p.code} · ${p.name}` : p.name) : '—';
  }

  employeeLabel(id: string): string {
    const e = this.employees().find(x => x.id === id);
    return e ? `${e.first_name} ${e.last_name}` : '—';
  }

  /** Bill rate for a time entry: assignment override → employee default → 0. */
  rateFor(entry: UnbilledTimeEntry): string {
    const a = this.assignments().find(
      x => x.project_id === entry.project_id && x.employee_id === entry.employee_id,
    );
    if (a?.override_rate != null) return String(a.override_rate);
    const e = this.employees().find(x => x.id === entry.employee_id);
    return e?.default_bill_rate != null ? String(e.default_bill_rate) : '0';
  }

  lineAmount(entry: UnbilledTimeEntry): string {
    return this.lineAmountNumeric(entry).toFixed(2);
  }

  private lineAmountNumeric(entry: UnbilledTimeEntry): number {
    const h = Number(entry.hours);
    const r = Number(this.rateFor(entry));
    return Number.isFinite(h) && Number.isFinite(r) ? h * r : 0;
  }

  async submitDraft(): Promise<void> {
    const eng = this.engagement();
    if (!eng || !this.canSubmit() || this.submitting()) return;
    this.submitting.set(true);
    this.drawerError.set(null);

    const lines: Array<Record<string, unknown>> = [];
    for (const entry of this.unbilledEntries()) {
      if (!this.selectedIds().has(entry.id)) continue;
      lines.push({
        description:
          entry.description ||
          `${this.employeeLabel(entry.employee_id)} · ${this.projectLabel(entry.project_id)} (${entry.date})`,
        quantity: String(entry.hours),
        unit_price: this.rateFor(entry),
        time_entry_id: entry.id,
      });
    }
    if (this.includeExtra()) {
      lines.push({
        description: String(this.extraDescription() ?? '').trim(),
        quantity: String(this.extraQty() ?? '0'),
        unit_price: String(this.extraUnitPrice() ?? '0'),
      });
    }

    const payload = {
      engagement_id: eng.id,
      client_id: eng.client_id,
      currency: eng.currency,
      issue_date: this.issueDate || null,
      due_date: this.dueDate || null,
      lines,
    };

    try {
      const created = await firstValueFrom(
        this.http.post<{ id: string }>('/api/v1/invoices', payload),
      );
      this.submitting.set(false);
      this.drawerOpen.set(false);
      this.router.navigate(['/app/invoices'], { queryParams: { highlight: created.id } });
    } catch (err: unknown) {
      this.submitting.set(false);
      this.drawerError.set(userMessageForError(err, 'Invoice'));
    }
  }

  private todayIso(): string {
    return new Date().toISOString().split('T')[0];
  }

  private thirtyDaysIso(): string {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split('T')[0];
  }
}
