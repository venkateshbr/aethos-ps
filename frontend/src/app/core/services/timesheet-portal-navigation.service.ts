import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';

import { timesheetPortalLoginUrl } from '../utils/timesheet-portal-url';

/** Browser boundary for leaving the ERP origin and opening the employee portal. */
@Injectable({ providedIn: 'root' })
export class TimesheetPortalNavigationService {
  private document = inject(DOCUMENT);

  redirectToLogin(): void {
    this.document.location.assign(timesheetPortalLoginUrl());
  }
}
