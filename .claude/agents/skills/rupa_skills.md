# Rupa — Frontend Engineering Skills

## Skill: Angular 19 Component Pattern

All components must be standalone. No NgModules.

### New Feature Component Template
```typescript
// feature.component.ts
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';

interface FeatureItem {
  id: string;
  name: string;
  amount: string; // Amounts are always strings from the API
}

@Component({
  selector: 'app-feature',
  standalone: true,
  imports: [CommonModule, MatTableModule, MatButtonModule],
  template: `
    <div class="p-6">
      <h1 class="text-2xl font-semibold text-slate-50 mb-4">Feature</h1>
      @if (loading()) {
        <div class="flex justify-center py-8">
          <mat-spinner diameter="32" />
        </div>
      } @else {
        <mat-table [dataSource]="items()" class="bg-slate-800 rounded-lg">
          <ng-container matColumnDef="name">
            <mat-header-cell *matHeaderCellDef class="text-slate-300">Name</mat-header-cell>
            <mat-cell *matCellDef="let item" class="text-slate-50">{{ item.name }}</mat-cell>
          </ng-container>
          <ng-container matColumnDef="amount">
            <mat-header-cell *matHeaderCellDef class="text-slate-300">Amount</mat-header-cell>
            <mat-cell *matCellDef="let item" class="text-slate-50">{{ item.amount | currency }}</mat-cell>
          </ng-container>
          <mat-header-row *matHeaderRowDef="['name', 'amount']" />
          <mat-row *matRowDef="let row; columns: ['name', 'amount']" />
        </mat-table>
      }
    </div>
  `,
})
export class FeatureComponent implements OnInit {
  private http = inject(HttpClient);
  loading = signal(true);
  items = signal<FeatureItem[]>([]);
  totalAmount = computed(() =>
    this.items().reduce((sum, item) => sum + parseFloat(item.amount), 0)
  );

  ngOnInit() {
    this.http.get<FeatureItem[]>('/api/v1/features').subscribe({
      next: (data) => { this.items.set(data); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
```

### Lazy Route Registration
```typescript
// app.routes.ts
{
  path: 'features',
  loadComponent: () => import('./features/feature.component').then(m => m.FeatureComponent),
  canActivate: [authGuard],
}
```

## Skill: NgRx Signal Store Pattern

```typescript
import { signalStore, withState, withMethods, withComputed, patchState } from '@ngrx/signals';
import { inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

interface FeatureState {
  items: FeatureItem[];
  loading: boolean;
  error: string | null;
}

export const FeatureStore = signalStore(
  withState<FeatureState>({ items: [], loading: false, error: null }),
  withComputed((store) => ({
    itemCount: computed(() => store.items().length),
  })),
  withMethods((store) => {
    const http = inject(HttpClient);
    return {
      loadItems() {
        patchState(store, { loading: true, error: null });
        http.get<FeatureItem[]>('/api/v1/features').subscribe({
          next: (items) => patchState(store, { items, loading: false }),
          error: (e) => patchState(store, { error: e.message, loading: false }),
        });
      },
    };
  }),
);
```

## Skill: Theme Compliance Checklist

Before submitting any component:
- [ ] Uses `bg-slate-900` for page background (or appropriate `var(--t-*)` token)
- [ ] Cards use `bg-slate-800` with `border-slate-700`
- [ ] Text uses `text-slate-50` (primary) or `text-slate-300` (secondary)
- [ ] Accent colors use `indigo-400/500` or `amber-400/500`
- [ ] Works in both light and dark mode
- [ ] Hover/focus/active states present on all interactive elements
- [ ] No hardcoded colors — all via Tailwind classes or CSS variables
- [ ] All monetary values use `| currency` pipe
- [ ] Responsive at `sm`, `md`, and `lg` breakpoints

## Skill: Frontend Security Checklist

Before submitting any component that handles user data, auth, or financial info:

### XSS Prevention
- [ ] **Never use `innerHTML`** with user-controlled content — use Angular's template binding `{{ }}` instead
- [ ] **Never use `[innerHTML]`** unless content is sanitized via Angular's `DomSanitizer`
- [ ] Never use `bypassSecurityTrustHtml()`, `bypassSecurityTrustUrl()`, or other trust bypass methods without documented justification
- [ ] User-generated content rendered via `{{ variable }}` — Angular auto-escapes this

### Secure Data Handling
```typescript
// BAD — storing JWT in localStorage (accessible to XSS)
localStorage.setItem('token', jwt);

// GOOD — store in memory only (service-level signal)
// AuthService holds the token in a private signal — not persisted to browser storage
private _token = signal<string | null>(null);
```

- [ ] JWT tokens stored in memory (Angular service), NOT localStorage or sessionStorage
- [ ] No sensitive data (account numbers, tax IDs) rendered in component state longer than needed
- [ ] Payment card numbers masked: show only last 4 digits

### Content Security Policy (CSP) Headers
These are set by the backend/nginx — Rupa verifies the Angular app does not break under them:
- [ ] No inline `<script>` tags in templates
- [ ] No `javascript:` URLs in `[href]` bindings
- [ ] All external resources (fonts, CDN) must be in the CSP allowlist — flag to Sthira if new ones needed

### CSRF Protection
- [ ] Auth interceptor sends `Authorization: Bearer <token>` header — not cookies
- [ ] Angular `HttpClient` does not use cookies for auth — stateless JWT flow is CSRF-safe by design

### Sensitive Form Fields
```typescript
// Password fields — prevent browser autofill on sensitive forms
<input type="password" autocomplete="current-password" />

// Financial data — never autocomplete account numbers
<input type="text" autocomplete="off" [attr.aria-label]="'Bank account number'" />
```

### Error Messages — Don't Leak Internals
```typescript
// BAD — exposes internal error details to users
this.error.set(err.error.detail);  // Might show "supabase: column X does not exist"

// GOOD — map to user-friendly messages
this.error.set('Something went wrong. Please try again.');
console.error('API error:', err);  // Full details in console for debugging only
```
