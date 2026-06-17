import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-container">
      <div class="login-card">
        <h1>BalanceIQ</h1>
        <p class="subtitle">Financial Data Extraction Platform</p>

        <form (ngSubmit)="onSubmit()">
          <div class="form-group">
            <label for="email">Email</label>
            <input id="email" type="email" [(ngModel)]="email" name="email" required />
          </div>
          <div class="form-group">
            <label for="password">Password</label>
            <input id="password" type="password" [(ngModel)]="password" name="password" required />
          </div>
          @if (error) {
            <div class="error">{{ error }}</div>
          }
          <button type="submit" [disabled]="loading">
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: #f5f7fa;
    }
    .login-card {
      background: white;
      padding: 2.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.1);
      width: 100%;
      max-width: 400px;
    }
    h1 { text-align: center; color: #1a365d; margin-bottom: 0.25rem; }
    .subtitle { text-align: center; color: #718096; margin-bottom: 2rem; font-size: 0.9rem; }
    .form-group { margin-bottom: 1rem; }
    label { display: block; margin-bottom: 0.3rem; font-weight: 500; color: #4a5568; }
    input {
      width: 100%;
      padding: 0.6rem;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      font-size: 0.95rem;
    }
    button {
      width: 100%;
      padding: 0.7rem;
      background: #2b6cb0;
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 1rem;
      cursor: pointer;
      margin-top: 0.5rem;
    }
    button:hover { background: #2c5282; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .error { color: #e53e3e; margin-bottom: 0.5rem; font-size: 0.85rem; }
  `],
})
export class LoginComponent {
  email = '';
  password = '';
  error = '';
  loading = false;

  constructor(private authService: AuthService, private router: Router) {}

  onSubmit(): void {
    this.loading = true;
    this.error = '';
    this.authService.login(this.email, this.password).subscribe({
      next: () => {
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.error = err.error?.error || 'Login failed';
        this.loading = false;
      },
    });
  }
}
