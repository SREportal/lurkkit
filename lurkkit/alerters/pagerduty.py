from __future__ import annotations
import logging, socket
from typing import Dict
from lurkkit.alerters.base import BaseAlerter
from lurkkit.models import Alert, Severity

log = logging.getLogger(__name__)

class PagerDutyAlerter(BaseAlerter):
    ENDPOINT = "https://events.pagerduty.com/v2/enqueue"

    def __init__(self, cfg: Dict):
        self.key     = cfg.get("routing_key", "")
        self.sev_map = {Severity.CRITICAL: "critical", Severity.WARNING: "warning", Severity.INFO: "info", **cfg.get("severity_map", {})}

    def send(self, alert: Alert) -> None:
        if not self.key: return
        self._post_json(self.ENDPOINT, {
            "routing_key": self.key, "event_action": "resolve" if alert.resolved else "trigger",
            "dedup_key": alert.id,
            "payload": {"summary": alert.message[:1024], "source": alert.tags.get("host", socket.gethostname()),
                        "severity": self.sev_map.get(alert.severity, "warning"),
                        "timestamp": alert.timestamp.isoformat(),
                        "custom_details": {k: str(v) for k, v in alert.tags.items()}},
        })
