import logging
import configparser
import sys
from pathlib import Path
from typing import Optional

_CONFIG_CACHE: Optional[configparser.ConfigParser] = None
debug_enabled = False

def get_emtp_directory() -> Path:
    """Find and return the path to the 'emtp' directory."""
    # Resolve gets the absolute path. parents explores upwards.
    current = Path(__file__).resolve()
    
    for parent in [current, *current.parents]:
        emtp_dir = parent / "emtp"
        if emtp_dir.is_dir():
            return emtp_dir
            
    raise FileNotFoundError("Project root (with 'emtp' folder) not found.")

def get_config(config_name: str = "config.ini") -> configparser.ConfigParser:
    """Read and return the configuration file (cached)."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    config_path = get_emtp_directory() / config_name
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path)
    _CONFIG_CACHE = config
    return config

REQUIRED_CONFIG_KEYS = ["owui_base_url", "ollama_uri", "model_name"]

OPTIONAL_CONFIG_KEYS = {
    "authorization_token": None,
    "request_timeout": "60",
    "conversation_batch_size": "8",
    "search_result_count": "10",
    "model_expertise": "Software Engineering",
    "llm_provider": "ollama",
}

def validate_config(config: configparser.ConfigParser = None):
    """Validate config keys at startup. Exit on missing required, warn on missing optional."""
    if config is None:
        config = get_config()

    log = logging.getLogger("emtp.config")

    # Check required keys
    missing_required = [
        key for key in REQUIRED_CONFIG_KEYS
        if not config.has_option("DEFAULT", key)
    ]
    if missing_required:
        for key in missing_required:
            log.error(f"Missing required config key: '{key}'")
        log.error("Cannot proceed without required configuration. Exiting.")
        sys.exit(1)

    # Check optional keys
    for key, default in OPTIONAL_CONFIG_KEYS.items():
        if not config.has_option("DEFAULT", key):
            log.warning(f"Missing optional config key '{key}', using default: {default}")

def initialize_debug_setting():
    """Initialize the debug setting from config file."""
    global debug_enabled
    config = get_config()
    debug_enabled = config.getboolean("DEFAULT", "debug_logs", fallback=False)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True
    )

    if debug_enabled:
        logging.getLogger("emtp").setLevel(logging.DEBUG)

    validate_config(config)

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

def get_logger(name: str = __name__, verbose: Optional[bool] = None) -> logging.Logger:
    """Get a configured logger."""
    if not name.startswith("emtp.") and name != "emtp":
        name = f"emtp.{name}"
        
    logger = logging.getLogger(name)

    if verbose is not None:
        set_verbose(verbose)

    return logger

initialize_debug_setting()