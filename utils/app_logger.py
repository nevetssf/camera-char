"""
Application logging system.
Provides file-based logging to working directory with enable/disable control.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class AppLogger:
    """Application logger with file output and enable/disable control"""

    LOG_FILENAME = 'debug.log'

    def __init__(self):
        """Initialize application logger"""
        self.logger: Optional[logging.Logger] = None
        self.log_file_path: Optional[Path] = None
        self.file_handler: Optional[logging.FileHandler] = None
        self.console_handler: Optional[logging.StreamHandler] = None
        self.enabled = True

    def initialize(self, working_dir: Path, clear_on_start: bool = True) -> None:
        """
        Initialize the logger with file output.

        Args:
            working_dir: Directory where log file will be created
            clear_on_start: Clear log file on initialization
        """
        self.log_file_path = working_dir / self.LOG_FILENAME

        # Clear log file if requested
        if clear_on_start and self.log_file_path.exists():
            self.log_file_path.unlink()

        # Create logger
        self.logger = logging.getLogger('CameraSensorAnalyzer')
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers
        self.logger.handlers.clear()

        # File handler
        self.file_handler = logging.FileHandler(self.log_file_path, mode='a')
        self.file_handler.setLevel(logging.DEBUG)

        # Console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.file_handler.setFormatter(formatter)
        self.console_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

        # Initial log message
        self.info("=" * 60)
        self.info(f"Sensor Analysis - Session started")
        self.info(f"Log file: {self.log_file_path}")
        self.info("=" * 60)

    def enable(self) -> None:
        """Enable logging"""
        self.enabled = True
        if self.logger:
            self.logger.setLevel(logging.DEBUG)
            self.info("Logging enabled")

    def disable(self) -> None:
        """Disable logging"""
        if self.enabled and self.logger:
            self.info("Logging disabled")
        self.enabled = False
        if self.logger:
            self.logger.setLevel(logging.CRITICAL + 1)  # Disable all logging

    def is_enabled(self) -> bool:
        """Check if logging is enabled"""
        return self.enabled

    def debug(self, message: str) -> None:
        """Log debug message"""
        if self.enabled and self.logger:
            self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message"""
        if self.enabled and self.logger:
            self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message"""
        if self.enabled and self.logger:
            self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False) -> None:
        """Log error message"""
        if self.enabled and self.logger:
            self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False) -> None:
        """Log critical message"""
        if self.enabled and self.logger:
            self.logger.critical(message, exc_info=exc_info)

    def get_log_file_path(self) -> Optional[Path]:
        """Get path to log file"""
        return self.log_file_path

    def read_log(self) -> str:
        """Read current log file contents"""
        if self.log_file_path and self.log_file_path.exists():
            try:
                with open(self.log_file_path, 'r') as f:
                    return f.read()
            except Exception as e:
                return f"Error reading log file: {e}"
        return "Log file not found"

    def clear_log(self) -> None:
        """Clear log file"""
        if self.log_file_path and self.log_file_path.exists():
            try:
                self.log_file_path.unlink()
                self.info("Log file cleared")
            except Exception as e:
                self.error(f"Failed to clear log file: {e}")


# Global logger instance
_global_logger: Optional[AppLogger] = None


def get_logger() -> AppLogger:
    """
    Get or create global logger instance.

    Returns:
        AppLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = AppLogger()
    return _global_logger


def init_logger(working_dir: Path, clear_on_start: bool = True) -> AppLogger:
    """
    Initialize global logger.

    Args:
        working_dir: Directory for log file
        clear_on_start: Clear log on start

    Returns:
        Initialized AppLogger instance
    """
    logger = get_logger()
    logger.initialize(working_dir, clear_on_start)
    return logger
