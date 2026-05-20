import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TimeEntry {
  id: string;
  project_id: string;
  employee_id: string;
  date: string;
  hours: string;        // Decimal as string from API — never parseFloat for computation
  description: string;
  billable: boolean;
  billing_status: string; // 'unbilled' | 'billed' | 'non_billable'
}

export interface TimeEntryListResponse {
  items: TimeEntry[];
  total: number;
}

export interface TimeEntryCreate {
  project_id?: string;
  date: string;
  hours: string;
  description: string;
  billable?: boolean;
}

export interface TimeEntryFilters {
  project_id?: string;
  date_from?: string;
  date_to?: string;
}

@Injectable({ providedIn: 'root' })
export class TimeEntriesService {
  private http = inject(HttpClient);
  private base = '/api/v1';

  getEntries(filters?: TimeEntryFilters): Observable<TimeEntryListResponse> {
    let params = new HttpParams();
    if (filters?.project_id) params = params.set('project_id', filters.project_id);
    if (filters?.date_from)  params = params.set('date_from', filters.date_from);
    if (filters?.date_to)    params = params.set('date_to', filters.date_to);
    return this.http.get<TimeEntryListResponse>(`${this.base}/time-entries`, { params });
  }

  createEntry(data: TimeEntryCreate): Observable<TimeEntry> {
    return this.http.post<TimeEntry>(`${this.base}/time-entries`, data);
  }

  updateEntry(id: string, data: Partial<TimeEntryCreate>): Observable<TimeEntry> {
    return this.http.patch<TimeEntry>(`${this.base}/time-entries/${id}`, data);
  }

  deleteEntry(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/time-entries/${id}`);
  }
}
