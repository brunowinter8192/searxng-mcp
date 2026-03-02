# INFRASTRUCTURE
import os
import fnmatch
from urllib.parse import urlparse
import yaml

PROFILES_PATH = os.path.join(os.path.dirname(__file__), "profiles.yml")

_cached_config = None


# ORCHESTRATOR
def resolve_profile(url: str) -> dict:
    config = load_config()
    profile_name = match_url_to_profile(url, config.get("routing", {}))
    profiles = config.get("profiles", {})
    profile = profiles.get(profile_name, profiles.get("default", {}))
    return profile


# FUNCTIONS

# Load and cache YAML config from profiles.yml
def load_config() -> dict:
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    with open(PROFILES_PATH, "r") as f:
        _cached_config = yaml.safe_load(f)

    return _cached_config


# Match URL domain against routing patterns, return profile name
def match_url_to_profile(url: str, routing: dict) -> str:
    domain = urlparse(url).hostname or ""

    for pattern, profile_name in routing.items():
        if fnmatch.fnmatch(domain, pattern):
            return profile_name

    return "default"
