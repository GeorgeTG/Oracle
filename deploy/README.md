# Oracle Deployment

Build system for creating standalone executables and release packages.

## Prerequisites

- **Bun**: JavaScript/TypeScript runtime and package manager
- **Python 3.10+**: For server builds
- **Rust toolchain**: For Tauri frontend builds (install via [rustup](https://rustup.rs/))

## Quick Start

### Initial Setup
```bash
# Install dependencies and create virtual environments
bun setup
```

This will:
- Detect or prompt for Python 3 installation
- Create virtual environments for launcher and server
- Install all Python dependencies from requirements.txt
- Verify PyInstaller installation

### Build Commands

#### Build Everything and Create Release
```bash
bun release
```
Cleans, builds all targets, and creates release package.

#### Build All Targets
```bash
bun build
```
Builds launcher, server, and frontend with fresh timestamps.

#### Build Specific Targets
```bash
# Build only server
bun build:server

# Build only frontend
bun build:frontend

# Build only launcher
bun build:launcher

# Create package only
bun package
```

## Build System Architecture

### TypeScript Build Scripts
- **setup.ts**: Initializes Python virtual environments and dependencies
- **build.ts**: Main build orchestrator for all targets
- **release.ts**: Creates packaged releases

### Build Targets
Each target has its own configuration in `targets/`:
- **launcher/**: Python launcher GUI with PyInstaller spec
- **server/**: FastAPI server with PyInstaller specs for console and tray versions
- **frontend/**: Angular + Tauri desktop application
- **package/**: Release packaging and ZIP creation

### Build Artifacts
```
deploy/
├── build/
│   ├── launcher-venv/              # Launcher Python environment
│   ├── server-venv/                # Server Python environment
│   ├── Oracle-Launcher/            # PyInstaller build files
│   ├── Oracle-Server/              # PyInstaller build files
│   └── Oracle-Server-Tray/         # PyInstaller build files
│
└── output/
    ├── launcher/
    │   ├── Oracle-Launcher.exe
    │   ├── launcher.toml
    │   └── build.json
    ├── server/
    │   ├── Oracle-Server.exe
    │   ├── Oracle-Server-Tray.exe
    │   ├── config.toml
    │   ├── build.json
    │   └── [data files]
    ├── frontend/
    │   ├── oracle.exe
    │   └── build.json
    └── package/
        └── Oracle-Release-v[version]-[timestamp].zip
```


## Deployment

### Using the Launcher (Recommended)
1. Extract release package
2. Run `Oracle-Launcher.exe`
3. Click "Start Server" and "Start UI"

The launcher provides:
- One-click server and UI startup
- Build information display
- GitHub update checking
- Graceful shutdown management

### Manual Server Deployment

#### Standard Console Server
1. Navigate to `server/` directory
2. Edit `config.toml` if needed
3. Run `Oracle-Server.exe`

#### System Tray Server
1. Navigate to `server/` directory
2. Edit `config.toml` if needed
3. Run `Oracle-Server-Tray.exe`

**Tray Features:**
- Show/Hide console window
- Open server in browser
- Open API documentation
- About dialog with license info
- Graceful shutdown

Server runs on `http://localhost:8000` by default.

### Frontend Deployment

1. Run `oracle.exe` from the `frontend/` directory
2. No installation or browser required (native desktop app)
3. Application is fully portable

## Configuration

### Launcher Config (`launcher.toml`)
```toml
[repo]
main= "GeorgeTG/Oracle"
```

Used for GitHub release update checking.

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

### Virtual Environment Issues
If you see errors about missing Python or corrupted paths:
```bash
# Delete old virtual environments
rm -rf deploy/build/launcher-venv
rm -rf deploy/build/server-venv

# Run setup again
bun run setup.ts
```

### PyInstaller Build Failures
```bash
# Rebuild from clean state
bun run build.ts --clean

# Or manually clean build artifacts
rm -rf deploy/build/Oracle-*
```

### Frontend Build Issues
```bash
# Update Rust toolchain
rustup update

# Clean and rebuild
cd ui/Oracle
bun run tauri build
```

### Python Detection Issues
Set environment variable to specify Python:
```bash
$env:PYTHON3 = "C:\Path\To\python.exe"
bun run setup.ts
```

## Development

### Adding New Build Targets
1. Create target directory in `targets/`
2. Add `build.ts` with default export function
3. Create `build.json` configuration
4. Import and call from main `build.ts`

### Build Info System
Each target generates a `build.json` with:
- `name`: Component name
- `version`: From package.json or config
- `build`: ISO timestamp
- Additional metadata (dependencies, platform, etc.)

The launcher displays this information and uses it for update checking.



## Notes

- All executables include their respective runtimes (Python for server/launcher, native for frontend)
- No external dependencies required for end users
- Configuration files must be in the same directory as executables
- Logs are stored in the directory where executables run
- Build timestamps are automatically generated on each build
- Release packages include SHA256 checksums for verification

## License

MIT License - See LICENSE file for details.

**NO WARRANTY** - THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.