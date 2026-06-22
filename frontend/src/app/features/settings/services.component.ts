import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

export interface ServiceCatalogueItem {
  id: string;
  code: string;
  name: string;
  description?: string;
  service_line: string;
  billing_unit: string;
  default_rate?: string;
  default_currency: string;
  revenue_account_code?: string;
  revenue_account_name?: string;
  is_active: boolean;
  is_system: boolean;
}

const SERVICE_LINE_LABELS: Record<string, string> = {
  accounting: 'Accounting & Advisory',
  tax: 'Tax Services',
  cosec: 'Company Secretarial',
  payroll: 'Payroll',
  advisory: 'Advisory',
  other: 'Other',
};

const SERVICE_LINE_ORDER = ['accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other'];

const BILLING_UNIT_LABELS: Record<string, string> = {
  hour: 'Hourly (T&M)',
  fixed: 'Fixed Fee',
  retainer: 'Monthly Retainer',
  per_employee: 'Per Employee/Month',
  per_entity: 'Per Entity',
  per_event: 'Per Event',
  milestone: 'Milestone-based',
};

interface ServiceLineGroup {
  key: string;
  label: string;
  items: ServiceCatalogueItem[];
}

interface ChartOfAccount {
  id: string;
  code: string;
  name: string;
}

@Component({
  selector: 'app-services',
  standalone: true,
  imports: [FormsModule, ReactiveFormsModule, MatIconModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-border-default">
        <div class="flex items-center gap-2">
          <mat-icon class="text-indigo-400">inventory_2</mat-icon>
          <h3 class="text-base font-semibold text-text-primary">Services &amp; Products</h3>
        </div>
        <button
          type="button"
          (click)="openCreatePanel()"
          class="inline-flex items-center gap-1.5 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-1.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Add new service"
        >
          <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">add</mat-icon>
          Add Service
        </button>
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="divide-y divide-border-default animate-pulse" aria-busy="true" aria-label="Loading services">
          @for (i of [1, 2, 3, 4]; track i) {
            <div class="flex items-center gap-4 px-6 py-4">
              <div class="h-4 bg-surface rounded w-20"></div>
              <div class="h-4 bg-surface rounded w-1/3"></div>
              <div class="h-4 bg-surface rounded w-20"></div>
            </div>
          }
        </div>
      }

      <!-- Error state -->
      @if (loadError() && !loading()) {
        <div class="px-6 py-4 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Failed to load services.
          <button type="button" class="underline hover:no-underline ml-1" (click)="load()">Retry</button>
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !loadError() && services().length === 0) {
        <div class="px-6 py-10 text-center">
          <mat-icon class="text-3xl text-text-disabled mb-2 block">inventory_2</mat-icon>
          <p class="text-sm text-text-muted">No services configured yet.</p>
          <p class="text-xs text-text-disabled mt-1">Add custom services or wait for the system seed to populate.</p>
        </div>
      }

      <!-- Service lines grouped -->
      @if (!loading() && !loadError() && groupedLines().length > 0) {
        <div class="divide-y divide-border-default">
          @for (group of groupedLines(); track group.key) {
            <div>
              <!-- Section header -->
              <div class="flex items-center justify-between px-6 py-3 bg-surface-base/40">
                <h4 class="text-xs font-semibold text-text-muted uppercase tracking-wide">{{ group.label }}</h4>
                <span class="text-xs text-text-disabled">{{ group.items.length }} service{{ group.items.length !== 1 ? 's' : '' }}</span>
              </div>

              <!-- Service rows -->
              @for (svc of group.items; track svc.id) {
                <div
                  class="flex items-center gap-3 px-6 py-3 border-t border-border-default/50 hover:bg-surface-base/30 transition-colors"
                  [class.opacity-50]="!svc.is_active"
                >
                  <!-- Code badge -->
                  <span class="flex-none font-mono text-xs text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded w-20 text-center">
                    {{ svc.code }}
                  </span>

                  <!-- Name -->
                  <span class="flex-1 text-sm text-text-primary min-w-0 truncate" [title]="svc.name">
                    {{ svc.name }}
                  </span>

                  <!-- Billing unit -->
                  <span class="flex-none text-xs text-text-muted w-36 text-right hidden sm:block">
                    {{ billingLabel(svc.billing_unit) }}
                  </span>

                  <!-- System lock / active badge -->
                  @if (svc.is_system) {
                    <span
                      class="flex-none inline-flex items-center gap-1 text-xs text-text-disabled"
                      aria-label="System service — read-only"
                      title="System service — read-only"
                    >
                      <mat-icon style="font-size:0.9rem;width:0.9rem;height:0.9rem;" aria-hidden="true">lock</mat-icon>
                    </span>
                  } @else {
                    <!-- Active toggle -->
                    <button
                      type="button"
                      [disabled]="toggling() === svc.id"
                      (click)="toggleActive(svc); $event.stopPropagation()"
                      class="flex-none inline-flex items-center gap-1 text-xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded px-1"
                      [class]="svc.is_active ? 'text-accent-light hover:text-text-secondary' : 'text-text-disabled hover:text-text-muted'"
                      [attr.aria-label]="(svc.is_active ? 'Deactivate' : 'Activate') + ' ' + svc.name"
                      [attr.aria-pressed]="svc.is_active"
                    >
                      <span
                        class="w-2 h-2 rounded-full"
                        [class]="svc.is_active ? 'bg-emerald-400' : 'bg-slate-600'"
                        aria-hidden="true"
                      ></span>
                      @if (toggling() === svc.id) {
                        <span>Saving...</span>
                      } @else {
                        <span>{{ svc.is_active ? 'Active' : 'Inactive' }}</span>
                      }
                    </button>

                    <!-- Edit button -->
                    <button
                      type="button"
                      (click)="openEditPanel(svc); $event.stopPropagation()"
                      class="flex-none text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                      [attr.aria-label]="'Edit ' + svc.name"
                    >
                      <mat-icon style="font-size:1rem;width:1rem;height:1rem;">edit</mat-icon>
                    </button>

                    <!-- Delete/deactivate button -->
                    <button
                      type="button"
                      (click)="deactivateService(svc); $event.stopPropagation()"
                      class="flex-none text-text-disabled hover:text-confidence-low transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low rounded"
                      [attr.aria-label]="'Delete ' + svc.name"
                      title="Deactivate service"
                    >
                      <mat-icon style="font-size:1rem;width:1rem;height:1rem;">delete_outline</mat-icon>
                    </button>
                  }
                </div>
              }
            </div>
          }
        </div>
      }
    </div>

    <!-- Create / Edit slide-in panel -->
    @if (showPanel()) {
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/50 z-40"
        (click)="closePanel()"
        aria-hidden="true"
      ></div>
      <!-- Panel -->
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        [attr.aria-labelledby]="editTarget() ? 'edit-service-title' : 'create-service-title'"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2
            [id]="editTarget() ? 'edit-service-title' : 'create-service-title'"
            class="text-base font-semibold text-text-primary"
          >
            {{ editTarget() ? 'Edit Service' : 'Add Service' }}
          </h2>
          <button
            type="button"
            (click)="closePanel()"
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            aria-label="Close panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <form
          [formGroup]="serviceForm"
          (ngSubmit)="submitForm()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >
          <!-- Code -->
          <div>
            <label for="svc-code" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Code *</label>
            <input
              id="svc-code"
              type="text"
              formControlName="code"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
              placeholder="e.g. ACC-005"
            />
            @if (serviceForm.controls.code.touched && serviceForm.controls.code.errors) {
              <p class="text-xs text-confidence-low mt-1">Code is required.</p>
            }
          </div>

          <!-- Name -->
          <div>
            <label for="svc-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Name *</label>
            <input
              id="svc-name"
              type="text"
              formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. Advisory Retainer"
            />
            @if (serviceForm.controls.name.touched && serviceForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1">Name is required.</p>
            }
          </div>

          <!-- Service Line -->
          <div>
            <label for="svc-line" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Service Line *</label>
            <select
              id="svc-line"
              formControlName="service_line"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="">Select...</option>
              @for (line of serviceLineOptions; track line.key) {
                <option [value]="line.key">{{ line.label }}</option>
              }
            </select>
            @if (serviceForm.controls.service_line.touched && serviceForm.controls.service_line.errors) {
              <p class="text-xs text-confidence-low mt-1">Service line is required.</p>
            }
          </div>

          <!-- Billing Unit -->
          <div>
            <label for="svc-billing" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Billing Unit *</label>
            <select
              id="svc-billing"
              formControlName="billing_unit"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="">Select...</option>
              @for (unit of billingUnitOptions; track unit.key) {
                <option [value]="unit.key">{{ unit.label }}</option>
              }
            </select>
            @if (serviceForm.controls.billing_unit.touched && serviceForm.controls.billing_unit.errors) {
              <p class="text-xs text-confidence-low mt-1">Billing unit is required.</p>
            }
          </div>

          <!-- Default Rate -->
          <div>
            <label for="svc-rate" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Default Rate</label>
            <div class="flex gap-2">
              <select
                formControlName="default_currency"
                class="w-24 px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                aria-label="Currency"
              >
                <option value="GBP">GBP</option>
                <option value="USD">USD</option>
                <option value="SGD">SGD</option>
                <option value="INR">INR</option>
                <option value="AUD">AUD</option>
              </select>
              <input
                id="svc-rate"
                type="text"
                formControlName="default_rate"
                class="flex-1 px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm font-mono"
                placeholder="e.g. 250.00"
              />
            </div>
            <p class="text-xs text-text-disabled mt-1">Pre-fills when added to an engagement</p>
          </div>

          <!-- Description -->
          <div>
            <label for="svc-desc" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Description</label>
            <textarea
              id="svc-desc"
              formControlName="description"
              rows="2"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm resize-none"
              placeholder="Brief description of this service..."
            ></textarea>
          </div>

          <!-- Revenue Account -->
          <div>
            <label for="svc-account" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Revenue Account</label>
            <input
              id="svc-account"
              type="text"
              formControlName="revenue_account_search"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="Search chart of accounts..."
              (input)="searchAccounts($event)"
              autocomplete="off"
            />
            @if (accountResults().length > 0) {
              <ul
                class="mt-1 bg-surface-raised border border-border-default rounded shadow-xl max-h-40 overflow-y-auto text-sm"
                role="listbox"
                aria-label="Account suggestions"
              >
                @for (acct of accountResults(); track acct.id) {
                  <li>
                    <button
                      type="button"
                      (click)="selectAccount(acct)"
                      class="w-full text-left px-3 py-2 hover:bg-surface-base/60 text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent"
                      role="option"
                    >
                      <span class="font-mono text-xs text-text-muted mr-2">{{ acct.code }}</span>
                      {{ acct.name }}
                    </button>
                  </li>
                }
              </ul>
            }
            @if (selectedAccount()) {
              <div class="mt-1 flex items-center gap-1 text-xs text-accent-light">
                <mat-icon style="font-size:0.875rem;width:0.875rem;height:0.875rem;">check_circle</mat-icon>
                {{ selectedAccount()!.code }} — {{ selectedAccount()!.name }}
              </div>
            }
          </div>

          @if (panelError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">
              {{ panelError() }}
            </div>
          }
        </form>

        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closePanel()"
          >
            Cancel
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="serviceForm.invalid || saving()"
            (click)="submitForm()"
          >
            @if (saving()) {
              <span>Saving...</span>
            } @else {
              <span>{{ editTarget() ? 'Save Changes' : 'Add Service' }}</span>
            }
          </button>
        </div>
      </aside>
    }
  `,
  styles: [':host { display: block; }'],
})
export class ServicesComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  loading = signal(true);
  loadError = signal(false);
  services = signal<ServiceCatalogueItem[]>([]);
  toggling = signal<string | null>(null);

  // Panel state
  showPanel = signal(false);
  saving = signal(false);
  panelError = signal<string | null>(null);
  editTarget = signal<ServiceCatalogueItem | null>(null);

  // Account search
  accountResults = signal<ChartOfAccount[]>([]);
  selectedAccount = signal<ChartOfAccount | null>(null);

  readonly serviceLineOptions = SERVICE_LINE_ORDER.map(key => ({ key, label: SERVICE_LINE_LABELS[key] }));
  readonly billingUnitOptions = Object.entries(BILLING_UNIT_LABELS).map(([key, label]) => ({ key, label }));

  serviceForm = this.fb.nonNullable.group({
    code:                   ['', [Validators.required]],
    name:                   ['', [Validators.required]],
    service_line:           ['', [Validators.required]],
    billing_unit:           ['', [Validators.required]],
    default_rate:           [''],
    default_currency:       ['GBP'],
    description:            [''],
    revenue_account_search: [''],
    revenue_account_code:   [''],
    revenue_account_name:   [''],
  });

  groupedLines = computed<ServiceLineGroup[]>(() => {
    const all = this.services();
    const map = new Map<string, ServiceCatalogueItem[]>();
    for (const svc of all) {
      const key = svc.service_line;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(svc);
    }
    return SERVICE_LINE_ORDER
      .filter(key => map.has(key))
      .map(key => ({
        key,
        label: SERVICE_LINE_LABELS[key] ?? key,
        items: map.get(key)!,
      }));
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<ServiceCatalogueItem[]>('/api/v1/services').subscribe({
      next: (data) => {
        this.services.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  billingLabel(unit: string): string {
    return BILLING_UNIT_LABELS[unit] ?? unit;
  }

  toggleActive(svc: ServiceCatalogueItem): void {
    if (svc.is_system) return;
    this.toggling.set(svc.id);
    this.http.patch<ServiceCatalogueItem>(`/api/v1/services/${svc.id}`, { is_active: !svc.is_active }).subscribe({
      next: (updated) => {
        this.services.update(list => list.map(s => s.id === updated.id ? updated : s));
        this.toggling.set(null);
      },
      error: () => {
        this.toggling.set(null);
      },
    });
  }

  deactivateService(svc: ServiceCatalogueItem): void {
    if (svc.is_system) return;
    if (!confirm(`Deactivate "${svc.name}"? It will no longer appear in engagement dropdowns.`)) return;
    this.toggling.set(svc.id);
    this.http.delete<ServiceCatalogueItem>(`/api/v1/services/${svc.id}`).subscribe({
      next: (updated) => {
        // Backend returns deactivated item; update in list
        this.services.update(list => list.map(s => s.id === updated.id ? updated : s));
        this.toggling.set(null);
      },
      error: () => {
        // Fallback: just remove optimistically on 204
        this.services.update(list => list.map(s => s.id === svc.id ? { ...s, is_active: false } : s));
        this.toggling.set(null);
      },
    });
  }

  openCreatePanel(): void {
    this.editTarget.set(null);
    this.selectedAccount.set(null);
    this.accountResults.set([]);
    this.serviceForm.reset({
      code: '',
      name: '',
      service_line: '',
      billing_unit: '',
      default_rate: '',
      default_currency: 'GBP',
      description: '',
      revenue_account_search: '',
      revenue_account_code: '',
      revenue_account_name: '',
    });
    this.panelError.set(null);
    this.showPanel.set(true);
  }

  openEditPanel(svc: ServiceCatalogueItem): void {
    this.editTarget.set(svc);
    this.selectedAccount.set(
      svc.revenue_account_code
        ? { id: svc.revenue_account_code, code: svc.revenue_account_code, name: svc.revenue_account_name ?? '' }
        : null
    );
    this.accountResults.set([]);
    this.serviceForm.reset({
      code: svc.code,
      name: svc.name,
      service_line: svc.service_line,
      billing_unit: svc.billing_unit,
      default_rate: svc.default_rate ?? '',
      default_currency: svc.default_currency,
      description: svc.description ?? '',
      revenue_account_search: svc.revenue_account_name ?? svc.revenue_account_code ?? '',
      revenue_account_code: svc.revenue_account_code ?? '',
      revenue_account_name: svc.revenue_account_name ?? '',
    });
    this.panelError.set(null);
    this.showPanel.set(true);
  }

  closePanel(): void {
    this.showPanel.set(false);
    this.accountResults.set([]);
  }

  searchAccounts(event: Event): void {
    const query = (event.target as HTMLInputElement).value.trim();
    if (query.length < 2) {
      this.accountResults.set([]);
      return;
    }
    this.http.get<ChartOfAccount[]>(`/api/v1/accounts?search=${encodeURIComponent(query)}&limit=10`).subscribe({
      next: (results) => this.accountResults.set(results),
      error: () => this.accountResults.set([]),
    });
  }

  selectAccount(acct: ChartOfAccount): void {
    this.selectedAccount.set(acct);
    this.serviceForm.patchValue({
      revenue_account_search: `${acct.code} — ${acct.name}`,
      revenue_account_code: acct.code,
      revenue_account_name: acct.name,
    });
    this.accountResults.set([]);
  }

  submitForm(): void {
    if (this.serviceForm.invalid) {
      this.serviceForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.panelError.set(null);
    const v = this.serviceForm.getRawValue();
    const payload = {
      code:                 v.code,
      name:                 v.name,
      service_line:         v.service_line,
      billing_unit:         v.billing_unit,
      default_rate:         v.default_rate || null,
      default_currency:     v.default_currency,
      description:          v.description || null,
      revenue_account_code: v.revenue_account_code || null,
      revenue_account_name: v.revenue_account_name || null,
    };

    const target = this.editTarget();
    const req$ = target
      ? this.http.patch<ServiceCatalogueItem>(`/api/v1/services/${target.id}`, payload)
      : this.http.post<ServiceCatalogueItem>('/api/v1/services', payload);

    req$.subscribe({
      next: (result) => {
        if (target) {
          this.services.update(list => list.map(s => s.id === result.id ? result : s));
        } else {
          this.services.update(list => [...list, result]);
        }
        this.saving.set(false);
        this.closePanel();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.saving.set(false);
        const detail = err?.error?.detail;
        this.panelError.set(typeof detail === 'string' ? detail : 'Could not save service. Please try again.');
      },
    });
  }
}
