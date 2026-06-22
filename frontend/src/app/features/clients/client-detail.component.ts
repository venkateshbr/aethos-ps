/**
 * ClientDetailComponent — contact detail and edit page.
 *
 * Issue #212: view contact info, AR (invoices) and AP (bills) history,
 * and edit the contact via a slide-in panel.
 *
 * Route: /app/clients/:id
 */
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { DatePipe } from '@angular/common';

import { MoneyPipe } from '../../shared/pipes/money.pipe';
import { SkeletonRowsComponent } from '../../shared/components/skeleton-rows.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { userMessageForError } from '../../core/utils/error-message';

type ContactKind = 'customer' | 'vendor' | 'both';
type ClientGroupType =
  | 'family_office'
  | 'portfolio'
  | 'corporate_group'
  | 'billing_group'
  | 'client_relationship'
  | 'other';
type ClientGroupMemberRole =
  | 'parent'
  | 'subsidiary'
  | 'trust'
  | 'spv'
  | 'individual'
  | 'portfolio_company'
  | 'billing_entity'
  | 'other';

interface ContactDetail {
  id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  kind: ContactKind;
  created_at: string;
}

interface ContactOption {
  id: string;
  name: string;
  kind: ContactKind;
}

interface ClientGroupMember {
  id: string;
  group_id: string;
  client_id: string;
  client_name?: string | null;
  client_kind?: ContactKind | string | null;
  relationship_role: ClientGroupMemberRole | string;
  is_primary: boolean;
}

interface ClientGroup {
  id: string;
  name: string;
  group_type: ClientGroupType | string;
  primary_client_id?: string | null;
  billing_client_id?: string | null;
  currency?: string | null;
  status: string;
  member_count: number;
  members: ClientGroupMember[];
}

interface InvoiceSummary {
  id: string;
  invoice_number: string;
  issue_date: string | null;
  due_date: string | null;
  total: string;
  currency: string;
  status: string;
}

interface BillSummary {
  id: string;
  bill_number: string;
  issue_date: string | null;
  due_date: string | null;
  total: string;
  currency: string;
  status: string;
}

/** Days between a date string and today — positive = overdue / elapsed. */
function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  return Math.floor(diff / 86_400_000);
}

