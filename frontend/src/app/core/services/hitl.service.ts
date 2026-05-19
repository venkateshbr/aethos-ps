import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface HitlTask {
  id: string;
  kind: string;
  priority: string;
  title: string;
  agent_name: string;
  confidence: string;   // string from API per Aethos money/decimal contract
  status: string;
  created_at: string;
  suggestion_payload: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class HitlService {
  private http = inject(HttpClient);
  private base = '/api/v1/inbox';

  getTasks(status = 'open', kind?: string): Observable<HitlTask[]> {
    let url = `${this.base}/tasks?status=${status}`;
    if (kind) url += `&kind=${kind}`;
    return this.http.get<HitlTask[]>(url);
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
