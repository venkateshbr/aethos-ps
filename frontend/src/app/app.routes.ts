import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'app',
    loadComponent: () =>
      import('./shared/shell/shell.component').then(m => m.ShellComponent),
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
      { path: '', redirectTo: 'copilot', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: '' },
];
