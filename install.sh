#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# RiskManaged Gateway – universal installer
#
# Works on macOS, Linux, and WSL.  Requires only Python ≥ 3.11.
# Tries, in order: uv, pipx, pip / pip3, python3 -m pip, and finally
# bootstraps pip via ensurepip as a last resort.
#
# Usage: curl -sSL https://riskmanaged.io/gateway/install.sh | bash
# ---------------------------------------------------------------------------
set -euo pipefail

REPO="https://github.com/riskmanaged/riskmanaged-gateway.git"
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=11

# ── colours (disabled when stdout is not a tty) ──────────────────────────
if [ -t 1 ]; then
  BOLD="\033[1m"  GREEN="\033[32m"  YELLOW="\033[33m"  RED="\033[31m"  CYAN="\033[36m"  RESET="\033[0m"
else
  BOLD=""  GREEN=""  YELLOW=""  RED=""  CYAN=""  RESET=""
fi

info()  { printf "${BOLD}${GREEN}▸${RESET} %s\n" "$*"; }
warn()  { printf "${BOLD}${YELLOW}⚠${RESET} %s\n" "$*"; }
error() { printf "${BOLD}${RED}✖${RESET} %s\n" "$*" >&2; }
die()   { error "$*"; exit 1; }

# ── locate a usable Python ≥ 3.11 ───────────────────────────────────────
find_python() {
  for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      local ver
      ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
      local major minor
      major=${ver%%.*}
      minor=${ver##*.}
      if [ "$major" -ge "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]; then
        PYTHON=$(command -v "$cmd")
        return 0
      fi
    fi
  done
  return 1
}

# ── install via the best available tool ──────────────────────────────────
install_package() {
  # 1. uv – modern, fast, no venv needed
  if command -v uv >/dev/null 2>&1; then
    info "Installing with uv …"
    uv tool install "riskmanaged-gateway @ git+${REPO}"
    return 0
  fi

  # 2. pipx – isolated environments, recommended for CLI tools
  if command -v pipx >/dev/null 2>&1; then
    info "Installing with pipx …"
    pipx install "git+${REPO}"
    return 0
  fi

  # 3. pip / pip3 binary
  for pip_cmd in pip3 pip; do
    if command -v "$pip_cmd" >/dev/null 2>&1; then
      # Verify this pip belongs to a Python ≥ 3.11
      local pip_py_ver
      pip_py_ver=$("$pip_cmd" --version 2>/dev/null | grep -oE 'python [0-9]+\.[0-9]+' | head -1 | awk '{print $2}') || true
      if [ -n "$pip_py_ver" ]; then
        local major minor
        major=${pip_py_ver%%.*}
        minor=${pip_py_ver##*.}
        if [ "$major" -ge "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]; then
          info "Installing with $pip_cmd …"
          "$pip_cmd" install --user "git+${REPO}"
          return 0
        fi
      fi
    fi
  done

  # 4. python3 -m pip
  if [ -n "${PYTHON:-}" ] && "$PYTHON" -m pip --version >/dev/null 2>&1; then
    info "Installing with $PYTHON -m pip …"
    "$PYTHON" -m pip install --user "git+${REPO}"
    return 0
  fi

  # 5. Bootstrap pip via ensurepip, then install
  if [ -n "${PYTHON:-}" ]; then
    warn "pip not found – bootstrapping via ensurepip …"
    "$PYTHON" -m ensurepip --upgrade 2>/dev/null || die "ensurepip failed. Please install pip manually: https://pip.pypa.io/en/stable/installation/"
    "$PYTHON" -m pip install --user "git+${REPO}"
    return 0
  fi

  return 1
}

# ── main ─────────────────────────────────────────────────────────────────
main() {
  echo ""
  printf "${BOLD}${CYAN}============================================================${RESET}\n"
  printf "${BOLD}${CYAN}  RiskManaged Gateway — Installer${RESET}\n"
  printf "${BOLD}${CYAN}============================================================${RESET}\n"
  echo ""

  # Ensure we have Python
  if ! find_python; then
    die "Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} is required but was not found.\n   Install it from https://python.org or via your system package manager."
  fi
  info "Found Python: $PYTHON ($($PYTHON --version 2>&1))"

  # Install
  if ! install_package; then
    die "Could not find a suitable package installer (uv, pipx, pip, or ensurepip).\n   Install one of them and re-run this script."
  fi

  echo ""
  printf "${BOLD}${GREEN}✅ riskmanaged-gateway installed successfully!${RESET}\n"
  echo ""
  echo "Next steps:"
  echo "  1. Run initial setup:    riskmanaged-gateway bootstrap"
  echo "  2. Add an exchange:      riskmanaged-gateway add-exchange"
  echo "  3. Start the gateway:    riskmanaged-gateway"
  echo ""
  echo "Other commands:"
  echo "  riskmanaged-gateway list-exchanges   List configured exchanges"
  echo "  riskmanaged-gateway status           Show connection status"
  echo ""
}

main "$@"
