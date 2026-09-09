#!/usr/bin/env bash
# ==============================================================================
# MisLTy: Clean Uninstaller
# Purrfect Software Limited (PSL)
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}   MisLTy Clean System Uninstaller                    ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This uninstaller requires root privileges.${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

echo -e "➔ Removing installed binaries and symlinks..."
rm -f /usr/local/bin/mislty /usr/local/bin/misltyd /usr/libexec/mislty-net-helper

echo -e "➔ Removing udev rules and Polkit policies..."
rm -f /etc/udev/rules.d/99-ufi-permissions.rules
rm -f /usr/share/polkit-1/actions/org.mislty.policy
rm -f /etc/polkit-1/rules.d/49-mislty.rules

echo -e "➔ Removing systemd user unit..."
rm -f /etc/systemd/user/misltyd.service

echo -e "➔ Removing application directory /opt/mislty..."
rm -rf /opt/mislty

if command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload-rules || true
    udevadm trigger || true
fi

echo -e "${GREEN}${BOLD}✔ MisLTy successfully removed from system.${NC}"
