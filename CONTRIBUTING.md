# Contributing to LurkKit 🐱

Thanks for your interest! All contributions are welcome.

## Getting Started
```bash
git clone https://github.com/SREportal/lurkkit
cd lurkkit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v   # make sure everything passes before you start
```

## What to Work On

Check [Issues](https://github.com/SREportal/lurkkit/issues) for open work.
Labels to look for: `good first issue`, `help wanted`.

Ideas:
- New alerters: Microsoft Teams, Discord, email, webhook
- New collectors: Docker, Kubernetes, Redis, MySQL
- New telemetry sinks: Prometheus, OpenTelemetry
- Windows compatibility
- Better docs and example configs

## Adding a New Alerter
```python
# lurkkit/alerters/myalerter.py
from lurkkit.alerters.base import BaseAlerter
from lurkkit.models import Alert

class MyAlerter(BaseAlerter):
    def __init__(self, cfg: dict):
        self.webhook = cfg.get("webhook_url", "")

    def send(self, alert: Alert) -> None:
        self._post_json(self.webhook, {
            "text":     str(alert),
            "severity": alert.severity,
            "resolved": alert.resolved,
        })
```

Then register it in `lurkkit/alerters/__init__.py` and wire it in `lurkkit/agent.py`.

## Adding a New Collector
```python
# lurkkit/collectors/mycollector.py
from lurkkit.collectors.base import BaseCollector
from lurkkit.models import Metric, Alert, Severity

class MyCollector(BaseCollector):
    def collect(self):
        value   = get_my_metric()
        metrics = [Metric("myapp.value", {"count": value}, self._base_tags())]
        alerts  = []
        if value > self.cfg.get("threshold", 100):
            alerts.append(Alert("threshold_exceeded", f"Value is {value}",
                                Severity.WARNING, "myapp", self._base_tags()))
        return metrics, alerts
```

## Development Workflow
```bash
# Run tests
pytest tests/ -v

# Lint
ruff check lurkkit/

# Format
black lurkkit/ tests/
```

## Commit Style

Use [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add Microsoft Teams alerter
fix: handle log rotation on macOS
docs: add Docker Compose example
test: add OpsGenie resolve tests
```

## Pull Request Process

1. Fork → branch → make changes → open PR against `main`
2. Fill in the PR template
3. CI runs tests automatically across Python 3.9, 3.11, 3.12
4. Maintainer reviews and merges

## Release Process (maintainers)
```bash
# Bump version in pyproject.toml and lurkkit/__init__.py
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
# CI auto-publishes to PyPI
```
