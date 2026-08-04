import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-guide-header',
  standalone: true,
  imports: [RouterLink],
  template: `
    <header class="border-b border-border-subtle bg-surface-base/95 px-5 py-4 backdrop-blur md:px-8">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-5">
        <a routerLink="/" aria-label="Aethos — for professional services">
          <img
            [src]="themeSvc.meta().lockupSrc"
            [alt]="'Aethos — for professional services (' + themeSvc.meta().label + ')'"
            class="h-9 w-auto"
          />
        </a>
        <nav aria-label="Guide navigation" class="flex items-center gap-2 sm:gap-5">
          <a
            routerLink="/guides"
            class="rounded-md px-2 py-2 text-sm font-medium text-text-secondary transition-colors hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >Guides</a>
          <a
            routerLink="/login"
            class="rounded-md border border-border-default px-3 py-2 text-sm font-medium text-text-secondary transition-colors hover:border-border-strong hover:bg-surface-raised hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >Sign in</a>
        </nav>
      </div>
    </header>
  `,
})
export class GuideHeaderComponent {
  protected readonly themeSvc = inject(ThemeService);
}
