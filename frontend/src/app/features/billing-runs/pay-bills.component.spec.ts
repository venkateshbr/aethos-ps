import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NEVER } from 'rxjs';

import { BillingRunsService } from '../../core/services/billing-runs.service';
import { CurrentPermissionsService } from '../../core/services/current-permissions.service';
import { EngagementService } from '../../core/services/engagement.service';
import { PayBillsComponent } from './pay-bills.component';

describe('PayBillsComponent privileges', () => {
  function createComponent(privilegeCodes: string[]): {
    component: PayBillsComponent;
    billingRuns: jasmine.SpyObj<BillingRunsService>;
  } {
    const privileges = new Set(privilegeCodes);
    const billingRuns = jasmine.createSpyObj<BillingRunsService>('BillingRunsService', [
      'createBatch',
      'approveBatch',
      'exportBatch',
      'markSent',
      'settleBatch',
    ]);
    billingRuns.createBatch.and.returnValue(NEVER);
    billingRuns.approveBatch.and.returnValue(NEVER);
    billingRuns.exportBatch.and.returnValue(NEVER);
    billingRuns.markSent.and.returnValue(NEVER);
    billingRuns.settleBatch.and.returnValue(NEVER);
    TestBed.configureTestingModule({
      imports: [PayBillsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: BillingRunsService, useValue: billingRuns },
        { provide: EngagementService, useValue: {} },
        {
          provide: CurrentPermissionsService,
          useValue: {
            ensureLoaded: jasmine.createSpy('ensureLoaded'),
            hasPrivilege: (code: string) => privileges.has(code),
          },
        },
      ],
    });
    return {
      component: TestBed.createComponent(PayBillsComponent).componentInstance,
      billingRuns,
    };
  }

  it('does not call bill-payment mutations when exact privileges are absent', () => {
    const { component, billingRuns } = createComponent([]);
    component.selectedIds.set(new Set(['bill-1']));
    component.batchId.set('batch-1');
    component.batchStatus.set('approved');
    component.exported.set(true);

    component.createBatch({ selectedIndex: 1 });
    component.approveBatch();
    component.downloadCsv();
    component.markSent({ selectedIndex: 2 });
    component.batchStatus.set('sent_to_bank');
    component.settleBatch();

    expect(billingRuns.createBatch).not.toHaveBeenCalled();
    expect(billingRuns.approveBatch).not.toHaveBeenCalled();
    expect(billingRuns.exportBatch).not.toHaveBeenCalled();
    expect(billingRuns.markSent).not.toHaveBeenCalled();
    expect(billingRuns.settleBatch).not.toHaveBeenCalled();
  });

  it('enables each AP manager action only with its exact privilege and lifecycle state', () => {
    const { component } = createComponent([
      'bill_payments.prepare',
      'bill_payments.approve',
      'bill_payments.export',
      'bill_payments.settle',
    ]);

    expect(component.canPrepare()).toBeTrue();
    expect(component.canApprove()).toBeTrue();
    expect(component.canExport()).toBeFalse();

    component.batchStatus.set('approved');
    expect(component.canExport()).toBeTrue();
    expect(component.canMarkSent()).toBeFalse();

    component.exported.set(true);
    expect(component.canMarkSent()).toBeTrue();

    component.batchStatus.set('sent_to_bank');
    expect(component.canSettle()).toBeTrue();
  });

  it('does not give Finance Approver bill-payment mutation affordances', () => {
    const { component } = createComponent(['procurement.approve']);
    component.batchStatus.set('approved');
    component.exported.set(true);

    expect(component.canPrepare()).toBeFalse();
    expect(component.canApprove()).toBeFalse();
    expect(component.canExport()).toBeFalse();
    expect(component.canMarkSent()).toBeFalse();
  });
});
