import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigurationService } from './configuration.service';

@Injectable({
  providedIn: 'root'
})
export class StatsService {
  constructor(
    private http: HttpClient,
    private configService: ConfigurationService
  ) {}

  newSession(): Observable<any> {
    const url = `${this.configService.getApiUrl()}/sessions`;
    return this.http.post(url, {});
  }

  resetStats(): Observable<any> {
    const url = `${this.configService.getApiUrl()}/stats/reset`;
    return this.http.post(url, {});
  }
}
