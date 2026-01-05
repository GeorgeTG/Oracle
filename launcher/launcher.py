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
        self.server_running = False  # Track if server is running
        
        # Setup UI
        self.setup_styles()
        self.create_widgets()
        self.load_config()
        self.auto_detect_steamlibrary()
        
        # Start monitoring server requests if server is accessible
        self.monitor_server()
        
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
        
        # Buttons section
        buttons_frame = ttk.LabelFrame(main_frame, text="Launch Options", padding=15)
        buttons_frame.pack(fill='both', expand=True)
        
        # Create 2-column layout: buttons on left, requests on right
        content_frame = ttk.Frame(buttons_frame)
        content_frame.pack(fill='both', expand=True)
        
        # Left: Buttons
        btn_container = ttk.Frame(content_frame)
        btn_container.pack(side='left', fill='y', padx=(0, 10))
        
        # Tray button (3/4 width) with console button (1/4 width) next to it
        tray_frame = ttk.Frame(btn_container)
        tray_frame.pack(pady=5, fill='x')
        
        self.tray_btn = ttk.Button(tray_frame, text="📌 Server (Tray)", 
                                   command=self.start_server_tray, style='Big.TButton')
        self.tray_btn.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.server_btn = ttk.Button(tray_frame, text="🖥️", 
                                     command=self.start_server, style='Big.TButton', width=3)
        self.server_btn.pack(side='left')
        
        # Start UI button (full width)
        self.ui_btn = ttk.Button(btn_container, text="🎨 Start User Interface", 
                                command=self.start_ui, style='Big.TButton')
        self.ui_btn.pack(pady=5, fill='x')
        
        # Right: Server requests log
        log_container = ttk.Frame(content_frame)
        log_container.pack(side='left', fill='both', expand=True)
        
        ttk.Label(log_container, text="Server Requests:", style='Subtitle.TLabel').pack(anchor='w')
        
        log_text_frame = ttk.Frame(log_container)
        log_text_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        scrollbar = ttk.Scrollbar(log_text_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.requests_text = tk.Text(log_text_frame, wrap='word', yscrollcommand=scrollbar.set,
                                    font=('Consolas', 9), bg='#1e1e1e', fg='#d4d4d4', 
                                    relief='flat', height=10)
        self.requests_text.pack(fill='both', expand=True)
        scrollbar.config(command=self.requests_text.yview)
        self.requests_text.insert('1.0', 'Waiting for server requests...\n')
        self.requests_text.config(state='disabled')
        
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
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(info_frame)
        text_frame.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.info_text = tk.Text(text_frame, wrap='word', yscrollcommand=scrollbar.set,
                                font=('Consolas', 10), bg='#f5f5f5', relief='flat')
        self.info_text.pack(fill='both', expand=True)
        scrollbar.config(command=self.info_text.yview)
        
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
                            font=('Segoe UI', 10), bg='#f5f5f5', relief='flat')
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
        
    def start_server(self):
        """Start the Oracle server"""
        try:
            # Check if server is already running
            if self.server_running:
                messagebox.showwarning("Server Running", 
                                     "Server is already running!\n\n"
                                     "Please stop the existing server before starting a new one.")
                return
            
            self.update_status("Starting server...")
            
            # Check for deployed executable first
            server_exe = self.server_dir / "Oracle-Server.exe"
            if server_exe.exists():
                subprocess.Popen([str(server_exe)], cwd=str(server_exe.parent))
                self.update_status("✓ Server started (deployed)")
            else:
                # Fall back to Python script
                server_script = self.dev_server_path / "Oracle" / "server.py"
                if server_script.exists():
                    subprocess.Popen([sys.executable, str(server_script)], 
                                   cwd=str(self.dev_server_path))
                    self.update_status("✓ Server started (development)")
                else:
                    raise FileNotFoundError("Server executable or script not found")
                    
        except Exception as e:
            self.update_status(f"Error starting server: {e}", error=True)
            messagebox.showerror("Error", f"Failed to start server:\n{e}")
            
    def start_server_tray(self):
        """Start the Oracle server in tray mode"""
        try:
            # Check if server is already running
            if self.server_running:
                messagebox.showwarning("Server Running", 
                                     "Server is already running!\n\n"
                                     "Please stop the existing server before starting a new one.")
                return
            
            self.update_status("Starting server (tray mode)...")
            
            # Check for deployed executable first
            server_exe = self.server_dir / "Oracle-Server-Tray.exe"
            if server_exe.exists():
                subprocess.Popen([str(server_exe)], cwd=str(server_exe.parent))
                self.update_status("✓ Server (tray) started (deployed)")
            else:
                # Fall back to Python script
                tray_script = self.dev_server_path / "run_tray.py"
                if tray_script.exists():
                    subprocess.Popen([sys.executable, str(tray_script)], 
                                   cwd=str(self.dev_server_path))
                    self.update_status("✓ Server (tray) started (development)")
                else:
                    raise FileNotFoundError("Server tray executable or script not found")
                    
        except Exception as e:
            self.update_status(f"Error starting server (tray): {e}", error=True)
            messagebox.showerror("Error", f"Failed to start server (tray):\n{e}")
            
    def start_ui(self):
        """Start the Oracle UI"""
        try:
            self.update_status("Starting UI...")
            
            # Check for deployed executable first
            ui_exe = self.frontend_dir / "Oracle.exe"
            if ui_exe.exists():
                subprocess.Popen([str(ui_exe)], cwd=str(ui_exe.parent))
                self.update_status("✓ UI started (deployed)")
            else:
                # Fall back to npm/bun dev server
                if self.dev_ui_path.exists():
                    # Try to start dev server
                    messagebox.showinfo("Development Mode", 
                                      "Starting UI in development mode.\n\n"
                                      "Please run 'npm start' or 'bun run dev' "
                                      f"in:\n{self.dev_ui_path}")
                    self.update_status("Please start UI dev server manually")
                else:
                    raise FileNotFoundError("UI executable or source not found")
                    
        except Exception as e:
            self.update_status(f"Error starting UI: {e}", error=True)
            messagebox.showerror("Error", f"Failed to start UI:\n{e}")
            
    def load_build_info(self):
        """Load and display build.json information"""
        self.info_text.config(state='normal')
        self.info_text.delete('1.0', 'end')
        
        # Server build info
        server_build_file = self.server_dir / "build.json"
        self.info_text.insert('end', "=" * 80 + "\n")
        self.info_text.insert('end', "SERVER BUILD INFORMATION\n", 'header')
        self.info_text.insert('end', "=" * 80 + "\n\n")
        
        if server_build_file.exists():
            try:
                with open(server_build_file, 'r') as f:
                    server_build = json.load(f)
                self.info_text.insert('end', json.dumps(server_build, indent=2) + "\n\n")
            except Exception as e:
                self.info_text.insert('end', f"Error loading server build info: {e}\n\n")
        else:
            self.info_text.insert('end', "Server build.json not found\n\n")
            
        # UI build info
        ui_build_file = self.frontend_dir / "build.json"
        self.info_text.insert('end', "=" * 80 + "\n")
        self.info_text.insert('end', "UI BUILD INFORMATION\n", 'header')
        self.info_text.insert('end', "=" * 80 + "\n\n")
        
        if ui_build_file.exists():
            try:
                with open(ui_build_file, 'r') as f:
                    ui_build = json.load(f)
                self.info_text.insert('end', json.dumps(ui_build, indent=2) + "\n")
            except Exception as e:
                self.info_text.insert('end', f"Error loading UI build info: {e}\n")
        else:
            self.info_text.insert('end', "UI build.json not found\n")
            
        # Configure tags
        self.info_text.tag_config('header', font=('Consolas', 11, 'bold'))
        self.info_text.config(state='disabled')
        
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
    
    def monitor_server(self):
        """Monitor server for incoming requests"""
        def poll_server():
            # Get server URL from config
            server_config = self.config_data.get('server', {})
            host = server_config.get('host', '127.0.0.1')
            port = server_config.get('port', 8000)
            base_url = f"http://{host}:{port}"
            
            self.add_request_log(f"Monitoring {base_url}")
            
            was_reachable = False
            
            while True:
                try:
                    # Check root endpoint
                    req = urllib.request.Request(base_url + "/")
                    req.add_header('User-Agent', 'Oracle-Launcher/1.0')
                    
                    with urllib.request.urlopen(req, timeout=2) as response:
                        data = json.loads(response.read().decode())
                        
                        # Log reconnection if server was down
                        if not was_reachable:
                            self.add_request_log(f"✓ Server connected")
                            was_reachable = True
                            self.server_running = True
                        
                        self.add_request_log(f"GET / → {data.get('status')}: {data.get('message')}")
                    
                    # Wait a bit before status check
                    time.sleep(1)
                    
                    # Check status endpoint
                    req = urllib.request.Request(base_url + "/status")
                    req.add_header('User-Agent', 'Oracle-Launcher/1.0')
                    
                    with urllib.request.urlopen(req, timeout=2) as response:
                        data = json.loads(response.read().decode())
                        parsers = len(data.get('loaded_parsers', []))
                        services = len(data.get('loaded_services', []))
                        reader = data.get('log_reader_status', 'Unknown')
                        self.add_request_log(f"GET /status → Parsers: {parsers}, Services: {services}")
                        self.add_request_log(f"  Log Reader: {reader}")
                    
                    # Poll every 10 seconds
                    time.sleep(10)
                    
                except urllib.error.URLError as e:
                    # Only log once when server becomes unreachable
                    if was_reachable:
                        self.add_request_log(f"⚠ Server not reachable")
                        was_reachable = False
                        self.server_running = False
                    # Retry every 1 second when server is down
                    time.sleep(1)
                except Exception as e:
                    if was_reachable:
                        self.add_request_log(f"❌ Error: {e}")
                        was_reachable = False
                        self.server_running = False
                    time.sleep(1)
        
        # Run polling in background thread
        threading.Thread(target=poll_server, daemon=True).start()
    
    def add_request_log(self, message: str):
        """Add a message to the requests log with automatic cleanup"""
        try:
            self.requests_text.config(state='normal')
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.requests_text.insert('end', f"[{timestamp}] {message}\n")
            
            # Prevent memory buildup: keep only last 500 lines
            line_count = int(self.requests_text.index('end-1c').split('.')[0])
            if line_count > 500:
                # Delete oldest lines (keep last 400)
                self.requests_text.delete('1.0', f'{line_count - 400}.0')
            
            self.requests_text.see('end')
            self.requests_text.config(state='disabled')
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
