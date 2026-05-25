import {
  Component,
  signal,
  computed,
  effect,
  ElementRef,
  viewChild,
  OnInit,
  inject,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { EngagementDraftCardComponent, EngagementDraftPayload } from './cards/engagement-draft-card.component';
import { ExpenseExtractedCardComponent, ExpenseExtractedPayload } from './cards/expense-extracted-card.component';
import { BillExtractedCardComponent, BillExtractedPayload } from './cards/bill-extracted-card.component';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
  toolName?: string;
  toolDone?: boolean;
  /** Card fields — set when the agent SSE stream emits a card_type frame */
  cardType?: 'engagement_draft' | 'expense_draft' | 'bill_draft';
  cardPayload?: Record<string, unknown>;
  hitlTaskId?: string | null;
}

export interface ChatThread {
  id: string;
  title: string;
  created_at: string;
}

@Component({
  selector: 'app-copilot',
  standalone: true,
  imports: [
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    EngagementDraftCardComponent,
    ExpenseExtractedCardComponent,
    BillExtractedCardComponent,
  ],
  template: `
    <div class="h-full flex bg-surface-base text-text-primary">

      <!-- Thread sidebar -->
      <aside
        class="hidden sm:flex flex-col w-48 flex-none bg-surface border-r border-border-default"
        aria-label="Chat threads"
      >
        <div class="p-3 border-b border-border-default">
          <button
            class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium
                   bg-accent hover:bg-accent-hover text-accent-on transition-colors
                   focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            (click)="newThread()"
            aria-label="Start new chat"
          >
            <mat-icon class="text-base leading-none">add</mat-icon>
            New chat
          </button>
        </div>

        <div class="flex-1 overflow-y-auto py-2" role="list" aria-label="Thread history">
          @if (threads().length === 0) {
            <p class="px-3 py-2 text-xs text-text-muted">No conversations yet.</p>
          }
          @for (thread of threads(); track thread.id) {
            <button
              class="w-full text-left px-3 py-2 text-xs text-text-muted hover:text-text-primary hover:bg-surface-raised
                     truncate transition-colors focus-visible:outline-none focus-visible:bg-surface-raised"
              [class.bg-surface-raised]="currentThreadId() === thread.id"
              [class.text-text-primary]="currentThreadId() === thread.id"
              (click)="selectThread(thread)"
              [attr.aria-label]="'Open conversation: ' + thread.title"
              [attr.aria-current]="currentThreadId() === thread.id ? 'true' : null"
              role="listitem"
            >
              {{ thread.title }}
            </button>
          }
        </div>
      </aside>

      <!-- Main chat surface -->
      <div class="flex-1 flex flex-col min-w-0">

        <!-- Header -->
        <div class="flex-none px-4 py-3 border-b border-border-default flex items-center gap-3">
          <!-- Mobile thread toggle (hidden sm+) -->
          <button
            class="sm:hidden text-text-muted hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded"
            (click)="newThread()"
            aria-label="New chat"
          >
            <mat-icon>add</mat-icon>
          </button>
          <div class="w-7 h-7 rounded-full bg-surface-raised flex items-center justify-center">
            <mat-icon class="text-accent-light text-base leading-none">auto_awesome</mat-icon>
          </div>
          <h1 class="text-sm font-semibold text-text-primary">Aethos Copilot</h1>
        </div>

        <!-- Message list -->
        <div
          #messageContainer
          class="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4"
          role="log"
          aria-live="polite"
          aria-label="Conversation"
        >
          <!-- Welcome / empty state — shown on first use (no threads, no messages) -->
          @if (threads().length === 0 && messages().length === 0) {
            <div class="flex-1 flex flex-col items-center justify-center px-6 py-16 animate-fade-in">
              <div class="w-14 h-14 rounded-full bg-accent/15 border border-accent/40 flex items-center justify-center mb-5">
                <mat-icon class="text-accent-light" style="font-size:1.75rem;width:1.75rem;height:1.75rem;">auto_awesome</mat-icon>
              </div>
              <p class="text-text-primary font-semibold text-base mb-2">Welcome to Aethos</p>
              <p class="text-text-muted text-sm text-center max-w-xs leading-relaxed mb-6">
                Drop your most recent engagement letter or invoice and I'll set up your first client.
              </p>
              <div class="flex gap-3 flex-wrap justify-center">
                <button
                  class="px-4 py-2 text-xs rounded-lg bg-surface border border-border-default text-text-secondary hover:border-accent hover:text-accent-light transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  (click)="sendSuggestion('Drop engagement letter')"
                >
                  Drop engagement letter
                </button>
                <button
                  class="px-4 py-2 text-xs rounded-lg bg-surface border border-border-default text-text-secondary hover:border-border-strong transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-border-strong"
                  (click)="sendSuggestion('Create manually')"
                >
                  Create manually
                </button>
              </div>
            </div>
          }

          <!-- Returning user: no messages in current thread yet -->
          @if (threads().length > 0 && messages().length === 0 && !streaming()) {
            <div class="flex-1 flex items-center justify-center">
              <div class="text-center max-w-sm">
                <div class="w-12 h-12 rounded-full bg-surface-raised flex items-center justify-center mx-auto mb-4">
                  <mat-icon class="text-accent-light">auto_awesome</mat-icon>
                </div>
                <p class="text-text-secondary text-sm leading-relaxed">
                  How can I help you today?
                </p>
                <div class="flex flex-wrap gap-2 justify-center mt-4">
                  @for (suggestion of suggestions; track suggestion) {
                    <button
                      class="px-3 py-1.5 rounded-md border border-border-default text-xs text-text-muted
                             hover:border-border-strong hover:text-text-primary transition-colors
                             focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                      (click)="sendSuggestion(suggestion)"
                    >
                      {{ suggestion }}
                    </button>
                  }
                </div>
              </div>
            </div>
          }

          <!-- Messages -->
          @for (msg of messages(); track msg.id) {
            @if (msg.role === 'user') {
              <!-- User bubble -->
              <div class="flex justify-end" [attr.aria-label]="'You: ' + msg.content">
                <div class="bg-surface-raised text-text-primary rounded-lg px-4 py-3 max-w-lg text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {{ msg.content }}
                </div>
              </div>
            } @else {
              <!-- Assistant bubble + optional tool card + optional data cards -->
              <div class="flex flex-col gap-2 max-w-2xl self-start w-full">
                @if (msg.toolName) {
                  <!-- Tool-call card -->
                  <div
                    class="bg-surface/50 border border-border-default border-l-2 border-l-accent rounded px-3 py-2 text-xs text-text-muted"
                    [attr.aria-label]="msg.toolDone ? 'Tool completed: ' + msg.toolName : 'Running tool: ' + msg.toolName"
                  >
                    @if (!msg.toolDone) {
                      <span class="inline-block w-3 h-3 rounded-full border-2 border-accent-light border-t-transparent animate-spin mr-2 align-middle"></span>
                    } @else {
                      <mat-icon class="text-accent-light text-xs align-middle mr-1 leading-none">check_circle</mat-icon>
                    }
                    &#9889; {{ msg.toolName }}
                  </div>
                }

                <!-- Engagement draft card -->
                @if (msg.cardType === 'engagement_draft' && msg.cardPayload) {
                  <app-engagement-draft-card
                    [payload]="asEngagementPayload(msg.cardPayload)"
                    [hitlTaskId]="msg.hitlTaskId ?? null"
                    [streaming]="!!msg.streaming"
                    (onApprove)="approveCard(msg)"
                    (onEdit)="editCard(msg)"
                    (onReject)="rejectCard(msg)"
                  />
                }

                <!-- Expense extracted card -->
                @if (msg.cardType === 'expense_draft' && msg.cardPayload) {
                  <app-expense-extracted-card
                    [payload]="asExpensePayload(msg.cardPayload)"
                    [hitlTaskId]="msg.hitlTaskId ?? null"
                    [streaming]="!!msg.streaming"
                    (onApprove)="approveCard(msg)"
                    (onEdit)="editCard(msg)"
                    (onReject)="rejectCard(msg)"
                  />
                }

                <!-- Bill extracted card -->
                @if (msg.cardType === 'bill_draft' && msg.cardPayload) {
                  <app-bill-extracted-card
                    [payload]="asBillPayload(msg.cardPayload)"
                    [hitlTaskId]="msg.hitlTaskId ?? null"
                    [streaming]="!!msg.streaming"
                    (onApprove)="approveCard(msg)"
                    (onEdit)="editCard(msg)"
                    (onReject)="rejectCard(msg)"
                  />
                }

                @if (msg.content || msg.streaming) {
                  <div
                    class="bg-surface border border-border-strong text-text-primary rounded-lg px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words"
                    [attr.aria-label]="'Aethos: ' + msg.content"
                  >
                    {{ msg.content }}@if (msg.streaming) {
                      <span
                        class="inline-block w-0.5 h-3.5 bg-accent-light ml-0.5 align-middle animate-blink"
                        aria-hidden="true"
                      ></span>
                    }
                  </div>
                }
              </div>
            }
          }
        </div>

        <!-- Composer -->
        <div class="flex-none px-4 pb-4 pt-2 border-t border-border-default">
          @if (error()) {
            <div class="mb-2 px-3 py-2 rounded-md bg-confidence-low/10 border border-confidence-low/30 text-xs text-confidence-low" role="alert">
              <mat-icon class="text-xs align-middle mr-1">error_outline</mat-icon>
              {{ error() }}
            </div>
          }
          <div
            class="flex items-end gap-2 bg-surface border rounded-lg px-3 py-2 transition-colors"
            [class.border-border-strong]="!composerFocused()"
            [class.border-accent]="composerFocused()"
          >
            <textarea
              #composer
              [ngModel]="composerText()"
              (ngModelChange)="composerText.set($event)"
              (keydown)="onComposerKeydown($event)"
              (input)="autoResize($event)"
              (focus)="composerFocused.set(true)"
              (blur)="composerFocused.set(false)"
              rows="1"
              placeholder="Message Aethos…"
              class="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-disabled
                     resize-none outline-none leading-relaxed min-h-[1.5rem] max-h-36 overflow-y-auto"
              [disabled]="streaming()"
              aria-label="Message input"
              autocomplete="off"
              spellcheck="true"
            ></textarea>
            <button
              class="flex-none p-1.5 rounded-md transition-colors
                     focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              [class]="canSend()
                ? 'text-accent hover:text-accent-light'
                : 'text-text-disabled cursor-not-allowed'"
              [disabled]="!canSend()"
              (click)="sendFromComposer()"
              aria-label="Send message"
              [attr.aria-disabled]="!canSend()"
            >
              <mat-icon class="text-xl leading-none">send</mat-icon>
            </button>
          </div>
          <p class="text-xs text-text-muted mt-1.5 text-center">
            Shift + Enter for new line &middot; Enter to send
          </p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100%; }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0; }
    }
    .animate-blink { animation: blink 1s step-end infinite; }
  `],
})
export class CopilotComponent implements OnInit {
  private http = inject(HttpClient);

