"""
Centralized Logging Configuration for Kamikaze AI
Provides consistent logging setup across all components with proper directory structure.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Tuple


def setup_logging(
    component_name: str = "fluxtrader",
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_type: str = "system",
) -> logging.Logger:
    """
    Setup centralized logging configuration with organized directory structure.

    Args:
        component_name: Name of the component for log file naming
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        log_type: Type of log (system, trading_sessions, archived)

    Returns:
        Configured logger instance
    """
    # Ensure logs directory structure exists
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (logs_dir / "system").mkdir(exist_ok=True)
    (logs_dir / "trading_sessions").mkdir(exist_ok=True)
    (logs_dir / "archived").mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger(component_name)

    # Clear any existing handlers
    logger.handlers.clear()

    # Set log level
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Add file handler if requested
    if log_to_file:
        # Determine log file location based on type
        if log_type == "trading_sessions":
            log_file = logs_dir / "trading_sessions" / f"{component_name}.log"
        elif log_type == "archived":
            log_file = logs_dir / "archived" / f"{component_name}.log"
        else:  # system logs
            log_file = logs_dir / "system" / f"{component_name}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logs_directory() -> Path:
    """Get the logs directory path."""
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def create_session_log_file(session_type: str, session_id: str) -> Path:
    """
    Create a session log file in the trading_sessions directory.

    Args:
        session_type: Type of session (e.g., 'pump_dump', 'live_trading', 'backtest')
        session_id: Unique session identifier (usually timestamp)

    Returns:
        Path to the created log file
    """
    logs_dir = get_logs_directory()
    sessions_dir = logs_dir / "trading_sessions"
    sessions_dir.mkdir(exist_ok=True)

    log_filename = f"{session_type}_session_{session_id}.log"
    log_file_path = sessions_dir / log_filename

    return log_file_path


def setup_session_logging(
    session_type: str, session_id: str
) -> Tuple[logging.Logger, Path]:
    """
    Setup logging for a trading session with dedicated log file.

    Args:
        session_type: Type of session (e.g., 'pump_dump', 'live_trading')
        session_id: Unique session identifier

    Returns:
        Tuple of (logger, log_file_path)
    """
    log_file_path = create_session_log_file(session_type, session_id)

    # Create session-specific logger
    logger_name = f"{session_type}_session_{session_id}"
    logger = logging.getLogger(logger_name)

    # Clear any existing handlers
    logger.handlers.clear()

    # Set log level
    logger.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger, log_file_path


def setup_component_logging(component_name: str, config=None) -> logging.Logger:
    """
    Setup logging for a specific component with configuration.

    Args:
        component_name: Name of the component
        config: Configuration object with logging settings

    Returns:
        Configured logger instance
    """
    log_level = "INFO"

    # Get log level from config if available
    if config and hasattr(config, "app") and hasattr(config.app, "log_level"):
        log_level = config.app.log_level

    return setup_logging(
        component_name=component_name,
        log_level=log_level,
        log_to_file=True,
        log_to_console=True,
    )


class LogCapture:
    """Utility class to capture logs for API/UI display."""

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.entries = []
        self.handler = None

    def setup_capture(self, logger_name: str = None):
        """Setup log capture for a specific logger or root logger."""
        if logger_name:
            logger = logging.getLogger(logger_name)
        else:
            logger = logging.getLogger()

        self.handler = LogCaptureHandler(self)
        logger.addHandler(self.handler)

    def get_recent_logs(self, count: Optional[int] = None) -> list:
        """Get recent log entries."""
        if count:
            return self.entries[-count:]
        return self.entries.copy()

    def clear_logs(self):
        """Clear captured logs."""
        self.entries.clear()

    def add_entry(self, record):
        """Add a log entry."""
        entry = {
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.getMessage(),
            "source": record.name,
        }

        self.entries.append(entry)

        # Keep only max_entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries :]


class LogCaptureHandler(logging.Handler):
    """Custom logging handler to capture logs for API/UI display."""

    def __init__(self, log_capture: LogCapture):
        super().__init__()
        self.log_capture = log_capture

    def emit(self, record):
        """Emit a log record."""
        try:
            self.log_capture.add_entry(record)
        except Exception:
            # Ignore errors in log capture to avoid breaking the application
            pass


# Global log capture instance for API/UI
global_log_capture = LogCapture()


def setup_global_log_capture():
    """Setup global log capture for API/UI access."""
    global_log_capture.setup_capture()
    return global_log_capture


def get_log_files() -> dict:
    """Get list of available log files organized by type."""
    logs_dir = get_logs_directory()
    log_files = {"system": [], "trading_sessions": [], "archived": []}

    # Get system logs
    system_dir = logs_dir / "system"
    if system_dir.exists():
        for log_file in system_dir.glob("*.log"):
            log_files["system"].append(
                {
                    "name": log_file.name,
                    "path": str(log_file),
                    "size": log_file.stat().st_size,
                    "modified": log_file.stat().st_mtime,
                    "type": "system",
                }
            )

    # Get trading session logs
    sessions_dir = logs_dir / "trading_sessions"
    if sessions_dir.exists():
        for log_file in sessions_dir.glob("*.log"):
            log_files["trading_sessions"].append(
                {
                    "name": log_file.name,
                    "path": str(log_file),
                    "size": log_file.stat().st_size,
                    "modified": log_file.stat().st_mtime,
                    "type": "trading_session",
                }
            )

    # Get archived logs
    archived_dir = logs_dir / "archived"
    if archived_dir.exists():
        for log_file in archived_dir.glob("*.log"):
            log_files["archived"].append(
                {
                    "name": log_file.name,
                    "path": str(log_file),
                    "size": log_file.stat().st_size,
                    "modified": log_file.stat().st_mtime,
                    "type": "archived",
                }
            )

    # Sort each category by modification time (newest first)
    for category in log_files:
        log_files[category] = sorted(
            log_files[category], key=lambda x: x["modified"], reverse=True
        )

    return log_files


def cleanup_old_logs(days_to_keep: int = 30, archive_old_sessions: bool = True):
    """
    Clean up log files older than specified days.

    Args:
        days_to_keep: Number of days to keep logs
        archive_old_sessions: Whether to move old session logs to archived folder
    """
    import time

    logs_dir = get_logs_directory()
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
    archived_dir = logs_dir / "archived"
    archived_dir.mkdir(exist_ok=True)

    # Clean up system logs (rotate, don't delete)
    system_dir = logs_dir / "system"
    if system_dir.exists():
        for log_file in system_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    # Rotate system logs by keeping last 1000 lines
                    with open(log_file, "r") as f:
                        lines = f.readlines()

                    if len(lines) > 1000:
                        with open(log_file, "w") as f:
                            f.writelines(lines[-1000:])
                        print(f"Rotated system log file: {log_file.name}")
                except Exception as e:
                    print(f"Failed to rotate system log file {log_file.name}: {e}")

    # Handle trading session logs
    sessions_dir = logs_dir / "trading_sessions"
    if sessions_dir.exists():
        for log_file in sessions_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    if archive_old_sessions:
                        # Move to archived folder
                        archived_file = archived_dir / log_file.name
                        log_file.rename(archived_file)
                        print(f"Archived old session log: {log_file.name}")
                    else:
                        # Delete old session logs
                        log_file.unlink()
                        print(f"Deleted old session log: {log_file.name}")
                except Exception as e:
                    print(f"Failed to handle old session log {log_file.name}: {e}")

    # Clean up very old archived logs (older than 90 days)
    very_old_cutoff = time.time() - (90 * 24 * 60 * 60)
    if archived_dir.exists():
        for log_file in archived_dir.glob("*.log"):
            if log_file.stat().st_mtime < very_old_cutoff:
                try:
                    log_file.unlink()
                    print(f"Deleted very old archived log: {log_file.name}")
                except Exception as e:
                    print(f"Failed to delete archived log {log_file.name}: {e}")


# Default logger for the shared module
logger = setup_logging("shared")
