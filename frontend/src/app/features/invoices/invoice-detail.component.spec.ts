import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, input } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { CurrentPermissionsService } from '../../core/services/current-permissions.service';
import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';
import { InvoiceDetailComponent } from './invoice-detail.component';

@Component({
  selector: 'app-decision-timeline',
  standalone: true,
  template: '',
})
class DecisionTimelineStubComponent {
  entityType = input.required<string>();
  entityId = input.required<string>();
}

describe('InvoiceDetailComponent privileges', () => {
  let fixture: ComponentFixture<InvoiceDetailComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InvoiceDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'invoice-1' }) } },
        },
        {
          provide: CurrentPermissionsService,
          useValue: {
            ensureLoaded: () => undefined,
            hasPrivilege: () => false,
          },
        },
      ],
    })
      .overrideComponent(InvoiceDetailComponent, {
        remove: { imports: [DecisionTimelineComponent] },
        add: { imports: [DecisionTimelineStubComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(InvoiceDetailComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/invoices/invoice-1').flush({
      id: 'invoice-1',
      invoice_number: 'INV-0001',
      engagement_id: 'engagement-1',
      client_id: 'client-1',
      currency: 'USD',
      subtotal: '100.00',
      tax_total: '0.00',
      total: '100.00',
      status: 'draft',
      issue_date: '2026-05-31',
      due_date: '2026-06-30',
      paid_at: null,
      sent_at: null,
      notes: null,
      stripe_payment_link_url: null,
      public_token: 'token',
      lines: [],
    });
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('disables invoice posting when invoices.post is absent', () => {
    const approve = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find(candidate => candidate.textContent?.includes('Approve'));

    expect(approve).toBeDefined();
    expect(approve!.disabled).toBeTrue();
    approve!.click();
    http.expectNone('/api/v1/invoices/invoice-1/approve');
  });
});
