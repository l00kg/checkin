from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SiteConfig:
    name: str
    type: str
    url: str
    cookies: dict[str, str] = field(default_factory=dict)
    user_agent: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CheckinOutcome:
    site: str
    success: bool
    message: str
    raw: dict[str, Any] = field(default_factory=dict)
