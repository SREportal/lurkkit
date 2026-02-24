# 🐱 LurkKit

> Lightweight host monitoring agent — silently watching, loudly alerting.

[![CI](https://github.com/SREportal/lurkkit/actions/workflows/ci.yml/badge.svg)](https://github.com/SREportal/lurkkit/actions)
[![PyPI](https://img.shields.io/pypi/v/lurkkit.svg)](https://pypi.org/project/lurkkit/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

LurkKit is a zero-friction host monitoring agent. Drop it on any host, point it at a config file, and get system metrics, process health, HTTP probing, and log tail alerts forwarded to Slack, PagerDuty, Datadog, or OpsGenie.

---

## Quick Start
```bash
pip install lurkkit
lurkkit --init      # generate config
lurkkit             # run
```

## Commands
```bash
lurkkit --status                        # one-shot system snapshot
lurkkit --validate --config lurkkit.yaml  # validate config
lurkkit --config /etc/lurkkit/lurkkit.yaml
lurkkit --log-level DEBUG
lurkkit --version
```

## Installation Options

### User Install (no root)
```bash
pip install --user lurkkit
lurkkit --init
```

Config auto-detected from (first found wins):
- `$LURKKIT_CONFIG` env var
- `./lurkkit.yaml`
- `~/.config/lurkkit/lurkkit.yaml`
- `/etc/lurkkit/lurkkit.yaml`

### systemd (root)
```bash
sudo bash scripts/install.sh
journalctl -u lurkkit -f
```

### Docker
```bash
docker run -v $(pwd)/lurkkit.yaml:/etc/lurkkit/lurkkit.yaml ghcr.io/SREportal/lurkkit
```

---

## Alert Routing
```
CRITICAL → PagerDuty + OpsGenie  (pages on-call)
WARNING  → Slack + Datadog        (no 3am calls)
INFO     → Slack + Datadog
```

Configurable via `paging_severities` and `non_paging_severities` in your config.

---

## Monitors

| Monitor | What it watches |
|---------|----------------|
| **System** | CPU, memory, swap, disk, network, load average |
| **Process** | Named process count, CPU %, memory — with `critical: true` flag |
| **HTTP** | Status code, response time, body regex — per-check severity |
| **Logs** | Regex pattern matching on any log file, handles rotation |

---

## Metrics Reference

| Measurement | Fields |
|-------------|--------|
| `system.cpu` | `usage_percent`, `core_count` |
| `system.memory` | `usage_percent`, `used_bytes`, `available_bytes` |
| `system.disk` | `usage_percent`, `free_bytes` (per mount) |
| `system.network` | `bytes_sent`, `bytes_recv`, `errin`, `errout` |
| `system.load` | `load_1m`, `load_5m`, `load_15m` |
| `process.count` | `count` |
| `process.stats` | `cpu_percent`, `mem_mb` |
| `http.check` | `status_code`, `response_ms`, `up` |
| `log.matches` | `count` |

---

## Extending LurkKit

### Custom Collector
```python
from lurkkit import LurkKitAgent
from lurkkit.collectors.base import BaseCollector
from lurkkit.models import Metric, Alert, Severity

class MyCollector(BaseCollector):
    def collect(self):
        return [Metric("myapp.value", {"count": 42}, self._base_tags())], []

agent = LurkKitAgent.from_config("lurkkit.yaml")
agent.register_collector("myapp", MyCollector({"interval": 15}, agent.hostname))
agent.start()
```

---

## Development
```bash
git clone https://github.com/SREportal/lurkkit
cd lurkkit
pip install -e ".[dev]"
pytest tests/ -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

## License

MIT — see [LICENSE](LICENSE).
