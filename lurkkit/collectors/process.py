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

class ProcessCollector(BaseCollector):
    def collect(self) -> Tuple[List[Metric], List[Alert]]:
        if not _HAS_PSUTIL: return [], []
        metrics, alerts = [], []
        running: Dict[str, list] = {}
        for proc in psutil.process_iter(["name", "pid"]):
            try: running.setdefault(proc.info["name"], []).append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
        for watch in self.cfg.get("watch", []):
            self._check(watch, running, metrics, alerts)
        return metrics, alerts

    def _check(self, watch, running, metrics, alerts):
        wname = watch.get("name", ""); min_count = int(watch.get("min_count", 1))
        max_cpu = float(watch.get("max_cpu", 0)); max_mem = float(watch.get("max_mem_mb", 0))
        is_crit = watch.get("critical", False)
        matching = [p for pname, procs in running.items() if wname.lower() in pname.lower() for p in procs]
        tags = self._base_tags(process=wname)
        metrics.append(Metric("process.count", {"count": len(matching)}, tags))
        if len(matching) < min_count:
            alerts.append(Alert(f"process_missing_{wname}", f"Process '{wname}' has {len(matching)}/{min_count} instances",
                                Severity.CRITICAL, "process", tags)); return
        for proc in matching:
            try:
                cpu = proc.cpu_percent(interval=0.1); mem = proc.memory_info().rss / 1024 / 1024
                pt  = dict(tags, pid=str(proc.pid))
                metrics.append(Metric("process.stats", {"cpu_percent": cpu, "mem_mb": mem}, pt))
                if max_cpu > 0 and cpu > max_cpu:
                    alerts.append(Alert(f"process_cpu_{wname}_{proc.pid}", f"'{wname}' CPU {cpu:.1f}% > {max_cpu}%",
                                        Severity.CRITICAL if is_crit else Severity.WARNING, "process", pt))
                if max_mem > 0 and mem > max_mem:
                    alerts.append(Alert(f"process_mem_{wname}_{proc.pid}", f"'{wname}' mem {mem:.0f}MB > {max_mem}MB",
                                        Severity.CRITICAL if is_crit else Severity.WARNING, "process", pt))
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
