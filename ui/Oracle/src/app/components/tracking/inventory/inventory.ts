import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Tabs, TabList, Tab, TabPanels, TabPanel } from 'primeng/tabs';
import { Card } from 'primeng/card';
import { Select } from 'primeng/select';
import { InputText } from 'primeng/inputtext';
import { InventoryService } from '../../../services/inventory.service';
import { PlayerService } from '../../../services/player.service';
import { ItemDetailComponent } from '../../shared/item-detail/item-detail';
import { Item } from '../../../services/item.service';
import { Subscription } from 'rxjs';

interface InventorySlot {
  slot: number;
  item_name: string;
  item_id: number | null;
  quantity: number;
  timestamp: string;
}

interface InventoryPage {
  pageNumber: number;
  pageName: string;
  pageEmoji: string;
  slots: InventorySlot[];
}

@Component({
  selector: 'app-inventory',
  imports: [CommonModule, FormsModule, Tabs, TabList, Tab, TabPanels, TabPanel, Card, Select, InputText, ItemDetailComponent],
  templateUrl: './inventory.html',
  styleUrl: './inventory.css',
})
export class InventoryComponent implements OnInit, OnDestroy {
  pages: InventoryPage[] = [];
  loading: boolean = false;
  playerName: string | null = null;
  searchTerm: string = '';
  availablePlayers: { label: string; value: string }[] = [];
  selectedPlayer: string | null = null;
  showItemDetail: boolean = false;
  selectedItemId: number | null = null;
  private playerSubscription?: Subscription;
  private rawInventory: any = {};

  private getPageName(pageNum: number): string {
    // Special pages
    const specialPages: { [key: number]: string } = {
      100: "Gear",
      101: "Skills",
      102: "Commodities",
      103: "Other"
    };
    
    if (specialPages[pageNum]) {
      return specialPages[pageNum];
    }
    
    // Stash pages (1, 2, 3, ..., 150+, etc.)
    return pageNum === 1 ? "Stash" : `Stash ${pageNum}`;
  }

  private getPageEmoji(pageNum: number): string {
    // Special pages
    const specialEmojis: { [key: number]: string } = {
      100: "⚔️",
      101: "🌟",
      102: "💎",
      103: "📁"
    };
    
    if (specialEmojis[pageNum]) {
      return specialEmojis[pageNum];
    }
    
    // All stash pages use 📦
    return "📦";
  }

  constructor(
    private inventoryService: InventoryService,
    private playerService: PlayerService
  ) {}

  ngOnInit() {
    this.playerName = this.playerService.getName();
    this.playerSubscription = this.playerService.getNameObservable().subscribe(name => {
      this.playerName = name;
      // Update selected player to match the new active player
      this.selectedPlayer = name;
      // Reload inventory to get updated player list and data
      this.loadInventory();
    });
    this.loadInventory();
  }

  ngOnDestroy() {
    if (this.playerSubscription) {
      this.playerSubscription.unsubscribe();
    }
  }

  loadInventory() {
    this.loading = true;
    
    this.inventoryService.getInventory(this.selectedPlayer || undefined)
      .subscribe({
        next: (response) => {
          this.rawInventory = response.inventory;
          const playerNames = Object.keys(response.inventory);
          this.availablePlayers = playerNames.map(name => ({ label: name, value: name }));
          
          // If no player selected, select the first one
          if (!this.selectedPlayer && playerNames.length > 0) {
            this.selectedPlayer = playerNames[0];
          }
          
          this.buildPages();
          this.loading = false;
        },
        error: (error) => {
          console.error('[InventoryComponent] Error loading inventory:', error);
          this.loading = false;
        }
      });
  }

  onPlayerChange() {
    this.buildPages();
  }

  buildPages() {
    this.pages = [];
    
    if (!this.selectedPlayer || !this.rawInventory[this.selectedPlayer]) {
      return;
    }
    
    const playerPages = this.rawInventory[this.selectedPlayer];
    const pageNumbers = Object.keys(playerPages).map(p => parseInt(p)).sort((a, b) => a - b);
    
    console.log(`[InventoryComponent] Player: ${this.selectedPlayer}, Pages: ${pageNumbers.join(', ')}`);
    
    for (const pageNum of pageNumbers) {
      const pageNumber = parseInt(pageNum.toString());
      const pageName = this.getPageName(pageNumber);
      const pageEmoji = this.getPageEmoji(pageNumber);
      const slots = playerPages[pageNum];
      
      this.pages.push({
        pageNumber,
        pageName,
        pageEmoji,
        slots
      });
    }
  }

  getFilteredSlots(slots: InventorySlot[]): InventorySlot[] {
    if (!this.searchTerm) {
      return slots;
    }
    
    const term = this.searchTerm.toLowerCase();
    return slots.filter(slot => 
      slot.item_name.toLowerCase().includes(term) ||
      slot.slot.toString().includes(term)
    );
  }

  openItemDetail(itemId: number | null) {
    if (!itemId) return;
    
    // Pass game item_id to ItemDetailComponent which will use byItemId=true
    this.selectedItemId = itemId;
    this.showItemDetail = true;
  }

  onItemSaved(item: Item) {
    // Optionally refresh inventory or update local data
    console.log('Item saved:', item);
  }
}
