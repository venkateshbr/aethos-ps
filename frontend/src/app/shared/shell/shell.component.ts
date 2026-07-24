import { Component, OnInit, inject, signal } from '@angular/core';
import { Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatButtonModule } from '@angular/material/button';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { SupabaseService } from '../../core/services/supabase.service';

interface NavItem {
  label: string;
  icon: string;
  route: string;
}

interface SubscriptionStatus {
  trial_ends_at?: string | null;
  [key: string]: unknown;
}

/**
 * ShellComponent — top-navigation app chrome.
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────────────────┐
 *   │  ◆ Aethos   Nous · Inbox · Docs · Engage · Invoice …       │  ← top nav
 *   ├──────────────────────────────────────────────────────────────┤
 *   │                                                              │
 *   │                  <router-outlet />                           │  ← full-width content
 *   │                                                              │
 *   └──────────────────────────────────────────────────────────────┘
 *
 * Primary nav items are always visible in the bar.
 * Secondary items live in a "More ▾" Mat menu.
 * Settings sits at the far right.
 *
 * Theme note: all surfaces use `bg-surface-base` (the darkest token) to
 * exactly match the login / signup pages — there's no sidebar with a
 * contrasting bg, so the app interior looks the same shade as the auth
 * shell.
 */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatIconModule, MatMenuModule, MatButtonModule],
  template: `
    <div class="flex flex-col h-screen bg-surface-base text-text-primary">

      <!-- ── Top navigation bar ───────────────────────────────────── -->
      <header class="flex-none bg-surface-base border-b border-border-default">
        <div class="flex items-center gap-1 px-4 h-14">

          <!-- Logo mark + wordmark -->
          <a routerLink="/app/copilot"
             class="flex items-center gap-2 mr-4 flex-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
             aria-label="Aethos - go to Nous">
            <span class="lockup-mark inline-block w-4 h-4 bg-accent rounded-[2.5px] flex-none" aria-hidden="true"></span>
            <span class="text-sm font-bold tracking-wide text-text-primary hidden sm:block">Aethos</span>
          </a>

          <nav aria-label="Main navigation" class="flex items-center gap-1 min-w-0">
            <!-- Primary nav items -->
            @for (item of primaryNav; track item.route) {
              <a
                [routerLink]="item.route"
                routerLinkActive="bg-surface-raised text-text-primary"
                class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-raised hover:text-text-primary rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent whitespace-nowrap"
                [attr.aria-label]="item.label"
              >
                <mat-icon class="text-sm leading-none flex-none" style="font-size:1rem;width:1rem;height:1rem;">{{ item.icon }}</mat-icon>
                <span class="hidden md:inline">{{ item.label }}</span>
              </a>
            }

            <!-- "More ▾" overflow menu for secondary nav items -->
            <button
              [matMenuTriggerFor]="moreMenu"
              class="flex items-center gap-1 px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-raised hover:text-text-primary rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              aria-label="More navigation items"
            >
              <span class="hidden sm:inline text-sm">More</span>
              <mat-icon style="font-size:1rem;width:1rem;height:1rem;">expand_more</mat-icon>
            </button>
          </nav>

          <mat-menu #moreMenu="matMenu" class="!bg-surface-raised">
            @for (item of secondaryNav; track item.route) {
              <a
                mat-menu-item
                [routerLink]="item.route"
                class="flex items-center gap-2 text-text-secondary hover:text-text-primary"
              >
                <mat-icon class="text-base flex-none text-text-muted">{{ item.icon }}</mat-icon>
                <span>{{ item.label }}</span>
              </a>
            }
          </mat-menu>

          <!-- Spacer -->
          <div class="flex-1"></div>

          <!-- Trial badge -->
          @if (trialDaysLeft() !== null && trialDaysLeft()! <= 14) {
            <div class="hidden sm:flex items-center gap-1 px-3 py-1 rounded-full bg-confidence-med/10 border border-confidence-med/40 mr-2">
              <mat-icon class="text-confidence-med" style="font-size:0.875rem;width:0.875rem;height:0.875rem;">schedule</mat-icon>
              <span class="text-xs text-confidence-med font-medium whitespace-nowrap">
                @if (trialDaysLeft()! > 0) {
                  {{ trialDaysLeft() }}d left
                } @else {
                  Trial ended
                }
              </span>
            </div>
          }

          <!-- User menu — profile + settings + logout -->
          <button
            [matMenuTriggerFor]="userMenu"
            class="flex items-center justify-center w-8 h-8 text-text-secondary hover:bg-surface-raised hover:text-text-primary rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            aria-label="Account menu"
            title="Account"
          >
            <mat-icon style="font-size:1.2rem;width:1.2rem;height:1.2rem;">account_circle</mat-icon>
          </button>

          <mat-menu #userMenu="matMenu">
            <a mat-menu-item [routerLink]="'/app/profile'" class="flex items-center gap-2 text-text-secondary hover:text-text-primary">
              <mat-icon class="text-base flex-none text-text-muted">manage_accounts</mat-icon>
              <span>Profile</span>
            </a>
            <a mat-menu-item [routerLink]="'/app/settings'" class="flex items-center gap-2 text-text-secondary hover:text-text-primary">
              <mat-icon class="text-base flex-none text-text-muted">settings</mat-icon>
              <span>Settings</span>
            </a>
            <div class="border-t border-border-default my-1"></div>
            <button mat-menu-item (click)="logout()" class="flex items-center gap-2 text-confidence-low hover:text-confidence-low w-full">
              <mat-icon class="text-base flex-none text-confidence-low">logout</mat-icon>
              <span>Sign out</span>
            </button>
          </mat-menu>

        </div>
      </header>

      <!-- ── Page content ─────────────────────────────────────────── -->
      <main class="flex-1 overflow-auto bg-surface-base">
        <router-outlet />
      </main>

    </div>
  `,
  styles: [`
    /* Override Material menu panel background to match our theme */
    ::ng-deep .mat-mdc-menu-panel {
      background-color: rgb(var(--t-bg-surface-raised)) !important;
      border: 1px solid rgb(var(--t-border-default)) !important;
    }
    ::ng-deep .mat-mdc-menu-item {
      color: rgb(var(--t-text-secondary)) !important;
    }
    ::ng-deep .mat-mdc-menu-item:hover {
      background-color: rgb(var(--t-bg-surface)) !important;
      color: rgb(var(--t-text-primary)) !important;
    }
    ::ng-deep .mat-mdc-menu-item .mat-icon {
      color: rgb(var(--t-text-muted)) !important;
    }
  `],
})
export class ShellComponent implements OnInit {
  private http  = inject(HttpClient);
  private auth  = inject(AuthService);
  private supa  = inject(SupabaseService);
  private router = inject(Router);
  trialDaysLeft = signal<number | null>(null);

