import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FloatLabel } from 'primeng/floatlabel';
import { InputText, InputTextClasses } from 'primeng/inputtext';
import { Button } from 'primeng/button';
import { Checkbox } from 'primeng/checkbox';
import { ToggleSwitch } from 'primeng/toggleswitch';
import { InputNumber } from 'primeng/inputnumber';
import { Subscription } from 'rxjs';
import { WebSocketService, ComponentStatus } from '../../../services/websocket.service';
import { ConfigurationService } from '../../../services/configuration.service';

@Component({
  selector: 'app-configuration',
  imports: [FormsModule, FloatLabel, InputText, Button, ToggleSwitch, InputNumber],
  templateUrl: './configuration.html',
  styleUrl: './configuration.css',
})
export class ConfigurationComponent implements OnInit, OnDestroy {
  wsIp: string = '127.0.0.1';
  wsPort: string = '8000';
  transparentOverlay: boolean = false;
  showDataPerMinute: boolean = false;
  aggregateNumbers: boolean = false;
  riverMinValue: number = 1;
  hotkeyKey: string = 'PageUp';
  toggleOverlayKey: string = 'PageDown';
  recordingHotkey: boolean = false;
  recordingToggleOverlay: boolean = false;
  private activeRecording: 'hotkey' | 'toggleOverlay' | null = null;
  componentStatus: ComponentStatus[] = [];
  private statusSub?: Subscription;

  constructor(
    private websocketService: WebSocketService,
    private configService: ConfigurationService
  ) {}

  ngOnInit() {
    const config = this.configService.getConfig();
    this.wsIp = config.wsIp;
    this.wsPort = config.wsPort;
    this.transparentOverlay = config.transparentOverlay;
    this.showDataPerMinute = config.showDataPerMinute;
    this.aggregateNumbers = config.aggregateNumbers;
    this.riverMinValue = config.riverMinValue;
    this.hotkeyKey = config.hotkeyKey;
    this.toggleOverlayKey = config.toggleOverlayKey;

    this.statusSub = this.websocketService.componentStatus$.subscribe(status => {
      this.componentStatus = status;
    });
  }

  ngOnDestroy() {
    this.statusSub?.unsubscribe();
  }

  saveSettings() {
    this.configService.saveConfiguration({
      wsIp: this.wsIp,
      wsPort: this.wsPort,
      transparentOverlay: this.transparentOverlay,
      showDataPerMinute: this.showDataPerMinute,
      aggregateNumbers: this.aggregateNumbers,
      riverMinValue: this.riverMinValue,
      hotkeyKey: this.hotkeyKey,
      toggleOverlayKey: this.toggleOverlayKey
    });

    console.log('Settings saved:', { ip: this.wsIp, port: this.wsPort, hotkeyKey: this.hotkeyKey, toggleOverlayKey: this.toggleOverlayKey });

    this.websocketService.reconnect();
  }

  startRecording(target: 'hotkey' | 'toggleOverlay') {
    if (this.activeRecording === target) {
      // Cancel recording
      this.activeRecording = null;
      this.recordingHotkey = false;
      this.recordingToggleOverlay = false;
      return;
    }

    this.activeRecording = target;
    this.recordingHotkey = target === 'hotkey';
    this.recordingToggleOverlay = target === 'toggleOverlay';
  }

  @HostListener('window:keydown', ['$event'])
  onKeyDown(event: KeyboardEvent) {
    if (!this.activeRecording) return;
    event.preventDefault();
    event.stopPropagation();

    if (this.activeRecording === 'hotkey') {
      this.hotkeyKey = event.key;
    } else if (this.activeRecording === 'toggleOverlay') {
      this.toggleOverlayKey = event.key;
    }

    this.activeRecording = null;
    this.recordingHotkey = false;
    this.recordingToggleOverlay = false;
  }
}
