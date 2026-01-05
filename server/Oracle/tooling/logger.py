import sys
import datetime
import asyncio
from pathlib import Path
from typing import Optional
from colorama import init, Fore, Style

init(autoreset=True)


class LogLevel:
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    
    @staticmethod
    def from_string(level_str: str) -> int:
        """Convert string level to LogLevel constant."""
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARN": LogLevel.WARN,
            "WARNING": LogLevel.WARN,
            "ERROR": LogLevel.ERROR
        }
        return level_map.get(level_str.upper(), LogLevel.INFO)


class Logger:
    _log_dir: Optional[Path] = None
    _max_file_size: int = 10 * 1024 * 1024  # 10MB
    _max_files: int = 5
    _current_log_file: Optional[Path] = None  # Shared across all Logger instances
    _file_size: int = 0  # Shared across all Logger instances
    _default_level: Optional[int] = None  # Global default level from config
    _config_loaded: bool = False  # Track if we've tried to load config
    
    @classmethod
    def set_log_directory(cls, log_dir: Path):
        """Set the directory where log files will be stored."""
        cls._log_dir = log_dir
        cls._log_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def set_default_level(cls, level: int):
        """Set the default log level for all new Logger instances."""
        cls._default_level = level
        cls._config_loaded = True
    
    @classmethod
    def _load_config_level(cls):
        """Try to load log level from config.toml (only once)."""
        if cls._config_loaded:
            return
        
        cls._config_loaded = True  # Mark as attempted
        
        try:
            from Oracle.tooling.config import Config
            config = Config()
            logger_config = config.get("logger")
            if logger_config and "level" in logger_config:
                cls._default_level = LogLevel.from_string(logger_config["level"])
        except Exception:
            # Config not available yet, use DEBUG as default
            pass
    
    def _get_level_from_config(self, name: str) -> Optional[int]:
        """Get log level for specific logger from config."""
        try:
            from Oracle.tooling.config import Config
            config = Config()
            
            # Try service-specific level: [logger.ServiceName]
            logger_section = config.get("logger")
            if logger_section and name in logger_section:
                level_value = logger_section[name]
                # Handle nested dict (TOML sections) or direct string value
                if isinstance(level_value, dict) and "level" in level_value:
                    return LogLevel.from_string(level_value["level"])
                elif isinstance(level_value, str):
                    return LogLevel.from_string(level_value)
                
        except Exception:
            pass
        
        return None
    
    def __init__(self, name: str = "Oracle", level: Optional[int] = None):
        self.name = name
        
        # Try to load config if not already loaded
        if not self._config_loaded:
            self._load_config_level()
        
        # Priority: explicit parameter > service-specific config > global default > DEBUG
        if level is not None:
            self.level = level
        else:
            # Try to get service-specific level from config
            service_level = self._get_level_from_config(name)
            if service_level is not None:
                self.level = service_level
            elif self._default_level is not None:
                self.level = self._default_level
            else:
                self.level = LogLevel.DEBUG

    def set_level(self, level: int):
        self.level = level
    
    @classmethod
    def _get_log_file_path(cls) -> Optional[Path]:
        """Get the current log file path."""
        if not cls._log_dir:
            return None
        
        if cls._current_log_file is None:
            # Find the most recent log file or create new one
            log_files = sorted([f for f in cls._log_dir.glob("Oracle_*.log") if not f.name.startswith("Oracle_Parser_")])
            if log_files:
                # Use the most recent file if it's small enough
                latest_file = log_files[-1]
                file_size = latest_file.stat().st_size
                if file_size < cls._max_file_size:
                    cls._current_log_file = latest_file
                    cls._file_size = file_size
                    return cls._current_log_file
            
            # Create new log file
            timestamp = datetime.datetime.now().strftime("%d_%m_%y_%H_%M_%S")
            cls._current_log_file = cls._log_dir / f"Oracle_{timestamp}.log"
            cls._file_size = 0
        
        return cls._current_log_file
    
    @classmethod
    def _rotate_logs(cls):
        """Rotate log files when size limit is reached."""
        if not cls._log_dir:
            return
        
        # Create new log file
        timestamp = datetime.datetime.now().strftime("%d_%m_%y_%H_%M_%S")
        cls._current_log_file = cls._log_dir / f"Oracle_{timestamp}.log"
        cls._file_size = 0
        
        # Clean up old log files
        log_files = sorted([f for f in cls._log_dir.glob("Oracle_*.log") if not f.name.startswith("Oracle_Parser_")])
        if len(log_files) > cls._max_files:
            for old_file in log_files[:-cls._max_files]:
                try:
                    old_file.unlink()
                except Exception:
                    pass

    async def _write_to_file_async(self, log_line: str):
        """Write log line to file asynchronously."""
        log_file = self._get_log_file_path()
        if not log_file:
            return
        
        try:
            # Write to file in a non-blocking way
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self._write_to_file_sync, 
                log_file, 
                log_line
            )
        except Exception as e:
            # Silently fail - don't want logging to break the app
            pass
    
    @classmethod
    def _write_to_file_sync(cls, log_file: Path, log_line: str):
        """Synchronous file write (called in executor)."""
        with open(log_file, "a", encoding="utf-8") as f:
            # Write plain text without color codes
            plain_line = cls._strip_ansi(log_line)
            f.write(plain_line + "\n")
            cls._file_size += len(plain_line) + 1
        
        # Check if rotation is needed after write
        if cls._file_size >= cls._max_file_size:
            cls._rotate_logs()
    
    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI color codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _log(self, emoji: str, color: str, message: str, level: int):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{color}{emoji} [{ts}] [{self.name}] {message}{Style.RESET_ALL}"

        # Print to console (respect level)
        if level >= self.level:
            print(log_line, file=sys.stdout)
        
        # Write to file synchronously if no event loop, otherwise schedule async write
        log_file = self._get_log_file_path()
        if log_file:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._write_to_file_async(log_line))
            except RuntimeError:
                # No event loop running, write synchronously
                try:
                    self._write_to_file_sync(log_file, log_line)
                except Exception:
                    # Silently fail - don't want logging to break the app
                    pass

    def trace(self, e: Exception):
        """Print exception traceback to debug log."""
        import traceback
        tb_str = ''.join(traceback.format_tb(e.__traceback__))
        self.debug(f"Traceback:\n{tb_str}")

    def debug(self, msg: str):
        self._log("🛠️", Fore.CYAN, msg, LogLevel.DEBUG)

    def info(self, msg: str):
        self._log("ℹ️", Fore.GREEN, msg, LogLevel.INFO)

    def warning(self, msg: str):
        self._log("⚠️", Fore.YELLOW, msg, LogLevel.WARN)

    def error(self, msg: str):
        self._log("🛑", Fore.RED, msg, LogLevel.ERROR)
