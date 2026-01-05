import { Injectable } from '@angular/core';
import { MessageService } from 'primeng/api';

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  constructor(private messageService: MessageService) {}

  success(message: string, detail?: string, life: number = 5000) {
    this.messageService.add({
      severity: 'success',
      summary: message,
      detail: detail,
      life: life
    });
  }

  info(message: string, detail?: string, life: number = 5000) {
    this.messageService.add({
      severity: 'info',
      summary: message,
      detail: detail,
      life: life
    });
  }

  warn(message: string, detail?: string, life: number = 5000) {
    this.messageService.add({
      severity: 'warn',
      summary: message,
      detail: detail,
      life: life
    });
  }

  error(message: string, detail?: string, life: number = 8000) {
    this.messageService.add({
      severity: 'error',
      summary: message,
      detail: detail,
      life: life
    });
  }

  secondary(message: string, detail?: string, life: number = 5000) {
    this.messageService.add({
      severity: 'secondary',
      summary: message,
      detail: detail,
      life: life
    });
  }

  clear() {
    this.messageService.clear();
  }
}
