import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';

export interface HitlTask {
  id: string;
  tenant_id: string;
  kind: string;
  priority: string;
  title: string;
  agent_name: string;
  confidence: string;   // string from API per Aethos money/decimal contract
  status: string;
  created_at: string;
  suggestion_payload: Record<string, unknown>;
  required_approval_role?: string | null;
  approval_policy_reason?: string | null;
  approval_policy?: Record<string, unknown>;
  /** Entity that triggered this task — used for navigation on intelligence_alert cards. */
  related_entity_type?: string;
  related_entity_id?: string;
}

@Injectable({ providedIn: 'root' })
export class HitlService {
  private http = inject(HttpClient);
  private base = '/api/v1/inbox';

  getTasks(status = 'open', kind?: string): Observable<HitlTask[]> {
    let url = `${this.base}/tasks?status=${status}`;
    if (kind) url += `&kind=${kind}`;
    // Backend wraps the list: GET /inbox/tasks → { items: HitlTask[] }.
    return this.http.get<{ items: HitlTask[] }>(url).pipe(map(r => r.items ?? []));
  }

  approve(taskId: string): Observable<unknown> {
    return this.http.post(`${this.base}/tasks/${taskId}/approve`, {});
  }

  approveWithEdits(taskId: string, payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(`${this.base}/tasks/${taskId}/approve-with-edits`, { corrected_payload: payload });
  }

  reject(taskId: string, reason = ''): Observable<unknown> {
    return this.http.post(`${this.base}/tasks/${taskId}/reject`, { reason });
  }

  escalate(taskId: string): Observable<unknown> {
    return this.http.post(`${this.base}/tasks/${taskId}/escalate`, {});
  }
}
