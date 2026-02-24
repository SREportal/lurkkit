from __future__ import annotations
import logging
from typing import Any, Dict
from lurkkit.alerters.base import BaseAlerter
from lurkkit.models import Alert, Severity

log = logging.getLogger(__name__)

class SlackAlerter(BaseAlerter):
    def __init__(self, cfg: Dict):
        self.webhook  = cfg.get("webhook_url", ""); self.channel = cfg.get("channel", "")
        self.username = cfg.get("username", "LurkKit 🐱"); self.icon = cfg.get("icon_emoji", ":cat2:")
        self.mention_critical = cfg.get("mention_on_critical", ""); self.mention_warning = cfg.get("mention_on_warning", "")

    def send(self, alert: Alert) -> None:
        if not self.webhook: return
        colours = {Severity.INFO: "#36a64f", Severity.WARNING: "#ff9f00", Severity.CRITICAL: "#e01e5a", "resolved": "#36a64f"}
        state   = "resolved" if alert.resolved else alert.severity
        colour  = colours.get(state, "#808080")
        icon    = "✅" if alert.resolved else ("🚨" if alert.is_critical else "⚠️")
        mention = ""
        if not alert.resolved:
            if alert.severity == Severity.CRITICAL and self.mention_critical: mention = f"{self.mention_critical} "
            elif alert.severity == Severity.WARNING and self.mention_warning:  mention = f"{self.mention_warning} "
        payload: Dict[str, Any] = {
            "username": self.username, "icon_emoji": self.icon,
            "text": f"{mention}{icon} *{'RESOLVED' if alert.resolved else alert.severity.upper()}* on `{alert.tags.get('host','unknown')}`",
            "attachments": [{"color": colour, "title": alert.name.replace("_", " ").title(), "text": alert.message,
                "footer": f"LurkKit • {alert.source}", "ts": int(alert.timestamp.timestamp()),
                "fields": [{"title": "Severity", "value": alert.severity.upper(), "short": True},
                           {"title": "Host", "value": alert.tags.get("host", "—"), "short": True}]}],
        }
        if self.channel: payload["channel"] = self.channel
        self._post_json(self.webhook, payload)
