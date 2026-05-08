# RiskManaged Gateway

Connect your exchange to the [riskmanaged.io](https://riskmanaged.io) platform.

The gateway runs on your machine (VPS, home server, etc.) and acts as a secure bridge between the RiskManaged platform and your exchange API keys. **Your API keys never leave your machine.**

## Quick Install

```bash
curl -sSL https://riskmanaged.io/gateway/install.sh | bash
```

## Manual Install

```bash
# Clone the repository
git clone https://github.com/riskmanaged/riskmanaged-gateway.git
cd riskmanaged-gateway

# Install (requires Python 3.11+)
pip install -e .

# Run first-time setup
riskmanaged-gateway bootstrap
```

## Usage

```bash
# Start the gateway
riskmanaged-gateway

# Add an exchange
riskmanaged-gateway add-exchange

# List configured exchanges
riskmanaged-gateway list-exchanges

# Remove an exchange
riskmanaged-gateway remove-exchange <label>

# Check status
riskmanaged-gateway status
```

## Supported Exchanges (23)

| Exchange | CCXT ID | Auth Type |
|----------|---------|-----------|
| Binance | `binance` | Key + Secret |
| Bybit | `bybit` | Key + Secret |
| KuCoin | `kucoin` | Key + Secret + Passphrase |
| Kraken | `kraken` | Key + Secret |
| Coinbase | `coinbase` | Key + Secret |
| Bitvavo | `bitvavo` | Key + Secret |
| OKX | `okx` | Key + Secret + Passphrase |
| Crypto.com | `cryptocom` | Key + Secret |
| MEXC | `mexc` | Key + Secret |
| BitMEX | `bitmex` | Key + Secret |
| HyperLiquid | `hyperliquid` | Wallet (address + privateKey) |
| Gate.io | `gate` | Key + Secret |
| Bitget | `bitget` | Key + Secret + Passphrase |
| HTX | `htx` | Key + Secret |
| Phemex | `phemex` | Key + Secret |
| Bitfinex | `bitfinex` | Key + Secret |
| Gemini | `gemini` | Key + Secret |
| WhiteBIT | `whitebit` | Key + Secret |
| Poloniex | `poloniex` | Key + Secret |
| WOO X | `woo` | Key + Secret |
| LBank | `lbank` | Key + Secret |
| Deribit | `deribit` | Key + Secret |
| AscendEX | `ascendex` | Key + Secret |

## How It Works

```
┌─────────────────────┐     WebSocket     ┌──────────────────────┐
│  Your Machine        │◄───────────────►│  riskmanaged.io       │
│                      │   (RPC only)     │                       │
│  riskmanaged-gateway │                  │  Strategy Engine      │
│  ├── binance-main    │                  │  Position Manager     │
│  ├── bybit-trading   │                  │  Signal Processing    │
│  ├── gate-spot       │                  │  Risk Guard           │
│  └── bitget-deriv    │                  │                       │
│                      │                  │                       │
│  Exchange API Keys   │                  │  No API keys stored   │
│  (stored locally)    │                  │  (proxy mode only)    │
└─────────────────────┘                  └──────────────────────┘
```

1. You configure exchange API keys locally (stored in `~/.riskmanaged/`)
2. The gateway connects to the platform via WebSocket
3. When a trading signal fires, the platform sends CCXT RPC calls through the gateway
4. The gateway executes trades on your exchange and returns the result
5. Your API keys **never leave your machine**

## Configuration

All configuration is stored in `~/.riskmanaged/`:

```
~/.riskmanaged/
├── config.yaml                    # API key, bridge URL
└── exchanges/
    ├── binance-main.yaml          # One file per exchange
    ├── binance-subaccount-a.yaml
    ├── gate-spot.yaml
    └── bitget-trading.yaml
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RISKMANAGED_HOME` | `~/.riskmanaged` | Config directory |

## Running as a Service

During `bootstrap`, you'll be asked if you want to install the gateway as a systemd service. You can also do it manually:

```bash
# Copy the service file
cp riskmanaged-gateway.service ~/.config/systemd/user/

# Enable and start
systemctl --user daemon-reload
systemctl --user enable --now riskmanaged-gateway

# Check status
systemctl --user status riskmanaged-gateway

# View logs
journalctl --user -u riskmanaged-gateway -f
```

## Security

- API keys are stored as plaintext YAML files with `600` permissions (owner-only)
- The `~/.riskmanaged/` directory is set to `700` permissions
- API keys are **never** transmitted to the platform — only trade results
- The WebSocket connection is authenticated using your riskmanaged.io API token

## Requirements

- Python 3.11+
- Internet connection (for WebSocket to bridge)
- Exchange API keys with trading permissions

## License

MIT

