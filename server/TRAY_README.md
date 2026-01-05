# Oracle Server - System Tray Mode

## What is it?

Oracle Server can now run in the system tray (next to the clock) with an icon that gives you easy access to server functions.

## How to run

### Simple way:
```bash
python run_tray.py
```

### Or from the Oracle folder:
```bash
python -m Oracle.tray_server
```

## Features

When you right-click the tray icon, you'll see:

### 🖥️ Show/Hide Console
- Hides or shows the terminal window
- Useful for keeping a clean desktop while the server runs
- The checkmark (✓) shows if the console is visible

### 🌐 Open in Browser
- Opens the server in your default browser
- Quick access to API documentation

### ℹ️ About
- Displays application information
- Shows the MIT License
- **Includes NO WARRANTY/NO LIABILITY disclaimer**
- Shows the server address

### ❌ Quit
- Gracefully closes the server
- Stops all processes safely

## Requirements

New dependencies are already in `requirements.txt`:
- `pystray>=0.19.5` - System tray support
- `Pillow>=10.0.0` - Icon creation

### Installation:
```bash
cd server
pip install -r requirements.txt
```

## How it works

1. **Hidden Console**: The terminal hides automatically (you can show it anytime)
2. **Background Server**: FastAPI server runs in a background thread
3. **Tray Icon**: A blue icon appears in the system tray
4. **Graceful Shutdown**: All services close properly when you press Quit

## For PyInstaller Build

If you want to create an .exe, update `Oracle-Server.spec`:

```python
# In the entry point, change from:
# a = Analysis(['Oracle/server.py'], ...)

# To:
a = Analysis(['run_tray.py'], ...)
```

Then:
```bash
pyinstaller Oracle-Server.spec
```

## Troubleshooting

### Icon doesn't appear
- Check if `pystray` is installed
- On Windows, look in "Hidden Icons" (arrow next to system tray)

### Console doesn't hide
- This feature only works on Windows
- On Linux/Mac the console will remain visible

### How to see logs
- Click Show Console from the tray menu
- Or look in the `logs/` directory

## License Notice

**MIT License - NO WARRANTY**

The software is provided "AS IS", without any warranty. The creators have no liability for any damages arising from the use of the software.

See the [LICENSE](../LICENSE) file for full details.
