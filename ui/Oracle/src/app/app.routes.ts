import { Routes } from "@angular/router";

export const routes: Routes = [
  { path: '', redirectTo: '/live/currency', pathMatch: 'full' },
  { path: 'live/currency', loadComponent: () => import('./components/live/currency/currency').then(m => m.CurrencyComponent) },
  { path: 'live/session', loadComponent: () => import('./components/live/session/session').then(m => m.SessionComponent) },
  { path: 'overlay/stats', loadComponent: () => import('./components/overlay/stats-overlay/stats-overlay').then(m => m.StatsOverlayComponent) },
  { path: 'tracking/maps', loadComponent: () => import('./components/tracking/maps/maps').then(m => m.MapsComponent) },
  { path: 'tracking/sessions', loadComponent: () => import('./components/tracking/sessions/sessions').then(m => m.SessionsComponent) },
  { path: 'tracking/market', loadComponent: () => import('./components/tracking/market/market').then(m => m.MarketComponent) },
  { path: 'tracking/items', loadComponent: () => import('./components/tracking/items/items').then(m => m.ItemsComponent) },
  { path: 'tracking/inventory', loadComponent: () => import('./components/tracking/inventory/inventory').then(m => m.InventoryComponent) },
  { path: 'settings/configuration', loadComponent: () => import('./components/settings/configuration/configuration').then(m => m.ConfigurationComponent) },
  { path: 'settings/about', loadComponent: () => import('./components/settings/about/about').then(m => m.AboutComponent) },
];


