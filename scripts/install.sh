#!/usr/bin/env bash
# LurkKit — systemd install script
# Usage: sudo bash scripts/install.sh
#        sudo bash scripts/install.sh --uninstall
set -euo pipefail

INSTALL_DIR="/opt/lurkkit"
CONFIG_DIR="/etc/lurkkit"
SERVICE_FILE="/etc/systemd/system/lurkkit.service"
LOG_DIR="/var/log/lurkkit"
SERVICE_USER="lurkkit"

RED='\033[91m'; GREEN='\033[92m'; CYAN='\033[96m'; YELLOW='\033[93m'; RESET='\033[0m'; BOLD='\033[1m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || error "Run as root: sudo bash scripts/install.sh"

if [[ "${1:-}" == "--uninstall" ]]; then
    systemctl stop lurkkit 2>/dev/null || true
    systemctl disable lurkkit 2>/dev/null || true
    rm -f "$SERVICE_FILE"; systemctl daemon-reload
    rm -rf "$INSTALL_DIR"; userdel -r "$SERVICE_USER" 2>/dev/null || true
    success "LurkKit uninstalled."; exit 0
fi

info "Installing LurkKit..."
pip3 install lurkkit --break-system-packages 2>/dev/null || pip3 install lurkkit
id "$SERVICE_USER" &>/dev/null || useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR"

[[ -f "$CONFIG_DIR/lurkkit.yaml" ]] || lurkkit --init --config "$CONFIG_DIR/lurkkit.yaml" 2>/dev/null || true
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$LOG_DIR"

LURKKIT_BIN=$(which lurkkit 2>/dev/null || echo "python3 -m lurkkit")
cat > "$SERVICE_FILE" << SVCEOF
[Unit]
Description=LurkKit - Lightweight Host Monitoring Agent
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
ExecStart=$LURKKIT_BIN --config $CONFIG_DIR/lurkkit.yaml
Restart=on-failure
RestartSec=10
MemoryLimit=128M
CPUQuota=10%
NoNewPrivileges=true
StandardOutput=journal
SyslogIdentifier=lurkkit

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable lurkkit
systemctl start lurkkit
success "LurkKit installed and running!"
echo -e "  Config : ${BOLD}$CONFIG_DIR/lurkkit.yaml${RESET}"
echo -e "  Logs   : ${BOLD}journalctl -u lurkkit -f${RESET}"