  // --- State ---
  messages = signal<ChatMessage[]>([]);
  threads = signal<ChatThread[]>([]);
  currentThreadId = signal<string | null>(null);
  streaming = signal(false);
  error = signal<string | null>(null);
  composerFocused = signal(false);
  composerText = signal('');

  canSend = computed(() => this.composerText().trim().length > 0 && !this.streaming());

  /** Read token from localStorage — auth interceptor will set this in Week 3. */
  private token = signal<string | null>(
    typeof localStorage !== 'undefined' ? localStorage.getItem('aethos_token') : null
  );

  suggestions = [
    'Show my active engagements',
    'What invoices are overdue?',
    'Summarise time logged this week',
  ];

  // Keep messages scrolled to bottom
  private messageContainer = viewChild<ElementRef<HTMLElement>>('messageContainer');
  private _scrollEffect = effect(() => {
    this.messages();
    const el = this.messageContainer()?.nativeElement;
    if (el) {
      Promise.resolve().then(() => { el.scrollTop = el.scrollHeight; });
    }
  });

  ngOnInit(): void {
    // Thread created lazily on first message send.
  }

  // --- Thread management ---

  async newThread(): Promise<void> {
    const id = await this.createThread();
    if (id) {
      this.currentThreadId.set(id);
      this.messages.set([]);
      this.error.set(null);
    }
  }

