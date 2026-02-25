import logging
import configparser
from pathlib import Path
from typing import Optional

_CONFIG_CACHE: Optional[configparser.ConfigParser] = None
debug_enabled = False

def getEmtpDirectory() -> Path:
    """Find and return the path to the 'emtp' directory."""
    # Resolve gets the absolute path. parents explores upwards.
    current = Path(__file__).resolve()
    
    for parent in [current, *current.parents]:
        emtp_dir = parent / "emtp"
        if emtp_dir.is_dir():
            return emtp_dir
            
    raise FileNotFoundError("Project root (with 'emtp' folder) not found.")

def getConfig(config_name: str = "config.ini") -> configparser.ConfigParser:
    """Read and return the configuration file (cached)."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    config_path = getEmtpDirectory() / config_name
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)
    _CONFIG_CACHE = config
    return config

def initialize_debug_setting():
    """Initialize the debug setting from config file."""
    global debug_enabled
    config = getConfig()
    debug_enabled = config.getboolean("DEFAULT", "debug_logs", fallback=False)

    logging.basicConfig(
        level=logging.INFO, # Keep root at INFO so 3rd party libs stay quiet, should be NOTSET to see all debug logs
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True 
    )
    
    # Only set OUR app's specific logger to DEBUG if enabled
    if debug_enabled:
        logging.getLogger("emtp").setLevel(logging.DEBUG)

def is_verbose() -> bool:
    """Return current debug state."""
    return debug_enabled

def set_verbose(verbose: bool):
    """Update the debug state for the 'emtp' namespace."""
    global debug_enabled
    debug_enabled = verbose

    app_logger = logging.getLogger("emtp")
    app_logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if verbose:
        app_logger.debug("Debug logging enabled.")

def getLogger(name: str = __name__, verbose: Optional[bool] = None) -> logging.Logger:
    """Get a configured logger."""
    if not name.startswith("emtp.") and name != "emtp":
        name = f"emtp.{name}"
        
    logger = logging.getLogger(name)

    if verbose is not None:
        set_verbose(verbose)

    return logger

initialize_debug_setting()