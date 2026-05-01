from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Any

from ..models import CheckinOutcome, SiteConfig


class SiteAdapter(ABC):
    site_type: str

    @abstractmethod
    async def checkin(self, site: SiteConfig, *, headless: bool, mobile: bool, channel: str) -> CheckinOutcome:
        raise NotImplementedError

    @staticmethod
    def outcome(site: SiteConfig, success: bool, message: str, **raw: Any) -> CheckinOutcome:
        site_data = asdict(site)
        site_data["cookies"] = {name: "[REDACTED]" for name in site_data.get("cookies", {})}
        return CheckinOutcome(site=site.name, success=success, message=message, raw={"site": site_data, **raw})
