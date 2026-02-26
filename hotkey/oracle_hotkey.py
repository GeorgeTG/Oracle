"""
Oracle Hotkey - Global hotkey listener with GUI.
Sends key events to Oracle server via WebSocket and provides automatic hover detection.
Requires administrator privileges to capture keys when elevated applications have focus.
"""
import ctypes
import ctypes.wintypes
import json
import sys
import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
from pathlib import Path

import tomli
import websocket
from pynput import keyboard

try:
    import sv_ttk
except ImportError:
    sv_ttk = None

CONFIG_FILE = "config.toml"

DEFAULT_CONFIG = """\
[server]
host = "127.0.0.1"
port = 8000

[hotkey]
edit_mode_key = "page_up"
toggle_overlay_key = "page_down"

[hover]
enabled = true
hover_delay_ms = 500
leave_delay_ms = 500
poll_interval_ms = 50
"""


def load_config() -> dict:
    """Load configuration from config.toml."""
    config_path = Path(sys.argv[0]).parent / CONFIG_FILE
    if not config_path.exists():
        config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        config_path = Path(sys.argv[0]).parent / CONFIG_FILE
        config_path.write_text(DEFAULT_CONFIG)

    with open(config_path, "rb") as f:
        return tomli.load(f)


# Map pynput key objects to simple string names
KEY_MAP = {
    keyboard.Key.page_up: "page_up",
    keyboard.Key.page_down: "page_down",
    keyboard.Key.home: "home",
    keyboard.Key.end: "end",
    keyboard.Key.insert: "insert",
    keyboard.Key.delete: "delete",
    keyboard.Key.f1: "f1",
    keyboard.Key.f2: "f2",
    keyboard.Key.f3: "f3",
    keyboard.Key.f4: "f4",
    keyboard.Key.f5: "f5",
    keyboard.Key.f6: "f6",
    keyboard.Key.f7: "f7",
    keyboard.Key.f8: "f8",
    keyboard.Key.f9: "f9",
    keyboard.Key.f10: "f10",
    keyboard.Key.f11: "f11",
    keyboard.Key.f12: "f12",
    keyboard.Key.pause: "pause",
    keyboard.Key.scroll_lock: "scroll_lock",
    keyboard.Key.num_lock: "num_lock",
    keyboard.Key.caps_lock: "caps_lock",
}


def get_cursor_pos() -> tuple[int, int]:
    """Get current mouse cursor position using ctypes (no pywin32 dependency)."""
    point = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def point_in_rect(x: int, y: int, rect: dict) -> bool:
    """Check if point (x, y) is inside a rectangle."""
    return (rect["x"] <= x <= rect["x"] + rect["width"] and
            rect["y"] <= y <= rect["y"] + rect["height"])


