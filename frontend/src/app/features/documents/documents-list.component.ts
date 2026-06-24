/**
 * DocumentsListComponent — uploaded-document inventory.
 *
 * Shows every document the tenant has uploaded via the Copilot composer with
 * its extraction status. Documents are grouped by type (engagement letters /
 * invoices / receipts) with filter tabs, and can be deleted (#146).
 */
import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { DecisionTimelineComponent } from '../../shared/components/decision-timeline.component';

export interface DocumentSummary {
  id: string;
  filename: string;
  mime_type: string;
  document_type: 'engagement_letter' | 'expense' | 'vendor_invoice';
  status: 'uploaded' | 'extracting' | 'extracted' | 'failed';
  created_at: string;
}

interface DocGroup {
  type: string;
  label: string;
  docs: DocumentSummary[];
}

/** Display order + labels for the document-type groups and filter tabs. */
const TYPE_LABELS: Record<string, string> = {
  engagement_letter: 'Engagement letters',
  vendor_invoice: 'Invoices',
  expense: 'Receipts & expenses',
};
const TYPE_ORDER = ['engagement_letter', 'vendor_invoice', 'expense'];

@Component({
  selector: 'app-documents-list',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatTooltipModule, RouterLink, DecisionTimelineComponent],
  template: `
    <div class="p-6 bg-surface-base min-h-full">
      <!-- Header -->
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-text-primary">Documents</h1>
          <p class="text-sm text-text-muted mt-1">
            Documents uploaded to Aethos for AI extraction.
          </p>
        </div>
        <a
          routerLink="/app/copilot"
          class="inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          aria-label="Upload a new document via Copilot"
        >
          <mat-icon class="text-base leading-none">upload_file</mat-icon>
          Upload document
        </a>
      </div>

      <!-- Filter tabs -->
      @if (!loading() && documents().length > 0) {
        <div class="flex gap-1 mb-5 flex-wrap">
          @for (tab of filterTabs(); track tab.value) {
            <button
              (click)="typeFilter.set(tab.value)"
              class="px-3 py-1.5 text-xs rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [class]="typeFilter() === tab.value
                ? 'bg-surface-raised text-text-primary font-medium'
                : 'text-text-muted hover:text-text-primary hover:bg-surface'"
              [attr.aria-pressed]="typeFilter() === tab.value"
            >{{ tab.label }} ({{ tab.count }})</button>
          }
        </div>
      }

      <!-- Loading -->
      @if (loading()) {
        <div class="flex items-center justify-center py-16">
          <div class="w-6 h-6 rounded-full border-2 border-accent border-t-transparent animate-spin" aria-label="Loading documents"></div>
        </div>
      }

      <!-- Error -->
      @if (error() && !loading()) {
        <div class="rounded-lg border border-confidence-low/30 bg-confidence-low/10 px-4 py-3 text-sm text-confidence-low" role="alert">
          <mat-icon class="text-base align-middle mr-1">error_outline</mat-icon>
          {{ error() }}
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && !error() && documents().length === 0) {
        <div class="flex flex-col items-center justify-center py-20 text-center">
          <div class="w-14 h-14 rounded-full bg-surface-raised border border-border-default flex items-center justify-center mb-4">
            <mat-icon class="text-text-muted" style="font-size:1.75rem;width:1.75rem;height:1.75rem;">upload_file</mat-icon>
          </div>
          <p class="text-text-primary font-medium mb-1">No documents yet</p>
          <p class="text-text-muted text-sm max-w-xs">
            Upload an engagement letter, invoice, or receipt via the Copilot
            and Aethos will extract the details for you.
          </p>
          <a
            routerLink="/app/copilot"
            class="mt-5 inline-flex items-center gap-2 bg-accent hover:bg-accent-hover text-accent-on font-medium px-4 py-2 rounded text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <mat-icon class="text-base leading-none">auto_awesome</mat-icon>
            Go to Copilot
          </a>
        </div>
      }

      <!-- Grouped document list -->
      @if (!loading() && documents().length > 0) {
        <div class="space-y-6">
          @for (group of groups(); track group.type) {
            <div>
              <h2 class="text-xs font-semibold uppercase tracking-wide text-text-muted mb-2">
                {{ group.label }} <span class="text-text-disabled">({{ group.docs.length }})</span>
              </h2>
              <div class="space-y-2">
                @for (doc of group.docs; track doc.id) {
                  <div class="bg-surface border border-border-default rounded-lg px-4 py-3 hover:border-border-strong transition-colors">
                    <div class="flex items-center gap-4">

                      <!-- Icon by status -->
                      <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-none"
                        [class]="statusIconClass(doc.status)"
                        [attr.aria-label]="'Status: ' + doc.status"
                      >
                        <mat-icon class="text-base leading-none">{{ statusIcon(doc.status) }}</mat-icon>
                      </div>

                      <!-- Name + meta -->
                      <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-text-primary truncate">{{ doc.filename }}</p>
                        <p class="text-xs text-text-muted mt-0.5">
                          {{ doc.mime_type }} &middot; {{ doc.created_at | date:'medium' }}
                        </p>
                      </div>

                      <!-- Status badge -->
                      <span class="flex-none text-xs px-2.5 py-1 rounded-full font-medium"
                        [class]="statusBadgeClass(doc.status)"
                      >{{ statusLabel(doc.status) }}</span>

                      <!-- Audit timeline -->
                      <button
                        (click)="toggleAudit(doc.id)"
                        class="flex-none p-1.5 rounded-md text-text-muted hover:text-accent-light hover:bg-accent/10 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                        [attr.aria-label]="'Show decision timeline for ' + doc.filename"
                        matTooltip="Decision timeline"
                      >
                        <mat-icon class="text-base leading-none">{{ auditDocId() === doc.id ? 'history_toggle_off' : 'history' }}</mat-icon>
                      </button>

                      <!-- Delete -->
                      <button
                        (click)="confirmDelete(doc)"
                        [disabled]="deleting() === doc.id"
                        class="flex-none p-1.5 rounded-md text-text-muted hover:text-confidence-low hover:bg-confidence-low/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low"
                        [attr.aria-label]="'Delete ' + doc.filename"
                        matTooltip="Delete document"
                      >
                        <mat-icon class="text-base leading-none">{{ deleting() === doc.id ? 'hourglass_top' : 'delete_outline' }}</mat-icon>
                      </button>
                    </div>

                    @if (auditDocId() === doc.id) {
                      <div class="mt-3 border-t border-border-subtle pt-3">
                        <app-decision-timeline entityType="document" [entityId]="doc.id" title="Document decision timeline" />
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          }
        </div>
      }

      <!-- Delete confirmation -->
      @if (pendingDelete(); as doc) {
        <div class="fixed inset-0 z-40 bg-black/50 flex items-center justify-center p-4" (click)="pendingDelete.set(null)">
          <div class="bg-surface-base border border-border-default rounded-lg shadow-xl max-w-sm w-full p-5" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
            <h2 class="text-sm font-semibold text-text-primary mb-2">Delete this document?</h2>
            <p class="text-sm text-text-muted mb-4 break-words">
              <span class="text-text-secondary">{{ doc.filename }}</span> will be permanently removed. This cannot be undone.
            </p>
            <div class="flex items-center gap-2 justify-end">
              <button
                (click)="pendingDelete.set(null)"
                class="px-4 py-2 text-sm font-medium rounded border border-border-strong text-text-secondary hover:text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-border-strong"
              >Cancel</button>
              <button
                (click)="deleteDoc(doc)"
                class="px-4 py-2 text-sm font-medium rounded bg-confidence-low hover:bg-confidence-low/80 text-text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-confidence-low"
              >Delete</button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
})
export class DocumentsListComponent implements OnInit {
  private http = inject(HttpClient);

  loading   = signal(true);
  error     = signal<string | null>(null);
  documents = signal<DocumentSummary[]>([]);
  typeFilter = signal<string>('all');
  pendingDelete = signal<DocumentSummary | null>(null);
  deleting = signal<string | null>(null);
  auditDocId = signal<string | null>(null);

  /** Filter tabs with live counts, in canonical type order. */
  filterTabs = computed(() => {
    const docs = this.documents();
    const tabs: { value: string; label: string; count: number }[] = [
      { value: 'all', label: 'All', count: docs.length },
    ];
    for (const t of TYPE_ORDER) {
      const count = docs.filter(d => d.document_type === t).length;
      if (count > 0) tabs.push({ value: t, label: TYPE_LABELS[t], count });
    }
    return tabs;
  });

  /** Documents grouped by type, honouring the active filter. */
  groups = computed<DocGroup[]>(() => {
    const filter = this.typeFilter();
    const docs = this.documents();
    const types = filter === 'all' ? TYPE_ORDER : [filter];
    return types
      .map(t => ({
        type: t,
        label: TYPE_LABELS[t] ?? t,
        docs: docs.filter(d => d.document_type === t),
      }))
      .filter(g => g.docs.length > 0);
  });

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.http.get<DocumentSummary[]>('/api/v1/documents').subscribe({
      next: (docs) => {
        this.documents.set(docs);
        this.loading.set(false);
      },
      error: (err: { status?: number }) => {
        if (err.status === 404) {
          this.documents.set([]);
        } else {
          this.error.set('Could not load documents. Please refresh to try again.');
        }
        this.loading.set(false);
      },
    });
  }

  confirmDelete(doc: DocumentSummary): void {
    this.pendingDelete.set(doc);
  }

  toggleAudit(docId: string): void {
    this.auditDocId.set(this.auditDocId() === docId ? null : docId);
  }

  deleteDoc(doc: DocumentSummary): void {
    this.pendingDelete.set(null);
    this.deleting.set(doc.id);
    this.http.delete(`/api/v1/documents/${doc.id}`).subscribe({
      next: () => {
        this.documents.update(ds => ds.filter(d => d.id !== doc.id));
        this.deleting.set(null);
        // If the active filter group is now empty, fall back to All.
        if (this.typeFilter() !== 'all' && !this.documents().some(d => d.document_type === this.typeFilter())) {
          this.typeFilter.set('all');
        }
      },
      error: () => {
        this.error.set('Could not delete the document. Please try again.');
        this.deleting.set(null);
      },
    });
  }

  statusIcon(status: DocumentSummary['status']): string {
    const icons: Record<DocumentSummary['status'], string> = {
      uploaded:   'upload_file',
      extracting: 'hourglass_top',
      extracted:  'check_circle',
      failed:     'error_outline',
    };
    return icons[status] ?? 'description';
  }

  statusIconClass(status: DocumentSummary['status']): string {
    const classes: Record<DocumentSummary['status'], string> = {
      uploaded:   'bg-surface-raised text-text-muted',
      extracting: 'bg-confidence-med/10 text-confidence-med',
      extracted:  'bg-accent/15 text-accent-light',
      failed:     'bg-confidence-low/10 text-confidence-low',
    };
    return classes[status] ?? 'bg-surface-raised text-text-muted';
  }

  statusBadgeClass(status: DocumentSummary['status']): string {
    const classes: Record<DocumentSummary['status'], string> = {
      uploaded:   'bg-surface-raised text-text-muted border border-border-default',
      extracting: 'bg-confidence-med/10 text-confidence-med border border-confidence-med/30',
      extracted:  'bg-accent/15 text-accent-light border border-accent/30',
      failed:     'bg-confidence-low/10 text-confidence-low border border-confidence-low/30',
    };
    return classes[status] ?? 'bg-surface-raised text-text-muted';
  }

  statusLabel(status: DocumentSummary['status']): string {
    const labels: Record<DocumentSummary['status'], string> = {
      uploaded:   'Uploaded',
      extracting: 'Extracting',
      extracted:  'Extracted',
      failed:     'Failed',
    };
    return labels[status] ?? status;
  }
}
