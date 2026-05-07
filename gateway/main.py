"""RiskManaged Gateway — CLI entry point.

Usage:
    riskmanaged-gateway                    Start the gateway service
    riskmanaged-gateway bootstrap          First-time setup
    riskmanaged-gateway add-exchange       Add a new exchange credential
    riskmanaged-gateway remove-exchange    Remove an exchange credential
    riskmanaged-gateway list-exchanges     List configured exchanges
    riskmanaged-gateway status             Show gateway status
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="riskmanaged-gateway",
    help="RiskManaged Gateway — Connect your exchange to riskmanaged.io",
    add_completion=False,
    invoke_without_command=True,
)
console = Console()


@app.callback()
def main(ctx: typer.Context):
    """Start the gateway if no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        _start_gateway()


def _start_gateway():
    """Start the gateway service (WS client + CCXT executor)."""
    from gateway.ccxt_executor import CCXTExecutor
    from gateway.config import GatewayConfig
    from gateway.utils.logging import setup_logging
    from gateway.ws_client import GatewayWSClient

    config = GatewayConfig.load()

    if not config.is_configured:
        console.print("[red]Gateway not configured. Run:[/red]")
        console.print("  [bold]riskmanaged-gateway bootstrap[/bold]")
        raise typer.Exit(1)

    setup_logging(config.log_level)

    console.print("\n[bold cyan]RiskManaged Gateway[/bold cyan]")
    console.print(f"  Bridge: {config.bridge_url}")

    # Load exchange instances
    executor = CCXTExecutor()
    executor.load_exchanges()

    exchanges = executor.get_registered_exchanges()
    if not exchanges:
        console.print("[yellow]⚠ No exchanges configured. Add one with:[/yellow]")
        console.print("  [bold]riskmanaged-gateway add-exchange[/bold]")
    else:
        console.print(f"  Exchanges: {len(exchanges)}")
        for ex in exchanges:
            sandbox = " [sandbox]" if ex.get("sandbox") else ""
            console.print(f"    • {ex['label']} ({ex['exchange_name']}){sandbox}")

    console.print()

    # Start the WS client
    client = GatewayWSClient(config=config, executor=executor)

    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        console.print("\n[dim]Gateway stopped[/dim]")


@app.command()
def bootstrap():
    """Interactive first-time setup."""
    from gateway.bootstrap import run_bootstrap
    from gateway.utils.logging import setup_logging

    setup_logging("INFO")
    run_bootstrap()


@app.command("add-exchange")
def add_exchange():
    """Add a new exchange credential."""
    from gateway.exchange_manager import add_exchange_interactive
    from gateway.utils.logging import setup_logging

    setup_logging("INFO")
    add_exchange_interactive()


@app.command("remove-exchange")
def remove_exchange(
    label: str = typer.Argument(..., help="Label of the exchange to remove"),
):
    """Remove an exchange credential by label."""
    from gateway.exchange_manager import remove_exchange as _remove
    from gateway.utils.logging import setup_logging

    setup_logging("INFO")
    _remove(label)


@app.command("list-exchanges")
def list_exchanges_cmd():
    """List all configured exchanges."""
    from gateway.exchange_manager import list_exchanges
    from gateway.utils.logging import setup_logging

    setup_logging("INFO")
    list_exchanges()


@app.command()
def status():
    """Show gateway configuration and connection status."""
    from gateway.config import GatewayConfig, load_all_exchanges
    from gateway.utils.logging import setup_logging

    setup_logging("INFO")

    config = GatewayConfig.load()
    exchanges = load_all_exchanges()

    console.print("\n[bold cyan]Gateway Status[/bold cyan]")
    console.print(f"  Configured: {'[green]Yes[/green]' if config.is_configured else '[red]No[/red]'}")
    console.print(f"  API Key: {config.api_key[:8]}..." if config.api_key else "  API Key: [red]Not set[/red]")
    console.print(f"  Bridge URL: {config.bridge_url}")
    console.print(f"  Log Level: {config.log_level}")
    console.print(f"  Exchanges: {len(exchanges)}")

    for ex in exchanges:
        sandbox = " [yellow](sandbox)[/yellow]" if ex.sandbox else ""
        console.print(f"    • {ex.label} — {ex.exchange_name}{sandbox} [{ex.id[:8]}...]")

    console.print()


@app.command("create-wallet")
def create_wallet():
    """Generate an API wallet for wallet-based exchanges (e.g. HyperLiquid)."""
    from gateway.utils.logging import setup_logging
    from gateway.wallet_manager import create_hyperliquid_wallet

    setup_logging("INFO")
    create_hyperliquid_wallet()


if __name__ == "__main__":
    app()
