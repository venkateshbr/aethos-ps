import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

type IntegrationStatus = 'available' | 'planned' | 'research';
type IntegrationRisk = 'low' | 'medium' | 'high';

interface IntegrationCatalogItem {
  key: string;
  category: string;
  display_name: string;
  provider: string;
  status: IntegrationStatus;
  risk: IntegrationRisk;
  auth_model: string;
  supported_markets: string[];
  data_classes: string[];
  capabilities: string[];
  notes?: string | null;
}

interface IntegrationCatalogResponse {
  integrations: IntegrationCatalogItem[];
  total: number;
}

const CATEGORY_LABELS: Record<string, string> = {
  payments: 'Payments',
  email: 'Email',
  calendar_email: 'Calendar & Email',
  banking: 'Banking',
  government_tax: 'Government & Tax',
  payroll: 'Payroll',
  crm: 'CRM',
  document_storage: 'Document Storage',
};

@Component({
  selector: 'app-integrations',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="bg-surface-raised border border-border-default rounded-lg overflow-hidden">
      <div class="flex items-center justify-between gap-4 px-6 py-4 border-b border-border-default">
        <div class="flex items-center gap-2">
          <mat-icon class="text-indigo-400">integration_instructions</mat-icon>
          <h3 class="text-base font-semibold text-text-primary">Integration Roadmap</h3>
        </div>
        @if (!loading() && !loadError()) {
          <span class="text-xs text-text-muted">{{ total() }} surfaces</span>
        }
      </div>

      @if (loading()) {
        <div class="divide-y divide-border-default animate-pulse" aria-busy="true" aria-label="Loading integrations">
          @for (i of [1, 2, 3, 4]; track i) {
            <div class="px-6 py-4">
              <div class="h-4 bg-surface rounded w-1/3 mb-2"></div>
              <div class="h-3 bg-surface rounded w-2/3"></div>
            </div>
          }
        </div>
      } @else if (loadError()) {
        <div class="px-6 py-4 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Failed to load integration roadmap.
          <button type="button" class="underline hover:no-underline ml-1" (click)="load()">Retry</button>
        </div>
      } @else {
        <div class="divide-y divide-border-default">
          @for (item of integrations(); track item.key) {
            <div class="px-6 py-4 hover:bg-surface-base/30 transition-colors">
              <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <h4 class="text-sm font-medium text-text-primary">{{ item.display_name }}</h4>
                    <span class="text-xs text-text-muted">{{ categoryLabel(item.category) }}</span>
                    <span class="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium" [class]="statusClass(item.status)">
                      {{ statusLabel(item.status) }}
                    </span>
                  </div>
                  <p class="text-xs text-text-secondary mt-1">{{ item.provider }}</p>
                  @if (item.notes) {
                    <p class="text-xs text-text-muted mt-1">{{ item.notes }}</p>
                  }
                </div>

                <div class="flex flex-wrap gap-2 md:justify-end md:max-w-md">
                  <span class="inline-flex items-center gap-1 rounded bg-surface-base px-2 py-1 text-xs text-text-secondary">
                    <mat-icon style="font-size:0.9rem;width:0.9rem;height:0.9rem;">shield</mat-icon>
                    {{ riskLabel(item.risk) }}
                  </span>
                  <span class="rounded bg-surface-base px-2 py-1 text-xs text-text-secondary">
                    {{ authLabel(item.auth_model) }}
                  </span>
                  <span class="rounded bg-surface-base px-2 py-1 text-xs text-text-secondary">
                    {{ item.supported_markets.join(' / ') }}
                  </span>
                </div>
              </div>

              <div class="mt-3 flex flex-wrap gap-2">
                @for (capability of item.capabilities.slice(0, 3); track capability) {
                  <span class="rounded border border-border-default px-2 py-0.5 text-xs text-text-muted">
                    {{ capabilityLabel(capability) }}
                  </span>
                }
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class IntegrationsComponent implements OnInit {
  private http = inject(HttpClient);

  loading = signal(true);
  loadError = signal(false);
  integrations = signal<IntegrationCatalogItem[]>([]);
  total = computed(() => this.integrations().length);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.http.get<IntegrationCatalogResponse>('/api/v1/integrations/catalog').subscribe({
      next: (response) => {
        this.integrations.set(response.integrations);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  categoryLabel(category: string): string {
    return CATEGORY_LABELS[category] ?? category;
  }

  statusLabel(status: IntegrationStatus): string {
    return status === 'available' ? 'Available' : status === 'planned' ? 'Planned' : 'Research';
  }

  statusClass(status: IntegrationStatus): string {
    if (status === 'available') return 'bg-emerald-500/15 text-emerald-300';
    if (status === 'planned') return 'bg-indigo-500/15 text-indigo-300';
    return 'bg-amber-500/15 text-amber-300';
  }

  riskLabel(risk: IntegrationRisk): string {
    return `${risk[0].toUpperCase()}${risk.slice(1)} risk`;
  }

  authLabel(authModel: string): string {
    return authModel
      .split('_')
      .map((part) => `${part[0].toUpperCase()}${part.slice(1)}`)
      .join(' ');
  }

  capabilityLabel(capability: string): string {
    return capability
      .split('_')
      .map((part) => `${part[0].toUpperCase()}${part.slice(1)}`)
      .join(' ');
  }
}
