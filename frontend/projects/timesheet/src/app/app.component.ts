import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'ts-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `<div class="min-h-screen bg-surface-base text-text-primary"><router-outlet /></div>`,
})
export class AppComponent {}
