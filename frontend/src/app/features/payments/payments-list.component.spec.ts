import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { PaymentsListComponent } from './payments-list.component';

const PAYMENT = {
  id: 'pay-1',
  invoice_id: 'inv-1',
  invoice_number: 'INV-ISH-001',
  amount: '1000.00',
  currency: 'USD',
  base_amount: '1000.00',
  paid_at: '2026-06-30T00:00:00Z',
  notes: 'Wire',
};

describe('PaymentsListComponent write actions', () => {
  let fixture: ComponentFixture<PaymentsListComponent>;
  let http: HttpTestingController;
  const role = signal<string | null>('admin');

  async function setup(roleValue: string | null = 'admin'): Promise<void> {
    role.set(roleValue);
    await TestBed.configureTestingModule({
      imports: [PaymentsListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthService, useValue: { role: role.asReadonly() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PaymentsListComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/payments').flush({ items: [PAYMENT] });
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  it('shows the Reconcile Stripe action to an admin', async () => {
    await setup('admin');
    const btn = fixture.nativeElement.querySelector(
      '[aria-label="Reconcile Stripe payments"]',
    ) as HTMLButtonElement | null;
    expect(btn).not.toBeNull();
  });

  it('hides the Reconcile Stripe action from a non-admin role', async () => {
    await setup('member');
    const btn = fixture.nativeElement.querySelector('[aria-label="Reconcile Stripe payments"]');
    expect(btn).toBeNull();
  });

  it('reconciles Stripe payments and reports the result', async () => {
    await setup('admin');
    const done = fixture.componentInstance['reconcileStripe']();

    const req = http.expectOne('/api/v1/payments/reconcile-stripe');
    expect(req.request.method).toBe('POST');
    req.flush({ reconciled: 2, skipped: 1, errors: 0 });

    // POST resolution schedules the list reload on a microtask.
    await fixture.whenStable();
    http.expectOne('/api/v1/payments').flush({ items: [PAYMENT] });
    await done;
    fixture.detectChanges();

    const status = fixture.nativeElement.querySelector('[role="status"]') as HTMLElement;
    expect(status.textContent).toContain('2 reconciled');
    expect(status.textContent).toContain('1 skipped');
  });

  it('navigates to invoices to record a payment', async () => {
    await setup('admin');
    const router = TestBed.inject(Router);
    const spy = spyOn(router, 'navigate');
    (fixture.nativeElement.querySelector(
      '[aria-label="Record a payment against an invoice"]',
    ) as HTMLButtonElement).click();
    expect(spy).toHaveBeenCalledWith(['/app/invoices']);
  });
});
