import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';

interface FinancePersona {
  id: string;
  label: string;
  mapped_roles: string[];
  description: string;
  areas: string[];
  allowed_actions: string[];
  restricted_actions: string[];
  read_only: boolean;
}

@Component({
  selector: 'app-finance-personas',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-3 border-b border-border-default px-4 py-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div class="flex items-center gap-2">
            <mat-icon class="text-accent-light" style="font-size:1rem;width:1rem;height:1rem;">badge</mat-icon>
            <h3 class="text-sm font-semibold text-text-primary">Finance role personas</h3>
          </div>
          <p class="mt-1 text-xs text-text-muted">Product-facing finance labels mapped to enforced tenant roles.</p>
        </div>
        <div class="text-left md:text-right">
          <p class="text-[11px] uppercase tracking-wide text-text-disabled">Current enforced role</p>
          <p class="mt-1 text-sm font-medium text-text-primary">{{ roleLabel(currentRole()) }}</p>
          @if (compatiblePersonas().length) {
            <div class="mt-2 flex flex-wrap gap-1.5 md:justify-end">
              @for (persona of compatiblePersonas(); track persona.id) {
                <span class="rounded bg-accent/10 px-2 py-1 text-xs text-accent-light">{{ persona.label }}</span>
              }
            </div>
          }
        </div>
      </div>

      @if (loading()) {
        <div class="space-y-3 px-4 py-4" aria-busy="true">
          @for (item of [1,2,3]; track item) {
            <div class="h-14 rounded bg-surface"></div>
          }
        </div>
      } @else if (error()) {
        <div class="px-4 py-4 text-sm text-confidence-low" role="alert">{{ error() }}</div>
      } @else {
        <div class="divide-y divide-border-subtle">
          @for (persona of personas(); track persona.id) {
            <article [class]="personaRowClass(persona)">
              <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <h4 class="text-sm font-medium text-text-primary">{{ persona.label }}</h4>
                    @if (persona.read_only) {
                      <span class="rounded bg-surface px-2 py-0.5 text-[11px] uppercase tracking-wide text-text-muted">Read only</span>
                    }
                    @if (isCompatible(persona)) {
                      <span class="rounded bg-accent/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-accent-light">Current role</span>
                    }
                  </div>
                  <p class="mt-1 text-xs text-text-muted">{{ persona.description }}</p>
                  <div class="mt-2 flex flex-wrap gap-1.5">
                    @for (area of persona.areas; track area) {
                      <span class="rounded bg-surface px-2 py-1 text-xs text-text-secondary">{{ area }}</span>
                    }
                  </div>
                </div>
                <div class="min-w-0 lg:w-72">
                  <p class="text-[11px] uppercase tracking-wide text-text-disabled">Mapped tenant roles</p>
                  <div class="mt-1 flex flex-wrap gap-1.5">
                    @for (role of persona.mapped_roles; track role) {
                      <span class="rounded px-2 py-1 text-xs {{ roleBadgeClass(role) }}">{{ roleLabel(role) }}</span>
                    }
                  </div>
                </div>
              </div>
              <div class="mt-3 grid gap-2 md:grid-cols-2">
                <div class="rounded border border-border-subtle bg-surface px-3 py-2">
                  <p class="text-[11px] uppercase tracking-wide text-text-disabled">Allowed through current gates</p>
                  <ul class="mt-1 space-y-1 text-xs text-text-secondary">
                    @for (action of persona.allowed_actions; track action) {
                      <li>{{ action }}</li>
                    }
                  </ul>
                </div>
                <div class="rounded border border-border-subtle bg-surface px-3 py-2">
                  <p class="text-[11px] uppercase tracking-wide text-text-disabled">Still restricted</p>
                  <ul class="mt-1 space-y-1 text-xs text-text-secondary">
                    @for (action of persona.restricted_actions; track action) {
                      <li>{{ action }}</li>
                    }
                  </ul>
                </div>
              </div>
            </article>
          }
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class FinancePersonasComponent implements OnInit {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  personas = signal<FinancePersona[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  currentRole = computed(() => this.auth.role() ?? 'viewer');
  compatiblePersonas = computed(() =>
    this.personas().filter(persona => this.isCompatible(persona)),
  );

  ngOnInit(): void {
    this.http.get<{ items: FinancePersona[] }>('/api/v1/tenants/finance-personas').subscribe({
      next: (res) => {
        this.personas.set(res.items ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not load finance role personas.');
        this.loading.set(false);
      },
    });
  }

  isCompatible(persona: FinancePersona): boolean {
    return persona.mapped_roles.includes(this.currentRole());
  }

  roleLabel(role: string): string {
    const labels: Record<string, string> = {
      owner: 'Owner',
      admin: 'Admin',
      manager: 'Manager',
      member: 'Member',
      viewer: 'Viewer',
      employee: 'Employee',
    };
    return labels[role] ?? role;
  }

  roleBadgeClass(role: string): string {
    if (role === 'owner') return 'bg-confidence-low/10 text-confidence-low';
    if (role === 'admin') return 'bg-confidence-med/10 text-confidence-med';
    if (role === 'manager') return 'bg-accent/10 text-accent-light';
    if (role === 'viewer') return 'bg-surface-raised text-text-muted';
    return 'bg-surface text-text-muted';
  }

  personaRowClass(persona: FinancePersona): string {
    return `px-4 py-3${this.isCompatible(persona) ? ' bg-accent/5' : ''}`;
  }
}
