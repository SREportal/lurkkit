from __future__ import annotations
import logging, socket, time, urllib.request
from collections import deque
from threading import Lock
from typing import List, Optional
from lurkkit.models import Metric

log = logging.getLogger(__name__)

class StdoutSink:
    def send(self, metrics: List[Metric]) -> None:
        for m in metrics: print(f"[METRIC] {m.to_line_protocol()}")

class InfluxDBSink:
    def __init__(self, url: str, token: str = ""):
        self.url = url; self.token = token
    def send(self, metrics: List[Metric]) -> None:
        if not metrics: return
        payload = "\n".join(m.to_line_protocol() for m in metrics).encode()
        hdrs    = {"Content-Type": "text/plain; charset=utf-8"}
        if self.token: hdrs["Authorization"] = f"Token {self.token}"
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url, data=payload, headers=hdrs, method="POST"), timeout=5): pass
        except Exception as e: log.warning(f"InfluxDB failed: {e}")

class StatsDSink:
    def __init__(self, host: str = "localhost", port: int = 8125):
        self.host = host; self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    def send(self, metrics: List[Metric]) -> None:
        for m in metrics:
            for line in m.to_statsd():
                try: self._sock.sendto(line.encode(), (self.host, self.port))
                except Exception as e: log.warning(f"StatsD failed: {e}")

def make_sink(cfg: dict) -> Optional[object]:
    if not cfg.get("enabled", False): return None
    t = cfg.get("type", "stdout")
    if t == "influxdb": return InfluxDBSink(cfg.get("url", "http://localhost:8086/write?db=lurkkit"), cfg.get("token", ""))
    if t == "statsd":   return StatsDSink(cfg.get("statsd_host", "localhost"), int(cfg.get("statsd_port", 8125)))
    return StdoutSink()

class MetricBuffer:
    def __init__(self, sink, batch_size: int = 20, flush_interval: int = 10):
        self.sink = sink; self.batch_size = batch_size; self.flush_interval = flush_interval
        self._buf: deque = deque(); self._lock = Lock(); self._last_flush = time.time()

    def add(self, metrics: List[Metric]) -> None:
        if not self.sink or not metrics: return
        with self._lock: self._buf.extend(metrics)
        self._maybe_flush()

    def _maybe_flush(self) -> None:
        with self._lock:
            should = len(self._buf) >= self.batch_size or (time.time() - self._last_flush) >= self.flush_interval
            batch  = (list(self._buf), self._buf.clear() or True, setattr(self, '_last_flush', time.time()))[0] if should and self._buf else []
        if batch:
            try: self.sink.send(batch)
            except Exception as e: log.error(f"Flush error: {e}")

    def flush(self) -> None:
        with self._lock: batch = list(self._buf); self._buf.clear()
        if batch and self.sink:
            try: self.sink.send(batch)
            except Exception as e: log.error(f"Final flush error: {e}")
