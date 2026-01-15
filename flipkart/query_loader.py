import json
import os

def load_queries(config_path="search_config.json"):
    """
    Loads search queries and settings from JSON config file.
    
    Returns:
        dict: {
            "searchQueries": [...],
            "settings": {...}
        }
    """
    # Resolve path relative to this file's directory if the default path is used and doesn't exist 'locally'
    if config_path == "search_config.json" and not os.path.exists(config_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "search_config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Basic validation
    if "searchQueries" not in config or not isinstance(config["searchQueries"], list):
        raise ValueError("Invalid config: 'searchQueries' must be a list")

    if "settings" not in config or not isinstance(config["settings"], dict):
        raise ValueError("Invalid config: 'settings' must be an object")

    return config
