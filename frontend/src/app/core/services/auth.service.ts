import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '@env';

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'balanceiq_access_token';
  private readonly REFRESH_KEY = 'balanceiq_refresh_token';

  private currentUser = signal<UserResponse | null>(null);
  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => !!this.getToken());

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${environment.apiUrl}/auth/login`, { email, password })
      .pipe(tap((tokens) => this.storeTokens(tokens)));
  }

  register(email: string, password: string, fullName?: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${environment.apiUrl}/auth/register`, {
        email,
        password,
        full_name: fullName,
      })
      .pipe(tap((tokens) => this.storeTokens(tokens)));
  }

  refreshToken(): Observable<TokenResponse> {
    const refreshToken = localStorage.getItem(this.REFRESH_KEY);
    return this.http
      .post<TokenResponse>(`${environment.apiUrl}/auth/refresh`, {
        refresh_token: refreshToken,
      })
      .pipe(tap((tokens) => this.storeTokens(tokens)));
  }

  loadCurrentUser(): void {
    this.http
      .get<UserResponse>(`${environment.apiUrl}/auth/me`)
      .subscribe({
        next: (user) => this.currentUser.set(user),
        error: () => this.logout(),
      });
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_KEY);
    this.currentUser.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private storeTokens(tokens: TokenResponse): void {
    localStorage.setItem(this.TOKEN_KEY, tokens.access_token);
    localStorage.setItem(this.REFRESH_KEY, tokens.refresh_token);
  }
}
