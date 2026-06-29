import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { AuthService } from '../../core/services/auth.service';

type AtlasRuntime = 'aethos_basic' | 'hermes_agent';
type AiModelId =
  | 'google/gemma-4-31b-it:free'
  | 'openrouter/free'
  | 'anthropic/claude-haiku-4.5';

interface AiModelOption {
  id: AiModelId;
  label: string;
  cost_class: 'free' | 'router' | 'paid';
  description: string;
}

interface AiSettings {
  tenant_id: string | null;
  policy_source: 'system_default' | 'tenant_default';
  atlas_runtime: AtlasRuntime;
  provider: 'openrouter';
  primary_model: AiModelId;
  use_free_router: boolean;
  fallback_model: AiModelId;
  model_chain: string[];
  allowed_models: AiModelOption[];
  created_at: string | null;
  updated_at: string | null;
}

const FALLBACK_MODEL_OPTIONS: AiModelId[] = [
  'anthropic/claude-haiku-4.5',
  'openrouter/free',
  'google/gemma-4-31b-it:free',
];

@Component({
  selector: 'app-ai-settings',
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule],
  template: `
    <div class="overflow-hidden rounded-lg border border-border-default bg-surface-raised">
      <div class="flex flex-col gap-3 border-b border-border-default px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex min-w-0 items-center gap-2">
          <mat-icon class="flex-none text-accent-light">auto_awesome</mat-icon>
          <div class="min-w-0">
            <h3 class="truncate text-base font-semibold text-text-primary">AI Inference Settings</h3>
            @if (settings()) {
              <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                <span>{{ settingsSourceLabel(settings()!.policy_source) }}</span>
                @if (settings()!.updated_at; as updatedAt) {
                  <span aria-hidden="true">/</span>
                  <span>Updated {{ formatDate(updatedAt) }}</span>
                }
              </div>
            } @else {
              <p class="mt-1 text-xs text-text-muted">OpenRouter runtime and model routing for Atlas and Aethos Basic fallback.</p>
            }
          </div>
        </div>

        <button
          type="button"
          (click)="load()"
          class="inline-flex h-9 items-center gap-1.5 self-start rounded border border-border-default px-3 text-sm font-medium text-text-secondary transition-colors hover:border-accent/60 hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent lg:self-auto"
        >
          <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">refresh</mat-icon>
          Refresh
        </button>
      </div>

      @if (loading()) {
        <div class="px-6 py-5 animate-pulse" aria-busy="true" aria-label="Loading AI settings">
          <div class="mb-4 h-4 w-64 rounded bg-surface"></div>
          <div class="grid gap-3 md:grid-cols-2">
            <div class="h-20 rounded bg-surface"></div>
            <div class="h-20 rounded bg-surface"></div>
            <div class="h-20 rounded bg-surface"></div>
            <div class="h-20 rounded bg-surface"></div>
          </div>
        </div>
      } @else {
        <form [formGroup]="form" (ngSubmit)="save()" class="space-y-5 px-6 py-5" novalidate>
          <div class="grid gap-4 lg:grid-cols-2">
            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Atlas runtime</span>
              <select
                formControlName="atlas_runtime"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="hermes_agent">Advanced Atlas powered by Hermes</option>
                <option value="aethos_basic">Aethos Basic AI</option>
              </select>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Primary model</span>
              <select
                formControlName="primary_model"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (option of modelOptions(); track option.id) {
                  <option [value]="option.id">{{ option.label }} · {{ option.cost_class }}</option>
                }
              </select>
            </label>

            <label class="flex items-start gap-3 rounded border border-border-subtle bg-surface-base px-3 py-3">
              <input
                type="checkbox"
                formControlName="use_free_router"
                class="mt-1 h-4 w-4 rounded border-border-default bg-surface-raised text-accent focus:ring-accent"
              />
              <span>
                <span class="block text-sm font-medium text-text-primary">Use OpenRouter free router before paid fallback</span>
                <span class="mt-1 block text-xs leading-5 text-text-muted">
                  Inserts <span class="font-mono">openrouter/free</span> after the primary model when it is not already selected.
                </span>
              </span>
            </label>

            <label class="block">
              <span class="mb-2 block text-xs uppercase tracking-wide text-text-muted">Fallback model</span>
              <select
                formControlName="fallback_model"
                class="w-full rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              >
                @for (modelId of fallbackModelOptions; track modelId) {
                  <option [value]="modelId">{{ modelLabel(modelId) }}</option>
                }
              </select>
            </label>
          </div>

          <div class="rounded border border-border-subtle bg-surface-base px-3 py-3">
            <div class="mb-2 text-xs uppercase tracking-wide text-text-muted">Effective model chain</div>
            <div class="flex flex-wrap gap-2">
              @for (model of previewModelChain(); track model; let index = $index) {
                <span class="inline-flex items-center gap-1 rounded-full border border-border-default px-2 py-1 font-mono text-xs text-text-secondary">
                  <span class="text-text-muted">{{ index + 1 }}</span>
                  {{ model }}
                </span>
              }
            </div>
            @if (form.controls.atlas_runtime.value === 'hermes_agent') {
              <p class="mt-3 text-xs leading-5 text-text-muted">
                Hermes uses the mounted Atlas profile for its primary model. These model-chain settings are applied by Aethos Basic and by the built-in fallback path.
              </p>
            }
          </div>

          @if (!canEdit()) {
            <div class="rounded border border-border-default bg-surface-base px-3 py-2 text-sm text-text-muted" role="status">
              AI settings changes require Admin or Tenant Admin / Owner.
            </div>
          }

          @if (loadError()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              Failed to load AI settings.
            </div>
          }

          @if (saveError()) {
            <div class="rounded border border-confidence-low/30 bg-confidence-low/10 px-3 py-2 text-sm text-confidence-low" role="alert">
              Failed to save AI settings.
            </div>
          }

          @if (saved()) {
            <div class="rounded border border-accent/30 bg-accent/10 px-3 py-2 text-sm text-accent-light" role="status">
              AI settings saved.
            </div>
          }

          <div class="flex justify-end">
            <button
              type="submit"
              [disabled]="!canEdit() || form.invalid || saving()"
              class="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-accent-on transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              @if (saving()) {
                <span>Saving...</span>
              } @else {
                <mat-icon style="font-size:1rem;width:1rem;height:1rem;" aria-hidden="true">save</mat-icon>
                <span>Save AI Settings</span>
              }
            </button>
          </div>
        </form>
      }
    </div>
  `,
  styles: [':host { display: block; }'],
})
export class AiSettingsComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);

  settings = signal<AiSettings | null>(null);
  modelOptions = signal<AiModelOption[]>([]);
  loading = signal(true);
  saving = signal(false);
  loadError = signal(false);
  saveError = signal(false);
  saved = signal(false);

  readonly fallbackModelOptions = FALLBACK_MODEL_OPTIONS;

  canEdit = computed(() => {
    const role = this.auth.role();
    return role === 'admin' || role === 'owner';
  });

  form = this.fb.nonNullable.group({
    atlas_runtime: ['hermes_agent' as AtlasRuntime, [Validators.required]],
    primary_model: ['google/gemma-4-31b-it:free' as AiModelId, [Validators.required]],
    use_free_router: [true],
    fallback_model: ['anthropic/claude-haiku-4.5' as AiModelId, [Validators.required]],
  });

  ngOnInit(): void {
    this.applyEditState();
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.loadError.set(false);
    this.saved.set(false);
    this.http.get<AiSettings>('/api/v1/ai-settings/effective').subscribe({
      next: (settings) => {
        this.applySettings(settings);
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.loading.set(false);
      },
    });
  }

  save(): void {
    if (!this.canEdit() || this.form.invalid) return;
    this.saving.set(true);
    this.saveError.set(false);
    this.saved.set(false);
    const value = this.form.getRawValue();
    this.http.put<AiSettings>('/api/v1/ai-settings/default', {
      atlas_runtime: value.atlas_runtime,
      provider: 'openrouter',
      primary_model: value.primary_model,
      use_free_router: value.use_free_router,
      fallback_model: value.fallback_model,
    }).subscribe({
      next: (settings) => {
        this.applySettings(settings);
        this.saving.set(false);
        this.saved.set(true);
      },
      error: () => {
        this.saving.set(false);
        this.saveError.set(true);
      },
    });
  }

  previewModelChain(): string[] {
    const value = this.form.getRawValue();
    const chain = [value.primary_model];
    if (value.use_free_router) chain.push('openrouter/free' as AiModelId);
    chain.push(value.fallback_model);
    return chain.filter((model, index) => chain.indexOf(model) === index);
  }

  modelLabel(modelId: string): string {
    const option = this.modelOptions().find(item => item.id === modelId);
    return option ? `${option.label} · ${option.cost_class}` : modelId;
  }

  settingsSourceLabel(source: AiSettings['policy_source']): string {
    return source === 'tenant_default' ? 'Tenant AI settings' : 'System default';
  }

  formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private applySettings(settings: AiSettings): void {
    this.settings.set(settings);
    this.modelOptions.set(settings.allowed_models ?? []);
    this.form.patchValue({
      atlas_runtime: settings.atlas_runtime,
      primary_model: settings.primary_model,
      use_free_router: settings.use_free_router,
      fallback_model: settings.fallback_model,
    });
    this.applyEditState();
  }

  private applyEditState(): void {
    if (this.canEdit()) {
      this.form.enable({ emitEvent: false });
    } else {
      this.form.disable({ emitEvent: false });
    }
  }
}
