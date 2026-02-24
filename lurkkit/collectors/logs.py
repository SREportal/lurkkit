from __future__ import annotations
import logging, os, re
from collections import defaultdict
from typing import Dict, List, Tuple
from lurkkit.collectors.base import BaseCollector
from lurkkit.models import Alert, Metric, Severity

log = logging.getLogger(__name__)

class LogCollector(BaseCollector):
    def __init__(self, cfg, hostname):
        super().__init__(cfg, hostname); self._positions: Dict[str, int] = {}

    def collect(self) -> Tuple[List[Metric], List[Alert]]:
        metrics, alerts = [], []
        for fdef in self.cfg.get("files", []):
            m, a = self._tail(fdef); metrics.extend(m); alerts.extend(a)
        return metrics, alerts

    def _tail(self, fdef):
        path = fdef.get("path", ""); patterns = fdef.get("patterns", [])
        if not path or not os.path.exists(path): return [], []
        tags = self._base_tags(logfile=os.path.basename(path))
        try:
            with open(path, "rb") as f:
                f.seek(0, 2); eof = f.tell(); last = self._positions.get(path, 0)
                if last == 0: f.seek(max(0, eof - 32768)); lines = f.read().decode("utf-8", errors="replace").splitlines()[-fdef.get("tail_lines", 200):]
                else:
                    if eof < last: last = 0
                    f.seek(last); lines = f.read().decode("utf-8", errors="replace").splitlines()
                self._positions[path] = eof
        except (PermissionError, OSError) as e: log.warning(f"Cannot read {path}: {e}"); return [], []
        metrics, alerts, counts = [], [], defaultdict(int)
        for line in lines:
            for p in patterns:
                regex = p.get("regex", ""); sev = p.get("severity", Severity.WARNING)
                if regex and re.search(regex, line, re.IGNORECASE):
                    counts[regex] += 1
                    if p.get("alert", True):
                        alerts.append(Alert(f"log_{os.path.basename(path)}_{regex[:20]}", f"Pattern '{regex}' in {path}: {line.strip()[:200]}", sev, "logs", dict(tags, pattern=regex[:50])))
        for regex, count in counts.items():
            metrics.append(Metric("log.matches", {"count": count}, dict(tags, pattern=regex[:50])))
        return metrics, alerts
