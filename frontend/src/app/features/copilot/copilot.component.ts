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
import { firstValueFrom } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../../core/services/auth.service';
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
  title: string | null;
  created_at: string;
}

interface PersistedChatMessage {
  id: string;
  role: string;
  content: string | null;
  tool_name?: string | null;
  created_at: string;
}

interface DocumentStatusResponse {
  id: string;
  status: string;
}

interface AttachedDocument {
  id: string;
  name: string | null;
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
        class="hidden sm:flex flex-col w-56 flex-none bg-surface border-r border-border-default"
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
              [attr.aria-label]="'Open conversation: ' + threadTitle(thread)"
              [attr.aria-current]="currentThreadId() === thread.id ? 'true' : null"
              role="listitem"
            >
              {{ threadTitle(thread) }}
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
          <div class="min-w-0">
            <h1 class="text-sm font-semibold text-text-primary">Aethos Atlas</h1>
            <p class="text-xs text-text-muted truncate" [attr.title]="activeThreadTitle()">
              {{ activeThreadTitle() }}
            </p>
          </div>
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
              <p class="text-text-primary font-semibold text-base mb-2">Welcome to Aethos Atlas</p>
              <p class="text-text-muted text-sm text-center max-w-xs leading-relaxed mb-6">
                Drop your most recent engagement letter or invoice and I'll set up your first client.
              </p>
              <div class="flex gap-3 flex-wrap justify-center">
                <button
                  class="px-4 py-2 text-xs rounded-lg bg-surface border border-border-default text-text-secondary hover:border-accent hover:text-accent-light transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  (click)="fileInput.click()"
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
                    [attr.aria-label]="'Atlas: ' + msg.content"
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

          <!-- Document upload status banner -->
          @if (uploadStatus()) {
            <div
              class="mb-2 px-3 py-2 rounded-md text-xs flex items-center gap-2"
              [class]="uploadStatusClass()"
              role="status"
              aria-live="polite"
            >
              @if (uploadStatus() === 'uploading' || uploadStatus() === 'extracting') {
                <span class="inline-block w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin flex-none"></span>
              }
              @if (uploadStatus() === 'attached') {
                <mat-icon class="text-xs leading-none">attach_file</mat-icon>
              }
              @if (uploadStatus() === 'done') {
                <mat-icon class="text-xs leading-none">check_circle</mat-icon>
              }
              @if (uploadStatus() === 'error') {
                <mat-icon class="text-xs leading-none">error_outline</mat-icon>
              }
              <span class="min-w-0 flex-1">{{ uploadStatusMessage() }}</span>
              @if (uploadDocumentId()) {
                <span class="ml-auto flex flex-none items-center gap-2">
                  <a
                    class="font-medium underline decoration-current/40 underline-offset-2 hover:decoration-current"
                    href="/app/documents"
                  >
                    Documents
                  </a>
                  @if (uploadStatus() === 'done') {
                    <a
                      class="font-medium underline decoration-current/40 underline-offset-2 hover:decoration-current"
                      href="/app/inbox"
                    >
                      Inbox
                    </a>
                  }
                </span>
              }
            </div>
          }

          <div class="mb-2 flex flex-wrap gap-2" role="group" aria-label="Atlas quick actions">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border-default text-xs text-text-muted
                     hover:border-border-strong hover:text-text-primary transition-colors
                     focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent
                     disabled:opacity-50 disabled:cursor-not-allowed"
              [disabled]="streaming()"
              (click)="prefillLogTime()"
              aria-label="Log time"
            >
              <mat-icon class="text-sm leading-none" style="font-size:1rem;width:1rem;height:1rem;">timer</mat-icon>
              Log time
            </button>
          </div>

          <div
            class="flex items-end gap-2 bg-surface border rounded-lg px-3 py-2 transition-colors"
            [class.border-border-strong]="!composerFocused()"
            [class.border-accent]="composerFocused()"
          >
            <!-- Hidden file input; triggered by the label below -->
            <input
              #fileInput
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.txt"
              class="sr-only"
              aria-label="Attach document"
              (change)="onFileSelected($event)"
            />

