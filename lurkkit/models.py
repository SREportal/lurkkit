from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

class Severity:
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"
    _RANK    = {"info": 0, "warning": 1, "critical": 2}

    @classmethod
    def rank(cls, sev: str) -> int:
        return cls._RANK.get(sev, 0)

    @classmethod
    def is_pageable(cls, sev: str) -> bool:
        return sev == cls.CRITICAL

@dataclass
class Alert:
    name:      str
    message:   str
    severity:  str
    source:    str
    tags:      Dict[str, str] = field(default_factory=dict)
    resolved:  bool           = False
    timestamp: datetime       = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def id(self) -> str:
        return f"{self.source}:{self.name}"

    @property
    def is_critical(self) -> bool:
        return self.severity == Severity.CRITICAL

    @property
    def is_pageable(self) -> bool:
        return Severity.is_pageable(self.severity) and not self.resolved

    def __str__(self) -> str:
        state = "RESOLVED" if self.resolved else self.severity.upper()
        return f"[{state}] {self.name}: {self.message}"

@dataclass
class Metric:
    measurement:  str
    fields:       Dict[str, Any]
    tags:         Dict[str, str] = field(default_factory=dict)
    timestamp_ns: int            = field(default_factory=lambda: int(time.time() * 1e9))

    def to_line_protocol(self) -> str:
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(self.tags.items())) if self.tags else ""
        meas    = f"{self.measurement},{tag_str}" if tag_str else self.measurement
        fields  = ",".join(self._fmt(k, v) for k, v in self.fields.items())
        return f"{meas} {fields} {self.timestamp_ns}"

    def to_statsd(self) -> List[str]:
        return [f"{self.measurement}.{k}:{v}|g" for k, v in self.fields.items()]

    @staticmethod
    def _fmt(k: str, v: Any) -> str:
        if isinstance(v, bool):  return f"{k}={str(v).lower()}"
        if isinstance(v, int):   return f"{k}={v}i"
        if isinstance(v, float): return f"{k}={v:.4f}"
        return f'{k}="{v}"'