class OracleHotkey:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Oracle Hotkey")
        self.root.geometry("500x400")
        self.root.resizable(True, True)

        # Set window icon
        try:
            if getattr(sys, 'frozen', False):
                icon_path = Path(sys.executable).parent / "favicon.ico"
            else:
                icon_path = Path(__file__).parent / "favicon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

        # Load config
        self.config = load_config()
        self.host = self.config["server"]["host"]
        self.port = self.config["server"]["port"]
        hotkey_config = self.config["hotkey"]
        self.edit_mode_key = hotkey_config.get("edit_mode_key", "page_up").lower()
        self.toggle_overlay_key = hotkey_config.get("toggle_overlay_key", "page_down").lower()
        self.watched_keys = {self.edit_mode_key, self.toggle_overlay_key}
        self.ws = None
        self.connected = False
        self.running = True
        self._ws_lock = threading.Lock()
        self._version = self._load_version()

        # Hover detection config
        hover_config = self.config.get("hover", {})
        self.hover_enabled = hover_config.get("enabled", True)
        self.hover_delay_ms = hover_config.get("hover_delay_ms", 500)
        self.leave_delay_ms = hover_config.get("leave_delay_ms", 500)
        self.poll_interval_ms = hover_config.get("poll_interval_ms", 50)

        # Hover state
        self.dialog_bounds: list[dict] = []
        self._bounds_lock = threading.Lock()
        self._hover_active = False
        self._hover_enter_time: float | None = None
        self._hover_leave_time: float | None = None

        # Setup UI
        self.setup_ui()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Create the GUI."""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill='both', expand=True)

        # Title
        title = ttk.Label(main_frame, text="Oracle Hotkey", font=('Segoe UI', 14, 'bold'))
        title.pack(pady=(0, 10))

        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="Configuration", padding=10)
        info_frame.pack(fill='x', pady=(0, 10))

        info_items = [
            ("Server", f"{self.host}:{self.port}"),
            ("Edit Mode Key", self.edit_mode_key),
            ("Toggle Overlay", self.toggle_overlay_key),
            ("Hover Detection", "Enabled" if self.hover_enabled else "Disabled"),
        ]
        if self.hover_enabled:
            info_items.append(("Hover Delay", f"{self.hover_delay_ms}ms"))
            info_items.append(("Leave Delay", f"{self.leave_delay_ms}ms"))

        for label, value in info_items:
            row = ttk.Frame(info_frame)
            row.pack(fill='x', pady=1)
            ttk.Label(row, text=f"{label}:", font=('Segoe UI', 9, 'bold'), width=18, anchor='w').pack(side='left')
            ttk.Label(row, text=value, font=('Segoe UI', 9)).pack(side='left')

        # Status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill='x', pady=(0, 5))
        ttk.Label(status_frame, text="Status:", font=('Segoe UI', 9, 'bold')).pack(side='left')
        self.status_label = ttk.Label(status_frame, text="Starting...", font=('Segoe UI', 9))
        self.status_label.pack(side='left', padx=(5, 0))

        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding=5)
        log_frame.pack(fill='both', expand=True)

        terminal_frame = ttk.Frame(log_frame)
        terminal_frame.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(terminal_frame)
        scrollbar.pack(side='right', fill='y')

        self.log_text = tk.Text(terminal_frame, wrap='word', yscrollcommand=scrollbar.set,
                                font=('Consolas', 9), bg='#1e1e1e', fg='#d4d4d4',
                                relief='flat', height=10)
        self.log_text.pack(fill='both', expand=True)
        scrollbar.config(command=self.log_text.yview)
        self.log_text.config(state='disabled')

    def log(self, message: str):
        """Add a log message (thread-safe)."""
        def _update():
            try:
                self.log_text.config(state='normal')
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.log_text.insert('end', f"[{timestamp}] {message}\n")

                line_count = int(self.log_text.index('end-1c').split('.')[0])
                if line_count > 500:
                    self.log_text.delete('1.0', f'{line_count - 400}.0')

                self.log_text.see('end')
                self.log_text.config(state='disabled')
            except Exception:
                pass
        self.root.after(0, _update)

    def set_status(self, text: str, color: str = 'green'):
        """Update status label (thread-safe)."""
        def _update():
            self.status_label.config(text=text, foreground=color)
        self.root.after(0, _update)

    def get_ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws"

    def connect(self):
        """Connect to the Oracle server WebSocket."""
        while self.running:
            try:
                url = self.get_ws_url()
                self.log(f"Connecting to {url}...")
                self.set_status("Connecting...", '#E5C07B')
                ws = websocket.WebSocket()
                ws.connect(url, timeout=5)
                with self._ws_lock:
                    self.ws = ws
                    self.connected = True
                self.log("Connected to Oracle server")
                self.set_status("Connected", 'green')
                return
            except Exception as e:
                with self._ws_lock:
                    self.connected = False
                self.log(f"Connection failed: {e}")
                self.set_status("Disconnected", 'red')
                self.log("Retrying in 5 seconds...")
                time.sleep(5)

    def _send(self, msg: dict):
        """Send a JSON message via WebSocket (thread-safe)."""
        with self._ws_lock:
            if not self.connected or not self.ws:
                return False
            try:
                self.ws.send(json.dumps(msg))
                return True
            except Exception as e:
                self.log(f"Send failed: {e}")
                self.connected = False
                self.set_status("Disconnected", 'red')
                return False

    def send_hotkey(self, key: str):
        """Send a hotkey event via WebSocket."""
        if self._send({"command": "hotkey", "key": key}):
            self.log(f"Hotkey sent: {key}")
        else:
            self.log(f"Not connected, skipping: {key}")
            threading.Thread(target=self.connect, daemon=True).start()

    def on_key_press(self, key):
        """Handle key press from pynput listener."""
        key_name = None

        if isinstance(key, keyboard.Key):
            key_name = KEY_MAP.get(key)
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                key_name = key.char.lower()

        if key_name and key_name in self.watched_keys:
            self.send_hotkey(key_name)

    def ws_receive_thread(self):
        """Background thread that listens for incoming WS messages."""
        while self.running:
            with self._ws_lock:
                ws = self.ws
                connected = self.connected

            if not connected or not ws:
                time.sleep(1)
                continue

            try:
                ws.settimeout(1.0)
                data = ws.recv()
                if not data:
                    continue
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "overlay_bounds_update":
                    bounds = msg.get("bounds", [])
                    with self._bounds_lock:
                        self.dialog_bounds = bounds
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException:
                self.log("WS connection closed")
                with self._ws_lock:
                    self.connected = False
                self.set_status("Disconnected", 'red')
                threading.Thread(target=self.connect, daemon=True).start()
                time.sleep(2)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                self.log(f"WS receive error: {e}")
                time.sleep(1)

    def mouse_tracking_thread(self):
        """Background thread that tracks mouse position and detects hover over dialogs."""
        poll_interval = self.poll_interval_ms / 1000.0
        hover_delay = self.hover_delay_ms / 1000.0
        leave_delay = self.leave_delay_ms / 1000.0

        while self.running:
            time.sleep(poll_interval)

            with self._bounds_lock:
                bounds = list(self.dialog_bounds)

            if not bounds:
                if self._hover_active:
                    self._send_hover_leave()
                self._hover_enter_time = None
                self._hover_leave_time = None
                continue

            try:
                mx, my = get_cursor_pos()
            except Exception:
                continue

            inside = any(
                b.get("visible", False) and point_in_rect(mx, my, b)
                for b in bounds
            )

            now = time.monotonic()

            if inside:
                self._hover_leave_time = None
                if not self._hover_active:
                    if self._hover_enter_time is None:
                        self._hover_enter_time = now
                    elif now - self._hover_enter_time >= hover_delay:
                        self._send_hover_enter()
                        self._hover_enter_time = None
            else:
                self._hover_enter_time = None
                if self._hover_active:
                    if self._hover_leave_time is None:
                        self._hover_leave_time = now
                    elif now - self._hover_leave_time >= leave_delay:
                        self._send_hover_leave()
                        self._hover_leave_time = None

    def _send_hover_enter(self):
        """Send hover enter command."""
        if self._send({"command": "hover_enter"}):
            self._hover_active = True
            self.log("Hover: Enter - click-through disabled")

    def _send_hover_leave(self):
        """Send hover leave command."""
        if self._send({"command": "hover_leave"}):
            self._hover_active = False
            self.log("Hover: Leave - click-through enabled")

    def _load_version(self) -> str:
        """Load version from build.json."""
        try:
            if getattr(sys, 'frozen', False):
                build_path = Path(sys.executable).parent / "build.json"
            else:
                build_path = Path(__file__).parent / "build.json"
            if not build_path.exists():
                # Try deploy path
                build_path = Path(__file__).parent.parent / "deploy" / "targets" / "hotkey" / "build.json"
            with open(build_path) as f:
                return json.load(f).get("version", "unknown")
        except Exception:
            return "dev"

    def _heartbeat_thread(self):
        """Send periodic heartbeat to server."""
        while self.running:
            self._send({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat(),
                "name": "hotkey",
                "version": self._version
            })
            time.sleep(1)

    def start(self):
        """Start all background threads."""
        self.log("Starting Oracle Hotkey...")

        # Connect to server
        threading.Thread(target=self.connect, daemon=True).start()

        # Start WS receive thread
        threading.Thread(target=self.ws_receive_thread, daemon=True).start()

        # Start heartbeat thread
        threading.Thread(target=self._heartbeat_thread, daemon=True).start()
        self.log(f"Heartbeat started (v{self._version})")

        # Start mouse tracking if hover enabled
        if self.hover_enabled:
            threading.Thread(target=self.mouse_tracking_thread, daemon=True).start()
            self.log("Mouse hover tracking started")

        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()
        self.log("Keyboard listener started")

    def on_close(self):
        """Handle window close."""
        self.running = False
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        with self._ws_lock:
            if self.ws:
                try:
                    self.ws.close()
                except Exception:
                    pass
        self.root.destroy()


def main():
    root = tk.Tk()

    if sv_ttk:
        sv_ttk.set_theme("dark")

    app = OracleHotkey(root)
    app.start()
    root.mainloop()


if __name__ == "__main__":
    main()
