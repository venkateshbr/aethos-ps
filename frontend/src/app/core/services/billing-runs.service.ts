import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface Bill {
  id: string;
  bill_number: string;
  client_id: string;
  amount: string;
  total?: string;
  subtotal?: string;
  currency: string;
  due_date: string;
  status: string;
  /** Set when the bill was materialised from a vendor-invoice extraction (#127). */
  source_document_id?: string | null;
}

export interface PaymentBatch {
  id: string;
  status: string;
  total?: string;
  total_amount: string;
  currency: string;
  pay_date: string;
  bank_account_label: string;
  bill_ids: string[];
  export_file_sha256?: string | null;
  file_format?: string | null;
}

export interface PaymentSettlement {
  batch_id: string;
  status: string;
  settled_count: number;
  journal_entry_ids: string[];
}

@Injectable({ providedIn: 'root' })
export class BillingRunsService {
  private http = inject(HttpClient);

  getBills = (status = 'approved'): Observable<Bill[]> =>
    this.http
      .get<Bill[] | { items?: Array<Bill & { total?: string; subtotal?: string }>; total?: number }>(
        `/api/v1/bills?status=${status}`,
      )
      .pipe(
        map((res) => {
          const raw = Array.isArray(res) ? res : (res.items ?? []);
          return raw.map((bill) => ({
            ...bill,
            amount: bill.amount ?? bill.total ?? bill.subtotal ?? '0.00',
          }));
        }),
      );

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

  settleBatch = (id: string): Observable<PaymentSettlement> =>
    this.http.post<PaymentSettlement>(`/api/v1/bill-payments/batches/${id}/settle`, {});

  exportBatch = (id: string, fmt: 'nacha' | 'csv'): Observable<Blob> =>
    this.http.get(`/api/v1/bill-payments/batches/${id}/export?format=${fmt}`, {
      responseType: 'blob',
    });
}
