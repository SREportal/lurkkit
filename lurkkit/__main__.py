from __future__ import annotations
import argparse, logging, os, socket, sys
from datetime import datetime
from pathlib import Path
from typing import Optional

RESET="\033[0m"; BOLD="\033[1m"; RED="\033[91m"; YELLOW="\033[93m"; GREEN="\033[92m"; CYAN="\033[96m"; GREY="\033[90m"

class ColourFormatter(logging.Formatter):
    _C = {logging.DEBUG: GREY, logging.INFO: CYAN, logging.WARNING: YELLOW, logging.ERROR: RED, logging.CRITICAL: RED+BOLD}
    def format(self, r):
        return f"{GREY}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET} {self._C.get(r.levelno,'')}{r.levelname:<8}{RESET} {r.getMessage()}"

def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    ch = logging.StreamHandler(); ch.setFormatter(ColourFormatter()); root.addHandler(ch)
    if log_file:
        fh = logging.FileHandler(log_file); fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")); root.addHandler(fh)

SAMPLE_CONFIG = """\
agent:
  host_tag: ""
  interval: 30
  log_level: INFO
  log_file: ""

telemetry:
  enabled: false
  type: stdout
  url: "http://localhost:8086/write?db=lurkkit"
  statsd_host: "localhost"
  statsd_port: 8125
  batch_size: 20
  flush_interval: 10

monitors:
  system:
    enabled: true
    interval: 30
    thresholds:
      cpu_percent: 85
      memory_percent: 90
      disk_percent: 90
      load_1m: 0.0
      swap_percent: 80
    critical_overrides:
      cpu_percent: 95
      memory_percent: 97
      disk_percent: 97

  processes:
    enabled: false
    interval: 30
    watch:
      - name: nginx
        min_count: 1
        max_cpu: 80.0
        max_mem_mb: 512
        critical: false
      - name: postgres
        min_count: 1
        critical: true

  http:
    enabled: false
    interval: 60
    checks:
      - name: "App Health"
        url: "http://localhost:8080/health"
        method: GET
        timeout: 5
        expect_status: 200
        severity: critical

  logs:
    enabled: false
    interval: 15
    files:
      - path: /var/log/syslog
        tail_lines: 200
        patterns:
          - regex: "ERROR|CRITICAL|panic"
            severity: critical
            alert: true
          - regex: "WARNING"
            severity: warning
            alert: false

alerting:
  cooldown: 300
  send_resolve: true
  paging_severities: [critical]
  non_paging_severities: [warning, info]

  slack:
    enabled: false
    webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    channel: "#alerts"
    username: "LurkKit 🐱"
    icon_emoji: ":cat2:"
    mention_on_critical: ""
    mention_on_warning: ""

  pagerduty:
    enabled: false
    routing_key: "YOUR_PAGERDUTY_ROUTING_KEY"

  datadog:
    enabled: false
    api_key: "YOUR_DATADOG_API_KEY"
    site: "datadoghq.com"
    tags:
      - "env:production"

  opsgenie:
    enabled: false
    api_key: "YOUR_OPSGENIE_API_KEY"
    region: "us"
    team: ""
    priority_map:
      critical: P1
      warning: P3
      info: P5
"""

def print_status():
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   LurkKit — Status Snapshot      ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════╝{RESET}")
    print(f"  Host : {socket.gethostname()}")
    print(f"  Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1); mem = psutil.virtual_memory()
        bar = lambda p: GREEN if p < 70 else (YELLOW if p < 90 else RED)
        print(f"\n  {BOLD}System{RESET}")
        print(f"  CPU   {bar(cpu)}{cpu:5.1f}%{RESET}")
        print(f"  Mem   {bar(mem.percent)}{mem.percent:5.1f}%{RESET}  ({mem.used//1024**2}MB / {mem.total//1024**2}MB)")
        if hasattr(psutil, "getloadavg"):
            l1, l5, l15 = psutil.getloadavg(); print(f"  Load  {l1:.2f} / {l5:.2f} / {l15:.2f}")
        print(f"\n  {BOLD}Disk{RESET}")
        for part in psutil.disk_partitions(all=False)[:4]:
            try:
                du = psutil.disk_usage(part.mountpoint)
                print(f"  {part.mountpoint:<12} {bar(du.percent)}{du.percent:5.1f}%{RESET}  ({du.free//1024**3}GB free)")
            except: pass
    except ImportError:
        print(f"  {YELLOW}psutil not installed: pip install psutil{RESET}")
    print()

def main():
    parser = argparse.ArgumentParser(prog="lurkkit", description="LurkKit — Lightweight Host Monitoring Agent")
    parser.add_argument("--config",    "-c", metavar="PATH", help="Config file path")
    parser.add_argument("--init",            action="store_true", help="Write sample config and exit")
    parser.add_argument("--status",          action="store_true", help="Print system status and exit")
    parser.add_argument("--validate",        action="store_true", help="Validate config and exit")
    parser.add_argument("--log-level",       default=None,        help="DEBUG/INFO/WARNING/ERROR")
    parser.add_argument("--version", "-v",   action="store_true", help="Print version and exit")
    args = parser.parse_args()

    if args.version:
        from lurkkit import __version__; print(f"lurkkit {__version__}"); return

    if args.init:
        target = Path(args.config or "lurkkit.yaml")
        if target.exists(): print(f"Config already exists: {target}")
        else: target.write_text(SAMPLE_CONFIG); print(f"{GREEN}Config written:{RESET} {target}")
        return

    if args.status:
        print_status(); return

    from lurkkit.config import load_config
    cfg       = load_config(args.config)
    agent_cfg = cfg.get("agent", {})
    setup_logging(args.log_level or agent_cfg.get("log_level", "INFO"), agent_cfg.get("log_file") or None)

    if args.validate:
        print(f"Validating: {args.config or 'auto'}")
        for key in ["slack", "pagerduty", "datadog", "opsgenie"]:
            acfg = cfg.get("alerting", {}).get(key, {})
            if acfg.get("enabled"):
                has_creds = bool(acfg.get("webhook_url") or acfg.get("api_key") or acfg.get("routing_key"))
                print(f"  {'✓' if has_creds else '✗'} {key}: {'ok' if has_creds else 'MISSING credentials'}")
        print(f"{GREEN}Config OK{RESET}"); return

    from lurkkit.agent import LurkKitAgent
    LurkKitAgent(cfg).start()

if __name__ == "__main__":
    main()
