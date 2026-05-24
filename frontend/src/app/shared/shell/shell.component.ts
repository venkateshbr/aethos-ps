import { Component, signal, computed, OnInit, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { HttpClient } from '@angular/common/http';
import { ThemePickerComponent } from '../components/theme-picker.component';

interface NavItem {
  label: string;
  icon: string;
  route: string;
}

interface SubscriptionStatus {
  trial_ends_at?: string | null;
  [key: string]: unknown;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatIconModule, ThemePickerComponent],
  template: `
    <div class="flex h-screen bg-surface-base text-text-primary">
      <!-- Sidebar -->
      <nav [class]="sidebarClass()" aria-label="Main navigation">
        <!-- Logo (rotated-square mark + wordmark) -->
        <div class="px-4 py-5 border-b border-border-default flex-none flex items-center gap-2.5">
          <span
            class="lockup-mark inline-block w-3.5 h-3.5 bg-accent rounded-[2px] flex-none"
            aria-hidden="true"
          ></span>
          @if (!collapsed()) {
            <div class="leading-tight">
              <span class="text-lg font-bold tracking-brand text-text-primary block">Aethos</span>
              <span class="text-[10px] uppercase tracking-[0.18em] text-text-muted block -mt-0.5">
                for professional services
              </span>
            </div>
          }
        </div>

        <!-- Trial countdown badge -->
        @if (trialDaysLeft() !== null && trialDaysLeft()! <= 14) {
          <div class="mx-3 mb-2 mt-2 px-3 py-2 bg-confidence-med/10 border border-confidence-med/40 rounded-lg flex-none">
            @if (!collapsed()) {
              <div class="text-xs text-confidence-med font-medium">
                @if (trialDaysLeft()! > 0) {
                  {{ trialDaysLeft() }} days left in trial
                } @else {
                  Trial ended — upgrade to continue
                }
              </div>
            } @else {
              <mat-icon
                class="text-confidence-med"
                style="font-size:1rem;width:1rem;height:1rem;"
                [title]="trialDaysLeft()! > 0 ? trialDaysLeft() + ' days left in trial' : 'Trial ended'"
              >warning</mat-icon>
            }
          </div>
        }

        <!-- Nav items -->
        <div class="flex-1 overflow-y-auto py-3">
          @for (item of navItems; track item.route) {
            <a
              [routerLink]="item.route"
              routerLinkActive="bg-surface-raised text-text-primary"
              class="flex items-center gap-3 px-4 py-2 text-sm text-text-secondary hover:bg-surface-raised hover:text-text-primary rounded mx-2 mb-0.5 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [title]="collapsed() ? item.label : ''"
              [attr.aria-label]="item.label"
            >
              <mat-icon class="text-base leading-none flex-none">{{ item.icon }}</mat-icon>
              @if (!collapsed()) {
                <span>{{ item.label }}</span>
              }
            </a>
          }
        </div>

        <!-- Theme picker — lets the user switch palette at runtime during pilot -->
        <div class="flex-none border-t border-border-default px-3 py-2">
          @if (!collapsed()) {
            <app-theme-picker />
          } @else {
            <app-theme-picker size="compact" />
          }
        </div>

        <!-- Collapse toggle -->
        <div class="flex-none border-t border-border-default py-2">
          <button
            (click)="toggleCollapsed()"
            class="mx-2 p-2 rounded text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors flex items-center gap-2 w-[calc(100%-1rem)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [title]="collapsed() ? 'Expand sidebar' : 'Collapse sidebar'"
            [attr.aria-label]="collapsed() ? 'Expand sidebar' : 'Collapse sidebar'"
            [attr.aria-expanded]="!collapsed()"
          >
            <mat-icon style="font-size:1.1rem;width:1.1rem;height:1.1rem;">
              {{ collapsed() ? 'chevron_right' : 'chevron_left' }}
            </mat-icon>
            @if (!collapsed()) { <span class="text-xs">Collapse</span> }
          </button>
        </div>
      </nav>

      <!-- Main content -->
      <main class="flex-1 overflow-auto">
        <router-outlet />
      </main>
    </div>
  `,
})
export class ShellComponent implements OnInit {
  private http = inject(HttpClient);

  collapsed      = signal(false);
  trialDaysLeft  = signal<number | null>(null);

  /** Toggle the sidebar collapsed state. Wraps the signal update so the
   *  template binding stays a plain method call — Angular template parsers
   *  reject arrow functions in event bindings (NG5002). See bug #107. */
  toggleCollapsed(): void {
    this.collapsed.update((v) => !v);
  }

  sidebarClass = computed(() =>
    `${this.collapsed() ? 'w-14' : 'w-56'} flex-none bg-surface border-r border-border-default flex flex-col relative transition-all duration-200`
  );

  navItems: NavItem[] = [
    { label: 'Copilot',      icon: 'auto_awesome',    route: '/app/copilot' },
    { label: 'Inbox',        icon: 'inbox',           route: '/app/inbox' },
    { label: 'Engagements',  icon: 'work',            route: '/app/engagements' },
    { label: 'Projects',     icon: 'folder',          route: '/app/projects' },
    { label: 'Clients',      icon: 'people',          route: '/app/clients' },
    { label: 'Invoices',     icon: 'receipt',         route: '/app/invoices' },
    { label: 'Billing Runs', icon: 'payments',        route: '/app/billing-runs' },
    { label: 'Expenses',     icon: 'receipt_long',    route: '/app/expenses' },
    { label: 'Time',         icon: 'schedule',        route: '/app/time' },
    { label: 'Payments',     icon: 'account_balance', route: '/app/payments' },
    { label: 'Reports',      icon: 'bar_chart',       route: '/app/reports' },
    { label: 'People',       icon: 'badge',           route: '/app/people' },
    { label: 'Settings',     icon: 'settings',        route: '/app/settings' },
  ];

  ngOnInit(): void {
    this.fetchTrialStatus();
  }

  private fetchTrialStatus(): void {
    this.http.get<SubscriptionStatus>('/api/v1/billing/subscription-status').subscribe({
      next: (res) => {
        if (res.trial_ends_at) {
          const endsAt = new Date(res.trial_ends_at);
          const now    = new Date();
          const diffMs = endsAt.getTime() - now.getTime();
          const days   = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
          // Only surface when ≤ 14 days remain (or expired)
          this.trialDaysLeft.set(Math.max(days, 0));
        }
      },
      error: () => {
        // Silently ignore — the badge is non-critical
      },
    });
  }
}
