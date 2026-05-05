#!/usr/bin/env bash
# RiskManaged Gateway — One-line installer
# Usage: curl -sSL https://riskmanaged.io/gateway/install.sh | bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  RiskManaged Gateway — Installer${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

# 1. Check Python
echo -e "${YELLOW}[1/4]${NC} Checking Python..."
PYTHON=""
for cmd in python3.12 python3.11 python3; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$cmd"
            echo -e "  ${GREEN}✓${NC} Found $cmd ($version)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "  ${YELLOW}!${NC} Python 3.11+ not found — attempting install via uv..."
    if ! command -v uv &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    uv python install 3.11
    PYTHON="python3.11"
    echo -e "  ${GREEN}✓${NC} Python 3.11 installed via uv"
fi

# 2. Clone or update repo
echo -e "${YELLOW}[2/4]${NC} Setting up gateway..."
INSTALL_DIR="${GATEWAY_DIR:-$HOME/riskmanaged-gateway}"

if [ -d "$INSTALL_DIR" ]; then
    echo "  Directory exists: $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || echo "  (not a git repo or no remote)"
else
    echo "  Cloning to: $INSTALL_DIR"
    git clone https://github.com/riskmanaged/riskmanaged-gateway.git "$INSTALL_DIR" 2>/dev/null || {
        echo -e "  ${YELLOW}!${NC} Git clone failed — creating from local"
        mkdir -p "$INSTALL_DIR"
    }
    cd "$INSTALL_DIR"
fi

# 3. Install dependencies
echo -e "${YELLOW}[3/4]${NC} Installing Python dependencies..."
if command -v uv &>/dev/null; then
    uv pip install -e . 2>/dev/null || uv pip install -e .
    echo -e "  ${GREEN}✓${NC} Installed via uv"
else
    $PYTHON -m pip install -e . --quiet
    echo -e "  ${GREEN}✓${NC} Installed via pip"
fi

# 4. Bootstrap
echo -e "${YELLOW}[4/4]${NC} Running setup..."
echo ""
riskmanaged-gateway bootstrap

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "  ${GREEN}Installation complete!${NC}"
echo ""
echo "  Commands:"
echo -e "    ${BOLD}riskmanaged-gateway${NC}               Start the gateway"
echo -e "    ${BOLD}riskmanaged-gateway bootstrap${NC}     Re-run setup"
echo -e "    ${BOLD}riskmanaged-gateway add-exchange${NC}  Add an exchange"
echo -e "    ${BOLD}riskmanaged-gateway status${NC}        Show status"
echo -e "${CYAN}============================================================${NC}"
echo ""
