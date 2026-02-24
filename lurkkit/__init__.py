"""LurkKit - Lightweight Host Monitoring Agent"""
__version__ = "1.0.0"
__author__  = "LurkKit Contributors"
__license__ = "MIT"
__url__     = "https://github.com/SREportal/lurkkit"

from lurkkit.agent import LurkKitAgent
from lurkkit.models import Alert, Metric, Severity

__all__ = ["LurkKitAgent", "Alert", "Metric", "Severity", "__version__"]
