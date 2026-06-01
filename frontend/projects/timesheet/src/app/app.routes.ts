import { Routes } from '@angular/router';
import { authGuard } from './core/auth';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'timesheet',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/timesheet/timesheet.component').then((m) => m.TimesheetComponent),
  },
  { path: '', redirectTo: 'timesheet', pathMatch: 'full' },
  { path: '**', redirectTo: 'timesheet' },
];
