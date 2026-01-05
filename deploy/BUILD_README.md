# 🚀 Oracle Build System

Modern build system for the Oracle project using Bun and TypeScript.

## Features

- ✨ **TypeScript-based** - Written in TypeScript for type safety
- 🎨 **Beautiful Terminal Output** - Colors and spinners with chalk & ora
- ⚡ **Fast** - Powered by Bun
- 🎯 **Targeted Builds** - Build frontend, server, launcher, or all
- 📦 **Version Management** - Automatic version and build date management
- 🔄 **Environment Management** - Automatic environment file updates
- 🐍 **Isolated Build Environment** - Dedicated Python venv with all dependencies
- 🎯 **Modular Architecture** - Separate build targets in `targets/` directory

## First-Time Setup

Before your first build, run setup to create the build environment:

```bash
cd deploy
bun install
bun run setup
```

This will:
- Create a dedicated Python virtual environment (`.venv`)
- Install PyInstaller for creating executables
- Install all required server dependencies

## Usage

### Basic Commands

```bash
# Build all (frontend + server + launcher) - development mode
bun run build

# Build only frontend
bun run build:frontend

# Build only server
bun run build:server

# Build only launcher
bun run build:launcher

# Build all in release mode (production)
bun run release

# Build launcher executable
bun run release:launcher
```

### Advanced Usage

```bash
# Build with custom options
bun run build.ts --target=all --release

# Build without cleaning
bun run build.ts --target=frontend

# See all options
bun run build.ts --help
```

## Options

- `-t, --target <type>` - Build target: `server`, `frontend`, `launcher`, or `all` (default: `all`)
- `-r, --release` - Create release build (production mode with executables)
- `-c, --clean` - Clean output directory before building
- `--tray` - Build server with system tray support

## Output Structure

```
deploy/
├── .venv/                # Build environment (Python virtual env)
├── build.ts              # Main build orchestrator
├── setup.ts              # Environment setup script
├── requirements.txt      # Python build dependencies
├── package.json          # Bun dependencies
├── frontend.json         # Frontend version info
├── server.json           # Server version info
├── targets/              # Modular build targets
│   ├── frontend/
│   │   └── frontend.ts   # Frontend build module
│   ├── server/
│   │   ├── server.ts     # Server build module
│   │   └── pack_modules.py
│   └── launcher/
│       └── launcher.ts   # Launcher build module
└── output/
    ├── frontend/         # Built Angular app
    │   ├── browser/
    │   └── Oracle.msi    (release mode)
    ├── server/           # Server files
    │   ├── config.toml
    │   ├── *.json
    │   ├── modules/
    │   └── Oracle-Server.exe (release mode)
    ├── launcher/         # Launcher application
    │   ├── .venv/        # Launcher's own Python environment
    │   ├── launcher.py
    │   └── Oracle-Launcher.exe (release mode)
    └── Oracle-Release-vX.X-YYYY-MM-DD/  # Release package
        ├── frontend/
        ├── server/
        └── launcher/
```

## Version Management

Versions are stored in:
- `deploy/frontend.json`
- `deploy/server.json`

And automatically updated in environment files during build.

## Development

To add new functionality:

1. Open the appropriate file in `targets/<component>/`
2. Add your functions
3. Update the main build orchestrator if needed
4. Test with `bun run build.ts`

## Modular Architecture

Each build target is self-contained:
- **Frontend** (`targets/frontend/frontend.ts`) - Angular + Tauri builds
- **Server** (`targets/server/server.ts`) - Python server with PyInstaller
- **Launcher** (`targets/launcher/launcher.ts`) - tkinter GUI launcher

Each module:
- Manages its own dependencies
- Creates its own build.json
- Handles version tracking
- Produces output in `deploy/output/<target>/`
