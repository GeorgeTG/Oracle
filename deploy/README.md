# Oracle Deployment

Build scripts for creating standalone executables on Windows.

## Prerequisites

### Server Build
- Python 3.10+
- Virtual environment (`.venv`) in `server/` directory

### Frontend Build
- Node.js 18+
- Bun package manager
- Rust toolchain (for Tauri)

## Build Scripts

### Build Everything
```powershell
.\build_all.ps1
```
Builds both server and frontend.

### Build Server Only
```powershell
.\build_server.ps1
```
Creates `Oracle-Server.exe` and `Oracle-Server-Tray.exe` using PyInstaller.

### Build Frontend Only
```powershell
.\build_frontend.ps1
```
Creates portable Tauri executable.

## Output Structure

```
deploy/
├── dist/
│   └── oracle/                      # Angular build output
├── build/
│   └── Oracle-Server/ 
│   └── oracle-Server-Tray/          # PyInstaller build output
│
└── output/                          # Build output Directory
    ├── server/
    │   ├── Oracle-Server.exe        # Standard console server
    │   ├── Oracle-Server-Tray.exe   # System tray version
    │   ├── config.toml
    │   ├── en_id_map_table.json
    │   ├── en_id_table.json
    │   ├── Experience.json
    │   ├── price_table.json
    │   └── favicon.ico
    └── frontend/
        └── oracle.exe               # Portable application
```

## Server Deployment

### Standard Console Server
1. Copy all files from `output/server/` to deployment directory
2. Edit `config.toml` if needed
3. Run `Oracle-Server.exe`

### System Tray Server
1. Copy all files from `output/server/` to deployment directory
2. Edit `config.toml` if needed
3. Run `Oracle-Server-Tray.exe`

**Tray Features:**
- Show/Hide console window
- Open server in browser
- Open API documentation
- About dialog with license info
- Graceful shutdown

Server will run on `http://localhost:8000`

## Frontend Deployment

1. Copy `oracle.exe` from `output/frontend/` to desired location
2. Launch `oracle.exe` - no installation required (portable)

## Configuration

### Server Config (`config.toml`)
```toml
[server]
host = "127.0.0.1"
port = 8000

[parser]
log_path = "path/to/logfile.txt"

[websocket]
reconnect_interval = 5

[logger]
level = "INFO"
```

## Troubleshooting

### PyInstaller Issues
If server build fails:
```powershell
pip install --upgrade pyinstaller
```

### Tauri Issues
If frontend build fails:
```powershell
rustup update
cargo clean
```

### Missing Dependencies
Server build requires:
```powershell
pip install -r server/requirements.txt
pip install pyinstaller
```

Frontend build requires:
```powershell
cd ui/Oracle
bun install
```

## License

MIT License - See LICENSE file for details.

**NO WARRANTY** - THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

### Missing Dependencies
```powershell
# Server
cd ..\server
pip install -r requirements.txt

# Frontend
cd ..\ui\Oracle
bun install
```

## Notes

- Server executable includes Python runtime (no Python installation required)
- Frontend is a native desktop app (no browser required)
- Config file must be in the same directory as the executable
- Logs are stored in the directory where the executable runs

## License

MIT License - Copyright (c) 2025 Oracle Contributors
includes Python runtime (no Python installation required)
- Frontend is a native desktop app (no browser required)
- Config file must be in the same directory as the executable
- Logs are stored in the directory where the executable runs