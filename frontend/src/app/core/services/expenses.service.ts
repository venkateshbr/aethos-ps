import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Expense {
  id: string;
  project_id?: string;
  date: string;
  vendor: string;
  amount: string;         // Decimal as string from API
  currency: string;
  category: string;
  billable: boolean;
  description?: string;
  status?: string;
  /** Set when the expense was materialised from a receipt extraction (#127). */
  document_id?: string | null;
}

// Backend returns a bare array (not a paginated wrapper).
export type ExpenseListResponse = Expense[];

export interface ExpenseFilters {
  project_id?: string;
  date_from?: string;
  date_to?: string;
}

@Injectable({ providedIn: 'root' })
export class ExpensesService {
  private http = inject(HttpClient);
  private base = '/api/v1';

  getExpenses(filters?: ExpenseFilters): Observable<ExpenseListResponse> {
    let params = new HttpParams();
    if (filters?.project_id) params = params.set('project_id', filters.project_id);
    if (filters?.date_from)  params = params.set('date_from', filters.date_from);
    if (filters?.date_to)    params = params.set('date_to', filters.date_to);
    return this.http.get<ExpenseListResponse>(`${this.base}/expenses`, { params });
  }
}
