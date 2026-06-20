import { Routes } from '@angular/router';
import { authGuard, authChildGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  // ── Public routes — no app shell, no auth ───────────────────────────────────
  {
    path: '',
    loadComponent: () =>
      import('./features/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    // Public invoice view — accessed by clients, no auth required.
    path: 'p/:token',
    loadComponent: () =>
      import('./features/public-invoice/public-invoice.component').then(m => m.PublicInvoiceComponent),
  },
  {
    // #115 — signup flow (multi-step: account → plan → card).
    path: 'signup',
    loadComponent: () =>
      import('./features/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    // #119 — login for returning users (Supabase signInWithPassword).
    path: 'login',
    loadComponent: () =>
      import('./features/login/login.component').then(m => m.LoginComponent),
  },

  // ── App shell — authenticated routes ────────────────────────────────────────
  // Guarded by authGuard (parent) + authChildGuard (child re-check) per #111.
  // Unauthenticated visitors are redirected to `/` with `?returnUrl=` set.
  {
    path: 'app',
    loadComponent: () =>
      import('./shared/shell/shell.component').then(m => m.ShellComponent),
    canActivate: [authGuard],
    canActivateChild: [authChildGuard],
    children: [
      {
        path: 'copilot',
        loadComponent: () =>
          import('./features/copilot/copilot.component').then(m => m.CopilotComponent),
      },
      {
        path: 'inbox',
        loadComponent: () =>
          import('./features/inbox/inbox.component').then(m => m.InboxComponent),
      },
      {
        path: 'engagements',
        loadComponent: () =>
          import('./features/engagements/engagements-list.component').then(m => m.EngagementsListComponent),
      },
      {
        path: 'engagements/:id',
        loadComponent: () =>
          import('./features/engagements/engagement-detail.component').then(m => m.EngagementDetailComponent),
      },
      {
        path: 'projects',
        loadComponent: () =>
          import('./features/projects/projects-standalone.component').then(m => m.ProjectsStandaloneComponent),
      },
      {
        path: 'invoices',
        loadComponent: () =>
          import('./features/invoices/invoices-list.component').then(m => m.InvoicesListComponent),
      },
      {
        path: 'invoices/:id',
        loadComponent: () =>
          import('./features/invoices/invoice-detail.component').then(m => m.InvoiceDetailComponent),
      },
      {
        // #112 — without this route, the Clients sidebar link hit the `**`
        // wildcard and redirected to '/'. Placeholder until the full Clients
        // CRUD ships.
        path: 'clients',
        loadComponent: () =>
          import('./features/clients/clients-list.component').then(m => m.ClientsListComponent),
      },
      {
        // #212 — contact detail and edit page.
        path: 'clients/:id',
        loadComponent: () =>
          import('./features/clients/client-detail.component').then(m => m.ClientDetailComponent),
      },
      {
        // #112 — placeholder, see comment on /clients above.
        path: 'payments',
        loadComponent: () =>
          import('./features/payments/payments-list.component').then(m => m.PaymentsListComponent),
      },
      {
        // #112 — placeholder, see comment on /clients above.
        path: 'people',
        loadComponent: () =>
          import('./features/people/people-list.component').then(m => m.PeopleListComponent),
      },
      {
        path: 'time',
        loadComponent: () =>
          import('./features/time-entries/time-entries-list.component').then(m => m.TimeEntriesListComponent),
      },
      {
        path: 'expenses',
        loadComponent: () =>
          import('./features/expenses/expenses-list.component').then(m => m.ExpensesListComponent),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./features/settings/settings.component').then(m => m.SettingsComponent),
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./features/profile/profile.component').then(m => m.ProfileComponent),
      },
      {
        path: 'reports',
        loadComponent: () =>
          import('./features/reports/reports.component').then(m => m.ReportsComponent),
      },
      {
        // #134 — manager timesheet approval queue.
        path: 'approvals',
        loadComponent: () =>
          import('./features/approvals/approvals.component').then(m => m.ApprovalsComponent),
      },
      {
        path: 'bills',
        loadComponent: () =>
          import('./features/bills/bills-list.component').then(m => m.BillsListComponent),
      },
      {
        path: 'bills/:id',
        loadComponent: () =>
          import('./features/bills/bill-detail.component').then(m => m.BillDetailComponent),
      },
      {
        path: 'billing-runs',
        loadComponent: () =>
          import('./features/billing-runs/pay-bills.component').then(m => m.PayBillsComponent),
      },
      {
        path: 'documents',
        loadComponent: () =>
          import('./features/documents/documents-list.component').then(m => m.DocumentsListComponent),
      },
      {
        // #208 — Manual Journal Entry UI (Accounting section)
        path: 'accounting/journals',
        loadComponent: () =>
          import('./features/accounting/journal-entries-list.component').then(m => m.JournalEntriesListComponent),
      },
      { path: '', redirectTo: 'copilot', pathMatch: 'full' },
    ],
  },

  { path: '**', redirectTo: '' },
];
