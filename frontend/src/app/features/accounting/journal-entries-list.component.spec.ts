import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { JournalEntriesListComponent } from './journal-entries-list.component';

describe('JournalEntriesListComponent close period', () => {
  let fixture: ComponentFixture<JournalEntriesListComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    localStorage.removeItem('aethos_role');
    await TestBed.configureTestingModule({
      imports: [JournalEntriesListComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(JournalEntriesListComponent);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    localStorage.removeItem('aethos_role');
    http.verify();
  });

  it('lets an end user select June and reloads that close checklist', () => {
    const component = fixture.componentInstance;
    component.closePeriod.set('2026-07');
    spyOn(component, 'loadCloseTasks');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({ periods: [] });
    fixture.detectChanges();

    const input = fixture.nativeElement.querySelector(
      'input[aria-label="Close period"]',
    ) as HTMLInputElement | null;
    expect(input).not.toBeNull();
    expect(input?.value).toBe('2026-07');

    input!.value = '2026-06';
    input!.dispatchEvent(new Event('change'));

    expect(component.closePeriod()).toBe('2026-06');
    expect(component.loadCloseTasks).toHaveBeenCalledTimes(2);
  });

  it('shows the selected period lock status with actor and timestamp', () => {
    localStorage.setItem('aethos_role', 'owner');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: true,
          locked_at: '2026-06-30T23:59:00Z',
          locked_by: 'controller-user-1',
        },
      ],
    });
    fixture.detectChanges();

    const status = fixture.nativeElement.querySelector(
      '[aria-label="Period close status"]',
    ) as HTMLElement | null;
    expect(status).not.toBeNull();
    const statusText = status!.textContent?.replace(/\s+/g, ' ').trim();
    expect(statusText).toContain('2026-06');
    expect(statusText).toContain('Locked');
    expect(statusText).toContain('controller-user-1');
    expect(statusText).toContain('2026-06-30 23:59 UTC');
  });

  it('offers an admin the lock action for an open period but never unlock', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: false,
          locked_at: null,
          locked_by: null,
        },
      ],
    });
    fixture.detectChanges();

    expect(buttonWithText('Lock period')).not.toBeNull();
    expect(buttonWithText('Unlock period')).toBeNull();
  });

  it('requires explicit confirmation before unlocking and cancel makes no request', () => {
    localStorage.setItem('aethos_role', 'owner');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: true,
          locked_at: '2026-06-30T23:59:00Z',
          locked_by: 'controller-user-1',
        },
      ],
    });
    fixture.detectChanges();

    buttonWithText('Unlock period')!.click();
    fixture.detectChanges();

    const confirmation = fixture.nativeElement.querySelector('[role="alertdialog"]') as HTMLElement | null;
    expect(confirmation).not.toBeNull();
    const confirmationText = confirmation!.textContent?.replace(/\s+/g, ' ').trim();
    expect(confirmationText).toContain('Unlock 2026-06?');
    expect(confirmationText).toContain('New journal entries can be posted');
    http.expectNone('/api/v1/accounting/periods/2026-06/lock');

    buttonWithText('Cancel')!.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alertdialog"]')).toBeNull();
    http.expectNone('/api/v1/accounting/periods/2026-06/lock');
  });

  it('changes lock state only after the API succeeds and refreshed status confirms it', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: false,
          locked_at: null,
          locked_by: null,
        },
      ],
    });
    fixture.detectChanges();

    buttonWithText('Lock period')!.click();
    fixture.detectChanges();
    buttonWithText('Confirm lock')!.click();
    fixture.detectChanges();

    const lockRequest = http.expectOne('/api/v1/accounting/periods/2026-06/lock');
    expect(lockRequest.request.method).toBe('POST');
    expect(lockRequest.request.body).toEqual({});
    expect(closeStatusText()).toContain('Open');
    expect(closeStatusText()).not.toContain('Locked');

    lockRequest.flush({
      period: '2026-06',
      action: 'locked',
      message: 'Period 2026-06 is now locked.',
      override_count: 0,
    });
    fixture.detectChanges();
    expect(closeStatusText()).not.toContain('Locked');

    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: true,
          locked_at: '2026-07-01T00:01:00Z',
          locked_by: 'admin-user-1',
        },
      ],
    });
    fixture.detectChanges();

    expect(closeStatusText()).toContain('Locked');
    expect(closeStatusText()).toContain('admin-user-1');
    expect(closeStatusText()).toContain('2026-07-01 00:01 UTC');
    expect(buttonWithText('Lock period')).toBeNull();
  });

  it('surfaces lock API blockers and keeps the confirmed period state unchanged', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: false,
          locked_at: null,
          locked_by: null,
        },
      ],
    });
    fixture.detectChanges();

    buttonWithText('Lock period')!.click();
    fixture.detectChanges();
    buttonWithText('Confirm lock')!.click();

    http.expectOne('/api/v1/accounting/periods/2026-06/lock').flush(
      {
        detail: {
          code: 'close_tasks_incomplete',
          period: '2026-06',
          message: 'Complete or waive close tasks before locking the period.',
        },
      },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();

    expect(closeStatusText()).toContain('Open');
    expect(closeStatusText()).not.toContain('Locked');
    expect(buttonWithText('Lock period')).not.toBeNull();
    const alertText = Array.from(
      fixture.nativeElement.querySelectorAll('[role="alert"]') as NodeListOf<HTMLElement>,
    ).map(alert => alert.textContent).join(' ');
    expect(alertText).toContain('Complete or waive close tasks before locking the period.');
    http.expectNone('/api/v1/accounting/periods');
  });

  it('lets an owner explicitly unlock and confirms the open state by refreshing', () => {
    localStorage.setItem('aethos_role', 'owner');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: true,
          locked_at: '2026-06-30T23:59:00Z',
          locked_by: 'controller-user-1',
        },
      ],
    });
    fixture.detectChanges();

    buttonWithText('Unlock period')!.click();
    fixture.detectChanges();
    buttonWithText('Confirm unlock')!.click();

    const unlockRequest = http.expectOne('/api/v1/accounting/periods/2026-06/lock');
    expect(unlockRequest.request.method).toBe('DELETE');
    expect(closeStatusText()).toContain('Locked');

    unlockRequest.flush({
      period: '2026-06',
      action: 'unlocked',
      message: 'Period 2026-06 has been unlocked.',
      override_count: 0,
    });
    fixture.detectChanges();
    expect(closeStatusText()).not.toContain('Open');

    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: false,
          locked_at: null,
          locked_by: null,
        },
      ],
    });
    fixture.detectChanges();

    expect(closeStatusText()).toContain('Open');
    expect(buttonWithText('Unlock period')).toBeNull();
    expect(buttonWithText('Lock period')).not.toBeNull();
  });

  it('shows period status without mutation controls to an unauthorized manager', () => {
    localStorage.setItem('aethos_role', 'manager');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        {
          period: '2026-06',
          locked: false,
          locked_at: null,
          locked_by: null,
        },
      ],
    });
    fixture.detectChanges();

    expect(closeStatusText()).toContain('2026-06');
    expect(closeStatusText()).toContain('Open');
    expect(buttonWithText('Lock period')).toBeNull();
    expect(buttonWithText('Unlock period')).toBeNull();
  });

  it('cancels a pending period confirmation when the selected month changes', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.componentInstance.closePeriod.set('2026-06');

    fixture.detectChanges();
    http.expectOne('/api/v1/accounting/journal-entries').flush([]);
    http.expectOne('/api/v1/accounting/periods/2026-06/close-tasks').flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({
      periods: [
        { period: '2026-05', locked: false, locked_at: null, locked_by: null },
        { period: '2026-06', locked: false, locked_at: null, locked_by: null },
      ],
    });
    fixture.detectChanges();

    buttonWithText('Lock period')!.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alertdialog"]')).not.toBeNull();

    const periodInput = fixture.nativeElement.querySelector(
      'input[aria-label="Close period"]',
    ) as HTMLInputElement;
    periodInput.value = '2026-05';
    periodInput.dispatchEvent(new Event('change'));
    http.expectOne('/api/v1/accounting/periods/2026-05/close-tasks').flush({ tasks: [] });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[role="alertdialog"]')).toBeNull();
    expect(closeStatusText()).toContain('2026-05');
  });

  it('labels close-package working capital as period-end evidence and WIP as an estimate', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.componentInstance.closePeriod.set('2026-06');
    fixture.detectChanges();
    flushInitialPageRequests([]);

    fixture.componentInstance.loadClosePackage();
    http.expectOne('/api/v1/accounting/periods/2026-06/close-package').flush({
      period: '2026-06',
      period_start: '2026-06-01',
      period_end: '2026-06-30',
      previous_period: '2026-05',
      generated_at: '2026-07-12T02:00:00Z',
      close_status: { status: 'ready', ready_to_lock: true, lock_blockers: [] },
      gl_summary: { net_income: '400.00' },
      previous_gl_summary: { net_income: '300.00' },
      working_capital: {
        ar_open_total: '250.00',
        ap_open_total: '100.00',
        wip_total: '350.00',
        base_currency: 'SGD',
        as_of_date: '2026-06-30',
        ar_ap_basis: 'posted_gl_base_currency',
        wip_basis: 'approved_time_period_end_current_rate_estimate',
      },
      readiness_evidence: {},
      close_overrides: [],
      variance_commentary: [],
    });
    fixture.detectChanges();
    http.expectOne(
      '/api/v1/financial-events/business-records/month_end_close/2026-06/decisions',
    ).flush({ items: [] });
    fixture.detectChanges();

    const pageText = fixture.nativeElement.textContent?.replace(/\s+/g, ' ') ?? '';
    expect(pageText).toContain('Period-end AR/AP');
    expect(pageText).toContain('SGD');
    expect(pageText).toContain('SGD base-currency GL · as of 2026-06-30');
    expect(pageText).toContain('Estimated WIP at period end');
    expect(pageText).toContain('Approved time · current rate card · as of 2026-06-30');
  });

  it('shows and submits the verified tenant base currency for a manual journal', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.detectChanges();
    flushInitialPageRequests([]);

    fixture.componentInstance.openForm();
    http.expectOne('/api/v1/accounts').flush([
      { id: 'account-dr', code: '6000', name: 'Software Expense', account_type: 'expense' },
      { id: 'account-cr', code: '1100', name: 'Bank', account_type: 'asset' },
    ]);
    const contextRequest = http.expectOne('/api/v1/tenants/accounting-context');
    expect(contextRequest.request.method).toBe('GET');
    contextRequest.flush({ tenant_id: 'tenant-1', base_currency: 'SGD' });
    fixture.detectChanges();

    const currency = fixture.nativeElement.querySelector(
      'input[aria-label="Manual journal currency"]',
    ) as HTMLInputElement | null;
    expect(currency).not.toBeNull();
    expect(currency!.readOnly).toBeTrue();
    expect(currency!.value).toBe('SGD');
    expect(fixture.nativeElement.textContent).toContain('Verified tenant base currency');

    const component = fixture.componentInstance;
    component.journalForm.patchValue({
      description: 'June software accrual',
      reason: 'Accrue the approved June software invoice before close.',
      entry_date: '2026-06-30',
    });
    component.linesArray.at(0).patchValue({
      account_id: 'account-dr',
      direction: 'DR',
      amount: '100.00',
    });
    component.linesArray.at(1).patchValue({
      account_id: 'account-cr',
      direction: 'CR',
      amount: '100.00',
    });

    component.submitJournal();

    const post = http.expectOne('/api/v1/accounting/journal-entries');
    expect(post.request.body.lines.map((line: { currency: string }) => line.currency)).toEqual([
      'SGD',
      'SGD',
    ]);
    post.flush({
      status: 'pending_approval',
      task_id: 'task-1',
      suggestion_id: 'suggestion-1',
      required_approval_role: 'admin',
      approval_policy_reason: 'manual_journal_above_approval_threshold',
      total_debits: '100.00',
      threshold: '100.00',
      message: 'Manual journal routed to Inbox.',
    });
  });

  it('initializes recurring templates from tenant base but preserves an explicit foreign currency', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.detectChanges();
    flushInitialPageRequests([]);

    const component = fixture.componentInstance;
    component.openRecurringTemplateForm();
    http.expectOne('/api/v1/accounts').flush([]);
    http.expectOne('/api/v1/tenants/accounting-context').flush({
      tenant_id: 'tenant-1',
      base_currency: 'SGD',
    });
    fixture.detectChanges();

    const currency = fixture.nativeElement.querySelector('#rjt-currency') as HTMLInputElement;
    expect(currency.value).toBe('SGD');
    expect(currency.readOnly).toBeFalse();

    component.journalForm.patchValue({
      description: 'Monthly GBP accrual',
      start_period: '2026-07',
      schedule_day: 31,
      currency: 'GBP',
    });
    component.linesArray.at(0).patchValue({
      account_id: 'account-dr',
      direction: 'DR',
      amount: '100.00',
    });
    component.linesArray.at(1).patchValue({
      account_id: 'account-cr',
      direction: 'CR',
      amount: '100.00',
    });

    component.submitRecurringTemplate();

    const post = http.expectOne('/api/v1/accounting/recurring-journal-templates');
    expect(post.request.body.currency).toBe('GBP');
    post.flush({
      id: 'template-1',
      name: 'Monthly GBP accrual',
      schedule_day: 31,
      start_period: '2026-07',
      end_period: null,
      currency: 'GBP',
      is_active: true,
      lines: [],
    });
  });

  it('blocks manual posting when tenant base currency cannot be verified', () => {
    localStorage.setItem('aethos_role', 'admin');
    fixture.detectChanges();
    flushInitialPageRequests([]);

    const component = fixture.componentInstance;
    component.openForm();
    http.expectOne('/api/v1/accounts').flush([]);
    http.expectOne('/api/v1/tenants/accounting-context').flush(
      { detail: 'Tenant base currency is not configured' },
      { status: 503, statusText: 'Service Unavailable' },
    );
    fixture.detectChanges();

    expect(component.tenantBaseCurrency()).toBeNull();
    expect(component.journalForm.controls.currency.value).toBe('');
    expect(fixture.nativeElement.textContent).toContain('Tenant base currency could not be verified');

    component.journalForm.patchValue({
      description: 'June software accrual',
      reason: 'Accrue the approved June software invoice before close.',
      entry_date: '2026-06-30',
    });
    component.linesArray.at(0).patchValue({
      account_id: 'account-dr',
      direction: 'DR',
      amount: '100.00',
    });
    component.linesArray.at(1).patchValue({
      account_id: 'account-cr',
      direction: 'CR',
      amount: '100.00',
    });
    component.submitJournal();

    expect(component.formError()).toContain('must be verified');
    http.expectNone('/api/v1/accounting/journal-entries');
  });

  it('renders independent journal audit detail including actor, accounts, and FX provenance', () => {
    fixture.detectChanges();
    flushInitialPageRequests([
      {
        id: 'journal-1',
        entry_number: 'JE-0001',
        description: 'Foreign receipt',
        reason: 'Independent audit evidence',
        entry_date: '2026-06-25',
        period: '2026-06',
        reference_type: 'payment',
        reference: 'invoice-1',
        created_by: 'controller-user-1',
        posted_by: 'controller-user-1',
        posted_at: '2026-06-25T09:00:00Z',
        total_dr: '100.00',
        lines: [
          {
            id: 'line-dr',
            direction: 'DR',
            account_id: 'account-bank',
            account_code: '1100',
            account_name: 'Bank',
            amount: '100.00',
            currency: 'GBP',
            base_amount: '125.00',
            fx_rate_id: 'fx-rate-1',
            description: 'Receipt',
          },
          {
            id: 'line-cr',
            direction: 'CR',
            account_id: 'account-ar',
            account_code: '1200',
            account_name: 'Accounts Receivable',
            amount: '100.00',
            currency: 'GBP',
            base_amount: '125.00',
            fx_rate_id: 'fx-rate-1',
            description: 'Clear AR',
          },
        ],
      },
    ]);
    fixture.detectChanges();

    const pageText = fixture.nativeElement.textContent?.replace(/\s+/g, ' ') ?? '';
    expect(pageText).toContain('100.00');
    expect(pageText).toContain('controller-user-1');

    const expand = fixture.nativeElement.querySelector(
      'button[aria-label="Expand journal lines"]',
    ) as HTMLButtonElement | null;
    expect(expand).not.toBeNull();
    expand!.click();
    fixture.detectChanges();
    expect(fixture.componentInstance.expandedRow()).toBe('journal-1');
    http.expectOne(
      '/api/v1/financial-events/business-records/journal_entry/journal-1/decisions',
    ).flush({ items: [] });
    http.expectNone('/api/v1/accounting/journal-entries/journal-1');
    fixture.detectChanges();

    const detail = fixture.nativeElement.querySelector(
      'table[aria-label="Journal lines for JE-0001"]',
    ) as HTMLTableElement | null;
    expect(detail).not.toBeNull();
    const detailText = detail!.textContent?.replace(/\s+/g, ' ') ?? '';
    expect(detailText).toContain('1100');
    expect(detailText).toContain('Bank');
    expect(detailText).toContain('1200');
    expect(detailText).toContain('Accounts Receivable');
    expect(detailText).toContain('GBP');
    expect(detailText).toContain('125.00');
    expect(detailText).toContain('fx-rate-1');

    const bankLine = fixture.nativeElement.querySelector(
      '[data-testid="journal-line"][data-account-code="1100"]',
    ) as HTMLElement | null;
    expect(bankLine).not.toBeNull();
    expect(bankLine!.dataset['journalId']).toBe('journal-1');
    expect(bankLine!.dataset['journalLineId']).toBe('line-dr');
    expect(bankLine!.dataset['amount']).toBe('100.00');
    expect(bankLine!.dataset['currency']).toBe('GBP');
    expect(bankLine!.dataset['baseAmount']).toBe('125.00');
    expect(bankLine!.dataset['fxRateId']).toBe('fx-rate-1');
    expect(
      bankLine!.querySelector('[data-testid="journal-line-account-code"]')?.textContent,
    ).toContain('1100');
    expect(
      bankLine!.querySelector('[data-testid="journal-line-base-amount"]')?.textContent,
    ).toContain('125.00');
    expect(
      bankLine!.querySelector('[data-testid="journal-line-fx-rate-id"]')?.textContent,
    ).toContain('fx-rate-1');
  });

  it('does not offer or claim expanded detail when the API returns no lines', () => {
    fixture.detectChanges();
    flushInitialPageRequests([
      {
        id: 'journal-without-lines',
        entry_number: 'JE-0002',
        description: 'Header only',
        entry_date: '2026-06-25',
        period: '2026-06',
        reference_type: 'auto',
        created_by: 'system-user-1',
        posted_by: 'system-user-1',
        posted_at: '2026-06-25T09:00:00Z',
        total_dr: '0.00',
        lines: [],
      },
    ]);
    fixture.detectChanges();

    expect(
      fixture.nativeElement.querySelector('button[aria-label="Expand journal lines"]'),
    ).toBeNull();
    const row = fixture.nativeElement.querySelector('tr[mat-row]') as HTMLElement;
    row.click();
    fixture.detectChanges();
    expect(fixture.componentInstance.expandedRow()).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('No line detail available.');
  });

  function flushInitialPageRequests(entries: unknown[]): void {
    http.expectOne('/api/v1/accounting/journal-entries').flush(entries);
    http.expectOne(request => request.url.includes('/close-tasks')).flush({ tasks: [] });
    http.expectOne('/api/v1/accounting/recurring-journal-templates').flush({ templates: [] });
    http.expectOne('/api/v1/accounting/periods').flush({ periods: [] });
  }

  function buttonWithText(label: string): HTMLButtonElement | null {
    const buttons = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    );
    return buttons.find(button => button.textContent?.includes(label)) ?? null;
  }

  function closeStatusText(): string {
    const status = fixture.nativeElement.querySelector(
      '[aria-label="Period close status"]',
    ) as HTMLElement;
    return status.textContent?.replace(/\s+/g, ' ').trim() ?? '';
  }
});
