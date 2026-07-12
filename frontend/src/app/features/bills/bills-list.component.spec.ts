import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { CurrentPermissionsService } from '../../core/services/current-permissions.service';
import { BillsListComponent, ProcurementDocumentSummary } from './bills-list.component';

describe('BillsListComponent procurement privileges', () => {
  function createComponent(
    privilegeCodes: string[],
    userId = 'user-1',
    legacyRole = 'viewer',
  ): BillsListComponent {
    const privileges = new Set(privilegeCodes);
    TestBed.configureTestingModule({
      imports: [BillsListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { role: signal<string | null>(legacyRole).asReadonly() },
        },
        {
          provide: CurrentPermissionsService,
          useValue: {
            ensureLoaded: jasmine.createSpy('ensureLoaded'),
            hasPrivilege: (code: string) => privileges.has(code),
            userId: signal<string | null>(userId).asReadonly(),
          },
        },
      ],
    });
    return TestBed.createComponent(BillsListComponent).componentInstance;
  }

  function document(requestedBy: string): ProcurementDocumentSummary {
    return {
      id: 'document-1',
      document_type: 'purchase_order',
      document_number: 'PO-0001',
      client_id: 'vendor-1',
      status: 'draft',
      currency: 'USD',
      total: '100.00',
      remaining_total: '100.00',
      requested_by: requestedBy,
    };
  }

  it('does not infer procurement management from a legacy manager role', () => {
    const component = createComponent([], 'user-1', 'manager');

    expect(component.canCreateApDocument()).toBeFalse();
    expect(component.canApproveProcurement()).toBeFalse();
  });

  it('allows a procurement manager to manage and approve another requester document', () => {
    const component = createComponent([
      'procurement.manage',
      'procurement.approve',
    ]);

    expect(component.canCreateApDocument()).toBeTrue();
    expect(component.canApproveProcurementDocument(document('requester-2'))).toBeTrue();
  });

  it('blocks requester self-approval with a clear segregation-of-duties explanation', () => {
    const component = createComponent(['procurement.approve']);
    const ownDocument = document('user-1');

    expect(component.canApproveProcurementDocument(ownDocument)).toBeFalse();
    expect(component.procurementApprovalTooltip(ownDocument)).toContain(
      'requester cannot approve their own',
    );
  });

  it('allows a finance approver to approve another requester without manage access', () => {
    const component = createComponent(['procurement.approve'], 'finance-approver-1', 'approver');

    expect(component.canCreateApDocument()).toBeFalse();
    expect(component.canApproveProcurementDocument(document('requester-1'))).toBeTrue();
  });

  it('keeps viewer procurement mutations unavailable while allowing read-only payments access', () => {
    const component = createComponent(['procurement.read', 'bill_payments.read']);

    expect(component.canCreateApDocument()).toBeFalse();
    expect(component.canApproveProcurementDocument(document('requester-2'))).toBeFalse();
    expect(component.canAccessBillPayments()).toBeTrue();
  });
});
