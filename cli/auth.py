import os
import click
from pathlib import Path
import json

# get the base url from the user (or default to the .config file)
# get the api key from the user (or default to the .config file)
# this is the default config directory
CONFIG_DIR = Path.home() / ".tandemn"
CONFIG_FILE = CONFIG_DIR / "config.json"

def get_stored_credentials():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("central_server_url"), config.get("storage_server_url"), config.get("api_key")
    return None, None, None

def set_stored_credentials(central_server_url, storage_server_url, api_key):
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"central_server_url": central_server_url, "storage_server_url": storage_server_url, "api_key": api_key}, f)
    click.echo(f"Credentials stored in {CONFIG_FILE}")


