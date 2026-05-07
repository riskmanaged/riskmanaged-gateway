"""Wallet Manager — generate API wallets for wallet-based exchanges.

Provides guided wallet creation for exchanges that use wallet-based auth
(e.g. HyperLiquid API wallets). Similar to the Bittensor gateway's
create-wallet flow.
"""

import uuid

from rich.console import Console

from gateway.config import ExchangeConfig
from gateway.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def create_hyperliquid_wallet():
    """Interactive HyperLiquid API wallet creation flow.

    Generates a new EVM keypair (agent wallet) that can be approved on
    HyperLiquid for trading. The agent wallet cannot withdraw funds —
    only place/cancel orders.

    Requires: eth_account (pip install eth-account)
    """
    console.print("\n[bold cyan]" + "=" * 60 + "[/bold cyan]")
    console.print("[bold cyan]  HyperLiquid — API Wallet Generator[/bold cyan]")
    console.print("[bold cyan]" + "=" * 60 + "[/bold cyan]\n")

    console.print("  This will generate a new EVM keypair for use as a")
    console.print("  HyperLiquid API Wallet (agent wallet).\n")

    console.print("  [bold yellow]⚠ Security Notes:[/bold yellow]")
    console.print("    • API wallets can ONLY trade — they cannot withdraw funds")
    console.print("    • Never share your private key with anyone")
    console.print("    • Store your private key securely (password manager, etc.)")
    console.print("    • You must approve this wallet on HyperLiquid before use\n")

    proceed = console.input("[bold]Generate a new API wallet? (Y/n):[/bold] ").strip().lower()
    if proceed in ("n", "no"):
        console.print("[dim]Cancelled[/dim]")
        return

    try:
        from eth_account import Account
    except ImportError:
        console.print("[red]Error: eth_account package is required.[/red]")
        console.print("[dim]Install it with: pip install eth-account[/dim]")
        return

    # Generate keypair
    account = Account.create()
    wallet_address = account.address
    private_key = account.key.hex()

    # Ensure 0x prefix on private key
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    console.print("\n[bold green]✓ Wallet Generated[/bold green]\n")
    console.print(f"  [bold]Wallet Address:[/bold]  {wallet_address}")
    console.print(f"  [bold]Private Key:[/bold]     {private_key}")

    console.print("\n  [bold yellow]Next Steps:[/bold yellow]")
    console.print("  1. Go to [link=https://app.hyperliquid.xyz]app.hyperliquid.xyz[/link]")
    console.print("  2. Navigate to [bold]API[/bold] section")
    console.print("  3. [bold]Approve[/bold] this wallet address as an API Wallet")
    console.print(f"     (paste: {wallet_address})")
    console.print("  4. Fund your main account if you haven't already")
    console.print("  5. The API wallet will then be able to trade on your behalf\n")

    console.print("[bold yellow]⚠ SAVE YOUR PRIVATE KEY NOW — it will not be shown again[/bold yellow]\n")

    # Offer to save as exchange config
    save = console.input("[bold]Save as a gateway exchange config? (Y/n):[/bold] ").strip().lower()
    if save in ("n", "no"):
        console.print("[dim]Wallet generated but not saved to gateway config[/dim]")
        return

    label = console.input("[bold]Label (e.g. hyperliquid-main):[/bold] ").strip()
    if not label:
        label = "hyperliquid"

    sandbox = console.input("[bold]Use testnet? (y/N):[/bold] ").strip().lower() in ("y", "yes")

    config = ExchangeConfig(
        id=str(uuid.uuid4()),
        exchange_name="hyperliquid",
        label=label,
        api_key=wallet_address,
        api_secret=private_key,
        wallet_address=wallet_address,
        sandbox=sandbox,
    )
    config.save()

    console.print(f"\n[green]✓[/green] Exchange config saved: {label}")
    console.print(f"  [dim]Config file: ~/.riskmanaged/exchanges/{label}.yaml[/dim]\n")
