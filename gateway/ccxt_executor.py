"""CCXT Executor — executes CCXT RPC calls on local exchange instances.

Maintains a pool of CCXT exchange instances (one per configured exchange config).
When an RPC call arrives from the bridge, the executor looks up the exchange
by ``remote_id`` (UUID), calls the requested method, and returns the result.
"""

import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import ccxt

from gateway.config import ExchangeConfig, load_all_exchanges
from gateway.utils.logging import get_logger

logger = get_logger(__name__)

# Thread pool for blocking CCXT calls (network I/O)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ccxt")

# Allowed methods — only these can be called via RPC
ALLOWED_METHODS = frozenset({
    "load_markets",
    "fetch_ticker",
    "create_order",
    "cancel_order",
    "fetch_order",
    "fetch_my_trades",
    "fetch_order_trades",
    "fetch_balance",
    "set_leverage",
})


class CCXTExecutor:
    """Manages local CCXT exchange instances and executes RPC calls."""

    def __init__(self):
        # {remote_id: ccxt.Exchange}
        self._exchanges: dict[str, ccxt.Exchange] = {}
        # {remote_id: ExchangeConfig}
        self._configs: dict[str, ExchangeConfig] = {}

    def load_exchanges(self):
        """Load all exchange configs and create CCXT instances."""
        configs = load_all_exchanges()
        for cfg in configs:
            try:
                self._create_exchange(cfg)
            except Exception as e:
                logger.error(
                    "Failed to create exchange instance",
                    label=cfg.label,
                    exchange=cfg.exchange_name,
                    error=str(e),
                )

        logger.info("CCXT executor loaded", exchange_count=len(self._exchanges))

    def _create_exchange(self, cfg: ExchangeConfig):
        """Create a CCXT exchange instance from an exchange config."""
        from gateway.exchange_manager import WALLET_BASED_EXCHANGES

        exchange_class = getattr(ccxt, cfg.exchange_name, None)
        if exchange_class is None:
            raise ValueError(f"Unknown CCXT exchange: {cfg.exchange_name}")

        # Wallet-based exchanges (e.g. HyperLiquid) use walletAddress + privateKey
        if cfg.exchange_name in WALLET_BASED_EXCHANGES:
            config = {
                "walletAddress": cfg.wallet_address or cfg.api_key,
                "privateKey": cfg.api_secret,
                "enableRateLimit": True,
            }
        else:
            config = {
                "apiKey": cfg.api_key,
                "secret": cfg.api_secret,
                "enableRateLimit": True,
            }
        if cfg.password:
            config["password"] = cfg.password

        exchange = exchange_class(config)

        if cfg.sandbox:
            exchange.set_sandbox_mode(True)
            logger.info("Sandbox mode enabled", label=cfg.label)

        self._exchanges[cfg.id] = exchange
        self._configs[cfg.id] = cfg

        logger.info(
            "Exchange instance created",
            label=cfg.label,
            exchange=cfg.exchange_name,
            remote_id=cfg.id,
            sandbox=cfg.sandbox,
        )

    def get_exchange(self, remote_id: str) -> ccxt.Exchange | None:
        """Get a CCXT exchange instance by remote_id."""
        return self._exchanges.get(remote_id)

    def get_registered_exchanges(self) -> list[dict]:
        """Get registration data for all configured exchanges."""
        return [cfg.to_registration_dict() for cfg in self._configs.values()]

    async def execute_rpc(self, remote_id: str, method: str, args: list, kwargs: dict) -> dict:
        """Execute a CCXT RPC call and return the result.

        Returns a dict with either ``result`` or ``error``.
        Runs the actual CCXT call in a thread pool to avoid blocking the event loop.
        """
        exchange = self._exchanges.get(remote_id)
        if exchange is None:
            return {"result": None, "error": f"Exchange not found: {remote_id}"}

        if method not in ALLOWED_METHODS:
            return {"result": None, "error": f"Method not allowed: {method}"}

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                lambda: self._call_method(exchange, method, args, kwargs),
            )
            return {"result": result, "error": None}
        except ccxt.BaseError as e:
            logger.error(
                "CCXT error",
                method=method,
                remote_id=remote_id,
                error=str(e),
            )
            return {"result": None, "error": str(e)}
        except Exception as e:
            logger.error(
                "RPC execution error",
                method=method,
                remote_id=remote_id,
                error=str(e),
                traceback=traceback.format_exc(),
            )
            return {"result": None, "error": str(e)}

    def _call_method(self, exchange: ccxt.Exchange, method: str, args: list, kwargs: dict) -> Any:
        """Call a method on a CCXT exchange instance (runs in thread pool)."""
        fn = getattr(exchange, method)
        return fn(*args, **kwargs)
