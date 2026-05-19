import { Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-copilot',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div class="h-full flex flex-col">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-700">
        <h1 class="text-lg font-semibold">Copilot</h1>
      </div>
      <!-- Chat area — empty state -->
      <div class="flex-1 flex items-center justify-center">
        <div class="text-center max-w-sm">
          <div class="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center mx-auto mb-4">
            <mat-icon class="text-emerald-400">auto_awesome</mat-icon>
          </div>
          <p class="text-slate-300 text-sm leading-relaxed">
            Drop your most recent engagement letter or invoice and I'll set up your first client.
          </p>
        </div>
      </div>
      <!-- Composer placeholder -->
      <div class="px-4 pb-4">
        <div class="bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-sm text-slate-500">
          Message Aethos&hellip;
        </div>
      </div>
    </div>
  `,
})
export class CopilotComponent {}
