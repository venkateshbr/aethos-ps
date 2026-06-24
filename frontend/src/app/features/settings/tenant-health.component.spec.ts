import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TenantHealthComponent } from './tenant-health.component';

const health = {
  status: 'degraded',
  tenant_id: 'tenant-1',
  generated_at: '2026-06-24T20:00:00Z',
  runtime: {
    environment: 'test',
    debug: false,
    queue_configured: true,
    queue_required: false,
    extraction_mode: 'sync',
  },
  rate_limit: {
    enabled: true,
    backend: 'supabase',
    distributed_configured: true,
    fallback_to_memory: true,
    window_seconds: 60,
  },
  checks: {
    tables: [
      { name: 'tenants', status: 'ok' },
      { name: 'agent_runs', status: 'error', message: 'PostgrestAPIError' },
    ],
  },
  telemetry: {
    request_failures: [
      { method: 'GET', path: '/api/v1/public/invoices/{token}', status_code: 429, count: 12 },
    ],
    background_failures: [
      { worker_name: 'rate_limit_distributed_backend', count: 2 },
    ],
    failed_agent_runs_24h: 1,
    failed_tool_invocations_24h: 1,
    failed_workflow_runs_24h: 0,
    failed_tools_by_name_24h: [{ tool_name: 'send_email', count: 1 }],
    window_start: '2026-06-23T20:00:00Z',
  },
  alerts: {
    route: {
      route_type: 'runbook_queue',
      channel: 'runbook',
      configured: false,
    },
    items: [
      {
        code: 'public_endpoint_abuse',
        severity: 'warning',
        message: 'Repeated rate-limit denials crossed the alert threshold.',
        count: 12,
        route_type: 'runbook_queue',
        channel: 'runbook',
        runbook: 'docs/test/e2e_ops_security.md#ops-alerts',
        metadata: { paths: [] },
      },
    ],
  },
} as const;

describe('TenantHealthComponent', () => {
  let fixture: ComponentFixture<TenantHealthComponent>;
  let http: HttpTestingController;

  async function setup(): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [TenantHealthComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TenantHealthComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
  });

  it('renders tenant health, distributed limiter, and routed alert signals', async () => {
    await setup();

    const req = http.expectOne('/api/v1/tenants/health');
    expect(req.request.method).toBe('GET');
    req.flush(health);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Operational Health');
    expect(text).toContain('Degraded');
    expect(text).toContain('supabase');
    expect(text).toContain('Distributed');
    expect(text).toContain('agent_runs');
    expect(text).toContain('/api/v1/public/invoices/{token}');
    expect(text).toContain('rate_limit_distributed_backend');
    expect(text).toContain('Public Endpoint Abuse');
    expect(text).not.toContain('token_1234567890abcdef');
  });

  it('shows a safe load failure state', async () => {
    await setup();

    http.expectOne('/api/v1/tenants/health').flush({}, { status: 403, statusText: 'Forbidden' });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Failed to load tenant health.');
  });
});