  async logout() {
    await this.supa.client.auth.signOut().catch(() => {});
    this.auth.clearToken();
    this.router.navigate(['/login']);
  }

  /** Primary nav — always visible in the top bar (with icon + label on ≥md) */
  readonly primaryNav: NavItem[] = [
    { label: 'Dashboard',  icon: 'dashboard',    route: '/app/dashboard' },
    { label: 'Nous',       icon: 'auto_awesome', route: '/app/copilot' },
    { label: 'Documents',   icon: 'upload_file',  route: '/app/documents' },
    { label: 'Inbox',       icon: 'inbox',        route: '/app/inbox' },
    { label: 'Engagements', icon: 'work',         route: '/app/engagements' },
    { label: 'Projects',    icon: 'folder_open',  route: '/app/projects' },
    { label: 'Invoices',    icon: 'receipt',      route: '/app/invoices' },
    { label: 'Reports',     icon: 'bar_chart',    route: '/app/reports' },
  ];

  /** Secondary nav — behind the "More" overflow menu */
  readonly secondaryNav: NavItem[] = [
    { label: 'Contacts',       icon: 'people',          route: '/app/clients' },
    { label: 'Expenses',       icon: 'receipt_long',    route: '/app/expenses' },
    { label: 'Bills',          icon: 'description',     route: '/app/bills' },
    { label: 'Billing Runs',   icon: 'payments',        route: '/app/billing-runs' },
    { label: 'Time',           icon: 'schedule',        route: '/app/time' },
    { label: 'Approvals',      icon: 'fact_check',      route: '/app/approvals' },
    { label: 'Payments',       icon: 'account_balance', route: '/app/payments' },
    { label: 'People',         icon: 'badge',           route: '/app/people' },
    // ── Accounting section (#208) ──────────────────────────────────────
    { label: 'Journal Entries', icon: 'menu_book',      route: '/app/accounting/journals' },
  ];

  ngOnInit(): void {
    this.http.get<SubscriptionStatus>('/api/v1/billing/subscription-status').subscribe({
      next: (res) => {
        if (res.trial_ends_at) {
          const endsAt = new Date(res.trial_ends_at);
          const diffMs = endsAt.getTime() - Date.now();
          this.trialDaysLeft.set(Math.max(0, Math.ceil(diffMs / 86_400_000)));
        }
      },
      error: () => { /* non-critical — badge is cosmetic */ },
    });
  }
}
