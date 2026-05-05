"""WebSocket client — connects to the bridge for bidirectional CCXT RPC.

This is the core runtime loop of the gateway. It:
1. Connects to wss://bridge.riskmanaged.io/bridge/ws/gateway
2. Authenticates with the API token
3. Registers all configured exchanges
4. Listens for CCXT RPC requests and executes them locally
5. Reconnects automatically on disconnect
"""

import asyncio
import json
import signal
import sys

import websockets

from gateway.ccxt_executor import CCXTExecutor
from gateway.config import GatewayConfig
from gateway.utils.logging import get_logger

logger = get_logger(__name__)


class GatewayWSClient:
    """WebSocket client that connects to the bridge for CCXT RPC."""

    def __init__(self, config: GatewayConfig, executor: CCXTExecutor):
        self.config = config
        self.executor = executor
        self._ws = None
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0

    async def start(self):
        """Start the gateway with automatic reconnection."""
        self._running = True

        # Handle graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        logger.info(
            "Gateway starting",
            bridge_url=self.config.bridge_url,
            exchanges=len(self.executor.get_registered_exchanges()),
        )

        while self._running:
            try:
                await self._connect_and_serve()
            except Exception as e:
                if not self._running:
                    break
                logger.error(
                    "Connection lost",
                    error=str(e),
                    reconnect_in=self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

        logger.info("Gateway stopped")

    async def _connect_and_serve(self):
        """Connect to the bridge and handle messages."""
        url = f"{self.config.bridge_url}?token={self.config.api_key}"

        async with websockets.connect(
            url, ping_interval=30, ping_timeout=10, max_size=10 * 1024 * 1024
        ) as ws:
            self._ws = ws
            self._reconnect_delay = 1.0  # Reset backoff on success

            # Wait for connected confirmation
            raw_hello = await asyncio.wait_for(ws.recv(), timeout=10)
            hello = json.loads(raw_hello)
            if hello.get("type") == "connected":
                logger.info(
                    "Connected to bridge",
                    user_id=hello.get("user_id"),
                    username=hello.get("username"),
                )
            else:
                logger.error("Unexpected hello message", msg=hello)
                return

            # Register exchanges
            await self._register_exchanges(ws)

            # Start heartbeat
            heartbeat_task = asyncio.create_task(self._heartbeat(ws))

            try:
                # Listen for messages
                async for message in ws:
                    try:
                        msg = json.loads(message)
                        await self._handle_message(ws, msg)
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON from bridge", raw=message[:200])
                    except Exception as e:
                        logger.error("Error handling message", error=str(e))
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

    async def _register_exchanges(self, ws):
        """Send registration message with all configured exchanges."""
        exchanges = self.executor.get_registered_exchanges()
        if not exchanges:
            logger.warning("No exchanges configured — gateway will not receive RPC calls")
            return

        register_msg = json.dumps({
            "type": "register",
            "exchanges": exchanges,
        })
        await ws.send(register_msg)

        # Wait for registration confirmation
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            response = json.loads(raw)
            if response.get("type") == "registration_complete":
                logger.info(
                    "Exchanges registered",
                    count=response.get("registered_count", 0),
                    remote_ids=response.get("remote_ids", []),
                )
            else:
                logger.warning("Unexpected registration response", msg=response)
        except asyncio.TimeoutError:
            logger.error("Registration confirmation timed out")

    async def _handle_message(self, ws, msg: dict):
        """Process an incoming message from the bridge."""
        msg_type = msg.get("type")

        if msg_type == "ccxt_rpc":
            await self._handle_rpc(ws, msg)

        elif msg_type == "pong":
            pass  # Heartbeat response

        elif msg_type == "error":
            logger.error("Bridge error", detail=msg.get("detail"))

        else:
            logger.debug("Unknown message type", type=msg_type)

    async def _handle_rpc(self, ws, msg: dict):
        """Execute a CCXT RPC call and send the response."""
        request_id = msg.get("request_id")
        remote_id = msg.get("credential_remote_id")
        method = msg.get("method")
        args = msg.get("args", [])
        kwargs = msg.get("kwargs", {})

        logger.info(
            "RPC call received",
            method=method,
            remote_id=remote_id,
            request_id=request_id,
        )

        # Execute the call
        result = await self.executor.execute_rpc(remote_id, method, args, kwargs)

        # Send response
        response = json.dumps({
            "type": "ccxt_rpc_response",
            "request_id": request_id,
            "result": result.get("result"),
            "error": result.get("error"),
        })

        try:
            await ws.send(response)
            logger.info(
                "RPC response sent",
                method=method,
                remote_id=remote_id,
                has_error=result.get("error") is not None,
            )
        except Exception as e:
            logger.error("Failed to send RPC response", error=str(e))

    async def _heartbeat(self, ws):
        """Send periodic heartbeats."""
        while True:
            try:
                await asyncio.sleep(30)
                await ws.send(json.dumps({"type": "ping"}))
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def stop(self):
        """Gracefully stop the gateway."""
        logger.info("Shutting down...")
        self._running = False
        if self._ws:
            await self._ws.close()
