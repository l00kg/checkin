from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from .models import SiteConfig

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


@dataclass(slots=True)
class Settings:
    headless: bool = True
    channel: str = "chrome"
    browser_name: str = "chromium"


@dataclass(slots=True)
class AppConfig:
    settings: Settings
    sites: list[SiteConfig]


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            return os.environ.get(key, "")

        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: str | Path) -> AppConfig:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    data = _expand_env(data)

    settings_data = data.get("settings", {})
    settings = Settings(
        headless=bool(settings_data.get("headless", True)),
        channel=str(settings_data.get("channel", "chrome")),
        browser_name=str(settings_data.get("browser_name", "chromium")),
    )

    sites: list[SiteConfig] = []
    for item in data.get("sites", []):
        cookies = item.get("cookies", {}) or {}
        extra = {
            k: v
            for k, v in item.items()
            if k not in {"name", "type", "url", "cookies", "user_agent"}
        }
        sites.append(
            SiteConfig(
                name=str(item["name"]),
                type=str(item["type"]),
                url=str(item["url"]),
                cookies={str(k): str(v) for k, v in cookies.items()},
                user_agent=item.get("user_agent"),
                extra=extra,
            )
        )

    return AppConfig(settings=settings, sites=sites)
