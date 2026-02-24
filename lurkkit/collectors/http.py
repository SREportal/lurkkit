from __future__ import annotations
import logging, re, time, urllib.error, urllib.request
from typing import Dict, List, Tuple
from lurkkit.collectors.base import BaseCollector
from lurkkit.models import Alert, Metric, Severity

log = logging.getLogger(__name__)

class HttpCollector(BaseCollector):
    def collect(self) -> Tuple[List[Metric], List[Alert]]:
        metrics, alerts = [], []
        for check in self.cfg.get("checks", []):
            m, a = self._check(check); metrics.extend(m); alerts.extend(a)
        return metrics, alerts

    def _check(self, check):
        name = check.get("name", check.get("url", "unknown")); url = check.get("url", "")
        timeout = int(check.get("timeout", 5)); expect = int(check.get("expect_status", 200))
        body_re = check.get("expect_body", ""); severity = check.get("severity", Severity.CRITICAL)
        tags = self._base_tags(endpoint=name.replace(" ", "_"))
        start = time.time(); ok = False; status = 0; error = ""
        try:
            req = urllib.request.Request(url, method=check.get("method", "GET").upper(), headers=check.get("headers", {}))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status; body = resp.read(4096).decode("utf-8", errors="replace")
                elapsed = (time.time() - start) * 1000
                if status != expect: error = f"Expected {expect}, got {status}"
                elif body_re and not re.search(body_re, body): error = f"Body mismatch: {body_re!r}"
                else: ok = True
        except urllib.error.HTTPError as e:
            elapsed = (time.time() - start) * 1000; status = e.code; error = f"HTTP {e.code}"
        except Exception as e:
            elapsed = (time.time() - start) * 1000; error = str(e)
        metrics = [Metric("http.check", {"status_code": status, "response_ms": elapsed, "up": 1 if ok else 0}, tags)]
        alerts  = [] if ok else [Alert(f"http_down_{name.lower().replace(' ','_')}", f"'{name}' DOWN — {error}", severity, "http", tags)]
        return metrics, alerts