            <!-- Attach button -->
            <button
              type="button"
              class="flex-none p-1.5 rounded-md transition-colors text-text-muted hover:text-accent-light
                     focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent
                     disabled:opacity-50 disabled:cursor-not-allowed"
              [disabled]="uploading()"
              (click)="fileInput.click()"
              aria-label="Attach document"
              matTooltip="Attach document (.pdf .png .jpg .webp .txt)"
            >
              <mat-icon class="text-xl leading-none">attach_file</mat-icon>
            </button>

            <textarea
              #composer
              [ngModel]="composerText()"
              (ngModelChange)="composerText.set($event)"
              (keydown)="onComposerKeydown($event)"
              (input)="autoResize($event)"
              (focus)="composerFocused.set(true)"
              (blur)="composerFocused.set(false)"
              rows="1"
              placeholder="Message Atlas…"
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
            Shift + Enter for new line &middot; Enter to send &middot; Attach documents with the paperclip
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
  draftConversation = signal(false);

  canSend = computed(() =>
    this.composerText().trim().length > 0 && !this.streaming() && !this.uploading()
  );

  activeThread = computed(() =>
    this.threads().find(thread => thread.id === this.currentThreadId()) ?? null
  );

  activeThreadTitle = computed(() => {
    if (this.draftConversation()) return 'Draft conversation';
    const threadId = this.currentThreadId();
    if (!threadId) return 'Draft conversation';
    return this.threadTitle(this.activeThread());
  });

  // --- Document upload ---
  uploading     = signal(false);
  uploadStatus  = signal<'attached' | 'uploading' | 'extracting' | 'done' | 'error' | null>(null);
  uploadDocumentId = signal<string | null>(null);
  uploadDocumentName = signal<string | null>(null);
  pendingDocumentId = signal<string | null>(null);

  uploadStatusMessage = computed(() => {
    const name = this.uploadDocumentName();
    const suffix = name ? `: ${name}` : '';
    switch (this.uploadStatus()) {
      case 'attached':    return `Attached${suffix} - add instructions and send to process.`;
      case 'uploading':   return `Uploading${suffix}…`;
      case 'extracting':  return `Processing${suffix} from your prompt - this may take up to 30 seconds...`;
      case 'done':        return `Processed${suffix} - review the resulting task in Inbox.`;
      case 'error':       return `Document action failed${suffix}. Please check the file and try again.`;
      default:            return '';
    }
  });

  uploadStatusClass = computed(() => {
    switch (this.uploadStatus()) {
      case 'attached':   return 'bg-surface-raised border border-border-default text-text-secondary';
      case 'uploading':
      case 'extracting': return 'bg-confidence-med/10 border border-confidence-med/30 text-confidence-med';
      case 'done':       return 'bg-accent/10 border border-accent/30 text-accent-light';
      case 'error':      return 'bg-confidence-low/10 border border-confidence-low/30 text-confidence-low';
      default:           return '';
    }
  });

  private auth = inject(AuthService);

