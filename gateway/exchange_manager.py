"""Exchange manager — add, remove, and list exchange credentials."""

import uuid

from rich.console import Console
from rich.table import Table

from gateway.config import ExchangeConfig, get_exchanges_dir, load_all_exchanges
from gateway.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Supported exchanges — maps to CCXT exchange IDs
SUPPORTED_EXCHANGES = {
    "1": ("binance", "Binance"),
    "2": ("bybit", "Bybit"),
    "3": ("kucoin", "KuCoin"),
    "4": ("kraken", "Kraken"),
    "5": ("coinbase", "Coinbase"),
    "6": ("bitvavo", "Bitvavo"),
    "7": ("okx", "OKX"),
    "8": ("cryptocom", "Crypto.com"),
    "9": ("mexc", "MEXC"),
    "10": ("bitmex", "BitMEX"),
}

# Exchanges that require a password/passphrase
EXCHANGES_WITH_PASSWORD = {"kucoin", "okx"}


def add_exchange_interactive() -> ExchangeConfig | None:
    """Interactive flow to add a new exchange credential.

    Returns the created ExchangeConfig, or None if cancelled.
    """
    console.print("\n[bold cyan]Supported Exchanges[/bold cyan]")
    for num, (exchange_id, display_name) in SUPPORTED_EXCHANGES.items():
        console.print(f"  {num}. {display_name}")

    choice = console.input("\n[bold]Select exchange (1-10):[/bold] ").strip()
    if choice not in SUPPORTED_EXCHANGES:
        console.print("[red]Invalid choice[/red]")
        return None

    exchange_id, display_name = SUPPORTED_EXCHANGES[choice]

    # Label
    default_label = exchange_id
    existing = load_all_exchanges()
    existing_labels = {e.label for e in existing}

    # Auto-suggest unique label
    if default_label in existing_labels:
        i = 2
        while f"{default_label}-{i}" in existing_labels:
            i += 1
        default_label = f"{default_label}-{i}"

    label = (
        console.input(
            f'[bold]Label[/bold] (e.g. "{exchange_id}-main", "{exchange_id}-sub-a") '
            f"[{default_label}]: "
        ).strip()
        or default_label
    )

    # Validate label uniqueness
    if label in existing_labels:
        console.print(f'[red]Label "{label}" already exists. Use a different label.[/red]')
        return None

    # Validate label characters (filesystem safe)
    safe_chars = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
    if not all(c in safe_chars for c in label.lower()):
        console.print("[red]Label must only contain letters, numbers, hyphens, and underscores.[/red]")
        return None

    # API credentials
    api_key = console.input("[bold]API Key:[/bold] ").strip()
    if not api_key:
        console.print("[red]API key is required[/red]")
        return None

    api_secret = console.input("[bold]API Secret:[/bold] ").strip()
    if not api_secret:
        console.print("[red]API secret is required[/red]")
        return None

    password = None
    if exchange_id in EXCHANGES_WITH_PASSWORD:
        password = console.input(f"[bold]{display_name} Passphrase:[/bold] ").strip()
        if not password:
            console.print(f"[red]{display_name} requires a passphrase[/red]")
            return None

    # Sandbox
    sandbox_input = console.input("[bold]Use sandbox/testnet? (y/N):[/bold] ").strip().lower()
    sandbox = sandbox_input in ("y", "yes")

    # Generate UUID
    exchange_uuid = str(uuid.uuid4())

    config = ExchangeConfig(
        id=exchange_uuid,
        exchange_name=exchange_id,
        label=label,
        api_key=api_key,
        api_secret=api_secret,
        password=password,
        sandbox=sandbox,
    )
    config.save()

    console.print(f'\n[green]✓[/green] Exchange "{label}" saved to '
                  f'~/.riskmanaged/exchanges/{label}.yaml')
    console.print(f"  [dim]ID: {exchange_uuid}[/dim]")

    if sandbox:
        console.print("  [yellow]Sandbox mode enabled[/yellow]")

    console.print("\n[dim]Note: Restart the gateway to register this exchange "
                  "with riskmanaged.io[/dim]")

    return config


def remove_exchange(label: str) -> bool:
    """Remove an exchange config by label.

    Returns True if removed, False if not found.
    """
    exchanges = load_all_exchanges()
    target = next((e for e in exchanges if e.label == label), None)

    if target is None:
        console.print(f'[red]Exchange "{label}" not found[/red]')
        return False

    confirm = console.input(
        f'[yellow]⚠[/yellow]  Remove exchange "{label}" ({target.exchange_name})? '
        f"This only removes the local config.\n"
        f"  Confirm (y/N): "
    ).strip().lower()

    if confirm not in ("y", "yes"):
        console.print("[dim]Cancelled[/dim]")
        return False

    target.delete()
    console.print(f'[green]✓[/green] Removed "{label}"')
    return True


def list_exchanges():
    """Display all configured exchanges in a table."""
    exchanges = load_all_exchanges()

    if not exchanges:
        console.print("[dim]No exchanges configured. Run:[/dim]")
        console.print("  riskmanaged-gateway add-exchange")
        return

    table = Table(title="Configured Exchanges", show_header=True, header_style="bold cyan")
    table.add_column("Label", style="bold")
    table.add_column("Exchange")
    table.add_column("Sandbox")
    table.add_column("ID", style="dim")

    for ex in exchanges:
        sandbox_str = "[yellow]Yes[/yellow]" if ex.sandbox else "No"
        table.add_row(
            ex.label,
            ex.exchange_name.capitalize(),
            sandbox_str,
            ex.id[:8] + "...",
        )

    console.print(table)
