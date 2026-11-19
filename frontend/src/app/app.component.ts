import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TimeoutError } from 'rxjs';
import { ChatResponse, ChatService } from './services/chat.service';

type Turn = {
  who: 'user' | 'assistant' | 'error';
  text: string;
  elapsedMs?: number;
};

type Suggestion = { label: string; eyebrow: string; question: string };

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  @ViewChild('transcript') transcript?: ElementRef<HTMLElement>;

  input = '';
  loading = false;
  healthState: 'checking' | 'up' | 'down' = 'checking';
  healthText = 'Comprobando Ollama';
  modelName = 'qwen2.5:3b';
  turns: Turn[] = [];
  readonly sessionId = globalThis.crypto?.randomUUID?.() ?? String(Date.now());

  readonly suggestions: Suggestion[] = [
    { eyebrow: 'Clima', label: '¿Lloverá en Guatavita?', question: '¿Cómo estará el clima en Guatavita el domingo?' },
    { eyebrow: 'Presupuesto', label: 'Calcular un plan', question: 'Somos 4 amigos con 350000 pesos. ¿Nos alcanza para ir a Zipaquirá?' },
    { eyebrow: 'Actividades', label: 'Qué hacer en Villa de Leyva', question: '¿Qué actividades podemos hacer en Villa de Leyva y cómo estará el clima el domingo?' },
    { eyebrow: 'Plan completo', label: 'Validar y reservar', question: 'Somos 3 y tenemos 250000. Si no llueve mucho y nos alcanza, reserva Suesca para el sábado a nombre de Laura.' }
  ];

  readonly specialists = [
    { code: 'CL', name: 'Clima', detail: 'Pronóstico del fin de semana' },
    { code: 'PR', name: 'Presupuesto', detail: 'Costos y saldo disponible' },
    { code: 'AC', name: 'Actividades', detail: 'Planes según el destino' },
    { code: 'RE', name: 'Reservas', detail: 'Cupos y confirmaciones' }
  ];

  constructor(private readonly api: ChatService) {}

  ngOnInit(): void { this.probe(); }

  probe(): void {
    this.healthState = 'checking';
    this.api.health().subscribe({
      next: response => {
        this.healthState = response.ok ? 'up' : 'down';
        this.modelName = response.result?.models?.[0]?.name ?? this.modelName;
        this.healthText = response.ok ? 'Sistema listo' : 'Ollama no responde';
      },
      error: () => {
        this.healthState = 'down';
        this.healthText = 'Backend desconectado';
      }
    });
  }

  useSuggestion(suggestion: Suggestion): void {
    if (this.loading) return;
    this.input = suggestion.question;
    this.send();
  }

  send(): void {
    const question = this.input.trim();
    if (!question || this.loading) return;

    this.turns.push({ who: 'user', text: question });
    this.input = '';
    this.loading = true;
    this.scrollToEnd();

    this.api.send({ question, sessionId: this.sessionId }).subscribe({
      next: response => this.finish(response),
      error: (error: HttpErrorResponse | TimeoutError) => {
        const message = error instanceof TimeoutError
          ? 'El modelo tardó más de cuatro minutos. Puedes intentar de nuevo.'
          : error instanceof HttpErrorResponse && error.status
            ? `La API respondió con el estado HTTP ${error.status}.`
            : 'No fue posible conectar con el planeador.';
        this.turns.push({ who: 'error', text: message });
        this.loading = false;
        this.healthState = 'down';
        this.healthText = 'Revisa los servicios';
        this.scrollToEnd();
      }
    });
  }

  handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  clearConversation(): void { this.turns = []; }

  private finish(response: ChatResponse): void {
    const valid = response.status === 'ok' && response.answer.trim().length > 0;
    this.turns.push({
      who: valid ? 'assistant' : 'error',
      text: valid ? response.answer : 'El modelo devolvió una respuesta vacía.',
      elapsedMs: response.elapsedMs
    });
    this.loading = false;
    this.probe();
    this.scrollToEnd();
  }

  private scrollToEnd(): void {
    setTimeout(() => this.transcript?.nativeElement.scrollTo({
      top: this.transcript.nativeElement.scrollHeight,
      behavior: 'smooth'
    }));
  }
}
