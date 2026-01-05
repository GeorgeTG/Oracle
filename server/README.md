# Oracle

Real-time game log parser and analytics system for Torchlight Infinite.

## Features

- **Real-time Log Parsing**: Monitors game logs and parses events as they happen
- **Event-Driven Architecture**: Modular parser and service system with dependency management
- **WebSocket API**: Real-time event streaming to connected clients
- **Statistics Tracking**: Track items per map and per hour with automatic updates
- **Map Management**: FSM-based map state tracking (IDLE → FARMING → PAUSED)
- **Inventory Tracking**: Complete inventory state management with snapshots
- **Service Dependencies**: Automatic dependency resolution with semantic versioning

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Oracle
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure `config.json`:
```json
{
  "log_path": "path/to/game/logs/UE_game.log",
  "host": "127.0.0.1",
  "port": 8000
}
```

4. Run the server:
```bash
python -m Oracle.server
```

## API

### REST Endpoints

- `GET /status` - Server status, loaded parsers and services
- `GET /` - Basic health check

### WebSocket

- `WS /ws` - Real-time event stream

## Architecture

### Parsers
- Dynamically loaded from `Oracle/parsing/parsers/`
- Parse game log lines into typed events
- Support for: EnterLevel, ExitLevel, MapLoaded, ItemChange, PlayerJoin, etc.

### Services
- Event-driven service system with dependency management
- `InventoryService` - Tracks inventory state
- `MapService` - Manages map sessions and transitions
- `StatsService` - Tracks farming statistics
- `WebSocketService` - Broadcasts events to clients

### Events
- **ParserEvents**: Game log events (ENTER_LEVEL, ITEM_CHANGE, etc.)
- **ServiceEvents**: Service-level events (MAP_STARTED, STATS_UPDATE, etc.)

## License

MIT License - see [LICENSE](LICENSE) file for details
