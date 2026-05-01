from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
import re
from pathlib import Path

from .config import AppConfig, load_config
from .models import CheckinOutcome
from .sites import get_adapter


_MOBILE_UA_RE = re.compile(r"Mobile|iPhone|Android|Opera Mini", re.I)


def _is_mobile_user_agent(user_agent: str | None) -> bool:
    return bool(user_agent and _MOBILE_UA_RE.search(user_agent))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="checkin")
    sub = parser.add_subparsers(dest="command", required=True)

    checkin = sub.add_parser("checkin", help="Run check-in for one or more sites")
    checkin.add_argument("site", nargs="?", help="Site name to check in")
    checkin.add_argument("--all", action="store_true", help="Run all configured sites")
    checkin.add_argument("--config", default="checkin.toml", help="Path to config TOML")
    checkin.add_argument("--json", action="store_true", help="Emit JSON output")

    return parser


def _select_sites(config: AppConfig, site_name: str | None, run_all: bool) -> list:
    if run_all:
        return config.sites
    if site_name:
        for site in config.sites:
            if site.name == site_name:
                return [site]
        raise SystemExit(f"Site not found: {site_name}")
    if len(config.sites) == 1:
        return config.sites
    raise SystemExit("Please specify a site name or use --all")


async def _run_checkin(config: AppConfig, site_name: str | None, run_all: bool) -> list[CheckinOutcome]:
    sites = _select_sites(config, site_name, run_all)
    outcomes: list[CheckinOutcome] = []
    for site in sites:
        adapter = get_adapter(site.type)
        outcome = await adapter.checkin(
            site,
            headless=config.settings.headless,
            mobile=_is_mobile_user_agent(site.user_agent),
            channel=config.settings.channel,
        )
        outcomes.append(outcome)
    return outcomes


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "checkin":
        config = load_config(Path(args.config))
        outcomes = asyncio.run(_run_checkin(config, args.site, args.all))
        if args.json:
            print(json.dumps([asdict(o) for o in outcomes], ensure_ascii=False, indent=2))
        else:
            for outcome in outcomes:
                status = "SUCCESS" if outcome.success else "FAILED"
                print(f"[{status}] {outcome.site}: {outcome.message}")
