"""
Oracle Launcher - Modern GUI launcher for Oracle server and UI
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import subprocess
import platform
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import tomli
import tomli_w
try:
    import sv_ttk
except ImportError:
    sv_ttk = None
try:
    import urllib.request
    import urllib.error
except ImportError:
    pass
try:
    from github import Github
except ImportError:
    Github = None


class OracleLauncher:
    """Main launcher application with modern UI"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Oracle Launcher")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Set window icon
        try:
            # When running as compiled exe, use sys.executable path
            if getattr(sys, 'frozen', False):
                icon_path = Path(sys.executable).parent / "server" / "favicon.ico"
            else:
                icon_path = Path(__file__).parent.parent / "server" / "favicon.ico"
            
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception as e:
            # Silently fail if icon cannot be loaded
            pass
        
        # Get base paths
        # When running as compiled exe, use sys.executable path instead of __file__
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.launcher_dir = Path(sys.executable).parent
            self.base_path = self.launcher_dir
        else:
            # Running as Python script
            self.launcher_dir = Path(__file__).parent
            self.base_path = self.launcher_dir.parent
        
        # Relative paths for deployed executables (when running from release)
        self.frontend_dir = self.launcher_dir / "frontend"
        self.server_dir = self.launcher_dir / "server"
        
        # Development paths
        self.dev_server_path = self.base_path / "server"
        self.dev_ui_path = self.base_path / "ui" / "Oracle"
        
        # Config file path (try deployed first, then dev)
        self.config_file = self.server_dir / "config.toml" if (self.server_dir / "config.toml").exists() else self.dev_server_path / "config.toml"
        self.config_data: Dict[str, Any] = {}
        
        # Variables
        self.log_path_var = tk.StringVar()
        self.steamlibrary_path = tk.StringVar()
        self.auto_detect_status = tk.StringVar(value="")
        self.server_process = None  # Track server subprocess
        self.ui_process = None  # Track UI subprocess
        self.server_running = False  # Track if server is running
        
        # Setup UI
        self.setup_styles()
        self.create_widgets()
        self.load_config()
        self.auto_detect_steamlibrary()
        
    def setup_styles(self):
        """Setup modern ttk styles"""
        # Don't configure styles if sv_ttk theme is applied
        # sv_ttk handles everything and we'll configure custom styles after
        if sv_ttk:
            return
            
        style = ttk.Style()
        
        # Use a modern theme
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')
            
        # Configure custom styles
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Segoe UI', 12))
        style.configure('Info.TLabel', font=('Segoe UI', 9))
        style.configure('Big.TButton', font=('Segoe UI', 11, 'bold'), padding=15)
        style.configure('Action.TButton', font=('Segoe UI', 10), padding=10)
        
    def create_widgets(self):
        """Create the main UI widgets"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_main_tab()
        self.create_info_tab()
        self.create_about_tab()
        
    def create_main_tab(self):
        """Create the main launcher tab"""
        main_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(main_frame, text='Launcher')

        # Title
        title = ttk.Label(main_frame, text="Oracle Launcher", style='Title.TLabel')
        title.pack(pady=(0, 20))

        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding=15)
        config_frame.pack(fill='x', pady=(0, 20))

        # Log path configuration
        log_frame = ttk.Frame(config_frame)
        log_frame.pack(fill='x', pady=5)

        ttk.Label(log_frame, text="Game Log Path:", style='Subtitle.TLabel').pack(anchor='w')

        path_entry_frame = ttk.Frame(log_frame)
        path_entry_frame.pack(fill='x', pady=(5, 0))

        log_entry = ttk.Entry(path_entry_frame, textvariable=self.log_path_var, width=60)
        log_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        browse_btn = ttk.Button(path_entry_frame, text="Browse...",
                               command=self.browse_log_file, width=12)
        browse_btn.pack(side='left')

        # Auto-detect button and status
        auto_detect_frame = ttk.Frame(log_frame)
        auto_detect_frame.pack(fill='x', pady=(5, 0))

        auto_detect_btn = ttk.Button(auto_detect_frame, text="Auto-Detect",
                                     command=self.auto_detect_steamlibrary, width=15)
        auto_detect_btn.pack(side='left')

        self.status_label_detect = ttk.Label(auto_detect_frame, textvariable=self.auto_detect_status, style='Info.TLabel')
        self.status_label_detect.pack(side='left', padx=(10, 0))

        # Save config button
        save_config_btn = ttk.Button(config_frame, text="Save Configuration",
                                     command=self.save_config, style='Action.TButton')
        save_config_btn.pack(pady=(10, 0))

        # Control buttons (before launch section so they appear above terminal)
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=(0, 10))

        # Start Oracle button (launches server + UI automatically)
        self.start_btn = ttk.Button(control_frame, text="▶ Start Oracle",
                                    command=self.start_oracle, style='Big.TButton')
        self.start_btn.pack(side='left', fill='x', expand=True, padx=(0, 5))

        # Stop button
        self.stop_btn = ttk.Button(control_frame, text="■ Stop Server",
                                   command=self.stop_server, style='Big.TButton', state='disabled')
        self.stop_btn.pack(side='left', fill='x', expand=True)

        # Launch section
        launch_frame = ttk.LabelFrame(main_frame, text="Server Output", padding=15)
        launch_frame.pack(fill='both', expand=True, pady=(0, 10))

        # Embedded terminal for server output
        terminal_frame = ttk.Frame(launch_frame)
        terminal_frame.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(terminal_frame)
        scrollbar.pack(side='right', fill='y')

        self.terminal_text = tk.Text(terminal_frame, wrap='word', yscrollcommand=scrollbar.set,
                                    font=('Consolas', 9), bg='#1e1e1e', fg='#d4d4d4',
                                    relief='flat')
        self.terminal_text.pack(fill='both', expand=True)
        scrollbar.config(command=self.terminal_text.yview)
        self.terminal_text.insert('1.0', 'Ready to start Oracle server...\n')
        self.terminal_text.config(state='disabled')

        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", style='Info.TLabel')
        self.status_label.pack(pady=(10, 0))
        
    def create_info_tab(self):
        """Create the info tab showing build information"""
        info_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(info_frame, text='Build Info')
        
        # Title
        title = ttk.Label(info_frame, text="Build Information", style='Title.TLabel')
        title.pack(pady=(0, 20))
        
        # Create content frame directly (no scrolling)
        self.info_content_frame = ttk.Frame(info_frame)
        self.info_content_frame.pack(fill='both', expand=True)
        
        # Load build info
        self.load_build_info()
        
    def create_about_tab(self):
        """Create the about tab with license and liability"""
        about_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(about_frame, text='About')
        
        # Title
        title = ttk.Label(about_frame, text="About Oracle", style='Title.TLabel')
        title.pack(pady=(0, 20))
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(about_frame)
        text_frame.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        about_text = tk.Text(text_frame, wrap='word', yscrollcommand=scrollbar.set,
                            font=('Segoe UI', 10), bg='#2b2b2b', fg='#d4d4d4', relief='flat')
        about_text.pack(fill='both', expand=True)
        scrollbar.config(command=about_text.yview)
        
        # Load license
        license_content = self.load_license()
        
        # Insert content
        about_text.insert('1.0', license_content)
        about_text.config(state='disabled')
        
    def load_config(self):
        """Load configuration from config.toml"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'rb') as f:
                    self.config_data = tomli.load(f)
                    
                # Load log path
                log_path = self.config_data.get('parser', {}).get('log_path', '')
                self.log_path_var.set(log_path)
                self.update_status("Configuration loaded successfully")
            else:
                self.update_status("Config file not found", error=True)
        except Exception as e:
            self.update_status(f"Error loading config: {e}", error=True)
            
    def save_config(self):
        """Save configuration to config.toml"""
        try:
            # Update config data
            if 'parser' not in self.config_data:
                self.config_data['parser'] = {}
            
            self.config_data['parser']['log_path'] = self.log_path_var.get()
            
            # Write to file
            with open(self.config_file, 'wb') as f:
                tomli_w.dump(self.config_data, f)
                
            self.update_status("Configuration saved successfully ✓")
            messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            self.update_status(f"Error saving config: {e}", error=True)
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
            
    def browse_log_file(self):
        """Open file dialog to browse for UE_game.log"""
        initial_dir = Path.home()
        
        # Try to use current path as initial directory
        current_path = self.log_path_var.get()
        if current_path and Path(current_path).parent.exists():
            initial_dir = Path(current_path).parent
            
        filename = filedialog.askopenfilename(
            title="Select Game Log File",
            initialdir=initial_dir,
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        
        if filename:
            self.log_path_var.set(filename)
            self.update_status(f"Log path updated: {filename}")
            
    def auto_detect_steamlibrary(self):
        """Auto-detect SteamLibrary folder and UE_game.log"""
        self.auto_detect_status.set("🔍 Searching...")
        self.status_label_detect.config(foreground='blue')
        self.root.update()
        
        # Common Steam library locations
        possible_paths = [
            Path("C:/Program Files (x86)/Steam/steamapps/common/Torchlight Infinite"),
            Path("C:/Program Files/Steam/steamapps/common/Torchlight Infinite"),
		]
        
        if platform.system() == "Windows":
            # Check common drive letters
            for drive in ['C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:']:
                steam_path = Path(f"{drive}/SteamLibrary/steamapps/common/Torchlight Infinite")
                possible_paths.append(steam_path)
                
            # Check Program Files
            for pf in ['Program Files (x86)', 'Program Files']:
                steam_path = Path(f"C:/{pf}/Steam/steamapps/common/Torchlight Infinite")
                possible_paths.append(steam_path)
        else:
            # Linux/Mac paths
            home = Path.home()
            possible_paths.append(home / ".steam/steam/steamapps/common/Torchlight Infinite")
            possible_paths.append(home / ".local/share/Steam/steamapps/common/Torchlight Infinite")
            
        # Search for the log file
        for base_path in possible_paths:
            log_path = base_path / "UE_game/TorchLight/Saved/Logs/UE_game.log"
            if log_path.exists():
                self.log_path_var.set(str(log_path))
                self.steamlibrary_path.set(str(base_path.parent.parent))
                self.auto_detect_status.set("✓ Found, please save configuration")
                self.status_label_detect.config(foreground='green')
                return
                
        # Not found
        self.auto_detect_status.set("✗ Not Found - Enable Log in game settings first, or try to manually browse.")
        self.status_label_detect.config(foreground='red')
        
    def start_oracle(self):
        """Start Oracle server and automatically launch UI when ready"""
        try:
            # Check if server is already running
            if self.server_running:
                messagebox.showwarning("Server Running",
                                     "Oracle is already running!\n\n"
                                     "Please stop the existing server before starting a new one.")
                return

            self.update_status("Starting Oracle server...")
            self.add_terminal_log("=" * 80)
            self.add_terminal_log("Starting Oracle Server...")
            self.add_terminal_log("=" * 80)

            # Disable start button, enable stop button
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')

            # Check for deployed executable first
            server_exe = self.server_dir / "Oracle-Server.exe"
            if server_exe.exists():
                self.add_terminal_log(f"Using deployed server: {server_exe}")
                # Start server with output redirection and UTF-8 encoding
                self.server_process = subprocess.Popen(
                    [str(server_exe)],
                    cwd=str(server_exe.parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1
                )
            else:
                # Fall back to Python script
                server_script = self.dev_server_path / "Oracle" / "server.py"
                if server_script.exists():
                    self.add_terminal_log(f"Using development server: {server_script}")
                    self.server_process = subprocess.Popen(
                        [sys.executable, "-u", str(server_script)],
                        cwd=str(self.dev_server_path),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        bufsize=1
                    )
                else:
                    raise FileNotFoundError("Server executable or script not found")

            # Start thread to read server output
            threading.Thread(target=self._read_server_output, daemon=True).start()

            # Start thread to monitor server health and launch UI
            threading.Thread(target=self._monitor_and_launch_ui, daemon=True).start()

            self.server_running = True
            self.update_status("Server starting...")

        except Exception as e:
            self.update_status(f"Error starting server: {e}", error=True)
            self.add_terminal_log(f"ERROR: {e}")
            messagebox.showerror("Error", f"Failed to start server:\n{e}")
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')

    def stop_server(self):
        """Stop the Oracle server"""
        try:
            self.update_status("Stopping server...")
            self.add_terminal_log("\n" + "=" * 80)
            self.add_terminal_log("Stopping Oracle Server...")
            self.add_terminal_log("=" * 80)

            if self.server_process:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                    self.add_terminal_log("Server forcefully killed (timeout)")

                self.server_process = None

            self.server_running = False
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.update_status("Server stopped")
            self.add_terminal_log("Server stopped successfully")

        except Exception as e:
            self.update_status(f"Error stopping server: {e}", error=True)
            self.add_terminal_log(f"ERROR stopping server: {e}")

    def _read_server_output(self):
        """Read server output in background thread"""
        if not self.server_process:
            return

        try:
            for line in iter(self.server_process.stdout.readline, ''):
                if not line:
                    break
                self.add_terminal_log(line.rstrip())
        except Exception as e:
            self.add_terminal_log(f"Error reading server output: {e}")

        # Server process ended
        if self.server_running:
            self.add_terminal_log("\n" + "=" * 80)
            self.add_terminal_log("Server process ended")
            self.add_terminal_log("=" * 80)
            self.root.after(0, lambda: self.stop_btn.config(state='disabled'))
            self.root.after(0, lambda: self.start_btn.config(state='normal'))
            self.server_running = False

    def _monitor_and_launch_ui(self):
        """Monitor server health and launch UI when ready"""
        server_config = self.config_data.get('server', {})
        host = server_config.get('host', '127.0.0.1')
        port = server_config.get('port', 8000)
        base_url = f"http://{host}:{port}"

        self.add_terminal_log(f"Waiting for server to be ready at {base_url}...")

        # Wait for server to be ready (max 30 seconds)
        for i in range(60):
            try:
                req = urllib.request.Request(base_url + "/")
                req.add_header('User-Agent', 'Oracle-Launcher/1.0')

                with urllib.request.urlopen(req, timeout=2) as response:
                    data = json.loads(response.read().decode())
                    self.add_terminal_log(f"✓ Server is ready! Status: {data.get('status')}")
                    self.root.after(0, lambda: self.update_status("Server ready, launching UI..."))

                    # Server is ready, launch UI
                    time.sleep(1)  # Small delay
                    self.root.after(0, self._launch_ui)
                    return

            except (urllib.error.URLError, Exception):
                # Server not ready yet
                if i % 5 == 0:  # Log every 5 seconds
                    self.add_terminal_log(f"Waiting for server... ({i//2}s)")
                time.sleep(0.5)

        # Timeout
        self.add_terminal_log("⚠ Server startup timeout (30s) - UI not launched automatically")
        self.add_terminal_log("Please check server logs above for errors")
        self.root.after(0, lambda: self.update_status("Server timeout - check logs", error=True))

    def _launch_ui(self):
        """Launch the Oracle UI"""
        try:
            self.add_terminal_log("Launching Oracle UI...")

            # Check for deployed executable first
            ui_exe = self.frontend_dir / "Oracle.exe"
            if ui_exe.exists():
                self.ui_process = subprocess.Popen([str(ui_exe)], cwd=str(ui_exe.parent))
                self.add_terminal_log(f"✓ UI launched: {ui_exe}")
                self.update_status("✓ Oracle running")
            else:
                # Fall back to npm/bun dev server
                if self.dev_ui_path.exists():
                    self.add_terminal_log("⚠ UI executable not found")
                    self.add_terminal_log(f"Please run 'npm start' or 'bun run dev' in: {self.dev_ui_path}")
                    messagebox.showinfo("Development Mode",
                                      "UI executable not found.\n\n"
                                      "Please run 'npm start' or 'bun run dev' "
                                      f"in:\n{self.dev_ui_path}")
                else:
                    raise FileNotFoundError("UI executable or source not found")

        except Exception as e:
            self.add_terminal_log(f"ERROR launching UI: {e}")
            messagebox.showerror("Error", f"Failed to launch UI:\n{e}")
            
    def load_build_info(self):
        """Load and display build.json information"""
        # Clear existing widgets
        for widget in self.info_content_frame.winfo_children():
            widget.destroy()
        
        # Server build info
        server_build_file = self.server_dir / "build.json"
        
        # Server section header
        server_header_frame = ttk.Frame(self.info_content_frame)
        server_header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(server_header_frame, text="╔" + "═" * 78 + "╗", 
                 font=('Consolas', 10), foreground='#4A9EFF').pack()
        ttk.Label(server_header_frame, text="║" + " " * 26 + "SERVER BUILD INFORMATION" + " " * 28 + "║",
                 font=('Consolas', 10, 'bold'), foreground='#4A9EFF').pack()
        ttk.Label(server_header_frame, text="╚" + "═" * 78 + "╝",
                 font=('Consolas', 10), foreground='#4A9EFF').pack()
        
        if server_build_file.exists():
            try:
                with open(server_build_file, 'r') as f:
                    server_build = json.load(f)
                
                # Display formatted build info with labels
                self._display_build_data_labels(self.info_content_frame, server_build)
            except Exception as e:
                error_label = ttk.Label(self.info_content_frame, 
                                       text=f"❌ Error loading server build info: {e}",
                                       font=('Consolas', 10), foreground='#E06C75')
                error_label.pack(anchor='w', pady=5)
        else:
            warning_label = ttk.Label(self.info_content_frame,
                                     text="⚠ Server build.json not found",
                                     font=('Consolas', 10), foreground='#E5C07B')
            warning_label.pack(anchor='w', pady=5)
        
        # Spacer
        ttk.Label(self.info_content_frame, text="").pack(pady=10)
        
        # UI build info
        ui_build_file = self.frontend_dir / "build.json"
        
        # UI section header
        ui_header_frame = ttk.Frame(self.info_content_frame)
        ui_header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(ui_header_frame, text="╔" + "═" * 78 + "╗",
                 font=('Consolas', 10), foreground='#4A9EFF').pack()
        ttk.Label(ui_header_frame, text="║" + " " * 28 + "UI BUILD INFORMATION" + " " * 30 + "║",
                 font=('Consolas', 10, 'bold'), foreground='#4A9EFF').pack()
        ttk.Label(ui_header_frame, text="╚" + "═" * 78 + "╝",
                 font=('Consolas', 10), foreground='#4A9EFF').pack()
        
        if ui_build_file.exists():
            try:
                with open(ui_build_file, 'r') as f:
                    ui_build = json.load(f)
                
                # Display formatted build info with labels
                self._display_build_data_labels(self.info_content_frame, ui_build)
            except Exception as e:
                error_label = ttk.Label(self.info_content_frame,
                                       text=f"❌ Error loading UI build info: {e}",
                                       font=('Consolas', 10), foreground='#E06C75')
                error_label.pack(anchor='w', pady=5)
        else:
            warning_label = ttk.Label(self.info_content_frame,
                                     text="⚠ UI build.json not found",
                                     font=('Consolas', 10), foreground='#E5C07B')
            warning_label.pack(anchor='w', pady=5)
        
        # Spacer
        ttk.Label(self.info_content_frame, text="").pack(pady=10)
        
        # Package/Release build info
        package_build_file = self.launcher_dir / "build.json"
        
        # Package section header
        package_header_frame = ttk.Frame(self.info_content_frame)
        package_header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(package_header_frame, text="╔" + "═" * 78 + "╗",
                 font=('Consolas', 10), foreground='#4A9EFF').pack()
        ttk.Label(package_header_frame, text="║" + " " * 26 + "PACKAGE BUILD INFORMATION" + " " * 27 + "║",
                 font=('Consolas', 10, 'bold'), foreground='#4A9EFF').pack()
        ttk.Label(package_header_frame, text="╚" + "═" * 78 + "╝",
                 font=('Consolas', 10), foreground='#4A9EFF').pack()
        
        current_version = None
        if package_build_file.exists():
            try:
                with open(package_build_file, 'r') as f:
                    package_build = json.load(f)
                    current_version = package_build.get('version')
                
                # Display formatted build info with labels (will add update status)
                self._display_build_data_labels(self.info_content_frame, package_build, 
                                               show_update_status=True, current_version=current_version)
            except Exception as e:
                error_label = ttk.Label(self.info_content_frame,
                                       text=f"❌ Error loading package build info: {e}",
                                       font=('Consolas', 10), foreground='#E06C75')
                error_label.pack(anchor='w', pady=5)
        else:
            warning_label = ttk.Label(self.info_content_frame,
                                     text="⚠ Package build.json not found (not running from release)",
                                     font=('Consolas', 10), foreground='#E5C07B')
            warning_label.pack(anchor='w', pady=5)
    
    def _display_build_data_labels(self, parent_frame: ttk.Frame, build_data: dict, 
                                   show_update_status: bool = False, current_version: str = None):
        """Helper to display build data with separate label widgets"""
        # Map of field names to display labels
        label_map = {
            'name': '📛 Name',
            'version': '📦 Version',
            'build': '🕒 Build',
            'build_date': '📅 Build Date',
            'build_time': '🕒 Build Time',
            'build_timestamp': '⏱️  Build Timestamp',
            'release_name': '🎁 Release Name',
            'commit': '🔖 Git Commit',
            'branch': '🌿 Git Branch',
            'builder': '👤 Built By',
            'platform': '💻 Platform',
            'python_version': '🐍 Python Version',
            'node_version': '📗 Node Version',
            'angular_version': '🅰️  Angular Version',
            'tauri_version': '🦀 Tauri Version',
        }
        
        # Display each field as a separate label
        for key, value in build_data.items():
            label_text = label_map.get(key, f'• {key.replace("_", " ").title()}')
            
            # Create a frame for each row
            row_frame = ttk.Frame(parent_frame)
            row_frame.pack(fill='x', pady=2, padx=10)
            
            if isinstance(value, dict):
                # Header for nested dict
                ttk.Label(row_frame, text=f"{label_text}:",
                         font=('Consolas', 10, 'bold'), foreground='#61AFEF').pack(anchor='w')
                for sub_key, sub_value in value.items():
                    sub_row = ttk.Frame(parent_frame)
                    sub_row.pack(fill='x', pady=1, padx=30)
                    ttk.Label(sub_row, text=f"{sub_key}: {sub_value}",
                             font=('Consolas', 9), foreground='#ABB2BF').pack(anchor='w')
            elif isinstance(value, list):
                # Header for list
                ttk.Label(row_frame, text=f"{label_text}:",
                         font=('Consolas', 10, 'bold'), foreground='#61AFEF').pack(anchor='w')
                for item in value:
                    item_row = ttk.Frame(parent_frame)
                    item_row.pack(fill='x', pady=1, padx=30)
                    ttk.Label(item_row, text=f"• {item}",
                             font=('Consolas', 9), foreground='#ABB2BF').pack(anchor='w')
            else:
                # Single value - label and value side by side
                ttk.Label(row_frame, text=f"{label_text:32s}",
                         font=('Consolas', 10, 'bold'), foreground='#61AFEF').pack(side='left')
                ttk.Label(row_frame, text=str(value),
                         font=('Consolas', 10), foreground='#ABB2BF').pack(side='left')
                
                # Add update status next to version if enabled
                if show_update_status and key == 'version':
                    # Create frame for update status (will be updated asynchronously)
                    self.update_status_frame = ttk.Frame(row_frame)
                    self.update_status_frame.pack(side='left', padx=(20, 0))
                    
                    checking_label = ttk.Label(self.update_status_frame, 
                                              text="(🔄 checking...)",
                                              font=('Consolas', 9), foreground='#61AFEF')
                    checking_label.pack(side='left')
                    
                    # Start GitHub update check in background
                    if current_version and Github:
                        threading.Thread(target=self._check_github_updates, 
                                       args=(current_version,), daemon=True).start()
                    elif not Github:
                        # Clear and show error
                        for widget in self.update_status_frame.winfo_children():
                            widget.destroy()
                        ttk.Label(self.update_status_frame, 
                                 text="(⚠ PyGithub not installed)",
                                 font=('Consolas', 9), foreground='#E5C07B').pack(side='left')
    
    def _check_github_updates(self, current_version: str):
        """Check GitHub for updates (runs in background thread)"""
        try:
            # Load config to get repo info
            config_file = self.launcher_dir / "launcher.toml"
            if not config_file.exists():
                config_file = Path(__file__).parent / "launcher.example.toml"
            
            if not config_file.exists():
                raise FileNotFoundError("launcher.toml not found")
            
            with open(config_file, 'rb') as f:
                config = tomli.load(f)
            
            repo_name = config.get('repo', {}).get('main', 'GeorgeTG/Oracle')
            
            # Connect to GitHub (public access, no auth needed)
            g = Github()
            repo = g.get_repo(repo_name)
            
            # Get latest tag
            tags = list(repo.get_tags())
            
            if not tags:
                self._update_status_ui("⚠ No releases found on GitHub", '#E5C07B')
                return
            
            latest_tag = tags[0].name
            # Remove 'v' prefix if present
            latest_version = latest_tag.lstrip('v')
            
            # Compare versions
            if self._compare_versions(current_version, latest_version):
                self._update_status_ui(f"✓ Up to date (v{current_version})", '#98C379')
            else:
                self._update_status_ui(f"⚠ Update available! Current: v{current_version}, Latest: v{latest_version}", '#E06C75')
                
        except Exception as e:
            self._update_status_ui(f"❌ Error checking updates: {str(e)}", '#E06C75')
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare version strings (returns True if current >= latest)"""
        try:
            # Simple version comparison (assumes semantic versioning)
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]
            
            # Pad to same length
            max_len = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))
            
            return current_parts >= latest_parts
        except:
            # If comparison fails, assume current
            return current == latest
    
    def _update_status_ui(self, message: str, color: str):
        """Update the status UI (thread-safe)"""
        def update():
            # Clear existing widgets
            for widget in self.update_status_frame.winfo_children():
                widget.destroy()
            
            # Add new status label inline
            ttk.Label(self.update_status_frame, text=f"({message})",
                     font=('Consolas', 9, 'bold'), foreground=color).pack(side='left')
        
        # Schedule UI update on main thread
        self.root.after(0, update)
        
    def load_license(self) -> str:
        """Load license and liability information"""
        license_file = self.base_path / "LICENSE"
        
        content = """ORACLE - Game Statistics Tracker
Version 0.1
Copyright (c) 2025 Oracle Contributors

"""
        
        if license_file.exists():
            try:
                with open(license_file, 'r', encoding='utf-8') as f:
                    content += f.read()
            except:
                content += "License file could not be loaded."
        else:
            content += "License file not found."
            
        content += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DISCLAIMER AND LIABILITY

This software is provided for educational and personal use only. The software is 
provided "AS IS", without warranty of any kind, express or implied, including but 
not limited to the warranties of merchantability, fitness for a particular purpose 
and noninfringement.

By using this software, you acknowledge and agree that:

1. This software is not affiliated with, endorsed by, or associated with the game 
   developers or publishers.

2. Use of this software is at your own risk. The authors and contributors shall not 
   be liable for any damages, including but not limited to loss of data, account 
   suspension, or any other consequences arising from the use of this software.

3. This software reads game log files and does not modify game files or memory. 
   However, users should review and comply with the game's Terms of Service.

4. The software collects no personal information and all data processing is done 
   locally on your machine.

5. The authors and contributors are not responsible for any misuse of this software.

By using this launcher and the associated Oracle software, you accept these terms 
and conditions.
"""
        return content
        
    def update_status(self, message: str, error: bool = False):
        """Update status label"""
        self.status_label.config(text=message)
        if error:
            self.status_label.config(foreground='red')
        else:
            self.status_label.config(foreground='green')

    def add_terminal_log(self, message: str):
        """Add a message to the terminal output with automatic cleanup"""
        try:
            self.terminal_text.config(state='normal')
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.terminal_text.insert('end', f"[{timestamp}] {message}\n")

            # Prevent memory buildup: keep only last 1000 lines
            line_count = int(self.terminal_text.index('end-1c').split('.')[0])
            if line_count > 1000:
                # Delete oldest lines (keep last 800)
                self.terminal_text.delete('1.0', f'{line_count - 800}.0')

            self.terminal_text.see('end')
            self.terminal_text.config(state='disabled')
        except Exception:
            pass
            

def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Apply the Sun Valley theme (dark mode)
    if sv_ttk:
        sv_ttk.set_theme("dark")
    
    app = OracleLauncher(root)
    root.mainloop()
    

if __name__ == "__main__":
    main()
