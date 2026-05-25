import { Component, inject, signal, OnInit } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';

import { EngagementService, EngagementDetail } from '../../core/services/engagement.service';
import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { ProjectsListComponent } from '../projects/projects-list.component';
import { userMessageForError } from '../../core/utils/error-message';

@Component({
  selector: 'app-engagement-detail',
  standalone: true,
  imports: [
    TitleCasePipe,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MoneyPipe,
    ProjectsListComponent,
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
          </div>
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
            [class]="statusClass(engagement()!.status)"
            [attr.aria-label]="'Status: ' + engagement()!.status"
          >
            <span class="w-1.5 h-1.5 rounded-full" [class]="statusDotClass(engagement()!.status)"></span>
            {{ engagement()!.status | titlecase }}
          </span>
        </div>

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

        <!-- Projects section -->
        <div class="mt-2">
          <h2 class="text-base font-semibold text-text-primary mb-4">Projects</h2>
          <app-projects-list [engagementId]="engagement()!.id" />
        </div>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class EngagementDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private engagementService = inject(EngagementService);

  loading = signal(true);
  error = signal<string | null>(null);
  engagement = signal<EngagementDetail | null>(null);

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
}
