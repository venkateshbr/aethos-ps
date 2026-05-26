import { Component, inject, input, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

/**
 * Renders a small "Source document" button that fetches a presigned URL for
 * the underlying upload (engagement letter / receipt / vendor invoice) and
 * opens it in a new tab.
 *
 * Backend contract: `GET /api/v1/documents/{id}/url?expires_in=3600`
 *   → `{ url: string; original_filename: string; ... }`  (tenant-scoped)
 *
 * Issue #127 — surface source-document link on extraction-derived rows.
 */
@Component({
  selector: 'app-source-document-link',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <button
      type="button"
      (click)="open()"
      [disabled]="loading()"
      class="inline-flex items-center gap-1.5 text-xs text-accent-light hover:text-accent transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
      [title]="filename() || 'Open source document'"
      [attr.aria-label]="filename() ? 'Open source document ' + filename() : 'Open source document'"
    >
      <mat-icon aria-hidden="true" style="font-size:1rem;width:1rem;height:1rem;">description</mat-icon>
      @if (loading()) {
        <span>Loading…</span>
      } @else {
        <span>{{ label() }}</span>
      }
    </button>
    @if (error()) {
      <span class="ml-2 text-xs text-confidence-low" role="alert">Could not open document</span>
    }
  `,
  styles: [':host { display: inline-flex; align-items: center; }'],
})
export class SourceDocumentLinkComponent {
  /** UUID of the row in `documents` table. Required. */
  documentId = input.required<string>();
  /** Override the button copy (defaults to "Source document"). */
  label = input<string>('Source document');

  protected loading = signal(false);
  protected error = signal(false);
  protected filename = signal<string | null>(null);

  private http = inject(HttpClient);

  async open(): Promise<void> {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set(false);
    try {
      const res = await firstValueFrom(
        this.http.get<{ url: string; original_filename: string }>(
          `/api/v1/documents/${this.documentId()}/url?expires_in=3600`,
        ),
      );
      this.filename.set(res.original_filename ?? null);
      window.open(res.url, '_blank', 'noopener,noreferrer');
    } catch {
      this.error.set(true);
    } finally {
      this.loading.set(false);
    }
  }
}
