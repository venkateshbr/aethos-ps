/**
 * DocumentsListComponent — uploaded-document inventory.
 *
 * Shows every document the tenant has uploaded via the Copilot composer
 * with its current extraction status (uploaded → extracting → extracted
 * → failed).  Read-only for now — uploads happen via the Copilot.
 */
import { Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';

export interface DocumentSummary {
  id: string;
  filename: string;
  mime_type: string;
  status: 'uploaded' | 'extracting' | 'extracted' | 'failed';
  created_at: string;
}

@Component({
  selector: 'app-documents-list',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, RouterLink],
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

      <!-- Document list -->
      @if (!loading() && documents().length > 0) {
        <div class="space-y-2">
          @for (doc of documents(); track doc.id) {
            <div class="flex items-center gap-4 bg-surface border border-border-default rounded-lg px-4 py-3 hover:border-border-strong transition-colors">

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
            </div>
          }
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

  ngOnInit(): void {
    this.http.get<DocumentSummary[]>('/api/v1/documents').subscribe({
      next: (docs) => {
        this.documents.set(docs);
        this.loading.set(false);
      },
      error: (err: { status?: number }) => {
        if (err.status === 404) {
          // Endpoint not yet live — show empty state gracefully
          this.documents.set([]);
        } else {
          this.error.set('Could not load documents. Please refresh to try again.');
        }
        this.loading.set(false);
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
