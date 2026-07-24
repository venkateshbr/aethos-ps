import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { forkJoin } from 'rxjs';

import { AgingReport, ReportsService } from '../../core/services/reports.service';
import { BarChartComponent, BarChartDatum } from '../../shared/components/bar-chart.component';
import { MoneyPipe } from '../../shared/pipes/money.pipe';

/**
 * Home dashboard (#405) — an at-a-glance working-capital view instead of dropping
 * straight into the copilot. Pulls AR/AP aging + the tenant base currency and
 * surfaces receivables/payables/net position with an AR aging chart + quick links.
 */
@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [MatIconModule, BarChartComponent, MoneyPipe],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-text-primary">Dashboard</h1>
        <p class="text-sm text-text-muted mt-1">Working capital at a glance · {{ baseCurrency() }} base currency</p>
      </div>

      @if (loading()) {
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-pulse" aria-busy="true">
          @for (i of [1, 2, 3]; track i) {
            <div class="bg-surface-raised border border-border-default rounded-lg p-5">
              <div class="h-3 bg-surface rounded w-24 mb-3"></div>
              <div class="h-7 bg-surface rounded w-32"></div>
            </div>
          }
        </div>
      } @else if (error()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          Could not load the dashboard.
          <button type="button" class="underline hover:no-underline ml-1" (click)="load()">Retry</button>
        </div>
      } @else {
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="bg-surface-raised border border-border-default rounded-lg p-5" data-testid="metric-ar">
            <p class="text-xs text-text-muted uppercase tracking-wide">Receivables (AR)</p>
            <p class="text-2xl font-bold text-accent-light font-mono tabular-nums mt-1">
              {{ ar()?.total || '0.00' | money: baseCurrency() }}
            </p>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-5" data-testid="metric-ap">
            <p class="text-xs text-text-muted uppercase tracking-wide">Payables (AP)</p>
            <p class="text-2xl font-bold text-orange-400 font-mono tabular-nums mt-1">
              {{ ap()?.total || '0.00' | money: baseCurrency() }}
            </p>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-5" data-testid="metric-net">
            <p class="text-xs text-text-muted uppercase tracking-wide">Net position</p>
            <p
              class="text-2xl font-bold font-mono tabular-nums mt-1"
              [class]="netPosition() >= 0 ? 'text-accent-light' : 'text-confidence-low'"
            >
              {{ netPositionString() | money: baseCurrency() }}
            </p>
          </div>
        </div>

        <div class="bg-surface-raised border border-border-default rounded-lg p-5 mt-4" data-testid="dashboard-ar-chart">
          <app-bar-chart
            [data]="arBuckets()"
            title="AR aging"
            format="currency"
            [currency]="baseCurrency()"
          />
        </div>

        <div class="flex flex-wrap gap-2 mt-6">
          @for (link of quickLinks; track link.route) {
            <button
              type="button"
              (click)="go(link.route)"
              class="inline-flex items-center gap-1.5 border border-border-default text-text-secondary hover:text-text-primary hover:bg-surface-raised font-medium px-3 py-1.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <mat-icon class="text-base leading-none" style="font-size:1rem;width:1rem;height:1rem;">{{ link.icon }}</mat-icon>
              {{ link.label }}
            </button>
          }
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class DashboardComponent implements OnInit {
  private reports = inject(ReportsService);
  private router = inject(Router);

  loading = signal(true);
  error = signal(false);
  ar = signal<AgingReport | null>(null);
  ap = signal<AgingReport | null>(null);
  baseCurrency = signal<string>('USD');

  readonly quickLinks = [
    { label: 'Reports', icon: 'bar_chart', route: '/app/reports' },
    { label: 'Invoices', icon: 'receipt', route: '/app/invoices' },
    { label: 'Bills', icon: 'description', route: '/app/bills' },
    { label: 'Inbox', icon: 'inbox', route: '/app/inbox' },
    { label: 'Nous', icon: 'auto_awesome', route: '/app/copilot' },
  ];

  totalAr = computed(() => Number(this.ar()?.total ?? '0') || 0);
  totalAp = computed(() => Number(this.ap()?.total ?? '0') || 0);
  netPosition = computed(() => this.totalAr() - this.totalAp());
  netPositionString = computed(() => this.netPosition().toFixed(2));

  arBuckets = computed<BarChartDatum[]>(() => {
    const d = this.ar();
    if (!d) return [];
    const num = (v: string | undefined) => Number(v ?? '0') || 0;
    return [
      { label: 'Current (0–30)', value: num(d['0_30']), colorClass: 'bg-accent' },
      { label: '31–60 days', value: num(d['31_60']), colorClass: 'bg-confidence-med' },
      { label: '61–90 days', value: num(d['61_90']), colorClass: 'bg-orange-400' },
      { label: 'Over 90 days', value: num(d.over_90), colorClass: 'bg-confidence-low' },
    ];
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(false);
    forkJoin({
      ar: this.reports.getArAging(),
      ap: this.reports.getApAging(),
      ctx: this.reports.getAccountingContext(),
    }).subscribe({
      next: ({ ar, ap, ctx }) => {
        this.ar.set(ar);
        this.ap.set(ap);
        if (ctx?.base_currency) this.baseCurrency.set(ctx.base_currency);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  go(route: string): void {
    this.router.navigate([route]);
  }
}
