import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AgingReport {
  '0_30': string;
  '31_60': string;
  '61_90': string;
  over_90: string;
  total: string;
}

export interface PnlRow {
  project_id: string;
  project_name: string;
  currency: string;
  revenue: string;
  direct_cost: string;
  gross_margin: string;
  gross_margin_pct: number;
}

export interface UtilRow {
  employee_id: string;
  total_hours: string;
  billable_hours: string;
  utilization_pct: number;
}

export interface WipRow {
  project_id: string;
  project_name: string;
  unbilled_hours: string;
  avg_rate: string;
  wip_value: string;
}

export interface RevenueRow {
  engagement_id: string;
  engagement_name?: string;
  total_invoiced: string;
  currency?: string;
}

export interface TrialBalanceLine {
  account_code: string;
  account_name: string;
  account_type: 'asset' | 'liability' | 'equity' | 'revenue' | 'expense';
  total_dr: string;
  total_cr: string;
  net: string;
}

export interface TrialBalanceReport {
  as_of_period: string | null;
  lines: TrialBalanceLine[];
  grand_total_dr: string;
  grand_total_cr: string;
  is_balanced: boolean;
  generated_at: string;
}

@Injectable({ providedIn: 'root' })
export class ReportsService {
  private http = inject(HttpClient);
  private base = '/api/v1/reports';

  getArAging = (): Observable<AgingReport> =>
    this.http.get<AgingReport>(`${this.base}/ar-aging`);

  getApAging = (): Observable<AgingReport> =>
    this.http.get<AgingReport>(`${this.base}/ap-aging`);

  getProjectPnl = (pid?: string): Observable<PnlRow[]> =>
    this.http.get<PnlRow[]>(`${this.base}/project-pnl${pid ? '?project_id=' + pid : ''}`);

  getUtilization = (): Observable<UtilRow[]> =>
    this.http.get<UtilRow[]>(`${this.base}/utilization`);

  getWip = (): Observable<WipRow[]> =>
    this.http.get<WipRow[]>(`${this.base}/wip`);

  getRevenueByEngagement = (): Observable<RevenueRow[]> =>
    this.http.get<RevenueRow[]>(`${this.base}/revenue-by-engagement`);

  getTrialBalance = (asOfPeriod?: string): Observable<TrialBalanceReport> => {
    const params = asOfPeriod ? `?as_of_period=${asOfPeriod}` : '';
    return this.http.get<TrialBalanceReport>(`${this.base}/trial-balance${params}`);
  };
}
