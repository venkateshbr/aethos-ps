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
  client_name?: string;
  rate_card_name?: string;
  start_date?: string | null;
  end_date?: string | null;
}

export interface EngagementListResponse {
  items: EngagementSummary[];
  total: number;
}

export interface EngagementDetail extends EngagementSummary {
  description?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface EngagementCreate {
  name: string;
  client_id: string;
  billing_arrangement: string;
  currency: string;
  total_value?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  rate_card_id?: string | null;
}

export interface ProjectSummary {
  id: string;
  name: string;
  engagement_id: string;
  currency: string;
  budget: string | null;
  status: string;
}

export interface ProjectListResponse {
  items: ProjectSummary[];
  total: number;
}

@Injectable({ providedIn: 'root' })
export class EngagementService {
  private http = inject(HttpClient);
  private base = '/api/v1';

  getEngagements(filters?: { status?: string; client_id?: string }): Observable<EngagementListResponse> {
    let params = new HttpParams();
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.client_id) params = params.set('client_id', filters.client_id);
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
}
