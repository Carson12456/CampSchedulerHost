"""
Structured Logging System for Summer Camp Scheduler
Provides configurable logging with file and console handlers
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


class SchedulerLogger:
    """Centralized logging system for the scheduler"""
    
    def __init__(self, name="scheduler", level=logging.INFO, log_dir="logs"):
        """
        Initialize logging system
        
        Args:
            name: Logger name
            level: Default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels, filter at handler
        
        # Clear any existing handlers
        self.logger.handlers = []
        
        # Create logs directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Console handler - user-facing messages (INFO and above)
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console_format = logging.Formatter('%(message)s')  # Clean output for user
        console.setFormatter(console_format)
        self.logger.addHandler(console)
        
        # File handler - detailed debugging (all levels)
        log_file = log_path / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB per file
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Error file handler - errors only
        error_file = log_path / f"scheduler_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_format)
        self.logger.addHandler(error_handler)
    
    def debug(self, msg, *args, **kwargs):
        """Log debug message (detailed information for diagnosing)"""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        """Log info message (general information)"""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """Log warning message (something unexpected but not critical)"""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        """Log error message (error occurred but program can continue)"""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """Log critical message (severe error, program may crash)"""
        self.logger.critical(msg, *args, **kwargs)
    
    def section(self, title, level="info"):
        """Log a section header"""
        separator = "=" * 70
        getattr(self.logger, level)(f"\n{separator}")
        getattr(self.logger, level)(title)
        getattr(self.logger, level)(separator)
    
    def subsection(self, title, level="info"):
        """Log a subsection header"""
        getattr(self.logger, level)(f"\n--- {title} ---")
    
    def schedule_event(self, troop_name, activity_name, slot, reason="", level="debug"):
        """Log a scheduling event"""
        msg = f"{troop_name}: {activity_name} -> {slot}"
        if reason:
            msg += f" ({reason})"
        getattr(self.logger, level)(f"  {msg}")
    
    def constraint_check(self, troop_name, activity_name, slot, constraint, passed):
        """Log constraint check result"""
        status = "PASS" if passed else "FAIL"
        self.logger.debug(
            f"  [{status}] {troop_name} -> {activity_name} @ {slot}: {constraint}"
        )
    
    def optimization(self, description, count=None):
        """Log optimization result"""
        if count is not None:
            msg = f"  {description}: {count} change(s)"
        else:
            msg = f"  {description}"
        self.logger.info(msg)
    
    def metric(self, name, value, target=None):
        """Log a metric"""
        msg = f"  {name}: {value}"
        if target is not None:
            msg += f" (target: {target})"
        self.logger.info(msg)


# Global logger instance (can be imported by other modules)
_global_logger = None


def get_logger(name="scheduler", level=logging.INFO):
    """Get or create global logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = SchedulerLogger(name, level)
    return _global_logger


def set_log_level(level):
    """
    Change the console logging level
    
    Args:
        level: logging.DEBUG, logging.INFO, logging.WARNING, etc.
    """
    logger = get_logger()
    for handler in logger.logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
            handler.setLevel(level)


# Convenience function for backward compatibility
def log_info(msg):
    """Log an info message (backward compatible with print)"""
    get_logger().info(msg)


def log_debug(msg):
    """Log a debug message"""
    get_logger().debug(msg)


def log_warning(msg):
    """Log a warning message"""
    get_logger().warning(msg)


def log_error(msg):
    """Log an error message"""
    get_logger().error(msg)


if __name__ == "__main__":
    # Demo/test of logging system
    logger = SchedulerLogger("test", level=logging.DEBUG)
    
    logger.section("TESTING LOGGING SYSTEM")
    
    logger.info("This is an info message")
    logger.debug("This is a debug message (only in file)")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    logger.subsection("Scheduling Events")
    logger.schedule_event("Tecumseh", "Archery", "Mon-1", "Top 5 preference", level="info")
    logger.schedule_event("Tamanend", "Delta", "Tue-1", "Commissioner B day", level="info")
    
    logger.subsection("Constraint Checks")
    logger.constraint_check("Tecumseh", "Archery", "Mon-1", "Beach slot rule", True)
    logger.constraint_check("Tecumseh", "Rifle", "Mon-1", "Accuracy limit", False)
    
    logger.subsection("Optimization Results")
    logger.optimization("Area clustering", 3)
    logger.optimization("No beneficial swaps found")
    
    logger.subsection("Metrics")
    logger.metric("Top 5 satisfaction", "98%", "95%")
    logger.metric("Beach violations", "2", "0")
    
    print(f"\nLog files created in logs/ directory")
