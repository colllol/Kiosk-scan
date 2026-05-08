"""
Configuration for Backend API
This file should be updated when building/deploying

Supports both script mode and EXE mode
"""

import os
import json
import sys

# Default configuration
DEFAULT_CONFIG = {
    "api_endpoints": {
        "queue_system": "http://27.71.20.120:2020/api/ticket/create"
    },
    "server": {
        "host": "0.0.0.0",
        "port": 5000
    },
    "directories": {
        "uploads": "uploads",
        "pdfs": "pdfs"
    }
}

def get_config_paths():
    """Get possible config.json paths for both EXE and script modes"""
    paths = []
    
    # When running as EXE (frozen)
    if getattr(sys, 'frozen', False):
        # EXE directory
        exe_dir = os.path.dirname(sys.executable)
        # 1. Same directory as EXE
        paths.append(os.path.join(exe_dir, "config.json"))
        # 2. In config subdirectory
        paths.append(os.path.join(exe_dir, "config", "config.json"))
    else:
        # Script mode
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 1. Parent directory (original location)
        paths.append(os.path.join(script_dir, "..", "config.json"))
        # 2. Same directory as script
        paths.append(os.path.join(script_dir, "config.json"))
    
    return paths

def load_config():
    """Load configuration from config.json or use defaults"""
    config_paths = get_config_paths()
    config_path = None
    
    # Find first existing config file
    for path in config_paths:
        if os.path.exists(path):
            config_path = path
            break
    
    if config_path:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            
            # Update from config.json
            if "apiEndpoints" in config_data:
                if "queueSystem" in config_data["apiEndpoints"]:
                    config["api_endpoints"]["queue_system"] = config_data["apiEndpoints"]["queueSystem"]
            
            if "backendSettings" in config_data:
                backend_settings = config_data["backendSettings"]
                if "host" in backend_settings:
                    config["server"]["host"] = backend_settings["host"]
                if "port" in backend_settings:
                    config["server"]["port"] = backend_settings["port"]
                if "uploadDir" in backend_settings:
                    config["directories"]["uploads"] = backend_settings["uploadDir"]
                if "pdfDir" in backend_settings:
                    config["directories"]["pdfs"] = backend_settings["pdfDir"]
            
            print(f"[CONFIG] Loaded configuration from {config_path}")
            return config
        except Exception as e:
            print(f"[CONFIG] Error loading config.json from {config_path}: {e}, using defaults")
    else:
        # List searched paths for debugging
        print(f"[CONFIG] config.json not found in any of these locations:")
        for i, path in enumerate(config_paths, 1):
            print(f"  {i}. {path}")
        print("[CONFIG] Using default configuration")
    
    return DEFAULT_CONFIG

# Load configuration
CONFIG = load_config()

# Export configuration variables
QUEUE_SYSTEM_API = CONFIG["api_endpoints"]["queue_system"]
SERVER_HOST = CONFIG["server"]["host"]
SERVER_PORT = CONFIG["server"]["port"]
UPLOAD_DIR = CONFIG["directories"]["uploads"]
PDF_DIR = CONFIG["directories"]["pdfs"]