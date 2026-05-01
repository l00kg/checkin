from __future__ import annotations

from .nodeseek import NodeSeekAdapter
from .v2ex import V2EXAdapter

ADAPTERS = {
    NodeSeekAdapter.site_type: NodeSeekAdapter(),
    V2EXAdapter.site_type: V2EXAdapter(),
}


def get_adapter(site_type: str):
    try:
        return ADAPTERS[site_type]
    except KeyError as exc:  # pragma: no cover
        raise KeyError(f"Unsupported site type: {site_type}") from exc
