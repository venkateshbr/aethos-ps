import {
  Component,
  signal,
  computed,
  effect,
  ElementRef,
  viewChild,
  OnInit,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
  toolName?: string;
  toolDone?: boolean;
}

export interface ChatThread {
  id: string;
  title: string;
  created_at: string;
}

@Component({
  selector: 'app-copilot',
  standalone: true,
  imports: [FormsModule, MatIconModule, MatButtonModule, MatTooltipModule],
  template: `
    <div class="h-full flex bg-slate-900 text-slate-100">

      <!-- Thread sidebar -->
      <aside
        class="hidden sm:flex flex-col w-48 flex-none bg-slate-800 border-r border-slate-700"
        aria-label="Chat threads"
      >
        <div class="p-3 border-b border-slate-700">
          <button
            class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium
                   bg-emerald-600 hover:bg-emerald-500 text-white transition-colors
                   focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
            (click)="newThread()"
            aria-label="Start new chat"
          >
            <mat-icon class="text-base leading-none">add</mat-icon>
            New chat
          </button>
        </div>

        <div class="flex-1 overflow-y-auto py-2" role="list" aria-label="Thread history">
          @if (threads().length === 0) {
            <p class="px-3 py-2 text-xs text-slate-500">No conversations yet.</p>
          }
          @for (thread of threads(); track thread.id) {
            <button
              class="w-full text-left px-3 py-2 text-xs text-slate-400 hover:text-slate-100 hover:bg-slate-700
                     truncate transition-colors focus-visible:outline-none focus-visible:bg-slate-700"
              [class.bg-slate-700]="currentThreadId() === thread.id"
              [class.text-slate-100]="currentThreadId() === thread.id"
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
        <div class="flex-none px-4 py-3 border-b border-slate-700 flex items-center gap-3">
          <!-- Mobile thread toggle (hidden sm+) -->
          <button
            class="sm:hidden text-slate-400 hover:text-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400 rounded"
            (click)="newThread()"
            aria-label="New chat"
          >
            <mat-icon>add</mat-icon>
          </button>
          <div class="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center">
            <mat-icon class="text-emerald-400 text-base leading-none">auto_awesome</mat-icon>
          </div>
          <h1 class="text-sm font-semibold text-slate-100">Aethos Copilot</h1>
        </div>

        <!-- Message list -->
        <div
          #messageContainer
          class="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4"
          role="log"
          aria-live="polite"
          aria-label="Conversation"
        >
          <!-- Welcome / empty state -->
          @if (messages().length === 0 && !streaming()) {
            <div class="flex-1 flex items-center justify-center">
              <div class="text-center max-w-sm">
                <div class="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center mx-auto mb-4">
                  <mat-icon class="text-emerald-400">auto_awesome</mat-icon>
                </div>
                <p class="text-slate-300 text-sm leading-relaxed">
                  Drop your most recent engagement letter or invoice and I'll set up your first client.
                </p>
                <div class="flex flex-wrap gap-2 justify-center mt-4">
                  @for (suggestion of suggestions; track suggestion) {
                    <button
                      class="px-3 py-1.5 rounded-md border border-slate-700 text-xs text-slate-400
                             hover:border-slate-500 hover:text-slate-200 transition-colors
                             focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
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
                <div class="bg-slate-700 text-slate-50 rounded-lg px-4 py-3 max-w-lg text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {{ msg.content }}
                </div>
              </div>
            } @else {
              <!-- Assistant bubble + optional tool card -->
              <div class="flex flex-col gap-2 max-w-2xl self-start w-full">
                @if (msg.toolName) {
                  <!-- Tool-call card -->
                  <div
                    class="bg-slate-800/50 border border-slate-700 border-l-2 border-l-emerald-500 rounded px-3 py-2 text-xs text-slate-400"
                    [attr.aria-label]="msg.toolDone ? 'Tool completed: ' + msg.toolName : 'Running tool: ' + msg.toolName"
                  >
                    @if (!msg.toolDone) {
                      <span class="inline-block w-3 h-3 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin mr-2 align-middle"></span>
                    } @else {
                      <mat-icon class="text-emerald-400 text-xs align-middle mr-1 leading-none">check_circle</mat-icon>
                    }
                    &#9889; {{ msg.toolName }}
                  </div>
                }
                @if (msg.content || msg.streaming) {
                  <div
                    class="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words"
                    [attr.aria-label]="'Aethos: ' + msg.content"
                  >
                    {{ msg.content }}@if (msg.streaming) {
                      <span
                        class="inline-block w-0.5 h-3.5 bg-emerald-400 ml-0.5 align-middle animate-blink"
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
        <div class="flex-none px-4 pb-4 pt-2 border-t border-slate-700">
          @if (error()) {
            <div class="mb-2 px-3 py-2 rounded-md bg-red-950 border border-red-900 text-xs text-red-400" role="alert">
              <mat-icon class="text-xs align-middle mr-1">error_outline</mat-icon>
              {{ error() }}
            </div>
          }
          <div
            class="flex items-end gap-2 bg-slate-800 border rounded-lg px-3 py-2 transition-colors"
            [class.border-slate-600]="!composerFocused()"
            [class.border-emerald-500]="composerFocused()"
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
              class="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500
                     resize-none outline-none leading-relaxed min-h-[1.5rem] max-h-36 overflow-y-auto"
              [disabled]="streaming()"
              aria-label="Message input"
              autocomplete="off"
              spellcheck="true"
            ></textarea>
            <button
              class="flex-none p-1.5 rounded-md transition-colors
                     focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
              [class]="canSend()
                ? 'text-emerald-500 hover:text-emerald-400'
                : 'text-slate-600 cursor-not-allowed'"
              [disabled]="!canSend()"
              (click)="sendFromComposer()"
              aria-label="Send message"
              [attr.aria-disabled]="!canSend()"
            >
              <mat-icon class="text-xl leading-none">send</mat-icon>
            </button>
          </div>
          <p class="text-xs text-slate-600 mt-1.5 text-center">
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
    // Re-run when messages change
    this.messages();
    const el = this.messageContainer()?.nativeElement;
    if (el) {
      // defer one tick so DOM updates first
      Promise.resolve().then(() => { el.scrollTop = el.scrollHeight; });
    }
  });

  ngOnInit(): void {
    // If no thread yet, we create one lazily on first message send.
    // Optionally load existing threads from API.
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
    // In a full implementation: load thread messages here
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
      // silently fail — thread creation will retry on next send
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

    // Ensure we have a thread
    let threadId = this.currentThreadId();
    if (!threadId) {
      threadId = await this.createThread();
      if (!threadId) {
        this.error.set('Could not start a conversation. Please try again.');
        return;
      }
      this.currentThreadId.set(threadId);
    }

    // 1. Push user message to local state immediately
    const userMsgId = crypto.randomUUID();
    this.messages.update(msgs => [
      ...msgs,
      { id: userMsgId, role: 'user', content },
    ]);

    // 2. Add pending assistant message
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

      // 3. POST with streaming
      const response = await fetch(
        `/api/v1/chat/threads/${threadId}/messages`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ content }),
        }
      );

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      // 4. Read SSE stream
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
            continue; // skip malformed SSE frames
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
              msgs.map(m =>
                m.id === assistantId ? { ...m, toolDone: true } : m
              )
            );
          }

          if (payload['done'] === true) {
            this.messages.update(msgs =>
              msgs.map(m =>
                m.id === assistantId ? { ...m, streaming: false } : m
              )
            );
          }
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      console.error('Copilot send error:', message);
      this.error.set('Something went wrong. Please try again.');
      // Mark streaming done + remove empty assistant bubble if nothing came back
      this.messages.update(msgs => {
        const assistantMsg = msgs.find(m => m.id === assistantId);
        if (assistantMsg && !assistantMsg.content) {
          return msgs.filter(m => m.id !== assistantId);
        }
        return msgs.map(m =>
          m.id === assistantId ? { ...m, streaming: false } : m
        );
      });
    } finally {
      this.streaming.set(false);
      // Ensure streaming flag cleared on message
      this.messages.update(msgs =>
        msgs.map(m => m.id === assistantId ? { ...m, streaming: false } : m)
      );
    }
  }
}