@Component({
  selector: 'app-client-detail',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    DatePipe,
    MoneyPipe,
    SkeletonRowsComponent,
    EmptyStateComponent,
  ],
  template: `
    <div class="p-6 bg-surface-base min-h-full">

      <!-- Back nav -->
      <button
        mat-button
        class="text-text-muted hover:text-text-primary mb-4 -ml-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        (click)="goBack()"
        aria-label="Back to contacts list"
      >
        <mat-icon>arrow_back</mat-icon>
        Contacts
      </button>

      <!-- Header skeleton -->
      @if (loading()) {
        <div class="animate-pulse mb-8" aria-busy="true" aria-label="Loading contact">
          <div class="flex items-center gap-4 mb-6">
            <div class="w-16 h-16 rounded-full bg-surface-raised"></div>
            <div class="space-y-2">
              <div class="h-7 bg-surface-raised rounded w-48"></div>
              <div class="h-4 bg-surface-raised rounded w-24"></div>
            </div>
          </div>
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            @for (i of [1,2,3,4]; track i) {
              <div class="bg-surface-raised rounded p-4 h-16"></div>
            }
          </div>
        </div>
      }

      <!-- Error -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
             role="alert">
          <mat-icon class="text-base flex-none">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- Main content -->
      @if (!loading() && !error() && contact()) {

        <!-- Header -->
        <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div class="flex items-center gap-4">
            <!-- Avatar -->
            <div
              class="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold text-white flex-none"
              [class]="avatarBgClass(contact()!.kind)"
              aria-hidden="true"
            >
              {{ contact()!.name.charAt(0).toUpperCase() }}
            </div>
            <div>
              <h1 class="text-2xl font-bold text-text-primary">{{ contact()!.name }}</h1>
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium mt-1"
                [class]="kindBadgeClass(contact()!.kind)"
                [attr.aria-label]="'Contact type: ' + kindLabel(contact()!.kind)"
              >{{ kindLabel(contact()!.kind) }}</span>
            </div>
          </div>

          <!-- Edit button -->
          <button
            type="button"
            class="inline-flex items-center gap-2 border border-border-strong hover:border-accent text-text-secondary hover:text-text-primary font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            (click)="openEditPanel()"
            aria-label="Edit contact"
          >
            <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;">edit</mat-icon>
            Edit
          </button>
        </div>

        <!-- Save/update feedback -->
        @if (saveMessage()) {
          <div class="mb-4 rounded-lg border border-emerald-800 bg-accent/10 px-4 py-3 text-sm text-accent-light flex items-center gap-2"
               role="status" aria-live="polite">
            <mat-icon class="text-base">check_circle</mat-icon>
            {{ saveMessage() }}
          </div>
        }

        <!-- Info cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Email</dt>
            <dd class="text-text-primary text-sm truncate">{{ contact()!.email || 'Not provided' }}</dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Phone</dt>
            <dd class="text-text-primary text-sm">{{ contact()!.phone || 'Not provided' }}</dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Type</dt>
            <dd class="text-text-primary text-sm">{{ kindLabel(contact()!.kind) }}</dd>
          </div>
          <div class="bg-surface-raised border border-border-default rounded-lg p-4">
            <dt class="text-xs font-medium text-text-muted uppercase tracking-wide mb-1">Member since</dt>
            <dd class="text-text-primary text-sm tabular-nums">
              {{ contact()!.created_at | date: 'mediumDate' }}
            </dd>
          </div>
        </div>

        <!-- Related entities -->
        <section class="mb-8" aria-labelledby="related-heading">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
            <h2 id="related-heading" class="text-base font-semibold text-text-primary">Related Entities</h2>
            <button
              type="button"
              class="inline-flex items-center gap-2 border border-border-strong hover:border-accent text-text-secondary hover:text-text-primary font-medium px-3 py-1.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              (click)="openCreateGroup()"
              aria-label="Create related entity group"
            >
              <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;">account_tree</mat-icon>
              New group
            </button>
          </div>

          @if (showCreateGroup()) {
            <form
              [formGroup]="createGroupForm"
              (ngSubmit)="submitCreateGroup()"
              class="mb-4 rounded-lg border border-border-default bg-surface p-4 grid grid-cols-1 md:grid-cols-[1fr_180px_120px_auto] gap-3 items-end"
              novalidate
            >
              <div>
                <label for="group-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                  Group name
                </label>
                <input
                  id="group-name"
                  type="text"
                  formControlName="name"
                  class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                  placeholder="e.g. Acme Family Office"
                />
              </div>
              <div>
                <label for="group-type" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                  Type
                </label>
                <select
                  id="group-type"
                  formControlName="group_type"
                  class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                >
                  @for (option of groupTypeOptions; track option.value) {
                    <option [value]="option.value">{{ option.label }}</option>
                  }
                </select>
              </div>
              <div>
                <label for="group-currency" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                  Currency
                </label>
                <input
                  id="group-currency"
                  type="text"
                  formControlName="currency"
                  maxlength="3"
                  class="w-full px-3 py-2 bg-surface-base border border-border-default rounded uppercase text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                  placeholder="USD"
                />
              </div>
              <div class="flex gap-2 justify-end">
                <button
                  type="button"
                  class="px-3 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                  (click)="closeCreateGroup()"
                >Cancel</button>
                <button
                  type="submit"
                  class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  [disabled]="createGroupForm.invalid || groupSaving()"
                >
                  @if (groupSaving()) { Saving… } @else { Create }
                </button>
              </div>
              @if (groupError()) {
                <div class="md:col-span-4 text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2" role="alert">
                  {{ groupError() }}
                </div>
              }
            </form>
          }

          @if (groupsLoading()) {
            <app-skeleton-rows [count]="2" ariaLabel="Loading related entities" />
          } @else if (groupsError()) {
            <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
                 role="alert">
              <mat-icon class="text-base flex-none">error_outline</mat-icon>
              {{ groupsError() }}
            </div>
          } @else if (clientGroups().length === 0) {
            <app-empty-state
              icon="account_tree"
              heading="No related entities"
              message="Groups created for this contact will appear here."
            />
          } @else {
            <div class="space-y-3">
              @for (group of clientGroups(); track group.id) {
                <div class="rounded-lg border border-border-default bg-surface p-4">
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div class="flex flex-wrap items-center gap-2">
                        <h3 class="text-sm font-semibold text-text-primary">{{ group.name }}</h3>
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent/15 text-accent-light">
                          {{ groupTypeLabel(group.group_type) }}
                        </span>
                      </div>
                      <p class="text-xs text-text-muted mt-1">
                        {{ group.member_count }} member{{ group.member_count === 1 ? '' : 's' }}
                        @if (group.currency) { &middot; {{ group.currency }} }
                      </p>
                    </div>
                    <button
                      type="button"
                      class="inline-flex items-center gap-1.5 border border-border-default hover:border-accent text-text-secondary hover:text-text-primary px-3 py-1.5 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                      (click)="openAddMember(group.id)"
                    >
                      <mat-icon class="text-base" style="font-size:1rem;width:1rem;height:1rem;">person_add</mat-icon>
                      Add member
                    </button>
                  </div>

                  <div class="mt-3 flex flex-wrap gap-2">
                    @for (member of group.members; track member.id) {
                      <a
                        [routerLink]="['/app/clients', member.client_id]"
                        class="inline-flex items-center gap-2 rounded border border-border-subtle bg-surface-base px-3 py-2 text-sm hover:border-border-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                        [attr.aria-label]="'Open ' + (member.client_name || 'member contact')"
                      >
                        <span class="font-medium text-text-primary">{{ member.client_name || member.client_id }}</span>
                        <span class="text-xs text-text-muted">{{ roleLabel(member.relationship_role) }}</span>
                        @if (member.is_primary) {
                          <span class="text-xs text-accent-light">Primary</span>
                        }
                      </a>
                    }
                  </div>

                  @if (addMemberGroupId() === group.id) {
                    <form
                      [formGroup]="addMemberForm"
                      (ngSubmit)="submitAddMember(group.id)"
                      class="mt-4 grid grid-cols-1 md:grid-cols-[1fr_180px_120px_auto] gap-3 items-end"
                      novalidate
                    >
                      <div>
                        <label for="member-client" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                          Contact
                        </label>
                        <select
                          id="member-client"
                          formControlName="client_id"
                          class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                        >
                          <option value="">Select contact</option>
                          @for (option of availableMemberOptions(group); track option.id) {
                            <option [value]="option.id">{{ option.name }}</option>
                          }
                        </select>
                      </div>
                      <div>
                        <label for="member-role" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
                          Role
                        </label>
                        <select
                          id="member-role"
                          formControlName="relationship_role"
                          class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
                        >
                          @for (option of roleOptions; track option.value) {
                            <option [value]="option.value">{{ option.label }}</option>
                          }
                        </select>
                      </div>
                      <label class="inline-flex items-center gap-2 text-sm text-text-secondary pb-2">
                        <input type="checkbox" formControlName="is_primary" class="accent-accent" />
                        Primary
                      </label>
                      <div class="flex gap-2 justify-end">
                        <button
                          type="button"
                          class="px-3 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                          (click)="closeAddMember()"
                        >Cancel</button>
                        <button
                          type="submit"
                          class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-3 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                          [disabled]="addMemberForm.invalid || memberSaving()"
                        >
                          @if (memberSaving()) { Adding… } @else { Add }
                        </button>
                      </div>
                      @if (memberError()) {
                        <div class="md:col-span-4 text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2" role="alert">
                          {{ memberError() }}
                        </div>
                      }
                    </form>
                  }
                </div>
              }
            </div>
          }
        </section>

        <!-- AR section — customers and both -->
        @if (isCustomer()) {
          <section class="mb-8" aria-labelledby="ar-heading">
            <div class="flex items-center justify-between mb-3">
              <h2 id="ar-heading" class="text-base font-semibold text-text-primary">Outstanding Invoices</h2>
              <a
                routerLink="/app/invoices"
                class="text-sm text-accent-light hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                aria-label="View all invoices"
              >View all invoices</a>
            </div>

            @if (invoicesLoading()) {
              <app-skeleton-rows [count]="3" ariaLabel="Loading invoices" />
            } @else if (invoicesError()) {
              <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
                   role="alert">
                <mat-icon class="text-base flex-none">error_outline</mat-icon>
                {{ invoicesError() }}
              </div>
            } @else if (invoices().length === 0) {
              <app-empty-state
                icon="receipt_long"
                heading="No outstanding invoices"
                message="Invoices with status Sent, Approved, or Overdue will appear here."
              />
            } @else {
              <div class="rounded-lg overflow-hidden border border-border-default">
                <!-- Table header -->
                <div class="grid grid-cols-[1fr_auto_auto_auto_auto] gap-x-4 px-4 py-2 bg-surface-raised border-b border-border-default text-xs font-medium text-text-muted uppercase tracking-wide">
                  <span>Invoice #</span>
                  <span class="text-right">Date</span>
                  <span class="text-right">Amount</span>
                  <span class="text-right">Status</span>
                  <span class="text-right">Days</span>
                </div>
                @for (inv of invoices(); track inv.id) {
                  <a
                    [routerLink]="['/app/invoices', inv.id]"
                    class="grid grid-cols-[1fr_auto_auto_auto_auto] gap-x-4 px-4 py-3 border-b border-border-subtle last:border-0 hover:bg-surface-raised transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent rounded"
                    [attr.aria-label]="'Invoice ' + inv.invoice_number"
                  >
                    <span class="text-sm font-mono font-medium text-accent-light">{{ inv.invoice_number }}</span>
                    <span class="text-sm text-text-secondary tabular-nums text-right">{{ inv.issue_date || '—' }}</span>
                    <span class="text-sm font-mono text-text-primary tabular-nums text-right">
                      {{ inv.total | money: inv.currency }}
                    </span>
                    <span
                      class="text-xs px-2 py-0.5 rounded-full font-medium text-right self-center"
                      [class]="invoiceStatusClass(inv.status)"
                    >{{ invoiceStatusLabel(inv.status) }}</span>
                    <span class="text-sm text-text-muted tabular-nums text-right">
                      {{ daysSinceDisplay(inv.issue_date) }}
                    </span>
                  </a>
                }
              </div>
              <!-- Total outstanding -->
              <div class="mt-3 flex justify-end">
                <p class="text-sm font-medium text-text-primary">
                  Total Outstanding:
                  <span class="font-mono font-bold ml-2 tabular-nums">
                    {{ arTotal() | money: (invoices()[0].currency || 'USD') }}
                  </span>
                </p>
              </div>
            }
          </section>
        }

        <!-- AP section — vendors and both -->
        @if (isVendor()) {
          <section class="mb-8" aria-labelledby="ap-heading">
            <div class="flex items-center justify-between mb-3">
              <h2 id="ap-heading" class="text-base font-semibold text-text-primary">Outstanding Bills</h2>
              <a
                routerLink="/app/billing-runs"
                class="text-sm text-accent-light hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
                aria-label="Pay bills"
              >Pay Bills</a>
            </div>

            @if (billsLoading()) {
              <app-skeleton-rows [count]="3" ariaLabel="Loading bills" />
            } @else if (billsError()) {
              <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low flex items-center gap-2"
                   role="alert">
                <mat-icon class="text-base flex-none">error_outline</mat-icon>
                {{ billsError() }}
              </div>
            } @else if (bills().length === 0) {
              <app-empty-state
                icon="description"
                heading="No outstanding bills"
                message="Bills with status Draft or Approved will appear here."
              />
            } @else {
              <div class="rounded-lg overflow-hidden border border-border-default">
                <!-- Table header -->
                <div class="grid grid-cols-[1fr_auto_auto_auto_auto] gap-x-4 px-4 py-2 bg-surface-raised border-b border-border-default text-xs font-medium text-text-muted uppercase tracking-wide">
                  <span>Bill #</span>
                  <span class="text-right">Date</span>
                  <span class="text-right">Amount</span>
                  <span class="text-right">Status</span>
                  <span class="text-right">Due</span>
                </div>
                @for (bill of bills(); track bill.id) {
                  <a
                    [routerLink]="['/app/bills', bill.id]"
                    class="grid grid-cols-[1fr_auto_auto_auto_auto] gap-x-4 px-4 py-3 border-b border-border-subtle last:border-0 hover:bg-surface-raised transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent rounded"
                    [attr.aria-label]="'Bill ' + bill.bill_number"
                  >
                    <span class="text-sm font-mono font-medium text-accent-light">{{ bill.bill_number }}</span>
                    <span class="text-sm text-text-secondary tabular-nums text-right">{{ bill.issue_date || '—' }}</span>
                    <span class="text-sm font-mono text-text-primary tabular-nums text-right">
                      {{ bill.total | money: bill.currency }}
                    </span>
                    <span
                      class="text-xs px-2 py-0.5 rounded-full font-medium text-right self-center"
                      [class]="billStatusClass(bill.status)"
                    >{{ billStatusLabel(bill.status) }}</span>
                    <span class="text-sm tabular-nums text-right"
                          [class]="dueDaysClass(bill.due_date)">
                      {{ dueDaysDisplay(bill.due_date) }}
                    </span>
                  </a>
                }
              </div>
              <!-- Total outstanding -->
              <div class="mt-3 flex justify-end">
                <p class="text-sm font-medium text-text-primary">
                  Total Outstanding:
                  <span class="font-mono font-bold ml-2 tabular-nums">
                    {{ apTotal() | money: (bills()[0].currency || 'USD') }}
                  </span>
                </p>
              </div>
            }
          </section>
        }

      } <!-- end @if contact() -->

    </div>

    <!-- ── Edit slide-in panel ─────────────────────────────────────────── -->
    @if (showEditPanel()) {
      <div
        class="fixed inset-0 bg-black/50 z-40"
        (click)="closeEditPanel()"
        aria-hidden="true"
      ></div>
      <aside
        class="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border-default z-50 flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-contact-title"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-default flex-none">
          <h2 id="edit-contact-title" class="text-base font-semibold text-text-primary">Edit contact</h2>
          <button
            class="text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeEditPanel()"
            aria-label="Close edit panel"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>

        <form
          [formGroup]="editForm"
          (ngSubmit)="submitEdit()"
          class="flex-1 overflow-y-auto px-6 py-5 space-y-5"
          novalidate
        >
          <!-- Name -->
          <div>
            <label for="edit-name" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              Name <span aria-hidden="true">*</span>
            </label>
            <input
              id="edit-name"
              type="text"
              formControlName="name"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="Contact name"
            />
            @if (editForm.controls.name.touched && editForm.controls.name.errors) {
              <p class="text-xs text-confidence-low mt-1" role="alert">Name is required.</p>
            }
          </div>

          <!-- Email -->
          <div>
            <label for="edit-email" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Email</label>
            <input
              id="edit-email"
              type="email"
              formControlName="email"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="contact@example.com"
            />
          </div>

          <!-- Phone -->
          <div>
            <label for="edit-phone" class="block text-xs uppercase tracking-wide text-text-muted mb-2">Phone</label>
            <input
              id="edit-phone"
              type="tel"
              formControlName="phone"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
              placeholder="+1 (555) 000-0000"
            />
          </div>

          <!-- Kind -->
          <div>
            <label for="edit-kind" class="block text-xs uppercase tracking-wide text-text-muted mb-2">
              Contact Type <span aria-hidden="true">*</span>
            </label>
            <select
              id="edit-kind"
              formControlName="kind"
              class="w-full px-3 py-2 bg-surface-base border border-border-default rounded text-text-primary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent text-sm"
            >
              <option value="customer">Customer (client you bill)</option>
              <option value="vendor">Vendor (supplier you pay)</option>
              <option value="both">Both (Customer &amp; Vendor)</option>
            </select>
          </div>

          @if (editError()) {
            <div
              role="alert"
              class="text-sm text-confidence-low bg-confidence-low/10 border border-confidence-low/30 rounded px-3 py-2"
            >{{ editError() }}</div>
          }
        </form>

        <div class="flex-none px-6 py-4 border-t border-border-default flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="closeEditPanel()"
          >Cancel</button>
          <button
            type="button"
            class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            [disabled]="editForm.invalid || saving()"
            (click)="submitEdit()"
          >
            @if (saving()) { Saving… } @else { Save changes }
          </button>
        </div>
      </aside>
    }
  `,
  styles: [':host { display: block; }'],
})
export class ClientDetailComponent implements OnInit {
  private route  = inject(ActivatedRoute);
  private router = inject(Router);
  private http   = inject(HttpClient);
  private fb     = inject(FormBuilder);