  selectThread(thread: ChatThread): void {
    this.currentThreadId.set(thread.id);
    this.messages.set([]);
    this.error.set(null);
  }

  private async createThread(): Promise<string | null> {
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      const tok = this.token();
      if (tok) headers['Authorization'] = `Bearer ${tok}`;

      const res = await fetch('/api/v1/chat/threads', {
        method: 'POST',
        headers,
        body: JSON.stringify({ title: 'New conversation' }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json() as { id: string; title: string; created_at: string };
      this.threads.update(t => [...t, { id: data.id, title: data.title, created_at: data.created_at }]);
      return data.id;
    } catch {
      return null;
    }
  }

  // --- Sending messages ---

  sendSuggestion(text: string): void {
    this.composerText.set(text);
    void this.sendMessage(text);
    this.composerText.set('');
  }

  sendFromComposer(): void {
    const text = this.composerText().trim();
    if (!text || this.streaming()) return;
    this.composerText.set('');
    void this.sendMessage(text);
  }

  onComposerKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendFromComposer();
    }
  }

  autoResize(event: Event): void {
    const el = event.target as HTMLTextAreaElement;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
  }

  async sendMessage(content: string): Promise<void> {
    this.error.set(null);

    let threadId = this.currentThreadId();
    if (!threadId) {
      threadId = await this.createThread();
      if (!threadId) {
        this.error.set('Could not start a conversation. Please try again.');
        return;
      }
      this.currentThreadId.set(threadId);
    }

    const userMsgId = crypto.randomUUID();
    this.messages.update(msgs => [
      ...msgs,
      { id: userMsgId, role: 'user', content },
    ]);

    const assistantId = crypto.randomUUID();
    this.messages.update(msgs => [
      ...msgs,
      { id: assistantId, role: 'assistant', content: '', streaming: true },
    ]);
    this.streaming.set(true);

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      const tok = this.token();
      if (tok) headers['Authorization'] = `Bearer ${tok}`;

      const response = await fetch(
        `/api/v1/chat/threads/${threadId}/messages`,
        { method: 'POST', headers, body: JSON.stringify({ content }) }
      );

      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      if (!response.body)  throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n').filter(l => l.startsWith('data: '));

        for (const line of lines) {
          let payload: Record<string, unknown>;
          try {
            payload = JSON.parse(line.slice(6)) as Record<string, unknown>;
          } catch {
            continue;
          }

          if (typeof payload['delta'] === 'string') {
            this.messages.update(msgs =>
              msgs.map(m =>
                m.id === assistantId
                  ? { ...m, content: m.content + (payload['delta'] as string) }
                  : m
              )
            );
          }

          if (typeof payload['tool_start'] === 'string') {
            this.messages.update(msgs =>
              msgs.map(m =>
                m.id === assistantId
                  ? { ...m, toolName: payload['tool_start'] as string, toolDone: false }
                  : m
              )
            );
          }

          if (payload['tool_end'] === true) {
            this.messages.update(msgs =>
              msgs.map(m => m.id === assistantId ? { ...m, toolDone: true } : m)
            );
          }

          // Card frame — agent extracted a structured entity
          if (typeof payload['card_type'] === 'string') {
            this.messages.update(msgs =>
              msgs.map(m =>
                m.id === assistantId ? {
                  ...m,
                  cardType:    payload['card_type'] as ChatMessage['cardType'],
                  cardPayload: payload['payload'] as Record<string, unknown>,
                  hitlTaskId:  (payload['hitl_task_id'] as string | null) ?? null,
                  streaming:   false,
                } : m
              )
            );
          }

          if (payload['done'] === true) {
            this.messages.update(msgs =>
              msgs.map(m => m.id === assistantId ? { ...m, streaming: false } : m)
            );
          }
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      console.error('Copilot send error:', message);
      this.error.set('Something went wrong. Please try again.');
      this.messages.update(msgs => {
        const assistantMsg = msgs.find(m => m.id === assistantId);
        if (assistantMsg && !assistantMsg.content && !assistantMsg.cardType) {
          return msgs.filter(m => m.id !== assistantId);
        }
        return msgs.map(m =>
          m.id === assistantId ? { ...m, streaming: false } : m
        );
      });
    } finally {
      this.streaming.set(false);
      this.messages.update(msgs =>
        msgs.map(m => m.id === assistantId ? { ...m, streaming: false } : m)
      );
    }
  }

