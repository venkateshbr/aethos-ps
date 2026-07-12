import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, input, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { CurrentPermissionsService } from '../../core/services/current-permissions.service';
import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';
import { BillDetailComponent } from './bill-detail.component';

@Component({
  selector: 'app-decision-timeline',
  standalone: true,
  template: '',
})
class DecisionTimelineStubComponent {
  entityType = input.required<string>();
  entityId = input.required<string>();
}

@Component({
  selector: 'app-source-document-link',
  standalone: true,
  template: '',
})
class SourceDocumentLinkStubComponent {
  documentId = input.required<string>();
  label = input<string>();
}

describe('BillDetailComponent privileges', () => {
  let fixture: ComponentFixture<BillDetailComponent>;
  let http: HttpTestingController;
  const privilegeCodes = signal<ReadonlySet<string>>(new Set(['bills.approve']));

  beforeEach(async () => {
    privilegeCodes.set(new Set(['bills.approve']));
    await TestBed.configureTestingModule({
      imports: [BillDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'bill-1' }) } },
        },
        {
          provide: CurrentPermissionsService,
          useValue: {
            ensureLoaded: () => undefined,
            hasPrivilege: (code: string) => privilegeCodes().has(code),
          },
        },
      ],
    })
      .overrideComponent(BillDetailComponent, {
        remove: {
          imports: [SourceDocumentLinkComponent, DecisionTimelineComponent],
        },
        add: {
          imports: [SourceDocumentLinkStubComponent, DecisionTimelineStubComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(BillDetailComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/bills/bill-1').flush({
      id: 'bill-1',
      bill_number: 'BILL-0001',
      vendor_name: 'Ishantech Cloud',
      vendor_id: 'vendor-1',
      currency: 'USD',
      subtotal: '100.00',
      tax_total: '0.00',
      total: '100.00',
      status: 'draft',
      issue_date: '2026-05-31',
      due_date: '2026-06-30',
      lines: [],
    });
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('lets an AP manager attempt approval and keeps draft state after denial', () => {
    const approve = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find(candidate => candidate.textContent?.includes('Approve'));
    expect(approve).toBeDefined();
    expect(approve!.disabled).toBeFalse();

    approve!.click();
    const request = http.expectOne('/api/v1/bills/bill-1/approve');
    expect(request.request.method).toBe('PATCH');
    request.flush(
      { detail: 'Permission required: bills.approve' },
      { status: 403, statusText: 'Forbidden' },
    );
    fixture.detectChanges();

    expect(fixture.componentInstance.bill()!.status).toBe('draft');
    expect(fixture.nativeElement.querySelector('[role="alert"]')).not.toBeNull();
  });

  it('disables bill approval when bills.approve is absent', () => {
    privilegeCodes.set(new Set<string>());
    fixture.detectChanges();
    const approve = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find(candidate => candidate.textContent?.includes('Approve'));

    expect(approve).toBeDefined();
    expect(approve!.disabled).toBeTrue();
    approve!.click();
    http.expectNone('/api/v1/bills/bill-1/approve');
  });
});
