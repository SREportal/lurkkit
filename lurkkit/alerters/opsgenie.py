from __future__ import annotations
import logging
from typing import Dict, List
from lurkkit.alerters.base import BaseAlerter
from lurkkit.models import Alert, Severity

log = logging.getLogger(__name__)

class OpsGenieAlerter(BaseAlerter):
    def __init__(self, cfg: Dict):
        self.api_key  = cfg.get("api_key", "")
        base          = "api.eu.opsgenie.com" if cfg.get("region") == "eu" else "api.opsgenie.com"
        self.url      = f"https://{base}/v2/alerts"
        self.team     = cfg.get("team", "")
        self.prio_map = {Severity.CRITICAL: "P1", Severity.WARNING: "P3", Severity.INFO: "P5", **cfg.get("priority_map", {})}

    def send(self, alert: Alert) -> None:
        if not self.api_key: return
        hdrs = {"Authorization": f"GenieKey {self.api_key}"}
        if alert.resolved:
            self._post_json(f"{self.url}/{alert.id}/close?identifierType=alias",
                            {"source": "lurkkit", "note": "Auto-resolved"}, headers=hdrs); return
        payload: Dict = {"message": alert.message[:130], "alias": alert.id, "description": alert.message,
                         "priority": self.prio_map.get(alert.severity, "P3"),
                         "source": alert.tags.get("host", "lurkkit"),
                         "details": {k: str(v) for k, v in alert.tags.items()}}
        if self.team: payload["responders"] = [{"name": self.team, "type": "team"}]
        self._post_json(self.url, payload, headers=hdrs)
