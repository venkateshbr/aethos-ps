import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { SubscriptionComponent, SubscriptionStatus } from './subscription.component';

const STATUS: SubscriptionStatus = {
  status: 'active',
  trial_ends_at: null,
  plan_tier: 'growth',
};

describe('SubscriptionComponent', () => {
  let fixture: ComponentFixture<SubscriptionComponent>;
  let http: HttpTestingController;

  async function setup(status: SubscriptionStatus = STATUS): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [SubscriptionComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(SubscriptionComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/billing/subscription-status').flush(status);
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  it('renders the current plan and status', async () => {
    await setup();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('growth plan');
    expect(text).toContain('Active');
  });

  it('shows a trial countdown when trialing', async () => {
    const soon = new Date(Date.now() + 3 * 86_400_000).toISOString();
    await setup({ status: 'trialing', trial_ends_at: soon, plan_tier: 'trial' });
    expect(fixture.nativeElement.textContent).toContain('Trial ends in 3 days');
  });

  it('opens the Stripe portal with a same-origin return URL', async () => {
    await setup();
    const spy = spyOn(fixture.componentInstance as unknown as { navigateExternal: (u: string) => void },
      'navigateExternal');
    fixture.componentInstance.openPortal();

    const req = http.expectOne('/api/v1/billing/portal');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.return_url).toBe(`${window.location.origin}/app/settings`);
    req.flush({ url: 'https://billing.stripe.com/session/abc' });

    expect(spy).toHaveBeenCalledWith('https://billing.stripe.com/session/abc');
  });

  it('explains when billing is not yet set up (409)', async () => {
    await setup();
    fixture.componentInstance.openPortal();
    http.expectOne('/api/v1/billing/portal').flush(
      { detail: 'Billing not yet set up for this tenant.' },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[role="alert"]')?.textContent)
      .toContain('Billing is not set up yet');
  });
});
