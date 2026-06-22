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

export interface ProjectHealthDriver {
  code: string;
  label: string;
  severity: 'watch' | 'critical' | string;
  impact: number;
  metric: string;
  threshold: string;
  summary: string;
  recommended_action: string;
}

export interface ProjectHealthRow {
  project_id: string;
  project_name: string;
  engagement_id: string | null;
  engagement_name?: string;
  service_line: string;
  currency: string;
  health_score: number;
  risk_level: 'healthy' | 'watch' | 'at_risk' | 'critical';
  drivers: ProjectHealthDriver[];
  metrics: Record<string, string | number | null>;
  recommended_actions: string[];
}

export interface CapacityAssignment {
  project_id: string;
  project_name?: string;
  role?: string;
  start_date?: string;
  end_date?: string;
}

export interface CapacityRow {
  employee_id: string;
  employee_name: string;
  email?: string;
  department?: string;
  practice_area?: string;
  seniority?: string;
  period_start: string;
  period_end: string;
  capacity_hours: string;
  logged_hours: string;
  billable_hours: string;
  utilization_pct: number;
  billable_utilization_pct: number;
  active_assignment_count: number;
  active_assignments: CapacityAssignment[];
  capacity_status: 'overallocated' | 'full' | 'underutilized' | 'balanced';
  recommended_action: string;
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

  getProjectHealth = (): Observable<ProjectHealthRow[]> =>
    this.http.get<ProjectHealthRow[]>(`${this.base}/project-health`);

  getCapacityPlanning = (): Observable<CapacityRow[]> =>
    this.http.get<CapacityRow[]>(`${this.base}/capacity-planning`);

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
