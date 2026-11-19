import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, timeout } from 'rxjs';

export interface ChatRequest {
  question: string;
  sessionId: string;
}

export interface ChatResponse {
  requestId: string;
  answer: string;
  elapsedMs: number;
  status: string;
}

export interface HealthResponse {
  ok: boolean;
  result?: { models?: Array<{ name?: string }> };
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  constructor(private readonly http: HttpClient) {}

  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>('/health/llm').pipe(timeout(8000));
  }

  send(request: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>('/api/v1/chat', request).pipe(timeout(240000));
  }
}
