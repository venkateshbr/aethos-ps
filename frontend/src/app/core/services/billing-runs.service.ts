import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Bill {
  id: string;
  bill_number: string;
  client_id: string;
  amount: string;
  currency: string;
  due_date: string;
  status: string;
}

export interface PaymentBatch {
  id: string;
  status: string;
  total_amount: string;
  currency: string;
  pay_date: string;
  bank_account_label: string;
  bill_ids: string[];
}

@Injectable({ providedIn: 'root' })
export class BillingRunsService {
  private http = inject(HttpClient);

  getBills = (status = 'approved'): Observable<Bill[]> =>
    this.http.get<Bill[]>(`/api/v1/bills?status=${status}`);

  createBatch = (billIds: string[], payDate?: string, bankLabel = ''): Observable<PaymentBatch> =>
    this.http.post<PaymentBatch>('/api/v1/bill-payments/batches', {
      bill_ids: billIds,
      pay_date: payDate,
      bank_account_label: bankLabel,
    });

  approveBatch = (id: string): Observable<PaymentBatch> =>
    this.http.post<PaymentBatch>(`/api/v1/bill-payments/batches/${id}/approve`, {});

  markSent = (id: string): Observable<PaymentBatch> =>
    this.http.patch<PaymentBatch>(`/api/v1/bill-payments/batches/${id}/mark-sent`, {});

  exportBatch = (id: string, fmt: 'nacha' | 'csv'): Observable<Blob> =>
    this.http.get(`/api/v1/bill-payments/batches/${id}/export?format=${fmt}`, {
      responseType: 'blob',
    });
}
