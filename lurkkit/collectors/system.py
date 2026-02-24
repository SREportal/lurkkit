from __future__ import annotations
import logging
from typing import Dict, List, Tuple
from lurkkit.collectors.base import BaseCollector
from lurkkit.models import Alert, Metric, Severity

log = logging.getLogger(__name__)
try:
    import psutil; _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

class SystemCollector(BaseCollector):
    def collect(self) -> Tuple[List[Metric], List[Alert]]:
        if not _HAS_PSUTIL: return [], []
        metrics, alerts = [], []
        thresh = self.cfg.get("thresholds", {}); crit = self.cfg.get("critical_overrides", {})
        tags   = self._base_tags()
        # CPU
        cpu = psutil.cpu_percent(interval=1)
        metrics.append(Metric("system.cpu", {"usage_percent": cpu, "core_count": psutil.cpu_count()}, tags))
        w, c = thresh.get("cpu_percent", 85.0), crit.get("cpu_percent", 95.0)
        if cpu >= c:   alerts.append(Alert("high_cpu", f"CPU at {cpu:.1f}% (critical: {c}%)", Severity.CRITICAL, "system", tags))
        elif cpu >= w: alerts.append(Alert("high_cpu", f"CPU at {cpu:.1f}% (warning: {w}%)",  Severity.WARNING,  "system", tags))
        # Memory
        mem = psutil.virtual_memory()
        metrics.append(Metric("system.memory", {"usage_percent": mem.percent, "used_bytes": mem.used, "available_bytes": mem.available, "total_bytes": mem.total}, tags))
        w, c = thresh.get("memory_percent", 90.0), crit.get("memory_percent", 97.0)
        if mem.percent >= c:   alerts.append(Alert("high_memory", f"Memory at {mem.percent:.1f}% (critical: {c}%)", Severity.CRITICAL, "system", tags))
        elif mem.percent >= w: alerts.append(Alert("high_memory", f"Memory at {mem.percent:.1f}% (warning: {w}%)",  Severity.WARNING,  "system", tags))
        # Disk
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
                dt = dict(tags, mount=part.mountpoint, device=part.device)
                metrics.append(Metric("system.disk", {"usage_percent": u.percent, "used_bytes": u.used, "free_bytes": u.free, "total_bytes": u.total}, dt))
                w, c = thresh.get("disk_percent", 90.0), crit.get("disk_percent", 97.0)
                n = f"high_disk_{part.mountpoint.replace('/', '_') or 'root'}"
                if u.percent >= c:   alerts.append(Alert(n, f"Disk {part.mountpoint} at {u.percent:.1f}%", Severity.CRITICAL, "system", dt))
                elif u.percent >= w: alerts.append(Alert(n, f"Disk {part.mountpoint} at {u.percent:.1f}%", Severity.WARNING,  "system", dt))
            except (PermissionError, OSError): pass
        # Network
        net = psutil.net_io_counters()
        metrics.append(Metric("system.network", {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv, "errin": net.errin, "errout": net.errout}, tags))
        # Load
        if hasattr(psutil, "getloadavg"):
            l1, l5, l15 = psutil.getloadavg()
            metrics.append(Metric("system.load", {"load_1m": l1, "load_5m": l5, "load_15m": l15}, tags))
            lt = float(thresh.get("load_1m", 0))
            if lt > 0 and l1 >= lt:
                alerts.append(Alert("high_load", f"Load {l1:.2f} (threshold: {lt})",
                                    Severity.CRITICAL if l1 >= lt * 1.5 else Severity.WARNING, "system", tags))
        return metrics, alerts
