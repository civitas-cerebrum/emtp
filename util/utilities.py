import os
import configparser
import logging

debug_enabled = False

def getEmtpDirectory():
    """Find and return the path to the 'emtp' directory"""
    current = os.path.dirname(__file__)
    while current != "":
        if "emtp" in os.listdir(current):
            break
        current = os.path.dirname(current)
    if current == "":
        raise FileNotFoundError("Project root (with 'emtp' folder) not found")
    return os.path.join(current, "emtp")

def getConfig(config_name="config.ini"):
    """Read and return the configuration file"""
    config = configparser.ConfigParser()
    config.read(os.path.join(getEmtpDirectory(), config_name))
    return config

def initialize_debug_setting():
    """Initialize the debug setting from config file"""
    global debug_enabled
    config = getConfig()
    debug_enabled = config.getboolean("DEFAULT", "debug_logs", fallback=False)

def is_verbose():
    """Return current debug state"""
    return debug_enabled

def set_verbose(verbose: bool):
    """Update the debug state without modifying config file"""
    if verbose:
        getLogger().info("Debug logging enabled.")
    global debug_enabled
    debug_enabled = verbose

def getLogger(name=__name__, verbose: bool = None):
    """Get a configured logger with dynamic debug setting"""
    if verbose is None:
        verbose = is_verbose()
    
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    return logging.getLogger(name)

initialize_debug_setting()