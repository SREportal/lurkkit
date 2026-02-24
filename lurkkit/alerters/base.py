from __future__ import annotations
import json, logging, urllib.error, urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from lurkkit.models import Alert

log = logging.getLogger(__name__)

class BaseAlerter(ABC):
    @abstractmethod
    def send(self, alert: Alert) -> None: ...

    def _post_json(self, url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 5) -> Optional[bytes]:
        data = json.dumps(payload).encode()
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        req  = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp: return resp.read()
        except urllib.error.HTTPError as e:
            log.error(f"{self.__class__.__name__} HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            log.error(f"{self.__class__.__name__} failed: {e}")
        return None
