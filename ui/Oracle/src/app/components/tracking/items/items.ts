import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ItemService, Item } from '../../../services/item.service';
import { ToastService } from '../../../services/toast.service';
import { TableModule } from 'primeng/table';
import { InputText } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';
import { save } from '@tauri-apps/plugin-dialog';

@Component({
  selector: 'app-tracking-items',
  imports: [CommonModule, FormsModule, TableModule, InputText, DialogModule, ButtonModule],
  templateUrl: './items.html',
  styleUrl: './items.css',
})
export class ItemsComponent implements OnInit {
  items: Item[] = [];
  loading: boolean = false;
  exporting: boolean = false;
  saving: boolean = false;
  selectedItemDetail: Item | null = null;
  showDetailDialog: boolean = false;
  isCreateMode: boolean = false;

  // Filter values
  filterCategory: string = '';
  filterMinPrice: number | null = null;
  filterMaxPrice: number | null = null;

  constructor(
    private itemService: ItemService,
    private toastService: ToastService
  ) {}

  ngOnInit() {
    this.loadItems();
  }

  loadItems() {
    this.loading = true;
    
    const category = this.filterCategory || undefined;
    const minPrice = this.filterMinPrice || undefined;
    const maxPrice = this.filterMaxPrice || undefined;
    
    this.itemService.getItems(category, minPrice, maxPrice, 1000)
      .subscribe({
        next: (items: Item[]) => {
          this.items = items;
          this.loading = false;
        },
        error: (error) => {
          console.error('[ItemsComponent] Error loading items:', error);
          this.toastService.error('Error', 'Failed to load items');
          this.loading = false;
        }
      });
  }

  onFilterChange() {
    this.loadItems();
  }

  formatNumber(value: number | undefined | null, decimals: number = 0): string {
    if (value === undefined || value === null) return 'N/A';
    const fixed = value.toFixed(decimals);
    const parts = fixed.split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return parts.join(',');
  }

  showItemDetails(item: Item) {
    this.isCreateMode = false;
    this.itemService.getItem(item.id).subscribe({
      next: (details) => {
        this.selectedItemDetail = details;
        this.showDetailDialog = true;
      },
      error: (error) => {
        console.error('Error loading item details:', error);
        this.toastService.error('Error', 'Failed to load item details');
      }
    });
  }

  openCreateDialog() {
    this.isCreateMode = true;
    this.selectedItemDetail = {
      id: 0,
      item_id: 0,
      name: '',
      category: '',
      rarity: '',
      price: 0
    };
    this.showDetailDialog = true;
  }

  confirmDeleteItem(item: Item) {
    if (confirm(`Are you sure you want to delete this item?\n${item.name || 'Item #' + item.item_id}`)) {
      this.deleteItem(item.id);
    }
  }

  deleteItem(itemId: number) {
    this.itemService.deleteItem(itemId).subscribe({
      next: () => {
        this.toastService.success('Item Deleted', 'Item deleted successfully');
        // Reload the table
        this.items = this.items.filter(i => i.id !== itemId);
      },
      error: (error) => {
        console.error('Error deleting item:', error);
        this.toastService.error('Delete Failed', 'Failed to delete item');
      }
    });
  }

  saveItem() {
    if (!this.selectedItemDetail) return;

    this.saving = true;

    if (this.isCreateMode) {
      // Create new item
      this.itemService.createItem({
        item_id: this.selectedItemDetail.item_id,
        name: this.selectedItemDetail.name || undefined,
        category: this.selectedItemDetail.category || undefined,
        rarity: this.selectedItemDetail.rarity || undefined,
        price: this.selectedItemDetail.price
      }).subscribe({
        next: (response) => {
          this.toastService.success('Created', 'Item created successfully');
          this.items = [response, ...this.items];
          this.showDetailDialog = false;
          this.saving = false;
        },
        error: (error) => {
          console.error('Error creating item:', error);
          this.toastService.error('Create Failed', error.error?.detail || 'Failed to create item');
          this.saving = false;
        }
      });
    } else {
      // Update existing item
      this.itemService.updateItem(this.selectedItemDetail.id, {
        name: this.selectedItemDetail.name || undefined,
        category: this.selectedItemDetail.category || undefined,
        rarity: this.selectedItemDetail.rarity || undefined,
        price: this.selectedItemDetail.price
      }).subscribe({
        next: (response) => {
          this.toastService.success('Updated', 'Item updated successfully');
          // Update the item in the list if it exists
          const itemIndex = this.items.findIndex(i => i.id === this.selectedItemDetail!.id);
          if (itemIndex !== -1) {
            this.items[itemIndex] = { ...this.selectedItemDetail! };
          }
          this.showDetailDialog = false;
          this.saving = false;
        },
        error: (error) => {
          console.error('Error updating item:', error);
          this.toastService.error('Update Failed', 'Failed to update item');
          this.saving = false;
        }
      });
    }
  }

  exportItems() {
    this.exporting = true;
    this.itemService.exportItems().subscribe({
      next: async (blob) => {
        try {
          // Use Tauri save dialog
          const filePath = await save({
            defaultPath: `items_export_${new Date().toISOString().split('T')[0]}.json`,
            filters: [{
              name: 'JSON',
              extensions: ['json']
            }]
          });

          if (filePath) {
            // Read blob as text
            const text = await blob.text();
            
            // Write file using Tauri
            const { writeTextFile } = await import('@tauri-apps/plugin-fs');
            await writeTextFile(filePath, text);
            
            this.toastService.success('Export Complete', 'Items exported successfully');
          }
        } catch (error) {
          console.error('Error saving file:', error);
          this.toastService.error('Export Failed', 'Failed to save file');
        } finally {
          this.exporting = false;
        }
      },
      error: (error) => {
        console.error('Error exporting items:', error);
        this.toastService.error('Export Failed', 'Failed to export items');
        this.exporting = false;
      }
    });
  }
}
