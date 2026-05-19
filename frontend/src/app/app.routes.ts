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
          import('./features/projects/projects-list.component').then(m => m.ProjectsListComponent),
      },
      { path: '', redirectTo: 'copilot', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: '' },
];
