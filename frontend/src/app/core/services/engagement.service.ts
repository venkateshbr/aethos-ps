import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface EngagementSummary {
  id: string;
  name: string;
  billing_arrangement: string;
  currency: string;
  total_value: string | null;
  status: string;
  client_id: string;
  description?: string | null;
  client_name?: string;
  service_line?: string | null;
  service_catalogue_id?: string | null;
  rate_card_id?: string | null;
  rate_card_name?: string;
  billing_terms?: {
    fixed_fee_amount?: string | null;
    milestone_total?: string | null;
    retainer_monthly_amount?: string | null;
    retainer_floor?: string | null;
    retainer_rollover?: boolean | null;
    cap_amount?: string | null;
    billing_unit?: string | null;
    unit_label?: string | null;
    unit_quantity?: string | null;
    unit_price?: string | null;
  } | null;
  start_date?: string | null;
  end_date?: string | null;
}

// Backend returns a bare array (not a paginated wrapper).
export type EngagementListResponse = EngagementSummary[];

/** Financial summary returned by GET /api/v1/engagements/{id}/summary */
export interface EngagementFinancialSummary {
  engagement_id: string;
  engagement_name: string;
  total_value: string | null;
  currency: string;
  billed_to_date: string;
  billed_pct: number | null;
  wip_hours: number;
  wip_value: string;
  remaining_value: string | null;
  invoice_count: number;
  last_invoice_date: string | null;
}

export interface EngagementDetail extends EngagementSummary {
  description?: string | null;
  created_at?: string;
  updated_at?: string;
  /** Set when the engagement was materialised from an AI extraction (#127). */
  source_document_id?: string | null;
}

export interface EngagementCreate {
  name: string;
  client_id: string;
  billing_arrangement: string;
  currency: string;
  total_value?: string | null;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  rate_card_id?: string | null;
  service_line?: string | null;
  service_catalogue_id?: string | null;
  billing_terms?: {
    fixed_fee_amount?: string | null;
    milestone_total?: string | null;
    retainer_monthly_amount?: string | null;
    retainer_floor?: string | null;
    retainer_rollover?: boolean | null;
    cap_amount?: string | null;
    billing_unit?: string | null;
    unit_label?: string | null;
    unit_quantity?: string | null;
    unit_price?: string | null;
  } | null;
}

export interface ProjectSummary {
  id: string;
  name: string;
  description?: string | null;
  code?: string | null;  // PRJ-0001 (migration 0021)
  engagement_id: string;
  currency: string;
  budget: string | null;
  budget_hours?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status: string;
}

// Backend returns a bare array (not a paginated wrapper).
export type ProjectListResponse = ProjectSummary[];

@Injectable({ providedIn: 'root' })
export class EngagementService {
  private http = inject(HttpClient);
  private base = '/api/v1';

  getEngagements(filters?: {
    status?: string;
    client_id?: string;
    limit?: number;
    offset?: number;
  }): Observable<EngagementListResponse> {
    let params = new HttpParams();
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.client_id) params = params.set('client_id', filters.client_id);
    if (filters?.limit) params = params.set('limit', filters.limit);
    if (filters?.offset) params = params.set('offset', filters.offset);
    return this.http.get<EngagementListResponse>(`${this.base}/engagements`, { params });
  }

  getEngagement(id: string): Observable<EngagementDetail> {
    return this.http.get<EngagementDetail>(`${this.base}/engagements/${id}`);
  }

  createEngagement(data: EngagementCreate): Observable<EngagementDetail> {
    return this.http.post<EngagementDetail>(`${this.base}/engagements`, data);
  }

  getProjects(filters?: { engagement_id?: string }): Observable<ProjectListResponse> {
    let params = new HttpParams();
    if (filters?.engagement_id) params = params.set('engagement_id', filters.engagement_id);
    return this.http.get<ProjectListResponse>(`${this.base}/projects`, { params });
  }

  getEngagementFinancialSummary(id: string): Observable<EngagementFinancialSummary> {
    return this.http.get<EngagementFinancialSummary>(`${this.base}/engagements/${id}/summary`);
  }
}
