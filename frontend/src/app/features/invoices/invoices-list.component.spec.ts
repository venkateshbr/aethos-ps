import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CurrentPermissionsService } from '../../core/services/current-permissions.service';
import { InvoiceSummary, InvoicesListComponent } from './invoices-list.component';

describe('InvoicesListComponent receipts', () => {
  let fixture: ComponentFixture<InvoicesListComponent>;
  let http: HttpTestingController;
  const privilegeCodes = signal<ReadonlySet<string>>(
    new Set<string>(['invoices.mark_paid']),
  );
  const permissions = {
    ensureLoaded: () => undefined,
    hasPrivilege: (code: string) => privilegeCodes().has(code),
  };

  const invoice: InvoiceSummary = {
    id: '11111111-1111-1111-1111-111111111111',
    invoice_number: 'INV-ISH-006',
    client_name: 'Ishantech Merlion Health',
    status: 'sent',
    currency: 'SGD',
    total_amount: '19620.00',
    issue_date: '2026-05-31',
    due_date: '2026-06-30',
  };

  beforeEach(async () => {
    privilegeCodes.set(new Set<string>(['invoices.mark_paid']));
    await TestBed.configureTestingModule({
      imports: [InvoicesListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: CurrentPermissionsService, useValue: permissions },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(InvoicesListComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/invoices').flush([invoice]);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('enables the receipt action for an AR manager with invoices.mark_paid', () => {
    const button = fixture.nativeElement.querySelector(
      '[aria-label="Mark invoice INV-ISH-006 paid"]',
    ) as HTMLButtonElement | null;

    expect(button).not.toBeNull();
    expect(button!.disabled).toBeFalse();
  });

  it('enables draft, post, and send for a billing specialist privileges', () => {
    privilegeCodes.set(new Set([
      'invoices.draft',
      'invoices.post',
      'invoices.send',
    ]));
    fixture.componentInstance.invoices.set([
      { ...invoice, id: 'draft-id', invoice_number: 'INV-DRAFT', status: 'draft' },
      { ...invoice, id: 'approved-id', invoice_number: 'INV-APPROVED', status: 'approved' },
    ]);
    fixture.detectChanges();

    const newInvoice = fixture.nativeElement.querySelector(
      '[aria-label="Create new invoice — go to Engagements to draft"]',
    ) as HTMLButtonElement;
    const approve = fixture.nativeElement.querySelector(
      '[aria-label="Approve invoice INV-DRAFT"]',
    ) as HTMLButtonElement;
    const send = fixture.nativeElement.querySelector(
      '[aria-label="Send invoice INV-APPROVED"]',
    ) as HTMLButtonElement;

    expect(newInvoice.disabled).toBeFalse();
    expect(approve.disabled).toBeFalse();
    expect(send.disabled).toBeFalse();
  });

  it('keeps a draft invoice unchanged and shows an alert when posting is denied', () => {
    privilegeCodes.set(new Set(['invoices.post']));
    const draft = {
      ...invoice,
      id: 'draft-id',
      invoice_number: 'INV-DRAFT',
      status: 'draft',
    };
    fixture.componentInstance.invoices.set([draft]);
    fixture.detectChanges();

    fixture.componentInstance.approveInvoice(draft);
    const request = http.expectOne('/api/v1/invoices/draft-id/approve');
    expect(request.request.method).toBe('PATCH');
    request.flush(
      { detail: 'Permission required: invoices.post' },
      { status: 403, statusText: 'Forbidden' },
    );
    fixture.detectChanges();

    expect(fixture.componentInstance.invoices()[0].status).toBe('draft');
    const alert = fixture.nativeElement.querySelector('[role="alert"]') as HTMLElement | null;
    expect(alert).not.toBeNull();
    expect(alert!.textContent).toContain('Permission required');
  });

  it('disables money actions when the current role has no invoice privileges', () => {
    privilegeCodes.set(new Set<string>());
    fixture.componentInstance.invoices.set([
      { ...invoice, id: 'draft-id', invoice_number: 'INV-DRAFT', status: 'draft' },
      { ...invoice, id: 'approved-id', invoice_number: 'INV-APPROVED', status: 'approved' },
      invoice,
    ]);
    fixture.detectChanges();

    for (const selector of [
      '[aria-label="Create new invoice — go to Engagements to draft"]',
      '[aria-label="Approve invoice INV-DRAFT"]',
      '[aria-label="Send invoice INV-APPROVED"]',
      '[aria-label="Mark invoice INV-ISH-006 paid"]',
    ]) {
      const control = fixture.nativeElement.querySelector(selector) as HTMLButtonElement | null;
      expect(control).withContext(selector).not.toBeNull();
      expect(control!.disabled).withContext(selector).toBeTrue();
    }

    fixture.componentInstance.approveInvoice(
      fixture.componentInstance.invoices()[0],
    );
    http.expectNone('/api/v1/invoices/draft-id/approve');
  });

  it('renders the client name in the invoice row', () => {
    const clientCell = fixture.nativeElement.querySelector(
      'tbody tr td.mat-column-client_name',
    ) as HTMLElement | null;
    expect(clientCell).not.toBeNull();
    expect(clientCell!.textContent).toContain('Ishantech Merlion Health');
  });

  it('shows a "No client" fallback when the invoice has no client name', () => {
    fixture.componentInstance.invoices.set([{ ...invoice, client_name: null }]);
    fixture.detectChanges();
    const clientCell = fixture.nativeElement.querySelector(
      'tbody tr td.mat-column-client_name',
    ) as HTMLElement;
    expect(clientCell.textContent).toContain('No client');
    expect(clientCell.querySelector('[aria-label="No client on this invoice"]')).not.toBeNull();
  });

  it('truncates a long client name but keeps the full value in a title tooltip', () => {
    const longName = 'Ishantech Global Advisory Consolidated Holdings and Partners International LLP';
    fixture.componentInstance.invoices.set([{ ...invoice, client_name: longName }]);
    fixture.detectChanges();
    const span = fixture.nativeElement.querySelector(
      'tbody tr td.mat-column-client_name span',
    ) as HTMLElement;
    expect(span.classList).toContain('truncate');
    expect(span.getAttribute('title')).toBe(longName);
  });

  it('keeps a partially settled invoice open when the receipt response remains sent', () => {
    const component = fixture.componentInstance;
    component.openMarkPaid(invoice);
    component.payAmount = '10000.00';
    component.payDate = '2026-05-31';
    component.payNotes = 'ISH-E2E partial receipt';

    component.submitMarkPaid();

    const request = http.expectOne(`/api/v1/invoices/${invoice.id}/payments`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body.amount).toBe('10000.00');
    request.flush({ status: 'sent' });
    fixture.detectChanges();

    expect(component.invoices()[0].status).toBe('sent');
    const row = fixture.nativeElement.querySelector('tbody tr') as HTMLElement;
    expect(row.textContent).toContain('Sent');
    expect(row.textContent).not.toContain('Paid');
    expect(row.querySelector('[aria-label="Mark invoice INV-ISH-006 paid"]')).not.toBeNull();
  });
});
