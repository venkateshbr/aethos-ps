import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EMPTY } from 'rxjs';

import { ReportsService } from '../../core/services/reports.service';
import { ReportsComponent } from './reports.component';

describe('ReportsComponent statement periods', () => {
  let fixture: ComponentFixture<ReportsComponent>;
  let service: jasmine.SpyObj<ReportsService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj<ReportsService>('ReportsService', [
      'getBalanceSheet',
      'getRetainedEarningsRollForward',
      'getIncomeStatement',
      'getCashFlow',
      'getStatutoryPack',
    ]);
    service.getBalanceSheet.and.returnValue(EMPTY);
    service.getRetainedEarningsRollForward.and.returnValue(EMPTY);
    service.getIncomeStatement.and.returnValue(EMPTY);
    service.getCashFlow.and.returnValue(EMPTY);
    service.getStatutoryPack.and.returnValue(EMPTY);

    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [{ provide: ReportsService, useValue: service }],
    }).compileComponents();

    fixture = TestBed.createComponent(ReportsComponent);
  });

  it('uses a Q2 range for ranged statements and the quarter end for as-of statements', () => {
    fixture.componentInstance.statementPeriodStart = '2026-04';
    fixture.componentInstance.statementPeriodEnd = '2026-06';

    fixture.componentInstance.loadFinancialStatements();

    expect(service.getIncomeStatement).toHaveBeenCalledOnceWith('2026-04', '2026-06');
    expect(service.getCashFlow).toHaveBeenCalledOnceWith('2026-04', '2026-06');
    expect(service.getStatutoryPack).toHaveBeenCalledOnceWith('2026-04', '2026-06');
    expect(service.getBalanceSheet).toHaveBeenCalledOnceWith('2026-06');
    expect(service.getRetainedEarningsRollForward).toHaveBeenCalledOnceWith('2026-06');
  });

  it('blocks a reversed range before any financial statement request', () => {
    fixture.componentInstance.statementPeriodStart = '2026-06';
    fixture.componentInstance.statementPeriodEnd = '2026-04';

    fixture.componentInstance.loadFinancialStatements();

    expect(fixture.componentInstance.statementPeriodValidationError()).toBe(
      'End period must be the same as or after the start period.',
    );
    expect(service.getIncomeStatement).not.toHaveBeenCalled();
    expect(service.getCashFlow).not.toHaveBeenCalled();
    expect(service.getStatutoryPack).not.toHaveBeenCalled();
    expect(service.getBalanceSheet).not.toHaveBeenCalled();
    expect(service.getRetainedEarningsRollForward).not.toHaveBeenCalled();
  });
});