  /**
   * Headers for the raw fetch() calls below. SSE streaming forces fetch over
   * HttpClient, which bypasses the auth interceptor — so we must attach BOTH
   * Authorization and X-Tenant-ID here ourselves. The backend's membership
   * dependency 403s ("Tenant context missing") without the tenant header.
   */
  private apiHeaders(): Record<string, string> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const tok = this.auth.getToken();
    if (tok) headers['Authorization'] = `Bearer ${tok}`;
    const tid = this.auth.getTenantId();
    if (tid) headers['X-Tenant-ID'] = tid;
    return headers;
  }

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
    void this.loadThreads();
  }

  // --- Thread management ---

  newThread(): void {
    this.currentThreadId.set(null);
    this.messages.set([]);
    this.error.set(null);
    this.draftConversation.set(true);
  }

  selectThread(thread: ChatThread): void {
    this.draftConversation.set(false);
    this.currentThreadId.set(thread.id);
    this.error.set(null);
    void this.loadMessages(thread.id);
  }

  private async loadThreads(): Promise<void> {
    try {
      const res = await fetch('/api/v1/chat/threads?limit=20', {
        method: 'GET',
        headers: this.apiHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json() as ChatThread[];
      this.threads.set(data);
      if (data.length > 0 && this.currentThreadId() === null && !this.draftConversation()) {
        this.currentThreadId.set(data[0].id);
        await this.loadMessages(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load Atlas threads:', err);
    }
  }

  private async loadMessages(threadId: string): Promise<void> {
    try {
      const res = await fetch(`/api/v1/chat/threads/${threadId}/messages?limit=100`, {
        method: 'GET',
        headers: this.apiHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json() as PersistedChatMessage[];
      this.messages.set(
        data
          .filter(msg => msg.role === 'user' || msg.role === 'assistant')
          .map(msg => ({
            id: msg.id,
            role: msg.role as 'user' | 'assistant',
            content: msg.content ?? '',
          }))
      );
    } catch (err) {
      console.error('Failed to load Atlas messages:', err);
      this.error.set('Could not load this conversation. Please try again.');
    }
  }

  private async createThread(title: string = 'New conversation'): Promise<string | null> {
    try {
      const res = await fetch('/api/v1/chat/threads', {
        method: 'POST',
        headers: this.apiHeaders(),
        body: JSON.stringify({ title }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json() as { id: string; title: string; created_at: string };
      this.threads.update(t => [{ id: data.id, title: data.title, created_at: data.created_at }, ...t]);
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

  prefillLogTime(): void {
    this.composerText.set('Log time for today: 2 hours on ');
  }

  threadTitle(thread: ChatThread | null | undefined): string {
    return thread?.title?.trim() || 'New conversation';
  }

  sendFromComposer(): void {
    const text = this.composerText().trim();
    if (!text || this.streaming() || this.uploading()) return;
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
    if (this.uploading()) return;

    let threadId = this.currentThreadId();
    if (!threadId) {
      threadId = await this.createThread(this.titleFromContent(content));
      if (!threadId) {
        this.error.set('Could not start a conversation. Please try again.');
        return;
      }
      this.draftConversation.set(false);
      this.currentThreadId.set(threadId);
    }
    this.renameThreadIfPlaceholder(threadId, content);

    const pendingDocument = this.pendingDocumentId()
      ? { id: this.pendingDocumentId() as string, name: this.uploadDocumentName() }
      : null;
    const visibleContent = pendingDocument?.name
      ? `${content}\n\nAttachment: ${pendingDocument.name}`
      : content;

    const userMsgId = crypto.randomUUID();
    this.messages.update(msgs => [
      ...msgs,
      { id: userMsgId, role: 'user', content: visibleContent },
    ]);

    const processedAttachment = pendingDocument
      ? await this.processPendingDocumentForPrompt()
      : null;
    if (pendingDocument && !processedAttachment) {
      return;
    }

    const contentForAgent = processedAttachment
      ? `${content}\n\n[Attached document processed: ${processedAttachment.name ?? 'document'}; document_id=${processedAttachment.id}. The document extraction workflow has created or queued any required Inbox review task. Tell the user to review Inbox if appropriate.]`
      : content;

    const assistantId = crypto.randomUUID();
    this.messages.update(msgs => [
      ...msgs,
      { id: assistantId, role: 'assistant', content: '', streaming: true },
    ]);
    this.streaming.set(true);

    try {
      const response = await fetch(
        `/api/v1/chat/threads/${threadId}/messages`,
        { method: 'POST', headers: this.apiHeaders(), body: JSON.stringify({ content: contentForAgent }) }
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

          // Tool events are intentionally not rendered in Atlas chat. The agent
          // ledger and backend traces retain tool evidence for audit users.

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

          if (typeof payload['error'] === 'string') {
            const safeMessage = 'Atlas is temporarily unavailable. Please try again.';
            this.error.set(safeMessage);
            this.messages.update(msgs =>
              msgs.map(m =>
                m.id === assistantId
                  ? { ...m, content: safeMessage, streaming: false }
                  : m
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
      console.error('Atlas send error:', message);
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

  // --- Document upload ---

  /**
   * Handle file selection from the hidden <input type="file">.
   * Atlas attachments are uploaded with process=false so selecting a file does
   * not create Inbox work until the user sends instructions in the composer.
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    // Reset input so the same file can be re-selected if needed
    input.value = '';

    this.uploading.set(true);
    this.uploadStatus.set('uploading');
    this.uploadDocumentId.set(null);
    this.pendingDocumentId.set(null);
    this.uploadDocumentName.set(file.name);

    const fd = new FormData();
    fd.append('file', file, file.name);
    fd.append('process', 'false');

    this.http.post<DocumentStatusResponse>('/api/v1/documents/upload', fd).subscribe({
      next: (doc) => {
        this.uploadDocumentId.set(doc.id);
        this.pendingDocumentId.set(doc.id);
        this.uploadStatus.set('attached');
        this.uploading.set(false);
      },
      error: (err: { status?: number }) => {
        this.uploading.set(false);
        this.uploadStatus.set('error');
        console.error('Document upload failed:', err.status);
        // Clear error banner after 10 s
        setTimeout(() => {
          if (this.uploadStatus() === 'error') this.uploadStatus.set(null);
        }, 10000);
      },
    });
  }

  private async processPendingDocumentForPrompt(): Promise<AttachedDocument | null> {
    const documentId = this.pendingDocumentId();
    if (!documentId) return null;

    const name = this.uploadDocumentName();
    this.uploading.set(true);
    this.uploadStatus.set('extracting');

    try {
      const triggered = await firstValueFrom(
        this.http.post<DocumentStatusResponse>(`/api/v1/documents/${documentId}/extract`, {})
      );

      if (triggered.status === 'failed') {
        throw new Error('Document extraction failed');
      }

      const extracted = triggered.status === 'extracted'
        || await this.waitForDocumentExtracted(documentId);

      if (!extracted) {
        throw new Error('Document extraction timed out');
      }

      this.uploadStatus.set('done');
      this.pendingDocumentId.set(null);
      return { id: documentId, name };
    } catch (err) {
      console.error('Document processing failed:', err);
      this.uploadStatus.set('error');
      this.error.set('Could not process the attached document. Please try again.');
      setTimeout(() => {
        if (this.uploadStatus() === 'error') this.uploadStatus.set(null);
      }, 10000);
      return null;
    } finally {
      this.uploading.set(false);
    }
  }

  private async waitForDocumentExtracted(docId: string): Promise<boolean> {
    const delaysMs = [3000, 5000, 10000, 10000, 10000];

    for (const delayMs of delaysMs) {
      await this.sleep(delayMs);
      const doc = await firstValueFrom(
        this.http.get<DocumentStatusResponse>(`/api/v1/documents/${docId}`)
      );
      if (doc.status === 'extracted') return true;
      if (doc.status === 'failed') return false;
    }

    return false;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private titleFromContent(content: string): string {
    const normalized = content.replace(/\s+/g, ' ').trim();
    return normalized.length > 80 ? `${normalized.slice(0, 77)}...` : normalized || 'New conversation';
  }

  private renameThreadIfPlaceholder(threadId: string, content: string): void {
    const title = this.titleFromContent(content);
    this.threads.update(threads => {
      const updated = threads.map(thread => {
        if (thread.id !== threadId) return thread;
        const currentTitle = thread.title?.trim();
        if (currentTitle && currentTitle !== 'New conversation') return thread;
        return { ...thread, title };
      });
      const index = updated.findIndex(thread => thread.id === threadId);
      if (index <= 0) return updated;
      const active = updated.splice(index, 1)[0];
      if (!active) return updated;
      return [active, ...updated];
    });
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
