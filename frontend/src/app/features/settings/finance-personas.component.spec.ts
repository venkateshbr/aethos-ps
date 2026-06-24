import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuthService } from '../../core/services/auth.service';
import { FinancePersonasComponent } from './finance-personas.component';

const personas = [
  {
    id: 'owner_admin',
    label: 'Owner/Admin',
    mapped_roles: ['owner', 'admin'],
    description: 'Tenant and finance operations administrator.',
    areas: ['Settings'],
    allowed_actions: ['Configure tenant controls and AI operations'],
    restricted_actions: ['Tenant-scoped only'],
    read_only: false,
  },
  {
    id: 'ap_lead',
    label: 'AP Lead',
    mapped_roles: ['manager', 'admin', 'owner'],
    description: 'Procure-to-pay operator.',
    areas: ['Bills', 'Pay Bills'],
    allowed_actions: ['Prepare payment batches for approval'],
    restricted_actions: ['Cannot approve admin or owner-threshold money-out work'],
    read_only: false,
  },
  {
    id: 'ar_lead',
    label: 'AR Lead',
    mapped_roles: ['manager', 'admin', 'owner'],
    description: 'Order-to-cash operator.',
    areas: ['Invoices', 'Collections'],
    allowed_actions: ['Draft and review invoices'],
    restricted_actions: ['Cannot bypass send approval gates'],
    read_only: false,
  },
  {
    id: 'auditor',
    label: 'Auditor',
    mapped_roles: ['viewer'],
    description: 'Read-only audit reviewer.',
    areas: ['Reports', 'Audit evidence'],
    allowed_actions: ['Inspect permitted tenant records'],
    restricted_actions: ['Cannot create, approve, edit, reject, post, pay, send, lock, or change settings'],
    read_only: true,
  },
  {
    id: 'executive',
    label: 'Executive',
    mapped_roles: ['viewer'],
    description: 'Read-only leader.',
    areas: ['Reports'],
    allowed_actions: ['Inspect dashboards and reports'],
    restricted_actions: ['Cannot create, approve, edit, reject, post, pay, send, lock, or change settings'],
    read_only: true,
  },
] as const;

describe('FinancePersonasComponent', () => {
  let fixture: ComponentFixture<FinancePersonasComponent>;
  let http: HttpTestingController;

  async function setup(roleValue: 'manager' | 'viewer' = 'manager'): Promise<void> {
    const role = signal<string | null>(roleValue);

    await TestBed.configureTestingModule({
      imports: [FinancePersonasComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { role: role.asReadonly() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FinancePersonasComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
  });

  it('loads the backend persona catalog and highlights manager-compatible finance roles', async () => {
    await setup('manager');

    const req = http.expectOne('/api/v1/tenants/finance-personas');
    expect(req.request.method).toBe('GET');
    req.flush({ items: personas });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Finance role personas');
    expect(text).toContain('Manager');
    expect(fixture.componentInstance.compatiblePersonas().map(persona => persona.id)).toEqual(['ap_lead', 'ar_lead']);
    expect(text).toContain('AP Lead');
    expect(text).toContain('AR Lead');
  });

  it('keeps viewer personas visibly read-only', async () => {
    await setup('viewer');

    http.expectOne('/api/v1/tenants/finance-personas').flush({ items: personas });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(fixture.componentInstance.compatiblePersonas().map(persona => persona.id)).toEqual(['auditor', 'executive']);
    expect(text).toContain('Auditor');
    expect(text).toContain('Executive');
    expect(text).toContain('Read only');
    expect(text).toContain('Cannot create, approve, edit, reject, post, pay, send, lock, or change settings');
  });
});
