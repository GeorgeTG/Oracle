"""
System Tray Server Launcher for Oracle Server

This module provides a system tray interface for the Oracle Server,
allowing users to:
- Show/Hide the console window
- View server status
- Access About information with license
- Quit the application gracefully
"""

import sys
import threading
import ctypes
import asyncio
from pathlib import Path
from io import BytesIO

import pystray
from PIL import Image, ImageDraw
from Oracle.tooling.logger import Logger
from Oracle.tooling.config import Config

logger = Logger("TrayServer")


class ServerTray:
    """System tray interface for Oracle Server."""
    
    def __init__(self):
        self.icon = None
        self.server_thread = None
        self.console_visible = True
        self.hwnd = None
        
        # Get console window handle (Windows only)
        if sys.platform == 'win32':
            kernel32 = ctypes.windll.kernel32
            self.hwnd = kernel32.GetConsoleWindow()
        
        # Load config for version info
        self.config = Config()
        server_config = self.config.get("server")
        self.host = server_config.get("host", "127.0.0.1")
        self.port = server_config.get("port", 8000)
    
    def create_icon_image(self):
        """Load icon from .ico file or create a simple one."""
        # Try to load from favicon.ico first
        from Oracle.tooling.paths import get_base_path
        icon_path = get_base_path() / "favicon.ico"
        
        if icon_path.exists():
            try:
                img = Image.open(icon_path)
                # Ensure proper size for system tray (usually 16x16 or 32x32)
                # ICO files contain multiple sizes, PIL picks the first one
                # Resize to 64x64 for better quality in tray
                if img.size != (64, 64):
                    img = img.resize((64, 64), Image.Resampling.LANCZOS)
                return img
            except Exception as e:
                logger.warning(f"Failed to load {icon_path}: {e}, using fallback")
        
        logger.info("Using fallback icon")
        # Fallback: Create a 64x64 image with a circle
        width = 64
        height = 64
        color1 = (52, 152, 219)  # Blue
        color2 = (255, 255, 255)  # White
        
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        
        # Draw a circle with "O" for Oracle
        dc.ellipse([8, 8, 56, 56], fill=color2, outline=color1, width=2)
        dc.ellipse([20, 20, 44, 44], fill=color1, outline=color2, width=3)
        
        return image
    
    def toggle_console(self, icon=None, item=None):
        """Toggle console window visibility (Windows only)."""
        if sys.platform != 'win32' or not self.hwnd:
            logger.warning("Console toggle only supported on Windows")
            return
        
        user32 = ctypes.windll.user32
        SW_HIDE = 0
        SW_SHOW = 5
        
        if self.console_visible:
            user32.ShowWindow(self.hwnd, SW_HIDE)
            self.console_visible = False
            logger.debug("Console hidden")
        else:
            user32.ShowWindow(self.hwnd, SW_SHOW)
            user32.SetForegroundWindow(self.hwnd)
            self.console_visible = True
            logger.debug("Console shown")
    
    def show_console(self, icon=None, item=None):
        """Show console and bring to front (double-click action)."""
        if sys.platform != 'win32' or not self.hwnd:
            return
        
        user32 = ctypes.windll.user32
        SW_SHOW = 5
        SW_RESTORE = 9
        
        # Always show and bring to front
        user32.ShowWindow(self.hwnd, SW_RESTORE)
        user32.SetForegroundWindow(self.hwnd)
        self.console_visible = True
        logger.debug("Console shown and focused")
    
    def show_about(self, icon=None, item=None):
        """Show About dialog with license information."""
        # For Windows, use MessageBox
        if sys.platform == 'win32':
            def show_dialog():
                user32 = ctypes.windll.user32
                MB_OK = 0x0
                MB_ICONINFORMATION = 0x40
                MB_TOPMOST = 0x00040000
                
                about_text = (
                    "Oracle Server v1.0.0\n\n"
                    "Advanced game log parsing and analytics server\n\n"
                    f"Server: http://{self.host}:{self.port}\n"
                    f"WebSocket: ws://{self.host}:{self.port}/ws\n\n"
                    "========================================\n\n"
                    "MIT License - Copyright (c) 2025\n"
                    "Oracle Contributors\n\n"
                    "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT\n"
                    "WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.\n\n"
                    "NO LIABILITY FOR ANY DAMAGES.\n\n"
                    "See LICENSE file for full details."
                )
                
                # Use console window handle or 0 if not available
                hwnd = self.hwnd if self.hwnd else 0
                user32.MessageBoxW(
                    hwnd,
                    about_text,
                    "About Oracle Server",
                    MB_OK | MB_ICONINFORMATION | MB_TOPMOST
                )
            
            # Run in separate thread to avoid blocking tray icon
            threading.Thread(target=show_dialog, daemon=True).start()
        else:
            # For other platforms, just log
            logger.info("Oracle Server v1.0.0 - MIT License - No Warranty")
    
    def open_browser(self, icon=None, item=None):
        """Open the server URL in default browser."""
        import webbrowser
        url = f"http://{self.host}:{self.port}"
        webbrowser.open(url)
        logger.info(f"Opening {url} in browser")
    
    def open_docs(self, icon=None, item=None):
        """Open the API documentation (Swagger) in default browser."""
        import webbrowser
        url = f"http://{self.host}:{self.port}/docs"
        webbrowser.open(url)
        logger.info(f"Opening API docs at {url}")
    
    def quit_server(self, icon=None, item=None):
        """Gracefully quit the server."""
        logger.info("🛑 Shutting down from system tray...")
        
        # Stop the icon
        if self.icon:
            self.icon.stop()
        
        # Force exit after a short delay to allow cleanup
        def force_quit():
            import time
            time.sleep(2)
            import os
            os._exit(0)
        
        threading.Thread(target=force_quit, daemon=True).start()
    
    def run_server(self):
        """Run the FastAPI server in the background."""
        import uvicorn
        from Oracle.server import app, config
        
        logger.info(f"🚀 Starting Oracle Server on {self.host}:{self.port}")
        
        # Detect if running from PyInstaller executable
        is_frozen = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        
        config_kwargs = {
            "app": app,
            "host": self.host,
            "port": self.port,
            "reload": False,
            "log_config": None,
            "access_log": False
        }
        
        try:
            uvicorn.run(**config_kwargs)
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
    
    def get_menu_item_checked(self):
        """Get checked state for console visibility menu item."""
        return self.console_visible
    
    def setup_tray(self):
        """Setup the system tray icon and menu."""
        menu = pystray.Menu(
            pystray.MenuItem(
                "Show/Hide Console",
                self.toggle_console,
                checked=lambda item: self.console_visible
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Open in Browser",
                self.open_browser
            ),
            pystray.MenuItem(
                "Open API Docs",
                self.open_docs
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "About",
                self.show_about
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Quit",
                self.quit_server
            )
        )
        
        self.icon = pystray.Icon(
            "oracle_server",
            self.create_icon_image(),
            "Oracle Server",
            menu,
            on_activate=self.show_console  # Double-click shows console
        )
    
    def run(self):
        """Start the server and system tray."""
        # Setup tray first
        self.setup_tray()
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        
        logger.info("🎯 Oracle Server running in system tray")
        logger.info(f"📡 Server: http://{self.host}:{self.port}")
        logger.info("🖱️ Right-click the tray icon for options")
        
        # Run the tray icon (blocks until quit)
        self.icon.run()


def main():
    """Main entry point for the tray server."""
    try:
        tray = ServerTray()
        tray.run()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
