"""Bootstrap — interactive first-time gateway setup."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from gateway.config import GatewayConfig, get_config_dir
from gateway.exchange_manager import add_exchange_interactive
from gateway.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

# Path to the systemd unit template shipped with the package
_SERVICE_TEMPLATE = Path(__file__).resolve().parent.parent / "riskmanaged-gateway.service"


def run_bootstrap():
    """Interactive first-time setup for the gateway."""

    console.print("\n[bold cyan]" + "=" * 60 + "[/bold cyan]")
    console.print("[bold cyan]  RiskManaged Gateway — Setup[/bold cyan]")
    console.print("[bold cyan]" + "=" * 60 + "[/bold cyan]\n")

    config_dir = get_config_dir()

    # ── Step 1: Config directory ──────────────────────────────────────────
    console.print("[bold yellow][1/3][/bold yellow] Setting up config directory...")

    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "exchanges").mkdir(parents=True, exist_ok=True)

    # Secure permissions
    try:
        config_dir.chmod(0o700)
    except OSError:
        pass

    console.print(f"  [green]✓[/green] Directory ready: {config_dir}\n")

    # ── Step 2: API Key ───────────────────────────────────────────────────
    console.print("[bold yellow][2/3][/bold yellow] RiskManaged.io API Key")

    existing_config = GatewayConfig.load()
    if existing_config.api_key:
        console.print(f"  [dim]Existing key found: {existing_config.api_key[:8]}...[/dim]")
        update = console.input("  [bold]Update API key? (y/N):[/bold] ").strip().lower()
        if update not in ("y", "yes"):
            console.print("  [dim]Keeping existing key[/dim]\n")
        else:
            api_key = console.input("  [bold]Enter your riskmanaged.io API key:[/bold] ").strip()
            if api_key:
                existing_config.api_key = api_key
                existing_config.save()
                console.print("  [green]✓[/green] API key saved\n")
            else:
                console.print("  [red]No key entered, keeping existing[/red]\n")
    else:
        api_key = console.input("  [bold]Enter your riskmanaged.io API key:[/bold] ").strip()
        if not api_key:
            console.print("  [red]API key is required to connect to riskmanaged.io[/red]")
            console.print("  [dim]Generate one at: https://riskmanaged.io/profile → API Keys[/dim]")
            return
        existing_config.api_key = api_key
        existing_config.save()
        console.print("  [green]✓[/green] API key saved\n")

    # ── Step 3: Exchange Configuration ────────────────────────────────────
    console.print("[bold yellow][3/3][/bold yellow] Exchange Configuration")

    add_now = console.input("  [bold]Configure an exchange now? (Y/n):[/bold] ").strip().lower()
    if add_now not in ("n", "no"):
        add_exchange_interactive()

        # Offer to add more
        while True:
            more = console.input("\n  [bold]Add another exchange? (y/N):[/bold] ").strip().lower()
            if more not in ("y", "yes"):
                break
            add_exchange_interactive()

    # ── Service Installation ──────────────────────────────────────────────
    console.print()
    _offer_service_install()

    # ── Done ──────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]" + "=" * 60 + "[/bold cyan]")
    console.print("[bold green]  Setup complete![/bold green]")
    console.print()
    console.print("  Start the gateway:")
    console.print("    [bold]riskmanaged-gateway[/bold]")
    console.print()
    console.print("  Manage exchanges:")
    console.print("    [bold]riskmanaged-gateway add-exchange[/bold]")
    console.print("    [bold]riskmanaged-gateway list-exchanges[/bold]")
    console.print("[bold cyan]" + "=" * 60 + "[/bold cyan]\n")


def _offer_service_install():
    """Ask user if they want to install as a systemd service."""
    # Only offer on Linux with systemd
    if sys.platform != "linux" or not shutil.which("systemctl"):
        return

    install = console.input(
        "  [bold]Start the gateway as a systemd service? (y/N):[/bold] "
    ).strip().lower()

    if install not in ("y", "yes"):
        return

    service_dest = Path.home() / ".config" / "systemd" / "user" / "riskmanaged-gateway.service"
    service_dest.parent.mkdir(parents=True, exist_ok=True)

    # Find the gateway executable
    gateway_bin = shutil.which("riskmanaged-gateway") or f"{sys.executable} -m gateway"

    service_content = f"""[Unit]
Description=RiskManaged Gateway
After=network-online.target
Wants=network-online.target

[Service]
ExecStart={gateway_bin}
Restart=always
RestartSec=5
Environment=RISKMANAGED_HOME={get_config_dir()}

[Install]
WantedBy=default.target
"""

    try:
        service_dest.write_text(service_content)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", "riskmanaged-gateway"],
            check=True, capture_output=True,
        )
        console.print("  [green]✓[/green] Service installed and started")
        console.print(f"  [dim]Service file: {service_dest}[/dim]")
        console.print("  [dim]Check status: systemctl --user status riskmanaged-gateway[/dim]")
    except Exception as e:
        console.print(f"  [red]Service installation failed: {e}[/red]")
        console.print("  [dim]You can start the gateway manually: riskmanaged-gateway[/dim]")
