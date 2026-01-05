import { Pipe, PipeTransform, inject } from '@angular/core';
import { ConfigurationService } from '../services/configuration.service';

@Pipe({
  name: 'currency',
  standalone: true,
  pure: false
})
export class CurrencyPipe implements PipeTransform {
  private configService = inject(ConfigurationService);

  transform(value: number, isPeriodic: boolean = false, unit: string = 'fe', decimals: number = 2): string {
    return isPeriodic ?
            this.configService.formatPeriodicValue(value, unit, decimals) :
            this.configService.formatValue(value, unit, decimals);
  }
}
