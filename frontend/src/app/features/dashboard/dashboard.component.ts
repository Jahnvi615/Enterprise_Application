import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dashboard">
      <header class="dashboard-header">
        <h1>BalanceIQ</h1>
        <div class="header-actions">
          <span class="user-info">{{ authService.user()?.email }}</span>
          <button (click)="logout()">Logout</button>
        </div>
      </header>
      <main class="dashboard-content">
        <h2>Dashboard</h2>
        <p>Financial data extraction platform ready.</p>
        <!-- Future: upload area, recent jobs, processing status -->
      </main>
    </div>
  `,
  styles: [`
    .dashboard { min-height: 100vh; }
    .dashboard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 2rem;
      background: #1a365d;
      color: white;
    }
    .dashboard-header h1 { font-size: 1.3rem; }
    .header-actions { display: flex; align-items: center; gap: 1rem; }
    .user-info { font-size: 0.85rem; opacity: 0.8; }
    .header-actions button {
      padding: 0.4rem 1rem;
      background: rgba(255,255,255,0.15);
      color: white;
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 4px;
      cursor: pointer;
    }
    .dashboard-content { padding: 2rem; }
    h2 { color: #2d3748; margin-bottom: 0.5rem; }
    p { color: #718096; }
  `],
})
export class DashboardComponent implements OnInit {
  constructor(public authService: AuthService) {}

  ngOnInit(): void {
    this.authService.loadCurrentUser();
  }

  logout(): void {
    this.authService.logout();
  }
}
