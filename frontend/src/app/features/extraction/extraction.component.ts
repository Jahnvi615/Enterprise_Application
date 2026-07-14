import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface ExtractionSummary {
  periods: string[];
  row_count: number;
  line_items: number;
}

interface ExtractionResponse {
  job_id: string;
  detected_pages: Record<string, number | null>;
  statements_extracted: string[];
  output_filename: string;
  template_output_filename: string | null;
  summary: Record<string, ExtractionSummary>;
}

@Component({
  selector: 'app-extraction',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './extraction.component.html',
  styleUrl: './extraction.component.scss',
})
export class ExtractionComponent {
  pdfFile: File | null = null;
  templateFile: File | null = null;
  loading = false;
  error = '';
  result: ExtractionResponse | null = null;
  timeTaken = '';

  constructor(private http: HttpClient) {}

  onPdfSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.pdfFile = input.files?.[0] || null;
  }

  onTemplateSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.templateFile = input.files?.[0] || null;
  }

  extract(): void {
    if (!this.pdfFile) return;

    this.loading = true;
    this.error = '';
    this.result = null;
    this.timeTaken = '';
    const startTime = performance.now();

    const formData = new FormData();
    formData.append('pdf', this.pdfFile);
    if (this.templateFile) {
      formData.append('template', this.templateFile);
    }

    this.http
      .post<ExtractionResponse>(`${environment.apiUrl}/extraction/upload`, formData)
      .subscribe({
        next: (res) => {
          this.result = res;
          this.timeTaken = this.formatDuration((performance.now() - startTime) / 1000);
          this.loading = false;
        },
        error: (err) => {
          this.error = err.error?.error || err.error?.detail || 'Extraction failed';
          this.loading = false;
        },
      });
  }

  private formatDuration(seconds: number): string {
    if (seconds < 60) {
      return `${seconds.toFixed(1)} sec`;
    }
    const minutes = Math.floor(seconds / 60);
    const remaining = Math.floor(seconds % 60);
    if (remaining === 0) {
      return `${minutes} min`;
    }
    return `${minutes} min ${remaining} sec`;
  }

  download(): void {
    if (!this.result) return;
    const url = `${environment.apiUrl}/extraction/download/${this.result.output_filename}`;
    window.open(url, '_blank');
  }

  downloadTemplate(): void {
    if (!this.result?.template_output_filename) return;
    const url = `${environment.apiUrl}/extraction/download/${this.result.template_output_filename}`;
    window.open(url, '_blank');
  }

  getPageEntries() {
    if (!this.result) return [];
    return Object.entries(this.result.detected_pages).map(([key, value]) => ({ key, value }));
  }

  getSummaryEntries() {
    if (!this.result) return [];
    return Object.entries(this.result.summary).map(([key, value]) => ({ key, value }));
  }

  formatStatementName(key: string): string {
    return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
}
