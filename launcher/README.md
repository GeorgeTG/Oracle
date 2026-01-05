# Oracle Launcher

Modern GUI launcher for Oracle game statistics tracker.

## Features

- 🎯 **Easy Launch**: Start server and UI with one click
- 🔍 **Auto-Detection**: Automatically finds game installation and log files
- ⚙️ **Configuration**: Automatically saves log path to server config
- 📊 **Status Monitoring**: Real-time status display in launcher window
- 🖥️ **System Tray**: Server runs quietly in the background
- 📜 **Build Info**: View version and build information for all components

### Getting Started

1. **Launch the Application**
   - Start the application.

2. **Configure Game Log Path**
   - Click **"Auto-Detect"** to automatically find your Torchlight Infinite installation
   - Or click **"Browse..."** to manually select the `UE_game.log` file
   - The launcher will search common Steam installation locations

3. **Save Configuration**
   - Once the log path is detected or selected, click **"Save to Config"**
   - This updates the server's configuration file with the correct log path

4. **Start the Server**
   - Click **"Start Server"** to launch the Oracle server
   - **Important**: The server runs in the system tray (notification area)
   - Look for the Oracle icon in your system tray to verify it's running
   - The launcher window will show the server status

5. **Start the UI**
   - Click **"Start UI"** to open the Oracle desktop application
   - The UI connects to the running server to display game statistics

6. **Monitor Status**
   - The launcher window displays the current status of all components
   - Server status is visible in the main window
   - The server continues running in the system tray even if you close the launcher

### Features Overview

#### Main Tab
- Configure game log path
- Auto-detect SteamLibrary installation
- Launch server, server (tray), or UI
- View real-time status of components

#### Build Info Tab
- View server build information
- View UI build information

#### About Tab
- License information (MIT)
- Disclaimer and liability notice

## Auto-Detection

The launcher automatically searches for Torchlight Infinite installation in common locations:
- `C:/SteamLibrary/steamapps/common/Torchlight Infinite`
- `D:/SteamLibrary/steamapps/common/Torchlight Infinite`
- `E:/SteamLibrary/steamapps/common/Torchlight Infinite`
- And other common drive letters and Steam installation paths

If auto-detection fails, you can manually browse for the `UE_game.log` file.

## Configuration

The launcher automatically saves the game log path to the server's `config.toml` file:
- `parser.log_path`: Path to the game's `UE_game.log` file

### System Tray Server

**Important**: When you start the server, it runs in the Windows system tray (notification area).

- Look for the Oracle icon in your system tray (bottom-right corner of your screen)
- The server continues running even if you close the launcher
- Right-click the tray icon to view server options or exit the server
- This allows the server to run in the background while you play the game

## License

MIT License - See LICENSE file for details
