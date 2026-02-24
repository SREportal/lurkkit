from __future__ import annotations
import logging, time
from threading import Lock
from typing import Dict, List, Set
from lurkkit.alerters.base import BaseAlerter
from lurkkit.models import Alert, Severity

log = logging.getLogger(__name__)

class AlertManager:
    def __init__(self, paging_alerters: List[BaseAlerter], non_paging_alerters: List[BaseAlerter],
                 paging_severities: List[str] = None, cooldown: int = 300, send_resolve: bool = True):
        self.paging_alerters     = paging_alerters
        self.non_paging_alerters = non_paging_alerters
        self.paging_severities   = set(paging_severities or [Severity.CRITICAL])
        self.cooldown            = cooldown
        self.send_resolve        = send_resolve
        self._last_fired: Dict[str, float] = {}
        self._firing: Set[str]             = set()
        self._lock                         = Lock()

    def process(self, new_alerts: List[Alert], checked_ids: Set[str]) -> None:
        with self._lock:
            now     = time.time()
            new_ids = {a.id for a in new_alerts}
            for alert in new_alerts:
                last = self._last_fired.get(alert.id, 0)
                if now - last >= self.cooldown:
                    self._last_fired[alert.id] = now
                    self._firing.add(alert.id)
                    self._dispatch(alert)
                    log.warning(str(alert))
                else:
                    log.debug(f"Suppressed (cooldown): {alert.id}")
            if self.send_resolve:
                for aid in (self._firing & checked_ids) - new_ids:
                    self._firing.discard(aid)
                    self._last_fired.pop(aid, None)
                    self._dispatch(Alert(name=aid.split(":", 1)[-1], message=f"Alert '{aid}' resolved",
                                        severity=Severity.INFO, source="lurkkit", resolved=True))
                    log.info(f"[RESOLVED] {aid}")

    def _dispatch(self, alert: Alert) -> None:
        targets = []
        if alert.severity in self.paging_severities or alert.resolved:
            targets.extend(self.paging_alerters)
        targets.extend(self.non_paging_alerters)
        for alerter in targets:
            try: alerter.send(alert)
            except Exception as e: log.error(f"{alerter.__class__.__name__} error: {e}")

    @property
    def firing_count(self) -> int:
        return len(self._firing)
