import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { GUIDE_CATALOG, GuideEntry } from './guide-catalog.generated';

@Component({
  selector: 'app-guide-reader',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="min-h-full bg-surface-base text-text-primary">
      @if (guide(); as currentGuide) {
        <div class="mx-auto max-w-[92rem] px-5 py-8 md:px-8 md:py-12">
          <div class="guide-print-hidden flex flex-wrap items-center justify-between gap-3">
            <a
              routerLink="/app/guides"
              class="inline-flex items-center gap-2 rounded-md text-sm text-text-muted transition-colors hover:text-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
            ><span aria-hidden="true">←</span> All guides</a>

            <button
              type="button"
              (click)="exportPdf()"
              [disabled]="loading() || error()"
              class="inline-flex items-center gap-2 rounded-md border border-border-default bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition-colors hover:border-border-strong hover:bg-surface-raised hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              aria-label="Export this guide as a PDF"
            >
              <span aria-hidden="true">⇩</span> Export PDF
            </button>
          </div>

          <div class="mt-8 grid items-start gap-10 xl:grid-cols-[13rem_minmax(0,52rem)_15rem] xl:justify-center">
            <aside class="guide-print-hidden hidden xl:block" aria-label="Guide details">
              <div class="sticky top-8 border-l border-border-default pl-5">
                <p class="text-xs font-semibold uppercase tracking-[0.18em] text-accent-light">{{ currentGuide.category }}</p>
                <dl class="mt-6 space-y-5 text-xs">
                  <div>
                    <dt class="text-text-muted">For</dt>
                    <dd class="mt-1 text-text-secondary">{{ currentGuide.audience }}</dd>
                  </div>
                  <div>
                    <dt class="text-text-muted">Reading time</dt>
                    <dd class="mt-1 text-text-secondary">{{ currentGuide.readMinutes }} minutes</dd>
                  </div>
                  <div>
                    <dt class="text-text-muted">Source</dt>
                    <dd class="mt-1 break-words text-text-secondary">{{ currentGuide.source }}</dd>
                  </div>
                </dl>
              </div>
            </aside>

            <article aria-label="{{ currentGuide.title }}" class="guide-printable min-w-0">
              @if (loading()) {
                <div class="space-y-4" role="status" aria-label="Loading guide">
                  <div class="h-10 w-4/5 animate-pulse rounded bg-surface-raised"></div>
                  <div class="h-4 w-full animate-pulse rounded bg-surface-raised"></div>
                  <div class="h-4 w-3/4 animate-pulse rounded bg-surface-raised"></div>
                </div>
              } @else if (error()) {
                <div class="rounded-lg border border-red-900/60 bg-red-950/30 p-6">
                  <h1 class="text-xl font-semibold">This guide could not be loaded.</h1>
                  <p class="mt-2 text-sm text-text-muted">Return to the library and choose another guide.</p>
                </div>
              } @else {
                <div class="guide-prose" [innerHTML]="html()"></div>
              }
            </article>

            <nav aria-label="On this page" class="guide-print-hidden hidden xl:block">
              <div class="sticky top-8 max-h-[calc(100vh-4rem)] overflow-y-auto border-l border-border-subtle pl-5">
                <p class="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">On this page</p>
                <ol class="space-y-2.5">
                  @for (heading of currentGuide.headings; track heading.id) {
                    <li [class.pl-3]="heading.level === 3">
                      <a
                        [href]="'#' + heading.id"
                        class="block text-xs leading-5 text-text-muted transition-colors hover:text-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                      >{{ heading.label }}</a>
                    </li>
                  }
                </ol>
              </div>
            </nav>
          </div>
        </div>
      } @else {
        <main class="mx-auto max-w-2xl px-5 py-24 text-center">
          <p class="text-xs font-semibold uppercase tracking-[0.18em] text-accent-light">Guide not found</p>
          <h1 class="mt-4 text-3xl font-bold">That field manual page does not exist.</h1>
          <a routerLink="/app/guides" class="mt-7 inline-flex rounded-md bg-accent px-5 py-3 text-sm font-medium text-accent-on">Browse all guides</a>
        </main>
      }
    </div>
  `,
})
export class GuideReaderComponent {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  protected readonly guide = signal<GuideEntry | undefined>(undefined);
  protected readonly html = signal('');
  protected readonly loading = signal(true);
  protected readonly error = signal(false);

  constructor() {
    const slug = this.route.snapshot.paramMap.get('slug');
    const guide = GUIDE_CATALOG.find(entry => entry.slug === slug);
    this.guide.set(guide);

    if (!guide) {
      this.loading.set(false);
      return;
    }

    this.http.get(`/guide-content/${guide.slug}.html`, { responseType: 'text' }).subscribe({
      next: html => {
        this.html.set(html);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(true);
        this.loading.set(false);
      },
    });
  }

  /**
   * Export the guide as a PDF via the browser's print pipeline.
   *
   * Deliberately not a client-side PDF library: html2canvas-style rasterising
   * turns a 1,100-line reference into a blurry image with no selectable text
   * or working links. `window.print()` with the `@media print` rules in
   * styles.scss produces real vector text, keeps anchors, paginates headings
   * sensibly, and every browser's print dialog offers "Save as PDF".
   */
  exportPdf(): void {
    if (typeof window === 'undefined' || this.loading() || this.error()) return;

    const guide = this.guide();
    const previousTitle = document.title;
    // The print dialog seeds the default filename from document.title.
    if (guide) document.title = guide.slug;

    const restore = () => {
      document.title = previousTitle;
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);

    window.print();
    // Safari never fires afterprint in some versions; restore defensively.
    window.setTimeout(restore, 1000);
  }
}
