import { Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { GuideHeaderComponent } from './guide-header.component';
import { GUIDE_CATALOG } from './guide-catalog.generated';

@Component({
  selector: 'app-guide-library',
  standalone: true,
  imports: [RouterLink, GuideHeaderComponent],
  template: `
    <div class="min-h-screen bg-surface-base text-text-primary">
      <app-guide-header />

      <main>
        <section class="border-b border-border-subtle px-5 py-14 md:px-8 md:py-20">
          <div class="mx-auto max-w-7xl">
            <p class="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-accent-light">Aethos field manual</p>
            <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-end">
              <div>
                <h1 class="max-w-3xl text-4xl font-bold tracking-tight md:text-6xl">Learn Aethos at your pace.</h1>
                <p class="mt-5 max-w-2xl text-base leading-7 text-text-muted md:text-lg">
                  Start with the operating model, borrow a proven Nous prompt, or rehearse a complete client scenario.
                  These guides are generated from the same maintained documentation used by the product team.
                </p>
              </div>
              <label class="block">
                <span class="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">Find a guide</span>
                <span class="flex items-center gap-3 rounded-lg border border-border-default bg-surface px-4 focus-within:border-accent">
                  <span aria-hidden="true" class="text-text-muted">⌕</span>
                  <input
                    type="search"
                    aria-label="Search guides"
                    placeholder="Search topics, roles, workflows…"
                    class="min-w-0 flex-1 bg-transparent py-3 text-sm text-text-primary outline-none placeholder:text-text-disabled"
                    [value]="query()"
                    (input)="updateQuery($event)"
                  />
                </span>
              </label>
            </div>
          </div>
        </section>

        <section class="px-5 py-10 md:px-8 md:py-14" aria-label="Guide library">
          <div class="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
            <aside aria-label="Guide categories" class="lg:border-r lg:border-border-subtle lg:pr-8">
              <p class="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Browse by</p>
              <div class="flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible">
                @for (category of categories; track category) {
                  <button
                    type="button"
                    class="whitespace-nowrap rounded-md px-3 py-2 text-left text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    [class.bg-accent-subtle]="activeCategory() === category"
                    [class.text-accent-light]="activeCategory() === category"
                    [class.text-text-secondary]="activeCategory() !== category"
                    [attr.aria-pressed]="activeCategory() === category"
                    (click)="activeCategory.set(category)"
                  >{{ category }}</button>
                }
              </div>
            </aside>

            <div>
              <div class="mb-5 flex items-end justify-between gap-4 border-b border-border-subtle pb-4">
                <div>
                  <p class="text-xs uppercase tracking-[0.16em] text-text-muted">{{ activeCategory() }}</p>
                  <h2 class="mt-1 text-xl font-semibold">{{ filteredGuides().length }} {{ filteredGuides().length === 1 ? 'guide' : 'guides' }}</h2>
                </div>
                <span class="text-xs text-text-muted">HTML · always current</span>
              </div>

              @if (filteredGuides().length) {
                <div class="grid gap-4 md:grid-cols-2">
                  @for (guide of filteredGuides(); track guide.slug; let index = $index) {
                    <a
                      [routerLink]="['/guides', guide.slug]"
                      class="group flex min-h-56 flex-col rounded-lg border border-border-default bg-surface p-5 shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-raised hover:shadow-card-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    >
                      <div class="flex items-start justify-between gap-4">
                        <span class="font-mono text-xs text-accent-light">FM—{{ paddedIndex(index) }}</span>
                        <span class="rounded-md bg-surface-sunken px-2 py-1 text-[11px] text-text-muted">{{ guide.status }}</span>
                      </div>
                      <h3 class="mt-8 text-xl font-semibold tracking-tight group-hover:text-accent-light">{{ guide.title }}</h3>
                      <p class="mt-3 flex-1 text-sm leading-6 text-text-muted">{{ guide.description }}</p>
                      <div class="mt-6 flex items-center justify-between border-t border-border-subtle pt-4 text-xs text-text-muted">
                        <span>{{ guide.audience }} · {{ guide.readMinutes }} min</span>
                        <span aria-hidden="true" class="text-accent-light transition-transform group-hover:translate-x-1">→</span>
                      </div>
                    </a>
                  }
                </div>
              } @else {
                <div class="rounded-lg border border-dashed border-border-default px-6 py-14 text-center">
                  <h2 class="text-lg font-semibold">No guides match that search.</h2>
                  <p class="mt-2 text-sm text-text-muted">Try a workflow such as “billing”, “prompt”, or “demo”.</p>
                  <button type="button" class="mt-5 rounded-md text-sm font-medium text-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent" (click)="clearFilters()">
                    Clear search
                  </button>
                </div>
              }
            </div>
          </div>
        </section>
      </main>
    </div>
  `,
})
export class GuideLibraryComponent {
  protected readonly guides = GUIDE_CATALOG;
  protected readonly categories = ['All guides', ...new Set(GUIDE_CATALOG.map(guide => guide.category))];
  protected readonly query = signal('');
  protected readonly activeCategory = signal('All guides');
  protected readonly filteredGuides = computed(() => {
    const query = this.query().trim().toLowerCase();
    const category = this.activeCategory();
    return this.guides.filter(guide => {
      const categoryMatches = category === 'All guides' || guide.category === category;
      const queryMatches = !query || [guide.title, guide.description, guide.category, guide.audience]
        .some(value => value.toLowerCase().includes(query));
      return categoryMatches && queryMatches;
    });
  });

  protected updateQuery(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
  }

  protected paddedIndex(index: number): string {
    return String(index + 1).padStart(2, '0');
  }

  protected clearFilters(): void {
    this.query.set('');
    this.activeCategory.set('All guides');
  }
}
