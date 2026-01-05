# Oracle

A comprehensive game log parsing and analytics platform for tracking player progression, map completions, inventory changes, and market activity.

## Overview

Oracle is a real-time game analytics system that monitors game logs, extracts meaningful events, and provides a web-based dashboard for tracking player statistics, farming sessions, and item economy.

## Usage Instructions

### Initial Setup

1. **Enable Game Logging**
   - Launch Torchlight Infinite
   - Go to game settings and **enable logging**
   - This creates the `UE_game.log` file needed for tracking

2. **Launch Oracle**
   - Run the `Oracle-Launcher.exe`
   - Click **"Auto-Detect"** to find the game log file automatically, or **"Browse..."** to select it manually
   - Click **"Save to Config"** to save the log path
   - Click **"Start Server"** - the server runs in the **system tray** (look for the Oracle icon)
   - Click **"Start UI"** to open the Oracle desktop application

3. **Prepare Your Character**
   - **Relog** (exit and re-enter the game) to reset the log parser state
   - Open your **inventory** and click **"Sort"** for all tabs
   - Open **all stash tabs** to ensure the parser captures your complete inventory

### Starting a Farming Session

1. **Create a New Session**
   - In the Oracle UI, navigate to **Live → Session**
   - Click **"New"** to start a new farming session
   - Give your session a name and description

2. **Enable Stats Overlay** (Optional)
   - Navigate to **Live → Currency**
   - Find the **"Stats Overlay"** button
   - Click to open the transparent overlay window
   - **Drag and position** the overlay wherever you want on your screen
   - Enable **"Transparent"** mode for a minimal, see-through display

3. **Configure Settings**
   - Go to **Settings → Configuration**
   - **Show Tax**: Enable to see currency values after 1/8 tax deduction
   - **Aggregate Numbers**: Enable to show large numbers as "22.3K" instead of "22300"
   - **Data Per Minute**: Switch between per-hour and per-minute statistics

### During Farming

- Complete maps normally
- The system automatically tracks:
  - Currency gained/lost
  - Experience per hour
  - Map completion time
  - Item changes
  - Market transactions

## Project Structure

### [Server](./server/README.md)
FastAPI-based backend service that:
- Parses game logs in real-time using a parser pipeline
- Tracks player progression, experience, and inventory
- Manages map completions with affixes and item changes
- Provides REST API and WebSocket for frontend consumption
- Handles market price tracking and item valuation

**Tech Stack:** Python, FastAPI, WebSocket, Tortoise ORM, SQLite, asyncio

### [UI](./ui/Oracle/README.md)
Angular-based web application featuring:
- Real-time player statistics dashboard
- Map completion tracking with detailed breakdowns
- Market activity monitoring
- Session-based farming analytics
- Item change visualization

**Tech Stack:** Angular 18, PrimeNG, TailwindCSS, TypeScript

### [Launcher](./launcher/README.md)
Desktop application launcher for managing the Oracle server:
- System tray integration
- Server lifecycle management
- Configuration interface
- Quick access to logs and UI

**Tech Stack:** Python, tkinter

### [Deploy](./deploy/README.md)
Build and deployment tooling:
- PyInstaller configurations for bundling Python applications
- Frontend build scripts
- Release packaging automation
- Distribution utilities

## Quick Start

1. **Server Setup**
   ```bash
   cd server
   pip install -r requirements.txt
   python -m Oracle.server
   ```

2. **UI Development**
   ```bash
   cd ui/Oracle
   npm install
   npm start
   ```

3. **Access Dashboard**
   Navigate to `http://localhost:4200`

## Features

### Real-Time Log Parsing
- Event-driven parser architecture
- 16+ specialized parsers for different game events
- Queue-based event processing with EventBus pattern

### Player Tracking
- Experience and level monitoring
- Inventory snapshot system
- Session-based activity grouping

### Map Analytics
- Duration, currency, and experience tracking
- Affix recording for map modifiers
- Entry cost calculation (consumed items)
- Item drop tracking with pricing

### Market Intelligence
- Transaction history (gained/lost/bought/sold)
- Price database with automatic updates
- Item category classification

### Web Dashboard
- Responsive material design with dark theme
- Lazy-loaded tables with pagination
- Real-time updates via REST API
- Session filtering and sorting

## Architecture

```
┌─────────────┐
│  Game Logs  │
└──────┬──────┘
       │
       v
┌─────────────────────┐
│   LogReader         │
│  (File Tailer)      │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│   Router            │
│  (Line Dispatcher)  │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│   Parsers (16+)     │
│  - EnterLevel       │
│  - ExitLevel        │
│  - ItemChange       │
│  - StageAffix       │
│  - etc.             │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│   EventBus          │
└──────┬──────────────┘
       │
       v
┌─────────────────────────────────┐
│   Services                      │
│  - MapService                   │
│  - InventoryService             │
│  - SessionService               │
│  - ExperienceService            │
└──────┬──────────────────────────┘
       │                       ^
       v                       │ 
┌─────────────────────┐        └───┐  
│   Database          │            │ 
│  (SQLite/Tortoise)  │            │
└─────────────────────┘            │
       ^                           │
       │                           v
┌──────┴──────────────┐  ┌───────────────────┐
│     REST API        │  │     WebSocket     │
│    (FastAPI)        │  │                   │
└──────┬──────────────┘  └───────────────────┘
       │                      ^
       │                      │ 
       │         ┌────────────┘ 
       v         v
┌─────────────────────┐
│   Angular UI        │
└─────────────────────┘
```

## Key Concepts

### FSM Parsers
Each parser implements a Finite State Machine to reliably extract multi-line events from logs.

### Service Architecture
Services communicate via EventBus using async events, enabling loose coupling and extensibility.

### Inventory Snapshots
Pre-map and post-map inventory snapshots enable accurate item change tracking and entry cost calculation.

### Session Management
Farming sessions group map completions for aggregate statistics and progression analysis.

## Development

See individual component READMEs for detailed development instructions:
- [Server Development](./server/README.md)
- [UI Development](./ui/Oracle/README.md)
- [Build & Deploy](./deploy/README.md)

## License

See [LICENSE](./LICENSE) for details.
