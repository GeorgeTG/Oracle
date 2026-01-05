import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface InventorySlot {
  slot: number;
  item_name: string;
  item_id: number | null;
  quantity: number;
  timestamp: string;
}

export interface InventoryPage {
  [page: number]: InventorySlot[];
}

export interface InventoryData {
  [playerName: string]: InventoryPage;
}

export interface InventoryResponse {
  inventory: InventoryData;
}

@Injectable({
  providedIn: 'root'
})
export class InventoryService {
  constructor(private http: HttpClient) {}

  private getApiUrl(): string {
    const ip = localStorage.getItem('server_ip') || 'localhost';
    const port = localStorage.getItem('server_port') || '8000';
    return `http://${ip}:${port}`;
  }

  getInventory(playerName?: string): Observable<InventoryResponse> {
    const url = `${this.getApiUrl()}/inventory`;
    
    let params = new HttpParams();
    if (playerName) {
      params = params.set('player_name', playerName);
    }
    
    return this.http.get<InventoryResponse>(url, { params });
  }
}
