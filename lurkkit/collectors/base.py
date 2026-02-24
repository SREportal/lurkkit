from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from lurkkit.models import Alert, Metric

class BaseCollector(ABC):
    def __init__(self, cfg: Dict, hostname: str):
        self.cfg = cfg; self.hostname = hostname
        self.interval = int(cfg.get("interval", 30))

    @abstractmethod
    def collect(self) -> Tuple[List[Metric], List[Alert]]: ...

    def _base_tags(self, **extra: str) -> Dict[str, str]:
        return {"host": self.hostname, **extra}
