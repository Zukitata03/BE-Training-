"""Multi-RPC Web3 helpers with failover for public endpoint rate limits."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from web3 import Web3
from web3.exceptions import Web3RPCError

from .config import get_config

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_blockchain_rpc_urls() -> list[str]:
    """Ordered list of RPC endpoints (comma-separated `blockchain_rpc_urls` or single `blockchain_rpc_url`)."""
    cfg = get_config()
    raw = (cfg.blockchain_rpc_urls or "").strip()
    if raw:
        urls = [u.strip() for u in raw.split(",") if u.strip()]
        if urls:
            return urls
    url = (cfg.blockchain_rpc_url or "").strip()
    return [url] if url else []


def _is_transient_rpc_error(exc: BaseException) -> bool:
    if isinstance(exc, Web3RPCError):
        msg = str(exc).lower()
        return "limit exceeded" in msg or "-32005" in str(exc) or "429" in msg
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    return False


def web3_with_failover(call: Callable[[Web3], T], *, timeout: int = 45) -> T:
    """Run `call(w3)` against each configured RPC until one succeeds or errors are exhausted."""
    urls = get_blockchain_rpc_urls()
    if not urls:
        raise RuntimeError("No blockchain RPC URLs configured (blockchain_rpc_url / blockchain_rpc_urls)")

    last_error: BaseException | None = None
    for url in urls:
        w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": timeout}))
        try:
            return call(w3)
        except Exception as exc:
            if _is_transient_rpc_error(exc):
                logger.warning("RPC %s failed (%s), trying next if any", url, exc)
                last_error = exc
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("All RPC endpoints failed")
