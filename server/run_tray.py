"""
Entry point for Oracle Server with System Tray

Run this script to start the Oracle Server with system tray support.
The server will run in the background with a tray icon that allows you to:
- Show/Hide the console window
- Open the server in your browser
- View About information and license
- Quit the application
"""

import sys
from pathlib import Path

# Add server directory to path if needed
server_dir = Path(__file__).parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from Oracle.tray_server import main

if __name__ == "__main__":
    main()
