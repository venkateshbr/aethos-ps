import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { RateCard, RateCardsComponent } from './rate-cards.component';

const CARD: RateCard = {
  id: 'rc-1',
  name: 'FY26 Standard Rates',
  currency: 'SGD',
  effective_date: '2026-01-01',
  lines: [
    { role: 'Partner', rate: '650.00', service_line: 'advisory' },
    { role: 'Associate', rate: '250.00', service_line: null },
  ],
};

describe('RateCardsComponent', () => {
  let fixture: ComponentFixture<RateCardsComponent>;
  let http: HttpTestingController;

  async function setup(initial: RateCard[] = [CARD]): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [RateCardsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(RateCardsComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/rate-cards').flush(initial);
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  it('lists rate cards and reveals roles on expand', async () => {
    await setup();
    expect(fixture.nativeElement.textContent).toContain('FY26 Standard Rates');
    expect(fixture.nativeElement.textContent).toContain('2 roles');

    fixture.componentInstance.toggleExpanded('rc-1');
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Partner');
    expect(text).toContain('SGD 650.00');
    expect(text).toContain('advisory');
  });

  it('shows an empty state when there are no rate cards', async () => {
    await setup([]);
    expect(fixture.nativeElement.textContent).toContain('No rate cards yet');
  });

  it('supports adding and removing line rows', async () => {
    await setup();
    fixture.componentInstance.openAddPanel();
    expect(fixture.componentInstance.lines.length).toBe(1);
    fixture.componentInstance.addLine();
    fixture.componentInstance.addLine();
    expect(fixture.componentInstance.lines.length).toBe(3);
    fixture.componentInstance.removeLine(0);
    expect(fixture.componentInstance.lines.length).toBe(2);
  });

  it('POSTs a new rate card with its lines and appends it', async () => {
    await setup([]);
    const c = fixture.componentInstance;
    c.openAddPanel();
    c.addForm.patchValue({ name: 'FY27 Rates', currency: 'USD', effective_date: '2027-01-01' });
    c.lines.at(0).patchValue({ role: 'Manager', rate: 400, service_line: 'tax' });
    c.submitAdd();

    const req = http.expectOne('/api/v1/rate-cards');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      name: 'FY27 Rates',
      currency: 'USD',
      effective_date: '2027-01-01',
      lines: [{ role: 'Manager', rate: '400', service_line: 'tax' }],
    });
    req.flush({ id: 'rc-2', name: 'FY27 Rates', currency: 'USD', effective_date: '2027-01-01',
      lines: [{ role: 'Manager', rate: '400.00', service_line: 'tax' }] });
    fixture.detectChanges();

    expect(c.showAddPanel()).toBeFalse();
    expect(c.cards().length).toBe(1);
    expect(c.cards()[0].name).toBe('FY27 Rates');
  });

  it('surfaces the server error detail and keeps the panel open on failure', async () => {
    await setup([]);
    const c = fixture.componentInstance;
    c.openAddPanel();
    c.addForm.patchValue({ name: 'Bad', currency: 'USD', effective_date: '2027-01-01' });
    c.lines.at(0).patchValue({ role: 'X', rate: 1, service_line: '' });
    c.submitAdd();

    http
      .expectOne('/api/v1/rate-cards')
      .flush({ detail: 'Rate card name already exists' }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();

    expect(c.addError()).toBe('Rate card name already exists');
    expect(c.showAddPanel()).toBeTrue();
  });
});
