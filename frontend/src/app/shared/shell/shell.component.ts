import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';

interface NavItem {
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatIconModule],
  template: `
    <div class="flex h-screen bg-slate-900 text-slate-100">
      <!-- Sidebar -->
      <nav class="w-56 flex-none bg-slate-800 border-r border-slate-700 flex flex-col">
        <!-- Logo -->
        <div class="px-4 py-5 border-b border-slate-700">
          <span class="text-lg font-semibold tracking-tight text-white">Aethos</span>
          <span class="text-xs text-slate-400 block mt-0.5">for professional services</span>
        </div>
        <!-- Nav items -->
        <div class="flex-1 overflow-y-auto py-3">
          @for (item of navItems; track item.route) {
            <a
              [routerLink]="item.route"
              routerLinkActive="bg-slate-700 text-white"
              class="flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded mx-2 mb-0.5 transition-colors"
            >
              <mat-icon class="text-base leading-none">{{ item.icon }}</mat-icon>
              {{ item.label }}
            </a>
          }
        </div>
      </nav>
      <!-- Main content -->
      <main class="flex-1 overflow-auto">
        <router-outlet />
      </main>
    </div>
  `,
})
export class ShellComponent {
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
}
