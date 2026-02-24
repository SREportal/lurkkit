from __future__ import annotations
import logging, os, sys
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

DEFAULTS: Dict[str, Any] = {
    "agent":     {"host_tag": "", "interval": 30, "log_level": "INFO", "log_file": ""},
    "telemetry": {"enabled": False, "type": "stdout", "url": "http://localhost:8086/write?db=lurkkit",
                  "statsd_host": "localhost", "statsd_port": 8125, "batch_size": 20, "flush_interval": 10},
    "monitors":  {
        "system":    {"enabled": True,  "interval": 30,
                      "thresholds": {"cpu_percent": 85.0, "memory_percent": 90.0, "disk_percent": 90.0, "load_1m": 0.0, "swap_percent": 80.0},
                      "critical_overrides": {"cpu_percent": 95.0, "memory_percent": 97.0, "disk_percent": 97.0}},
        "processes": {"enabled": False, "interval": 30, "watch": []},
        "http":      {"enabled": False, "interval": 60, "checks": []},
        "logs":      {"enabled": False, "interval": 15, "files": []},
    },
    "alerting": {
        "cooldown": 300, "send_resolve": True,
        "paging_severities": ["critical"],
        "non_paging_severities": ["warning", "info"],
        "slack": {"enabled": False}, "pagerduty": {"enabled": False},
        "datadog": {"enabled": False}, "opsgenie": {"enabled": False},
    },
}

def default_config_paths() -> List[Path]:
    paths = []
    env = os.environ.get("LURKKIT_CONFIG")
    if env: paths.append(Path(env))
    paths.append(Path("lurkkit.yaml"))
    paths.append(Path.home() / ".config" / "lurkkit" / "lurkkit.yaml")
    paths.append(Path("/etc/lurkkit/lurkkit.yaml"))
    return paths

def find_config() -> Optional[Path]:
    for p in default_config_paths():
        if p.exists():
            return p
    return None

def deep_merge(base: Dict, override: Dict) -> Dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

def load_config(path: Optional[str] = None) -> Dict:
    try:
        import yaml
    except ImportError:
        log.error("PyYAML required: pip install pyyaml"); sys.exit(1)
    if path:
        config_path = Path(path)
        if not config_path.exists():
            log.error(f"Config not found: {path}"); sys.exit(1)
    else:
        config_path = find_config()
        if not config_path:
            log.warning("No config found. Using defaults. Run: lurkkit --init")
            return deep_merge(DEFAULTS, {})
    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        return deep_merge(DEFAULTS, raw)
    except Exception as e:
        log.error(f"Failed to parse {config_path}: {e}"); sys.exit(1)

def cfg_get(d: Dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if not isinstance(d, dict): return default
        d = d.get(k)
        if d is None: return default
    return d
