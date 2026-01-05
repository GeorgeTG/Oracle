import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FloatLabel } from 'primeng/floatlabel';
import { InputText, InputTextClasses } from 'primeng/inputtext';
import { Button } from 'primeng/button';
import { Checkbox } from 'primeng/checkbox';
import { ToggleSwitch } from 'primeng/toggleswitch';
import { WebSocketService } from '../../../services/websocket.service';
import { ConfigurationService } from '../../../services/configuration.service';

@Component({
  selector: 'app-configuration',
  imports: [FormsModule, FloatLabel, InputText, Button, ToggleSwitch],
  templateUrl: './configuration.html',
  styleUrl: './configuration.css',
})
export class ConfigurationComponent implements OnInit {
  wsIp: string = '127.0.0.1';
  wsPort: string = '8000';
  transparentOverlay: boolean = false;
  showDataPerMinute: boolean = false;
  showTax: boolean = false;
  aggregateNumbers: boolean = false;

  constructor(
    private websocketService: WebSocketService,
    private configService: ConfigurationService
  ) {}

  ngOnInit() {
    // Load from ConfigurationService
    const config = this.configService.getConfig();
    this.wsIp = config.wsIp;
    this.wsPort = config.wsPort;
    this.transparentOverlay = config.transparentOverlay;
    this.showDataPerMinute = config.showDataPerMinute;
    this.showTax = config.showTax;
    this.aggregateNumbers = config.aggregateNumbers;
  }

  saveSettings() {
    // Save via ConfigurationService
    this.configService.saveConfiguration({
      wsIp: this.wsIp,
      wsPort: this.wsPort,
      transparentOverlay: this.transparentOverlay,
      showDataPerMinute: this.showDataPerMinute,
      showTax: this.showTax,
      aggregateNumbers: this.aggregateNumbers
    });
    
    console.log('Settings saved:', { ip: this.wsIp, port: this.wsPort, transparentOverlay: this.transparentOverlay, showDataPerMinute: this.showDataPerMinute });
    
    // Reconnect with new settings
    this.websocketService.reconnect();
  }
}
