import os
from platformdirs import user_config_dir

def get_config_dir():
    # Use platformdirs for a consistent approach across platforms
    config_dir = user_config_dir("AutoSubSync", appauthor=False, roaming=True)

    # Ensure the directory exists
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        
    return config_dir

def get_config_path():
    return os.path.join(get_config_dir(), "config.json")

config_dir = get_config_dir()
config_path = get_config_path()