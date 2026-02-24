# 🐱 LurkKit

> Lightweight host monitoring agent — silently watching, loudly alerting.

[![CI](https://github.com/SREportal/lurkkit/actions/workflows/ci.yml/badge.svg)](https://github.com/SREportal/lurkkit/actions)
[![PyPI](https://img.shields.io/pypi/v/lurkkit.svg)](https://pypi.org/project/lurkkit/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/lurkkit.svg)](https://pypi.org/project/lurkkit/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

LurkKit is a **zero-friction**, **zero-infrastructure** monitoring agent. Drop it on any host, point it at a YAML config, and instantly get system metrics, process health, HTTP probing, and log tail alerts — forwarded to your team via Slack, PagerDuty, Datadog, or OpsGenie.

Like a cat silently watching from the shadows — and then raising absolute hell when something goes wrong.

---

## Install

```bash
pip install lurkkit
```

> Requires Python 3.8+. No external dependencies beyond `psutil` and `pyyaml`.

---

## Quick Start

```bash
# 1. Install
pip install lurkkit

# 2. Generate a starter config
lurkkit --init

# 3. Edit config — add your API keys, set thresholds
nano lurkkit.yaml

# 4. Run
lurkkit
```

That's it. LurkKit is now watching your host.

---

## Features

| | |
|---|---|
| 📊 **System metrics** | CPU, memory, swap, disk (all mounts), network I/O, load average |
| 🔍 **Process monitoring** | Watch named processes for count, CPU %, and memory — with `critical` flag |
| 🌐 **HTTP health checks** | Status code, response time, body regex — per-check severity |
| 📝 **Log tailing** | Tail any log file, alert on regex matches, handles log rotation |
| 📡 **Telemetry** | InfluxDB line protocol, StatsD UDP, or stdout |
| 🚨 **Paging alerts** | PagerDuty + OpsGenie — triggered on CRITICAL |
| 🔔 **Non-paging alerts** | Slack + Datadog — triggered on WARNING and INFO |
| ♻️ **Auto-resolve** | Sends "resolved" notifications when issues clear automatically |
| 🔇 **Cooldown** | Per-alert suppression to prevent alert storms (default 5 min) |
| 🔌 **Extensible** | Plugin API for custom collectors and alerters |

---

## CLI Reference

```bash
lurkkit                                    # run with auto-detected config
lurkkit --init                             # generate starter lurkkit.yaml
lurkkit --status                           # one-shot system snapshot
lurkkit --validate --config lurkkit.yaml   # validate config and credentials
lurkkit --config /etc/lurkkit/lurkkit.yaml # explicit config path
lurkkit --log-level DEBUG                  # override log level
lurkkit --version                          # print version
```

---

## Installation Options

### pip (recommended)

```bash
pip install lurkkit
lurkkit --init
lurkkit
```

LurkKit auto-detects your config file (first found wins):

| Priority | Location |
|----------|----------|
| 1 | `$LURKKIT_CONFIG` environment variable |
| 2 | `./lurkkit.yaml` current directory |
| 3 | `~/.config/lurkkit/lurkkit.yaml` |
| 4 | `/etc/lurkkit/lurkkit.yaml` |

### systemd (Linux servers)

```bash
sudo bash scripts/install.sh

# Useful commands after install
journalctl -u lurkkit -f        # live logs
systemctl status lurkkit         # check status
systemctl restart lurkkit         # restart after config change
sudo bash scripts/install.sh --uninstall  # remove
```

### Docker

```bash
docker run \
  -v $(pwd)/lurkkit.yaml:/etc/lurkkit/lurkkit.yaml \
  ghcr.io/SREportal/lurkkit
```

Or build your own image:

```dockerfile
FROM python:3.12-slim
RUN pip install lurkkit
COPY lurkkit.yaml /etc/lurkkit/lurkkit.yaml
CMD ["lurkkit"]
```

### Background process (nohup)

```bash
nohup lurkkit --config lurkkit.yaml > /var/log/lurkkit.log 2>&1 &
```

---

## Configuration

Run `lurkkit --init` to generate a fully annotated `lurkkit.yaml`. Below is a full reference.

### Agent

```yaml
agent:
  host_tag: ""       # override auto-detected hostname
  interval: 30       # global collection interval in seconds
  log_level: INFO    # DEBUG | INFO | WARNING | ERROR
  log_file: ""       # optional path to write logs to file
```

### System Monitor

```yaml
monitors:
  system:
    enabled: true
    interval: 30
    thresholds:             # WARNING thresholds
      cpu_percent: 85
      memory_percent: 90
      disk_percent: 90
      load_1m: 4.0          # 0 = disabled
      swap_percent: 80
    critical_overrides:     # CRITICAL thresholds — triggers paging
      cpu_percent: 95
      memory_percent: 97
      disk_percent: 97
```

### Process Monitor

```yaml
monitors:
  processes:
    enabled: true
    watch:
      - name: nginx
        min_count: 1        # alert if fewer instances are running
        max_cpu: 80.0       # per-instance CPU % threshold
        max_mem_mb: 512     # per-instance memory threshold
        critical: false     # false = WARNING only; true = always CRITICAL

      - name: postgres
        min_count: 1
        critical: true      # any issue → CRITICAL → pages on-call
```

The `critical: true` flag means **any** problem with that process (missing, high CPU, high memory) escalates to CRITICAL and routes to your paging alerters regardless of global policy.

### HTTP Health Checks

```yaml
monitors:
  http:
    enabled: true
    interval: 60
    checks:
      - name: "App Health"
        url: "http://localhost:8080/health"
        method: GET
        expect_status: 200
        expect_body: '"status":"ok"'   # optional regex match on response body
        timeout: 5
        severity: critical             # severity when this check fails
        headers:
          Authorization: "Bearer TOKEN"

      - name: "Admin Panel"
        url: "http://localhost:8081/"
        expect_status: 200
        severity: warning              # warning only — won't page on-call
```

### Log File Monitoring

```yaml
monitors:
  logs:
    enabled: true
    interval: 15
    files:
      - path: /var/log/syslog
        tail_lines: 200
        patterns:
          - regex: "OOM|panic|segfault"
            severity: critical
            alert: true
          - regex: "ERROR"
            severity: warning
            alert: true
          - regex: "WARN"
            severity: info
            alert: false    # emit metric only, no alert
```

---

## Alert Routing

LurkKit uses a **two-tier routing model** to separate page-worthy events from informational ones:

```
Alert fires
    │
    ├─ severity in paging_severities? (default: critical)
    │       YES ──► PagerDuty + OpsGenie  (wakes someone up)
    │
    └─ severity in non_paging_severities? (default: warning, info)
            YES ──► Slack + Datadog       (visible, no 3am call)
```

Both tiers fire simultaneously for CRITICAL — it goes to PagerDuty **and** Slack.

```yaml
alerting:
  cooldown: 300          # seconds before same alert can re-fire
  send_resolve: true     # send resolved notification when issue clears

  paging_severities:     # → PagerDuty, OpsGenie
    - critical

  non_paging_severities: # → Slack, Datadog
    - warning
    - info
```

### Slack

```yaml
alerting:
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/..."
    channel: "#alerts"
    username: "LurkKit 🐱"
    icon_emoji: ":cat2:"
    mention_on_critical: "<!here>"
    mention_on_warning: ""
```

### PagerDuty

```yaml
alerting:
  pagerduty:
    enabled: true
    routing_key: "YOUR_ROUTING_KEY"   # PD → Services → Integrations → Events API v2
```

### Datadog

```yaml
alerting:
  datadog:
    enabled: true
    api_key: "YOUR_DATADOG_API_KEY"
    site: "datadoghq.com"    # or datadoghq.eu
    tags:
      - "env:production"
      - "team:platform"
```

### OpsGenie

```yaml
alerting:
  opsgenie:
    enabled: true
    api_key: "YOUR_OPSGENIE_API_KEY"
    region: "us"             # us | eu
    team: "platform-oncall"
    priority_map:
      critical: P1
      warning:  P3
```

---

## Telemetry

### InfluxDB / Telegraf

```yaml
telemetry:
  enabled: true
  type: influxdb
  url: "http://localhost:8086/write?db=lurkkit"
  token: ""    # for InfluxDB 2.x
```

Add this to `telegraf.conf` to receive metrics:
```toml
[[inputs.http_listener_v2]]
  service_address = ":8086"
  paths = ["/write"]
  data_format = "influx"
```

### StatsD

```yaml
telemetry:
  enabled: true
  type: statsd
  statsd_host: localhost
  statsd_port: 8125
```

### Stdout (debugging)

```yaml
telemetry:
  enabled: true
  type: stdout
```

---

## Metrics Reference

| Measurement | Tags | Fields |
|---|---|---|
| `system.cpu` | `host` | `usage_percent`, `core_count` |
| `system.memory` | `host` | `usage_percent`, `used_bytes`, `available_bytes`, `total_bytes` |
| `system.swap` | `host` | `usage_percent`, `used_bytes`, `total_bytes` |
| `system.disk` | `host`, `mount`, `device` | `usage_percent`, `used_bytes`, `free_bytes` |
| `system.network` | `host` | `bytes_sent`, `bytes_recv`, `errin`, `errout` |
| `system.load` | `host` | `load_1m`, `load_5m`, `load_15m` |
| `process.count` | `host`, `process` | `count` |
| `process.stats` | `host`, `process`, `pid` | `cpu_percent`, `mem_mb` |
| `http.check` | `host`, `endpoint` | `status_code`, `response_ms`, `up` |
| `log.matches` | `host`, `logfile`, `pattern` | `count` |

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    LurkKitAgent                        │
│                                                        │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐   │
│  │  System  │ │ Process  │ │  HTTP  │ │   Log    │   │
│  │Collector │ │Collector │ │ Probe  │ │  Tailer  │   │
│  │(thread)  │ │(thread)  │ │(thread)│ │ (thread) │   │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └────┬─────┘   │
│       └────────────┴───────────┴────────────┘         │
│              Metrics                Alerts             │
│                 │                     │                │
│        ┌────────▼──────┐    ┌─────────▼──────────┐    │
│        │ MetricBuffer  │    │   AlertManager      │    │
│        │(batch+flush)  │    │ (dedup + cooldown)  │    │
│        └────────┬──────┘    └─────────┬──────────┘    │
└─────────────────┼─────────────────────┼───────────────┘
                  │                     │
        ┌─────────▼──────┐   ┌──────────▼───────────────┐
        │ InfluxDB /     │   │  PAGING TIER             │
        │ StatsD /       │   │  ├── PagerDuty           │
        │ stdout         │   │  └── OpsGenie            │
        └────────────────┘   │                          │
                             │  NON-PAGING TIER         │
                             │  ├── Slack               │
                             │  └── Datadog             │
                             └──────────────────────────┘
```

---

## Extending LurkKit

### Custom Collector

```python
from lurkkit import LurkKitAgent
from lurkkit.collectors.base import BaseCollector
from lurkkit.models import Metric, Alert, Severity

class RedisQueueCollector(BaseCollector):
    def collect(self):
        depth   = get_queue_depth()
        metrics = [Metric("redis.queue", {"depth": depth}, self._base_tags())]
        alerts  = []
        if depth > self.cfg.get("max_depth", 10_000):
            alerts.append(Alert(
                name     = "queue_backed_up",
                message  = f"Redis queue depth is {depth:,}",
                severity = Severity.CRITICAL,
                source   = "redis",
                tags     = self._base_tags(),
            ))
        return metrics, alerts

agent = LurkKitAgent.from_config("lurkkit.yaml")
agent.register_collector("redis", RedisQueueCollector({"interval": 15, "max_depth": 5000}, agent.hostname))
agent.start()
```

### Custom Alerter

```python
from lurkkit.alerters.base import BaseAlerter
from lurkkit.models import Alert

class TeamsAlerter(BaseAlerter):
    def __init__(self, webhook_url: str):
        self.webhook = webhook_url

    def send(self, alert: Alert) -> None:
        self._post_json(self.webhook, {
            "@type":      "MessageCard",
            "themeColor": "FF0000" if alert.is_critical else "FFA500",
            "summary":    str(alert),
            "text":       alert.message,
        })
```

---

## Development

```bash
# Clone and install in development mode
git clone https://github.com/SREportal/lurkkit
cd lurkkit
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint and format
ruff check lurkkit/
black lurkkit/ tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide.

---

## Project Structure

```
lurkkit/
├── lurkkit/                  ← Python package (pip install lurkkit)
│   ├── __init__.py           ← Public API: LurkKitAgent, Alert, Metric, Severity
│   ├── __main__.py           ← CLI entry point
│   ├── agent.py              ← LurkKitAgent orchestrator
│   ├── alert_manager.py      ← Dedup, cooldown, two-tier routing
│   ├── config.py             ← YAML loading, auto-discovery, defaults
│   ├── models.py             ← Alert, Metric, Severity dataclasses
│   ├── collectors/           ← System, Process, HTTP, Log
│   ├── alerters/             ← Slack, PagerDuty, Datadog, OpsGenie
│   └── telemetry/            ← InfluxDB, StatsD, stdout sinks
├── configs/examples/         ← web-server.yaml, dev-local.yaml
├── scripts/install.sh        ← systemd installer
├── tests/                    ← pytest suite
├── .github/
│   ├── workflows/ci.yml      ← auto-test on PRs, auto-publish on version tags
│   └── ISSUE_TEMPLATE/       ← bug report and feature request forms
├── pyproject.toml            ← package metadata
├── CONTRIBUTING.md           ← contribution guide
├── CHANGELOG.md              ← version history
└── README.md
```

---

## Links

- 📦 **PyPI**: [pypi.org/project/lurkkit](https://pypi.org/project/lurkkit/)
- 🐛 **Issues**: [github.com/SREportal/lurkkit/issues](https://github.com/SREportal/lurkkit/issues)
- 📝 **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- 🤝 **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## License

MIT — see [LICENSE](LICENSE). Use freely, modify freely, ship freely.

If LurkKit is useful to you, a ⭐ on GitHub helps others find it. 🐱