  // Contact
  loading = signal(true);
  error   = signal<string | null>(null);
  contact = signal<ContactDetail | null>(null);

  // AR
  invoicesLoading = signal(false);
  invoicesError   = signal<string | null>(null);
  invoices        = signal<InvoiceSummary[]>([]);

  // AP
  billsLoading = signal(false);
  billsError   = signal<string | null>(null);
  bills        = signal<BillSummary[]>([]);

  // Related entities
  groupsLoading = signal(false);
  groupsError = signal<string | null>(null);
  clientGroups = signal<ClientGroup[]>([]);
  allContacts = signal<ContactOption[]>([]);
  showCreateGroup = signal(false);
  groupSaving = signal(false);
  groupError = signal<string | null>(null);
  addMemberGroupId = signal<string | null>(null);
  memberSaving = signal(false);
  memberError = signal<string | null>(null);
  createGroupForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    group_type: ['client_relationship' as ClientGroupType, [Validators.required]],
    currency: [''],
  });
  addMemberForm = this.fb.nonNullable.group({
    client_id: ['', [Validators.required]],
    relationship_role: ['subsidiary' as ClientGroupMemberRole, [Validators.required]],
    is_primary: [false],
  });

  readonly groupTypeOptions: { label: string; value: ClientGroupType }[] = [
    { label: 'Relationship', value: 'client_relationship' },
    { label: 'Family office', value: 'family_office' },
    { label: 'Portfolio', value: 'portfolio' },
    { label: 'Corporate group', value: 'corporate_group' },
    { label: 'Billing group', value: 'billing_group' },
    { label: 'Other', value: 'other' },
  ];
  readonly roleOptions: { label: string; value: ClientGroupMemberRole }[] = [
    { label: 'Subsidiary', value: 'subsidiary' },
    { label: 'Parent', value: 'parent' },
    { label: 'Trust', value: 'trust' },
    { label: 'SPV', value: 'spv' },
    { label: 'Individual', value: 'individual' },
    { label: 'Portfolio company', value: 'portfolio_company' },
    { label: 'Billing entity', value: 'billing_entity' },
    { label: 'Other', value: 'other' },
  ];

  // Edit panel
  showEditPanel = signal(false);
  saving        = signal(false);
  saveMessage   = signal<string | null>(null);
  editError     = signal<string | null>(null);
  editForm      = this.fb.nonNullable.group({
    name:  ['', [Validators.required]],
    email: [''],
    phone: [''],
    kind:  ['customer' as ContactKind, [Validators.required]],
  });

  // Computed helpers
  isCustomer = computed(() => {
    const k = this.contact()?.kind;
    return k === 'customer' || k === 'both';
  });
  isVendor = computed(() => {
    const k = this.contact()?.kind;
    return k === 'vendor' || k === 'both';
  });

  arTotal = computed(() =>
    this.invoices()
      .reduce((sum, inv) => sum + Number(inv.total), 0)
      .toFixed(2),
  );

  apTotal = computed(() =>
    this.bills()
      .reduce((sum, b) => sum + Number(b.total), 0)
      .toFixed(2),
  );

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.router.navigate(['/app/clients']);
      return;
    }

    this.http.get<ContactDetail>(`/api/v1/clients/${id}`).subscribe({
      next: (data) => {
        this.contact.set(data);
        this.loading.set(false);
        this.loadArAp(id, data.kind);
        this.loadGroups(id);
        this.loadContactOptions();
      },
      error: (err: unknown) => {
        this.error.set(userMessageForError(err, 'Contact'));
        this.loading.set(false);
      },
    });
  }

  private loadArAp(id: string, kind: ContactKind): void {
    if (kind === 'customer' || kind === 'both') {
      this.invoicesLoading.set(true);
      this.http
        .get<{ items: InvoiceSummary[] }>(
          `/api/v1/invoices?client_id=${id}&status=sent,approved,overdue`,
        )
        .subscribe({
          next: (res) => {
            this.invoices.set(res.items ?? []);
            this.invoicesLoading.set(false);
          },
          error: (err: unknown) => {
            this.invoicesError.set(userMessageForError(err, 'Invoices'));
            this.invoicesLoading.set(false);
          },
        });
    }

    if (kind === 'vendor' || kind === 'both') {
      this.billsLoading.set(true);
      this.http
        .get<{ items: BillSummary[] }>(
          `/api/v1/bills?client_id=${id}&status=draft,approved`,
        )
        .subscribe({
          next: (res) => {
            this.bills.set(res.items ?? []);
            this.billsLoading.set(false);
          },
          error: (err: unknown) => {
            this.billsError.set(userMessageForError(err, 'Bills'));
            this.billsLoading.set(false);
          },
        });
    }
  }

  private loadGroups(clientId: string): void {
    this.groupsLoading.set(true);
    this.groupsError.set(null);
    this.http.get<{ items: ClientGroup[] }>(`/api/v1/client-groups?client_id=${clientId}`).subscribe({
      next: (res) => {
        this.clientGroups.set(res.items ?? []);
        this.groupsLoading.set(false);
      },
      error: (err: unknown) => {
        this.groupsError.set(userMessageForError(err, 'Related entities'));
        this.groupsLoading.set(false);
      },
    });
  }

  private loadContactOptions(): void {
    this.http.get<{ items: ContactOption[] }>('/api/v1/clients').subscribe({
      next: (res) => this.allContacts.set(res.items ?? []),
      error: () => this.allContacts.set([]),
    });
  }

  goBack(): void {
    this.router.navigate(['/app/clients']);
  }

  openEditPanel(): void {
    const c = this.contact();
    if (!c) return;
    this.editForm.reset({
      name:  c.name,
      email: c.email ?? '',
      phone: c.phone ?? '',
      kind:  c.kind,
    });
    this.editError.set(null);
    this.showEditPanel.set(true);
  }

  closeEditPanel(): void {
    this.showEditPanel.set(false);
  }

  openCreateGroup(): void {
    const c = this.contact();
    this.createGroupForm.reset({
      name: c ? `${c.name} Group` : '',
      group_type: 'client_relationship',
      currency: '',
    });
    this.groupError.set(null);
    this.showCreateGroup.set(true);
  }

  closeCreateGroup(): void {
    this.showCreateGroup.set(false);
  }

  submitCreateGroup(): void {
    if (this.createGroupForm.invalid) {
      this.createGroupForm.markAllAsTouched();
      return;
    }
    const c = this.contact();
    if (!c) return;

    const value = this.createGroupForm.getRawValue();
    this.groupSaving.set(true);
    this.groupError.set(null);
    this.http.post<ClientGroup>('/api/v1/client-groups', {
      name: value.name,
      group_type: value.group_type,
      primary_client_id: c.id,
      billing_client_id: c.kind === 'vendor' ? null : c.id,
      currency: value.currency ? value.currency.toUpperCase() : null,
    }).subscribe({
      next: (group) => {
        this.clientGroups.update(groups => [group, ...groups]);
        this.groupSaving.set(false);
        this.closeCreateGroup();
      },
      error: (err: unknown) => {
        this.groupSaving.set(false);
        this.groupError.set(userMessageForError(err, 'Create related entity group'));
      },
    });
  }

  openAddMember(groupId: string): void {
    if (this.allContacts().length === 0) {
      this.loadContactOptions();
    }
    this.addMemberForm.reset({
      client_id: '',
      relationship_role: 'subsidiary',
      is_primary: false,
    });
    this.memberError.set(null);
    this.addMemberGroupId.set(groupId);
  }

  closeAddMember(): void {
    this.addMemberGroupId.set(null);
  }

  submitAddMember(groupId: string): void {
    if (this.addMemberForm.invalid) {
      this.addMemberForm.markAllAsTouched();
      return;
    }
    const c = this.contact();
    if (!c) return;

    const value = this.addMemberForm.getRawValue();
    this.memberSaving.set(true);
    this.memberError.set(null);
    this.http.post<ClientGroupMember>(`/api/v1/client-groups/${groupId}/members`, value).subscribe({
      next: () => {
        this.memberSaving.set(false);
        this.closeAddMember();
        this.loadGroups(c.id);
      },
      error: (err: unknown) => {
        this.memberSaving.set(false);
        this.memberError.set(userMessageForError(err, 'Add related entity member'));
      },
    });
  }

  submitEdit(): void {
    if (this.editForm.invalid) {
      this.editForm.markAllAsTouched();
      return;
    }
    const c = this.contact();
    if (!c) return;

    this.saving.set(true);
    this.editError.set(null);

    const v = this.editForm.getRawValue();
    const payload: Partial<ContactDetail> = {
      name:  v.name,
      email: v.email || null,
      phone: v.phone || null,
      kind:  v.kind as ContactKind,
    };

    // TODO (#212): PATCH /api/v1/clients/{id} — verify endpoint exists in Karya.
    // If missing, Karya should add it in a follow-up; this component is wired
    // for it and will work once the backend route is live.
    this.http.patch<ContactDetail>(`/api/v1/clients/${c.id}`, payload).subscribe({
      next: (updated) => {
        this.contact.set(updated);
        this.saving.set(false);
        this.closeEditPanel();
        this.saveMessage.set('Contact updated.');
        // If kind changed, reload AR/AP sections with updated kind
        this.invoices.set([]);
        this.bills.set([]);
        this.loadArAp(c.id, updated.kind);
        setTimeout(() => this.saveMessage.set(null), 5000);
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.editError.set(userMessageForError(err, 'Update contact'));
      },
    });
  }

  // ── Display helpers ──────────────────────────────────────────────────────

  kindLabel(kind: ContactKind): string {
    switch (kind) {
      case 'customer': return 'Customer';
      case 'vendor':   return 'Vendor';
      case 'both':     return 'Both';
    }
  }

  kindBadgeClass(kind: ContactKind): string {
    switch (kind) {
      case 'customer': return 'bg-blue-500/20 text-blue-300';
      case 'vendor':   return 'bg-amber-500/20 text-amber-300';
      case 'both':     return 'bg-purple-500/20 text-purple-300';
    }
  }

  groupTypeLabel(groupType: string): string {
    const labels: Record<string, string> = {
      family_office: 'Family office',
      portfolio: 'Portfolio',
      corporate_group: 'Corporate group',
      billing_group: 'Billing group',
      client_relationship: 'Relationship',
      other: 'Other',
    };
    return labels[groupType] ?? groupType.replaceAll('_', ' ');
  }

  roleLabel(role: string): string {
    const labels: Record<string, string> = {
      parent: 'Parent',
      subsidiary: 'Subsidiary',
      trust: 'Trust',
      spv: 'SPV',
      individual: 'Individual',
      portfolio_company: 'Portfolio company',
      billing_entity: 'Billing entity',
      other: 'Other',
    };
    return labels[role] ?? role.replaceAll('_', ' ');
  }

  availableMemberOptions(group: ClientGroup): ContactOption[] {
    const currentId = this.contact()?.id;
    const existingIds = new Set(group.members.map(member => member.client_id));
    return this.allContacts().filter(option =>
      option.id !== currentId && !existingIds.has(option.id)
    );
  }

  avatarBgClass(kind: ContactKind): string {
    switch (kind) {
      case 'customer': return 'bg-blue-700';
      case 'vendor':   return 'bg-amber-700';
      case 'both':     return 'bg-purple-700';
    }
  }

  invoiceStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Draft', approved: 'Approved', sent: 'Sent',
      paid: 'Paid', overdue: 'Overdue', void: 'Void',
    };
    return labels[status] ?? status;
  }

  invoiceStatusClass(status: string): string {
    switch (status) {
      case 'approved': return 'bg-indigo-950 text-indigo-400';
      case 'sent':     return 'bg-blue-950 text-blue-400';
      case 'overdue':  return 'bg-confidence-low/10 text-confidence-low';
      default:         return 'bg-surface-raised text-text-muted';
    }
  }

  billStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: 'Draft', approved: 'Approved', paid: 'Paid',
      overdue: 'Overdue', voided: 'Voided',
    };
    return labels[status] ?? status;
  }

  billStatusClass(status: string): string {
    switch (status) {
      case 'approved': return 'bg-indigo-950 text-indigo-400';
      case 'paid':     return 'bg-accent/15 text-accent-light';
      case 'overdue':  return 'bg-confidence-low/10 text-confidence-low';
      default:         return 'bg-surface-raised text-text-muted';
    }
  }

  daysSinceDisplay(dateStr: string | null): string {
    const days = daysSince(dateStr);
    if (days === null) return '—';
    if (days === 0) return 'Today';
    if (days < 0) return `In ${Math.abs(days)}d`;
    return `${days}d ago`;
  }

  dueDaysDisplay(dateStr: string | null): string {
    if (!dateStr) return '—';
    const days = daysSince(dateStr); // positive = past due
    if (days === null) return '—';
    if (days < 0) return `Due in ${Math.abs(days)}d`;
    if (days === 0) return 'Due today';
    return `${days}d overdue`;
  }

  dueDaysClass(dateStr: string | null): string {
    const days = daysSince(dateStr);
    if (days === null) return 'text-text-muted';
    if (days > 0) return 'text-confidence-low font-medium'; // overdue
    if (days > -7) return 'text-amber-400'; // due within a week
    return 'text-text-muted';
  }
}
