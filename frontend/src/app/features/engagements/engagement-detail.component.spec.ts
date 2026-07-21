import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, input, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';
import { SourceDocumentLinkComponent } from '../../shared/components/source-document-link.component';
import { ProjectsListComponent } from '../projects/projects-list.component';
import { CurrentPermissionsService } from '../../core/services/current-permissions.service';
import { EngagementDetailComponent } from './engagement-detail.component';

@Component({
  selector: 'app-projects-list',
  standalone: true,
  template: '',
})
class ProjectsListStubComponent {
  engagementId = input<string>();
}

@Component({
  selector: 'app-source-document-link',
  standalone: true,
  template: '',
})
class SourceDocumentLinkStubComponent {
  documentId = input.required<string>();
}

@Component({
  selector: 'app-decision-timeline',
  standalone: true,
  template: '',
})
class DecisionTimelineStubComponent {
  entityType = input.required<string>();
  entityId = input.required<string>();
}

describe('EngagementDetailComponent invoice drawer', () => {
  let fixture: ComponentFixture<EngagementDetailComponent>;
  let http: HttpTestingController;

  const engagementId = '11111111-1111-1111-1111-111111111111';
  const projectId = '22222222-2222-2222-2222-222222222222';
  const employeeId = '33333333-3333-3333-3333-333333333333';
  const privilegeCodes = signal<ReadonlySet<string>>(new Set(['invoices.draft']));

  beforeEach(async () => {
    privilegeCodes.set(new Set(['invoices.draft']));
    await TestBed.configureTestingModule({
      imports: [EngagementDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: engagementId }) } },
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
      .overrideComponent(EngagementDetailComponent, {
        remove: {
          imports: [
            ProjectsListComponent,
            SourceDocumentLinkComponent,
            DecisionTimelineComponent,
          ],
        },
        add: {
          imports: [
            ProjectsListStubComponent,
            SourceDocumentLinkStubComponent,
            DecisionTimelineStubComponent,
          ],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(EngagementDetailComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    http.expectOne(`/api/v1/engagements/${engagementId}`).flush({
      id: engagementId,
      client_id: '44444444-4444-4444-4444-444444444444',
      client_name: 'Ishantech Merlion Health',
      name: 'ERP Readiness Review',
      billing_arrangement: 'time_and_materials',
      currency: 'SGD',
      total_value: '20000.00',
      status: 'active',
      start_date: '2026-05-01',
      end_date: '2026-06-30',
      service_catalogue_id: '55555555-5555-5555-5555-555555555555',
      created_at: '2026-05-01T00:00:00Z',
    });
    http.expectOne(`/api/v1/engagements/${engagementId}/summary`).flush({
      engagement_id: engagementId,
      engagement_name: 'ERP Readiness Review',
      total_value: '20000.00',
      currency: 'SGD',
      billed_to_date: '0.00',
      billed_pct: 0,
      wip_hours: 2,
      wip_value: '400.00',
      remaining_value: '20000.00',
      invoice_count: 0,
      last_invoice_date: null,
    });
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('disables invoice drafting without invoices.draft', () => {
    privilegeCodes.set(new Set<string>());
    fixture.detectChanges();

    const button = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find(candidate => candidate.textContent?.includes('Draft invoice'));
    expect(button).toBeDefined();
    expect(button!.disabled).toBeTrue();
  });

  it('keeps loading unbilled time when tax rates fail to load', async () => {
    clickButton('Draft invoice');

    http.expectOne(`/api/v1/projects?engagement_id=${engagementId}`).flush([
      { id: projectId, name: 'Discovery', code: 'PRJ-001' },
    ]);
    await fixture.whenStable();

    http.expectOne('/api/v1/employees').flush({
      items: [
        {
          id: employeeId,
          first_name: 'Isha',
          last_name: 'Tan',
          default_bill_rate: '200.00',
        },
      ],
    });
    await fixture.whenStable();

    http.expectOne('/api/v1/billing/profile').flush({ country: 'SG' });
    http.expectOne('/api/v1/tax-rates').flush(
      { detail: 'Tax service unavailable' },
      { status: 503, statusText: 'Service Unavailable' },
    );
    await fixture.whenStable();

    http.expectOne(`/api/v1/projects/${projectId}/assignments`).flush({ items: [] });
    await fixture.whenStable();
    http.expectOne(`/api/v1/time-entries?project_id=${projectId}&billing_status=unbilled`).flush({
      items: [
        {
          id: '66666666-6666-6666-6666-666666666666',
          project_id: projectId,
          employee_id: employeeId,
          date: '2026-05-15',
          hours: '2.00',
          description: 'Discovery workshop',
          billing_status: 'unbilled',
        },
      ],
    });
    await fixture.whenStable();
    fixture.detectChanges();

    const dialog = fixture.nativeElement.querySelector('[role="dialog"]') as HTMLElement;
    expect(dialog.textContent).toContain('Discovery workshop');
    expect(dialog.textContent).toContain('Could not load tax rates');
    expect(dialog.textContent).not.toContain('Could not load unbilled time entries');
  });

  it('shows tenant-market system rates and identifies system and custom options', async () => {
    clickButton('Draft invoice');

    http.expectOne('/api/v1/tax-rates').flush([
      {
        id: 'tax-uk',
        name: 'VAT Standard',
        rate: '20.00',
        market: 'UK',
        is_system: true,
        is_active: true,
      },
      {
        id: 'tax-sg',
        name: 'GST Standard',
        rate: '9.00',
        market: 'SG',
        is_system: true,
        is_active: true,
      },
      {
        id: 'tax-custom',
        name: 'Ishantech Advisory Tax',
        rate: '7.50',
        market: null,
        is_system: false,
        is_active: true,
      },
      {
        id: 'tax-custom-inactive',
        name: 'Retired Custom Tax',
        rate: '5.00',
        market: 'UK',
        is_system: false,
        is_active: false,
      },
    ]);
    http.expectOne(`/api/v1/projects?engagement_id=${engagementId}`).flush([]);
    await fixture.whenStable();
    http.expectOne('/api/v1/employees').flush({ items: [] });
    await fixture.whenStable();

    http.expectOne('/api/v1/billing/profile').flush({ country: 'GB' });
    await fixture.whenStable();
    fixture.detectChanges();

    const optionLabels = Array.from(
      fixture.nativeElement.querySelectorAll('#inv-tax-rate option') as NodeListOf<HTMLOptionElement>,
      option => option.textContent?.trim(),
    );
    expect(optionLabels).toEqual([
      'No tax / zero-rated',
      'VAT Standard — 20.00% · UK · System',
      'Ishantech Advisory Tax — 7.50% · All markets · Custom',
    ]);
    expect(fixture.nativeElement.textContent).not.toContain('GST Standard');
    expect(fixture.nativeElement.textContent).not.toContain('Retired Custom Tax');
  });

  it('previews subtotal, per-line tax, and grand total with deterministic rounding', async () => {
    const timeEntryId = '66666666-6666-6666-6666-666666666666';
    clickButton('Draft invoice');

    http.expectOne('/api/v1/billing/profile').flush({ country: 'SG' });
    http.expectOne('/api/v1/tax-rates').flush([
      {
        id: 'tax-sg',
        name: 'GST 10',
        rate: '10.00',
        market: 'SG',
        is_system: true,
        is_active: true,
      },
    ]);
    http.expectOne(`/api/v1/projects?engagement_id=${engagementId}`).flush([
      { id: projectId, name: 'Discovery', code: 'PRJ-001' },
    ]);
    await fixture.whenStable();
    http.expectOne('/api/v1/employees').flush({
      items: [
        {
          id: employeeId,
          first_name: 'Isha',
          last_name: 'Tan',
          default_bill_rate: '0.05',
        },
      ],
    });
    await fixture.whenStable();
    http.expectOne(`/api/v1/projects/${projectId}/assignments`).flush({ items: [] });
    await fixture.whenStable();
    http.expectOne(`/api/v1/time-entries?project_id=${projectId}&billing_status=unbilled`).flush({
      items: [
        {
          id: timeEntryId,
          project_id: projectId,
          employee_id: employeeId,
          date: '2026-05-15',
          hours: '1.00',
          description: 'Rounding-sensitive workshop',
          billing_status: 'unbilled',
        },
      ],
    });
    await fixture.whenStable();
    fixture.detectChanges();

    clickElement(`#te-${timeEntryId}`);
    clickElement('input[name="inv-extra-on"]');
    setInputValue('input[name="inv-extra-desc"]', 'Rounding-sensitive manual line');
    setInputValue('input[name="inv-extra-qty"]', '1');
    setInputValue('input[name="inv-extra-price"]', '0.05');
    setSelectValue('#inv-tax-rate', 'tax-sg');
    fixture.detectChanges();

    const preview = fixture.nativeElement.querySelector(
      '[aria-label="Invoice totals preview"]',
    ) as HTMLElement | null;
    expect(preview).not.toBeNull();
    const previewText = preview!.textContent?.replace(/\s+/g, ' ').trim();
    expect(previewText).toContain('Subtotal SGD 0.10');
    expect(previewText).toContain('Tax SGD 0.00');
    expect(previewText).toContain('Grand total SGD 0.10');
  });

  it('posts the chosen tax rate on every selected time and manual invoice line', async () => {
    const firstTimeEntryId = '66666666-6666-6666-6666-666666666666';
    const secondTimeEntryId = '77777777-7777-7777-7777-777777777777';
    clickButton('Draft invoice');

    http.expectOne('/api/v1/billing/profile').flush({ country: 'SG' });
    http.expectOne('/api/v1/tax-rates').flush([
      {
        id: 'tax-sg',
        name: 'GST 9',
        rate: '9.00',
        market: 'SG',
        is_system: true,
        is_active: true,
      },
    ]);
    http.expectOne(`/api/v1/projects?engagement_id=${engagementId}`).flush([
      { id: projectId, name: 'Discovery', code: 'PRJ-001' },
    ]);
    await fixture.whenStable();
    http.expectOne('/api/v1/employees').flush({
      items: [
        {
          id: employeeId,
          first_name: 'Isha',
          last_name: 'Tan',
          default_bill_rate: '200.00',
        },
      ],
    });
    await fixture.whenStable();
    http.expectOne(`/api/v1/projects/${projectId}/assignments`).flush({ items: [] });
    await fixture.whenStable();
    http.expectOne(`/api/v1/time-entries?project_id=${projectId}&billing_status=unbilled`).flush({
      items: [
        {
          id: firstTimeEntryId,
          project_id: projectId,
          employee_id: employeeId,
          date: '2026-05-14',
          hours: '1.00',
          description: 'Requirements workshop',
          billing_status: 'unbilled',
        },
        {
          id: secondTimeEntryId,
          project_id: projectId,
          employee_id: employeeId,
          date: '2026-05-15',
          hours: '2.00',
          description: 'Control walkthrough',
          billing_status: 'unbilled',
        },
      ],
    });
    await fixture.whenStable();
    fixture.detectChanges();

    clickElement(`#te-${firstTimeEntryId}`);
    clickElement(`#te-${secondTimeEntryId}`);
    clickElement('input[name="inv-extra-on"]');
    setInputValue('input[name="inv-extra-desc"]', 'Engagement expenses');
    setInputValue('input[name="inv-extra-qty"]', '1');
    setInputValue('input[name="inv-extra-price"]', '50.00');
    setSelectValue('#inv-tax-rate', 'tax-sg');
    clickButton('Create draft invoice');

    const request = http.expectOne('/api/v1/invoices');
    expect(request.request.method).toBe('POST');
    expect(request.request.body.lines).toEqual([
      jasmine.objectContaining({
        time_entry_id: firstTimeEntryId,
        tax_rate_id: 'tax-sg',
      }),
      jasmine.objectContaining({
        time_entry_id: secondTimeEntryId,
        tax_rate_id: 'tax-sg',
      }),
      jasmine.objectContaining({
        description: 'Engagement expenses',
        quantity: '1',
        unit_price: '50',
        tax_rate_id: 'tax-sg',
      }),
    ]);
    request.flush({ id: '88888888-8888-8888-8888-888888888888' });
    await fixture.whenStable();
  });

  function clickButton(label: string): void {
    const buttons = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    );
    const button = buttons.find(candidate => candidate.textContent?.includes(label));
    expect(button).withContext(`button ${label}`).toBeDefined();
    button!.click();
    fixture.detectChanges();
  }

  function clickElement(selector: string): void {
    const element = fixture.nativeElement.querySelector(selector) as HTMLElement | null;
    expect(element).withContext(selector).not.toBeNull();
    element!.click();
    fixture.detectChanges();
  }

  function setInputValue(selector: string, value: string): void {
    const input = fixture.nativeElement.querySelector(selector) as HTMLInputElement | null;
    expect(input).withContext(selector).not.toBeNull();
    input!.value = value;
    input!.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function setSelectValue(selector: string, value: string): void {
    const select = fixture.nativeElement.querySelector(selector) as HTMLSelectElement | null;
    expect(select).withContext(selector).not.toBeNull();
    select!.value = value;
    select!.dispatchEvent(new Event('change'));
    fixture.detectChanges();
  }
});
