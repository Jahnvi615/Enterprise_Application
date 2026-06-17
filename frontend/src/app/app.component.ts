import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <main class="app-container">
      <router-outlet />
    </main>
  `,
  styles: [`
    .app-container {
      min-height: 100vh;
    }
  `],
})
export class AppComponent {
  title = 'BalanceIQ';
}
