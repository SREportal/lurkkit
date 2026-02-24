from __future__ import annotations
import logging, signal, socket, threading, time
from typing import Dict, List, Optional
from lurkkit.alert_manager import AlertManager
from lurkkit.alerters import DatadogAlerter, OpsGenieAlerter, PagerDutyAlerter, SlackAlerter
from lurkkit.alerters.base import BaseAlerter
from lurkkit.collectors import HttpCollector, LogCollector, ProcessCollector, SystemCollector
from lurkkit.collectors.base import BaseCollector
from lurkkit.config import cfg_get, load_config
from lurkkit.telemetry import MetricBuffer, make_sink

log = logging.getLogger(__name__)

class CollectorThread(threading.Thread):
    def __init__(self, name: str, collector: BaseCollector, buffer: MetricBuffer,
                 alert_mgr: AlertManager, checked_ids: set):
        super().__init__(name=f"lurkkit-{name}", daemon=True)
        self.collector = collector; self.buffer = buffer
        self.alert_mgr = alert_mgr; self.checked_ids = checked_ids
        self._stop = threading.Event()

    def stop(self) -> None: self._stop.set()

    def run(self) -> None:
        log.debug(f"Collector started: {self.name} (interval={self.collector.interval}s)")
        while not self._stop.is_set():
            try:
                metrics, alerts = self.collector.collect()
                self.buffer.add(metrics)
                self.alert_mgr.process(alerts, self.checked_ids)
            except Exception as e:
                log.error(f"Collector {self.name} error: {e}", exc_info=True)
            self._stop.wait(timeout=self.collector.interval)

class LurkKitAgent:
    def __init__(self, cfg: Dict):
        self.cfg      = cfg
        self.hostname = cfg_get(cfg, "agent", "host_tag") or socket.gethostname()
        self._threads: List[CollectorThread] = []
        self._buffer:    Optional[MetricBuffer]  = None
        self._alert_mgr: Optional[AlertManager]  = None
        self._running    = False
        self._checked_ids: set = set()

    @classmethod
    def from_config(cls, path: Optional[str] = None) -> "LurkKitAgent":
        return cls(load_config(path))

    def register_collector(self, name: str, collector: BaseCollector) -> "LurkKitAgent":
        if self._buffer is None: self._build()
        t = CollectorThread(name, collector, self._buffer, self._alert_mgr, self._checked_ids)
        self._threads.append(t)
        return self

    def start(self) -> None:
        self._build()
        self._running = True
        log.info(f"LurkKit starting — host={self.hostname}, collectors={len(self._threads)}")
        for t in self._threads: t.start()
        signal.signal(signal.SIGINT,  self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        while self._running: time.sleep(1)

    def stop(self) -> None:
        self._running = False
        for t in self._threads: t.stop()
        for t in self._threads: t.join(timeout=5)
        if self._buffer: self._buffer.flush()
        log.info("LurkKit stopped.")

    def _build(self) -> None:
        if self._buffer is not None: return
        tel_cfg   = self.cfg.get("telemetry", {})
        alert_cfg = self.cfg.get("alerting", {})
        mon_cfg   = self.cfg.get("monitors", {})
        agent_cfg = self.cfg.get("agent", {})
        self._buffer = MetricBuffer(make_sink(tel_cfg),
                                    batch_size=tel_cfg.get("batch_size", 20),
                                    flush_interval=tel_cfg.get("flush_interval", 10))
        paging: List[BaseAlerter]     = []
        non_paging: List[BaseAlerter] = []
        for key, cls, is_paging in [("pagerduty", PagerDutyAlerter, True), ("opsgenie", OpsGenieAlerter, True),
                                     ("slack", SlackAlerter, False), ("datadog", DatadogAlerter, False)]:
            acfg = alert_cfg.get(key, {})
            if acfg.get("enabled", False):
                (paging if is_paging else non_paging).append(cls(acfg))
                log.info(f"Alerter: {key} ({'paging' if is_paging else 'non-paging'})")
        if not paging and not non_paging:
            log.warning("No alerters configured — alerts will only be logged")
        self._alert_mgr = AlertManager(paging, non_paging,
                                       paging_severities=alert_cfg.get("paging_severities", ["critical"]),
                                       cooldown=alert_cfg.get("cooldown", 300),
                                       send_resolve=alert_cfg.get("send_resolve", True))
        global_interval = agent_cfg.get("interval", 30)
        for tname, cls, key in [("system", SystemCollector, "system"), ("processes", ProcessCollector, "processes"),
                                  ("http", HttpCollector, "http"), ("logs", LogCollector, "logs")]:
            ccfg = mon_cfg.get(key, {})
            if not ccfg.get("enabled", False): continue
            ccfg.setdefault("interval", global_interval)
            t = CollectorThread(tname, cls(ccfg, self.hostname), self._buffer, self._alert_mgr, self._checked_ids)
            self._threads.append(t)
            log.info(f"Collector: {tname} (interval={ccfg['interval']}s)")

    def _shutdown(self, sig, frame) -> None:
        log.info(f"Signal {sig} received, shutting down...")
        self.stop()
