import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { TaxRate, TaxRatesComponent } from './tax-rates.component';

const SYSTEM_RATE: TaxRate = {
  id: 'sys-gb-vat',
  name: 'UK VAT Standard Rate (20%)',
  rate: '20.00',
  market: 'UK',
  is_system: true,
  is_active: true,
};

const CUSTOM_RATE: TaxRate = {
  id: 'tenant-a-custom',
  name: 'Local services tax',
  rate: '7.50',
  market: 'US',
  is_system: false,
  is_active: true,
};

describe('TaxRatesComponent', () => {
  let fixture: ComponentFixture<TaxRatesComponent>;
  let http: HttpTestingController;

  async function setup(): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [TaxRatesComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(TaxRatesComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/tax-rates').flush([SYSTEM_RATE, CUSTOM_RATE]);
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  it('offers Edit only for custom rates, not system rates', async () => {
    await setup();
    const editButtons = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).filter(b => b.getAttribute('aria-label')?.startsWith('Edit '));
    expect(editButtons.length).toBe(1);
    expect(editButtons[0].getAttribute('aria-label')).toBe('Edit Local services tax');
  });

  it('prefills the edit form and PATCHes changed name/rate/market', async () => {
    await setup();
    fixture.componentInstance.openEditPanel(CUSTOM_RATE);
    fixture.detectChanges();

    expect(fixture.componentInstance.editForm.getRawValue()).toEqual({
      name: 'Local services tax',
      rate: 7.5,
      market: 'US',
      is_active: true,
    });

    fixture.componentInstance.editForm.patchValue({ name: 'State tax', rate: 9, market: 'AU' });
    fixture.componentInstance.submitEdit();

    const req = http.expectOne('/api/v1/tax-rates/tenant-a-custom');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({
      name: 'State tax',
      rate: '9',
      market: 'AU',
      is_active: true,
    });
    req.flush({ ...CUSTOM_RATE, name: 'State tax', rate: '9.00', market: 'AU' });
    fixture.detectChanges();

    expect(fixture.componentInstance.editRate()).toBeNull();
    expect(fixture.componentInstance.rates().find(r => r.id === 'tenant-a-custom')?.name).toBe(
      'State tax',
    );
  });

  it('sends market as null when cleared to "All markets"', async () => {
    await setup();
    fixture.componentInstance.openEditPanel(CUSTOM_RATE);
    fixture.componentInstance.editForm.patchValue({ market: '' });
    fixture.componentInstance.submitEdit();

    const req = http.expectOne('/api/v1/tax-rates/tenant-a-custom');
    expect(req.request.body.market).toBeNull();
    req.flush({ ...CUSTOM_RATE, market: null });
  });

  it('surfaces the server error detail and keeps the panel open on failure', async () => {
    await setup();
    fixture.componentInstance.openEditPanel(CUSTOM_RATE);
    fixture.componentInstance.editForm.patchValue({ name: 'Bad' });
    fixture.componentInstance.submitEdit();

    http
      .expectOne('/api/v1/tax-rates/tenant-a-custom')
      .flush({ detail: 'No updatable fields supplied' }, { status: 400, statusText: 'Bad Request' });
    fixture.detectChanges();

    expect(fixture.componentInstance.editError()).toBe('No updatable fields supplied');
    expect(fixture.componentInstance.editRate()).not.toBeNull();
  });
});
