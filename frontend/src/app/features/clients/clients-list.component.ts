/**
 * ClientsListComponent — client list with inline create form.
 *
 * Previously a placeholder (#112). Now shows a "New client" panel
 * so pilot users can add clients before uploading an engagement letter.
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

interface ClientSummary {
  id: string;
  name: string;
  kind: 'customer' | 'vendor';
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
          <h1 class="text-2xl font-bold text-text-primary">Clients</h1>
          <p class="text-sm text-text-muted mt-0.5">Companies and individuals you work with.</p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Create new client"
          (click)="openCreateForm()"
        >
          <mat-icon class="text-base leading-none">add</mat-icon>
          New client
        </button>
      </header>

      <!-- Loading -->
      @if (loading()) {
        <div class="flex items-center justify-center py-16">
          <div class="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" aria-label="Loading clients"></div>
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
      @if (!loading() && !error() && clients().length === 0) {
        <div class="flex-1 flex flex-col items-center justify-center text-center px-6">
          <mat-icon class="text-text-disabled mb-3" style="font-size:2.5rem;width:2.5rem;height:2.5rem;" aria-hidden="true">people_outline</mat-icon>
          <p class="text-text-secondary font-medium">No clients yet</p>
          <p class="text-text-disabled text-sm mt-1 max-w-md">
            Add a client manually or upload an engagement letter via Copilot and Aethos will create one for you.
          </p>
          <button
            type="button"
            class="mt-5 inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            (click)="openCreateForm()"
          >
            <mat-icon class="text-base leading-none">add</mat-icon>
            Add first client
          </button>
        </div>
      }

      <!-- Client list -->
      @if (!loading() && !error() && clients().length > 0) {
        <div class="flex-1 overflow-y-auto p-6">
          <div class="space-y-2">
            @for (client of clients(); track client.id) {
              <div class="flex items-center gap-4 bg-surface border border-border-default rounded-lg px-4 py-3 hover:border-border-strong transition-colors">
                <div class="w-9 h-9 rounded-full bg-accent/15 flex items-center justify-center flex-none">
                  <mat-icon class="text-accent-light text-base leading-none">
                    {{ client.kind === 'vendor' ? 'storefront' : 'person' }}
                  </mat-icon>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-text-primary truncate">{{ client.name }}</p>
                  <p class="text-xs text-text-muted mt-0.5 capitalize">{{ client.kind }}</p>
                </div>
              </div>
            }
          </div>
        </div>
      }
    </section>

    <!-- Create client slide-in panel -->
    @if (showCreateForm()) {
      <div class="fixed inset-0 bg-black/50 z-40" (click)="closeCreateForm()" aria-hidden="true"></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog" aria-modal="true" aria-labelledby="create-client-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="create-client-title" class="text-base font-semibold text-text-primary">New client</h2>
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
          <!-- Kind -->
          <div>
            <label for="client-kind" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Type *</label>
            <select id="client-kind" formControlName="kind"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm">
              <option value="customer">Customer (client you bill)</option>
              <option value="vendor">Vendor (supplier you pay)</option>
            </select>
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
            @if (creating()) { Creating… } @else { Create client }
          </button>
        </div>
      </aside>
    }
  `,
})
export class ClientsListComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  loading = signal(true);
  error = signal<string | null>(null);
  clients = signal<ClientSummary[]>([]);

  // Create form state
  showCreateForm = signal(false);
  creating = signal(false);
  createError = signal<string | null>(null);
  createForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    kind: ['customer' as 'customer' | 'vendor', [Validators.required]],
  });

  ngOnInit(): void {
    this.http.get<ClientSummary[]>('/api/v1/clients').subscribe({
      next: (list) => {
        this.clients.set(list);
        this.loading.set(false);
      },
      error: (err: { status?: number }) => {
        if (err.status === 404) {
          this.clients.set([]);
        } else {
          this.error.set('Could not load clients. Please refresh to try again.');
        }
        this.loading.set(false);
      },
    });
  }

  openCreateForm(): void {
    this.createForm.reset({ name: '', kind: 'customer' });
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
    this.http.post<ClientSummary>('/api/v1/clients', { name: v.name, kind: v.kind }).subscribe({
      next: (newClient) => {
        this.clients.update(list => [newClient, ...list]);
        this.creating.set(false);
        this.closeCreateForm();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.creating.set(false);
        const detail = err?.error?.detail;
        this.createError.set(
          typeof detail === 'string' ? detail : 'Could not create client. Please try again.'
        );
      },
    });
  }
}
