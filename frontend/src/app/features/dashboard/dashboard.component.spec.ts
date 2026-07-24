import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { DashboardComponent } from './dashboard.component';

const AR = { '0_30': '1000.00', '31_60': '500.00', '61_90': '0.00', over_90: '0.00', total: '1500.00' };
const AP = { '0_30': '400.00', '31_60': '0.00', '61_90': '0.00', over_90: '0.00', total: '400.00' };

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let http: HttpTestingController;

  async function setup(): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(DashboardComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/reports/ar-aging').flush(AR);
    http.expectOne('/api/v1/reports/ap-aging').flush(AP);
    http.expectOne('/api/v1/tenants/accounting-context').flush({ base_currency: 'SGD' });
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  it('shows AR, AP and net-position metrics in the base currency', async () => {
    await setup();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[data-testid="metric-ar"]')?.textContent).toContain('SGD');
    expect(el.querySelector('[data-testid="metric-ar"]')?.textContent).toContain('1,500.00');
    expect(el.querySelector('[data-testid="metric-ap"]')?.textContent).toContain('400.00');
    // net = 1500 - 400 = 1100
    expect(el.querySelector('[data-testid="metric-net"]')?.textContent).toContain('1,100.00');
  });

  it('renders the AR aging chart from the buckets', async () => {
    await setup();
    expect(fixture.componentInstance.arBuckets().map(b => b.value)).toEqual([1000, 500, 0, 0]);
    expect(fixture.nativeElement.querySelector('[data-testid="dashboard-ar-chart"]')).not.toBeNull();
  });

  it('surfaces an error state with retry', async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(DashboardComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    // Flush the siblings first; forkJoin errors (and cancels) only on the last.
    http.expectOne('/api/v1/reports/ap-aging').flush(AP);
    http.expectOne('/api/v1/tenants/accounting-context').flush({ base_currency: 'USD' });
    http.expectOne('/api/v1/reports/ar-aging').flush(null, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]')).not.toBeNull();
  });
});
