from __future__ import annotations
import logging
from typing import Dict, List
from lurkkit.alerters.base import BaseAlerter
from lurkkit.models import Alert, Severity

log = logging.getLogger(__name__)

class DatadogAlerter(BaseAlerter):
    def __init__(self, cfg: Dict):
        self.api_key = cfg.get("api_key", "")
        self.url     = f"https://api.{cfg.get('site', 'datadoghq.com')}/api/v1/events"
        self.tags: List[str] = cfg.get("tags", [])

    def send(self, alert: Alert) -> None:
        if not self.api_key: return
        state = "Resolved" if alert.resolved else alert.severity.title()
        self._post_json(self.url, {
            "title": f"[LurkKit][{state}] {alert.name.replace('_',' ').title()}",
            "text":  alert.message,
            "alert_type": "success" if alert.resolved else ("error" if alert.is_critical else "warning"),
            "source_type_name": "LurkKit", "aggregation_key": alert.id,
            "tags": list(self.tags) + [f"{k}:{v}" for k, v in alert.tags.items()],
        }, headers={"DD-API-KEY": self.api_key})
