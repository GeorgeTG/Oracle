import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DialogModule } from 'primeng/dialog';
import { InputText } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { Item, ItemService } from '../../../services/item.service';
import { ToastService } from '../../../services/toast.service';

@Component({
  selector: 'app-item-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, DialogModule, InputText, ButtonModule],
  templateUrl: './item-detail.html',
  styleUrl: './item-detail.css',
})
export class ItemDetailComponent {
  @Input() visible: boolean = false;
  @Input() itemId: number | null = null;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() onSave = new EventEmitter<Item>();

  itemDetail: Item | null = null;
  loading: boolean = false;

  constructor(
    private itemService: ItemService,
    private toastService: ToastService
  ) {}

  ngOnChanges() {
    if (this.visible && this.itemId) {
      this.loadItemDetails();
    }
  }

  loadItemDetails() {
    if (!this.itemId) return;
    
    this.loading = true;
    // Use byItemId=true since inventory passes game item_id
    this.itemService.getItem(this.itemId, true).subscribe({
      next: (details) => {
        this.itemDetail = details;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading item details:', error);
        this.toastService.error('Error', 'Failed to load item details');
        this.loading = false;
        this.closeDialog();
      }
    });
  }

  saveItem() {
    if (!this.itemDetail) return;
    
    this.itemService.updateItem(this.itemDetail.id, {
      name: this.itemDetail.name || undefined,
      category: this.itemDetail.category || undefined,
      rarity: this.itemDetail.rarity || undefined,
      price: this.itemDetail.price
    }).subscribe({
      next: (response) => {
        this.toastService.success('Updated', 'Item updated successfully');
        this.onSave.emit(this.itemDetail!);
        this.closeDialog();
      },
      error: (error) => {
        console.error('Error updating item:', error);
        this.toastService.error('Update Failed', 'Failed to update item');
      }
    });
  }

  closeDialog() {
    this.visible = false;
    this.visibleChange.emit(false);
    this.itemDetail = null;
  }
}
