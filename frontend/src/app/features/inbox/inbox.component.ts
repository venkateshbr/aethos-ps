import { Component } from '@angular/core';

@Component({
  selector: 'app-inbox',
  standalone: true,
  template: `
    <div class="px-6 py-4 border-b border-slate-700">
      <h1 class="text-lg font-semibold">Inbox</h1>
    </div>
    <div class="p-6 text-slate-400 text-sm">No pending reviews. You're all caught up.</div>
  `,
})
export class InboxComponent {}