  // --- Card actions ---

  approveCard(msg: ChatMessage): void {
    if (!msg.hitlTaskId) return;
    this.http.post(`/api/v1/inbox/tasks/${msg.hitlTaskId}/approve`, {}).subscribe({
      next: () => {
        this.messages.update(msgs =>
          msgs.map(m =>
            m.id === msg.id
              ? { ...m, cardType: undefined, cardPayload: undefined, content: '✓ Approved and applied.' }
              : m
          )
        );
      },
      error: () => {
        console.error(`Failed to approve card for task ${msg.hitlTaskId}`);
      },
    });
  }

  rejectCard(msg: ChatMessage): void {
    if (!msg.hitlTaskId) return;
    this.http.post(`/api/v1/inbox/tasks/${msg.hitlTaskId}/reject`, { reason: '' }).subscribe({
      next: () => {
        this.messages.update(msgs =>
          msgs.map(m =>
            m.id === msg.id
              ? { ...m, cardType: undefined, cardPayload: undefined, content: '✗ Rejected.' }
              : m
          )
        );
      },
      error: () => {
        console.error(`Failed to reject card for task ${msg.hitlTaskId}`);
      },
    });
  }

  editCard(msg: ChatMessage): void {
    // Week 4: open inline edit drawer.
    // For now, route to approve so the review queue unblocks.
    this.approveCard(msg);
  }

  // --- Payload type casts (safe: payload shapes validated by the SSE contract) ---

  asEngagementPayload(p: Record<string, unknown>): EngagementDraftPayload {
    return p as unknown as EngagementDraftPayload;
  }

  asExpensePayload(p: Record<string, unknown>): ExpenseExtractedPayload {
    return p as unknown as ExpenseExtractedPayload;
  }

  asBillPayload(p: Record<string, unknown>): BillExtractedPayload {
    return p as unknown as BillExtractedPayload;
  }
}
