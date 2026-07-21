import { Routes } from '@angular/router';
import { authGuard, passwordReadyGuard } from './core/auth';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'change-password',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/change-password/change-password.component').then(
        (m) => m.ChangePasswordComponent,
      ),
  },
  {
    path: 'timesheet',
    canActivate: [passwordReadyGuard],
    loadComponent: () =>
      import('./features/timesheet/timesheet.component').then((m) => m.TimesheetComponent),
  },
  { path: '', redirectTo: 'timesheet', pathMatch: 'full' },
  { path: '**', redirectTo: 'timesheet' },
];
