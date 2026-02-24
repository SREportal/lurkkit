"""LurkKit test suite. Run: pytest tests/ -v"""
import os, tempfile
from unittest.mock import MagicMock
from lurkkit.models import Alert, Metric, Severity
from lurkkit.config import deep_merge, DEFAULTS
from lurkkit.alert_manager import AlertManager
from lurkkit.telemetry import MetricBuffer

HOSTNAME = "test-host"

# Models
def test_metric_line_protocol():
    m = Metric("cpu", {"usage": 42}, {"host": "h1"})
    assert "cpu,host=h1" in m.to_line_protocol()
    assert "usage=42i" in m.to_line_protocol()

def test_metric_float():
    assert "pct=78.5000" in Metric("mem", {"pct": 78.5}, {}).to_line_protocol()

def test_metric_statsd():
    assert Metric("cpu", {"pct": 50.0}, {}).to_statsd() == ["cpu.pct:50.0|g"]

def test_alert_id():
    assert Alert("high_cpu", "msg", Severity.CRITICAL, "system").id == "system:high_cpu"

def test_alert_pageable():
    assert Alert("x", "msg", Severity.CRITICAL, "system").is_pageable is True
    assert Alert("x", "msg", Severity.CRITICAL, "system", resolved=True).is_pageable is False

def test_severity_rank():
    assert Severity.rank("info") < Severity.rank("warning") < Severity.rank("critical")

def test_deep_merge():
    r = deep_merge({"a": 1, "b": {"c": 2, "d": 3}}, {"b": {"c": 99}})
    assert r["a"] == 1 and r["b"]["c"] == 99 and r["b"]["d"] == 3

# Alert manager
def test_critical_routes_to_both_tiers():
    p, np = MagicMock(), MagicMock()
    mgr   = AlertManager([p], [np], paging_severities=["critical"], cooldown=300)
    alert = Alert("cpu", "high", Severity.CRITICAL, "system")
    mgr.process([alert], {alert.id})
    assert p.send.call_count == 1 and np.send.call_count == 1

def test_cooldown_suppresses():
    p   = MagicMock()
    mgr = AlertManager([p], [], paging_severities=["critical"], cooldown=300)
    a   = Alert("cpu", "high", Severity.CRITICAL, "system")
    mgr.process([a], {a.id}); mgr.process([a], {a.id})
    assert p.send.call_count == 1

def test_auto_resolve():
    p   = MagicMock()
    mgr = AlertManager([p], [], paging_severities=["critical"], cooldown=300)
    a   = Alert("cpu", "high", Severity.CRITICAL, "system")
    mgr.process([a], {a.id}); mgr.process([], {a.id})
    assert p.send.call_args_list[1][0][0].resolved is True

def test_warning_non_paging_only():
    p, np = MagicMock(), MagicMock()
    mgr   = AlertManager([p], [np], paging_severities=["critical"], cooldown=0)
    a     = Alert("mem", "high", Severity.WARNING, "system")
    mgr.process([a], {a.id})
    assert p.send.call_count == 0 and np.send.call_count == 1

# Telemetry
def test_metric_buffer_flush():
    sink = MagicMock()
    buf  = MetricBuffer(sink, batch_size=2, flush_interval=9999)
    m    = Metric("cpu", {"pct": 50.0}, {})
    buf.add([m, m])
    assert sink.send.call_count == 1

# Collectors
def test_system_collector():
    from lurkkit.collectors.system import SystemCollector
    cfg = {"interval": 10, "thresholds": {"cpu_percent": 100, "memory_percent": 100, "disk_percent": 100},
           "critical_overrides": {"cpu_percent": 100, "memory_percent": 100, "disk_percent": 100}}
    metrics, alerts = SystemCollector(cfg, HOSTNAME).collect()
    assert len(metrics) >= 3 and alerts == []

def test_process_collector():
    from lurkkit.collectors.process import ProcessCollector
    metrics, alerts = ProcessCollector({"interval": 10, "watch": [{"name": "python", "min_count": 1}]}, HOSTNAME).collect()
    assert any(m.fields.get("count", 0) >= 1 for m in metrics if m.measurement == "process.count")

def test_http_collector_down():
    from lurkkit.collectors.http import HttpCollector
    _, alerts = HttpCollector({"interval": 60, "checks": [{"name": "Bad", "url": "http://localhost:19997/", "timeout": 1, "expect_status": 200}]}, HOSTNAME).collect()
    assert len(alerts) == 1 and alerts[0].severity == Severity.CRITICAL

def test_log_collector():
    from lurkkit.collectors.logs import LogCollector
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write("INFO: ok\nERROR: broke\n"); path = f.name
    try:
        _, alerts = LogCollector({"interval": 15, "files": [{"path": path, "patterns": [{"regex": "ERROR", "severity": "warning", "alert": True}]}]}, HOSTNAME).collect()
        assert len(alerts) == 1
    finally:
        os.unlink(path)
