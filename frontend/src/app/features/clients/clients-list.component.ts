/**
 * ClientsListComponent — contact list with inline create form.
 *
 * Issue #201: rename "Clients" → "Contacts" in UI; add kind=both support;
 * add type badge (Customer / Vendor / Both) and kind filter chips.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

type ContactKind = 'customer' | 'vendor' | 'both';
type KindFilter  = 'all' | 'customer' | 'vendor';

interface ClientSummary {
  id: string;
  name: string;
  kind: ContactKind;
  phone?: string | null;
  website?: string | null;
  created_at?: string;
}

@Component({
  selector: 'app-clients-list',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule, MatButtonModule],
  template: `
    <section class="h-full flex flex-col bg-surface-base text-text-primary">
      <header class="px-6 py-4 border-b border-border-default flex items-center justify-between flex-none">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Contacts</h1>
          <p class="text-sm text-text-muted mt-0.5">Companies and individuals you work with.</p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Create new contact"
          (click)="openCreateForm()"
        >
          <mat-icon class="text-base leading-none">add</mat-icon>
          New contact
        </button>
      </header>

      <!-- Kind filter chips -->
      <div class="px-6 pt-4 pb-2 flex items-center gap-2 flex-none" role="group" aria-label="Filter by contact type">
        @for (chip of filterChips; track chip.value) {
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [class]="kindFilter() === chip.value
              ? 'bg-accent/20 text-accent-light border border-accent/40'
              : 'bg-surface-raised text-text-muted border border-border-default hover:border-border-strong hover:text-text-secondary'"
            [attr.aria-pressed]="kindFilter() === chip.value"
            (click)="setFilter(chip.value)"
          >
            {{ chip.label }}
          </button>
        }
      </div>

      <!-- Loading -->
      @if (loading()) {
        <div class="flex items-center justify-center py-16">
          <div class="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" aria-label="Loading contacts"></div>
        </div>
      }

      <!-- Error -->
      @if (error() && !loading()) {
        <div class="mx-6 mt-4 rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !error() && filteredContacts().length === 0) {
        <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
          <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;" aria-hidden="true">people_outline</mat-icon>
          @if (contacts().length === 0) {
            <p class="text-text-secondary font-medium">No contacts yet</p>
            <p class="text-text-disabled text-sm mt-1 max-w-md">
              Add a contact manually or process an engagement letter through Aethos Nous.
            </p>
            <button
              type="button"
              class="mt-5 inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              (click)="openCreateForm()"
            >
              <mat-icon class="text-base leading-none">add</mat-icon>
              Add first contact
            </button>
          } @else {
            <p class="text-text-secondary font-medium">No contacts match this filter</p>
            <button
              type="button"
              class="mt-3 text-sm text-accent-light hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
              (click)="setFilter('all')"
            >Show all contacts</button>
          }
        </div>
      }

      <!-- Contact list -->
      @if (!loading() && !error() && filteredContacts().length > 0) {
        <div class="flex-1 overflow-y-auto p-6">
          <div class="space-y-2">
            @for (contact of filteredContacts(); track contact.id) {
              <button
                type="button"
                class="w-full flex items-center gap-4 bg-surface border border-border-default rounded-lg px-4 py-3 hover:border-border-strong hover:bg-surface-raised transition-colors text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                [attr.aria-label]="'View ' + contact.name"
                (click)="navigateToContact(contact.id)"
              >
                <div class="w-9 h-9 rounded-full bg-accent/15 flex items-center justify-center flex-none">
                  <mat-icon class="text-accent-light text-base leading-none">
                    {{ contact.kind === 'vendor' ? 'storefront' : contact.kind === 'both' ? 'swap_horiz' : 'person' }}
                  </mat-icon>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <p class="text-sm font-medium text-text-primary truncate">{{ contact.name }}</p>
                    <!-- Type badge -->
                    <span
                      class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium flex-none"
                      [class]="kindBadgeClass(contact.kind)"
                      [attr.aria-label]="'Type: ' + kindLabel(contact.kind)"
                    >{{ kindLabel(contact.kind) }}</span>
                  </div>
                </div>
                <mat-icon class="text-text-disabled text-base flex-none" aria-hidden="true">chevron_right</mat-icon>
              </button>
            }
          </div>
          <p class="text-xs text-text-disabled mt-3">
            {{ filteredContacts().length }} contact{{ filteredContacts().length !== 1 ? 's' : '' }}
            @if (kindFilter() !== 'all') { (filtered) }
          </p>
        </div>
      }
    </section>

    <!-- Create contact slide-in panel -->
    @if (showCreateForm()) {
      <div class="fixed inset-0 bg-black/50 z-40" (click)="closeCreateForm()" aria-hidden="true"></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog" aria-modal="true" aria-labelledby="create-contact-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="create-contact-title" class="text-base font-semibold text-text-primary">New contact</h2>
          <button class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeCreateForm()" aria-label="Close panel">
            <mat-icon>close</mat-icon>
          </button>
        </div>
        <form [formGroup]="createForm" (ngSubmit)="submitCreate()" class="flex-1 overflow-y-auto px-6 py-5 space-y-5" novalidate>
          <!-- Name -->
          <div>
            <label for="client-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Name *</label>
            <input id="client-name" type="text" formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="e.g. Acme Corp" />
            @if (createForm.controls.name.touched && createForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1">Name is required.</p>
            }
          </div>
          <!-- Contact Type -->
          <div>
            <label for="client-kind" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Contact Type *</label>
            <select id="client-kind" formControlName="kind"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm">
              <option value="customer">Customer (client you bill)</option>
              <option value="vendor">Vendor (supplier you pay)</option>
              <option value="both">Both (Customer &amp; Vendor)</option>
            </select>
          </div>
          <!-- Phone -->
          <div>
            <label for="contact-phone" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Phone</label>
            <input id="contact-phone" type="tel" formControlName="phone" placeholder="+44 20 7123 4567"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm" />
          </div>
          <!-- Website -->
          <div>
            <label for="contact-website" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Website</label>
            <input id="contact-website" type="url" formControlName="website" placeholder="https://example.com"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm" />
          </div>
          @if (createError()) {
            <div role="alert" class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2">{{ createError() }}</div>
          }
        </form>
        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button type="button" class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded" (click)="closeCreateForm()">Cancel</button>
          <button type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="createForm.invalid || creating()" (click)="submitCreate()">
            @if (creating()) { Creating… } @else { Create contact }
          </button>
        </div>
      </aside>
    }
  `,
})
export class ClientsListComponent implements OnInit {
  private http   = inject(HttpClient);
  private fb     = inject(FormBuilder);
  private router = inject(Router);

  loading = signal(true);
  error = signal<string | null>(null);
  contacts = signal<ClientSummary[]>([]);
  kindFilter = signal<KindFilter>('all');

  /** Filter chips shown above the list. */
  readonly filterChips: { label: string; value: KindFilter }[] = [
    { label: 'All',       value: 'all' },
    { label: 'Customers', value: 'customer' },
    { label: 'Vendors',   value: 'vendor' },
  ];

  /**
   * Client-side filter: "customer" shows customer + both;
   * "vendor" shows vendor + both; "all" shows everything.
   */
  filteredContacts = computed(() => {
    const filter = this.kindFilter();
    if (filter === 'all') return this.contacts();
    return this.contacts().filter(c =>
      c.kind === filter || c.kind === 'both',
    );
  });

  // Create form state
  showCreateForm = signal(false);
  creating = signal(false);
  createError = signal<string | null>(null);
  createForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    kind: ['customer' as ContactKind, [Validators.required]],
    phone: [''],
    website: [''],
  });

  ngOnInit(): void {
    this.http.get<{ items: ClientSummary[]; total: number }>('/api/v1/clients').subscribe({
      next: (res) => {
        this.contacts.set(res.items ?? []);
        this.loading.set(false);
      },
      error: (err: { status?: number }) => {
        if (err.status === 404) {
          this.contacts.set([]);
        } else {
          this.error.set('Could not load contacts. Please refresh to try again.');
        }
        this.loading.set(false);
      },
    });
  }

  setFilter(value: KindFilter): void {
    this.kindFilter.set(value);
  }

  kindLabel(kind: ContactKind): string {
    return kind === 'both' ? 'Both' : kind === 'vendor' ? 'Vendor' : 'Customer';
  }

  kindBadgeClass(kind: ContactKind): string {
    switch (kind) {
      case 'customer': return 'bg-blue-500/20 text-blue-300';
      case 'vendor':   return 'bg-amber-500/20 text-amber-300';
      case 'both':     return 'bg-purple-500/20 text-purple-300';
    }
  }

  navigateToContact(id: string): void {
    this.router.navigate(['/app/clients', id]);
  }

  openCreateForm(): void {
    this.createForm.reset({ name: '', kind: 'customer', phone: '', website: '' });
    this.createError.set(null);
    this.showCreateForm.set(true);
  }

  closeCreateForm(): void {
    this.showCreateForm.set(false);
  }

  submitCreate(): void {
    if (this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }
    this.creating.set(true);
    this.createError.set(null);
    const v = this.createForm.getRawValue();
    this.http.post<ClientSummary>('/api/v1/clients', {
      name: v.name,
      kind: v.kind,
      phone: v.phone || null,
      website: v.website || null,
    }).subscribe({
      next: (newContact) => {
        this.contacts.update(list => [newContact, ...list]);
        this.creating.set(false);
        this.closeCreateForm();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.creating.set(false);
        const detail = err?.error?.detail;
        this.createError.set(
          typeof detail === 'string' ? detail : 'Could not create contact. Please try again.'
        );
      },
    });
  }
}
