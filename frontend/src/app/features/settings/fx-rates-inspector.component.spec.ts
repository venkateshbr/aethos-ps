import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FxRatesInspectorComponent } from './fx-rates-inspector.component';

describe('FxRatesInspectorComponent', () => {
  let fixture: ComponentFixture<FxRatesInspectorComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FxRatesInspectorComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(FxRatesInspectorComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('looks up and renders historical USD to SGD immutable provenance', () => {
    setSelect('#fx-from-currency', 'USD');
    setSelect('#fx-to-currency', 'SGD');
    setInput('#fx-rate-date', '2026-05-31');

    button('Lookup').click();

    const request = http.expectOne(
      '/api/v1/fx-rates/USD/SGD?rate_date=2026-05-31',
    );
    expect(request.request.method).toBe('GET');
    request.flush({
      from_currency: 'USD',
      to_currency: 'SGD',
      rate: '1.350000',
      refreshed_at: '2026-05-30T01:00:00+00:00',
      stale: false,
      requested_rate_date: '2026-05-31',
      rate_date: '2026-05-30',
      fx_rate_id: 'fx-usd-sgd-2026-05-30',
      source: 'openexchangerates',
      staleness_days: 1,
    });
    fixture.detectChanges();

    const provenance = fixture.nativeElement.querySelector(
      '[aria-label="Matched FX rate provenance"]',
    ) as HTMLElement | null;
    expect(provenance).not.toBeNull();
    const text = provenance!.textContent?.replace(/\s+/g, ' ').trim();
    expect(text).toContain('USD → SGD');
    expect(text).toContain('1.350000');
    expect(text).toContain('2026-05-31');
    expect(text).toContain('2026-05-30');
    expect(text).toContain('fx-usd-sgd-2026-05-30');
    expect(text).toContain('openexchangerates');
    expect(text).toContain('1 day');
  });

  it('shows the missing historical rate error without stale provenance', () => {
    setSelect('#fx-from-currency', 'USD');
    setSelect('#fx-to-currency', 'SGD');
    setInput('#fx-rate-date', '2026-05-01');

    button('Lookup').click();
    http.expectOne(
      '/api/v1/fx-rates/USD/SGD?rate_date=2026-05-01',
    ).flush(
      { detail: 'No FX rate found for USD→SGD on or before 2026-05-01' },
      { status: 404, statusText: 'Not Found' },
    );
    fixture.detectChanges();

    const alert = fixture.nativeElement.querySelector('[role="alert"]') as HTMLElement | null;
    expect(alert?.textContent).toContain(
      'No FX rate found for USD→SGD on or before 2026-05-01',
    );
    expect(
      fixture.nativeElement.querySelector('[aria-label="Matched FX rate provenance"]'),
    ).toBeNull();
  });

  function setSelect(selector: string, value: string): void {
    const select = fixture.nativeElement.querySelector(selector) as HTMLSelectElement;
    select.value = value;
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
  }

  function setInput(selector: string, value: string): void {
    const input = fixture.nativeElement.querySelector(selector) as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function button(label: string): HTMLButtonElement {
    const buttons = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    );
    return buttons.find(candidate => candidate.textContent?.includes(label))!;
  }
});
