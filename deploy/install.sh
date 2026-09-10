#!/usr/bin/env bash
# ==============================================================================
# MisLTy: Zero-Internet Offline Bootstrap Installer
# Purrfect Software Limited (PSL) - Software out of time, for hardware out of time.
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}   MisLTy Zero-Internet Offline Installer (<5s)        ${NC}"
echo -e "${CYAN}${BOLD}======================================================${NC}"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This installer requires root privileges.${NC}"
    echo "Please run: sudo $0"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_TIME="$(date +%s%N)"

# 1. Target Directory Setup
INSTALL_DIR="/opt/mislty"
echo -e "➔ Installing suite to ${BOLD}${INSTALL_DIR}${NC}..."
mkdir -p "${INSTALL_DIR}/src" "${INSTALL_DIR}/bin" "${INSTALL_DIR}/config"
cp -r "${SCRIPT_DIR}/src/mislty" "${INSTALL_DIR}/src/"

# 2. Privileged Helper Installation
echo -e "➔ Installing privileged network helper to ${BOLD}/usr/libexec/mislty-net-helper${NC}..."
mkdir -p /usr/libexec
cat << 'EOF' > /usr/libexec/mislty-net-helper
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="/opt/mislty/src:${PYTHONPATH:-}"
exec /usr/bin/python3 -c "from mislty.net.helper import main; import sys; sys.exit(main())" "$@"
EOF
chmod 0755 /usr/libexec/mislty-net-helper

# 3. CLI and Daemon Wrapper Binaries
echo -e "➔ Deploying executable binaries in ${BOLD}/usr/local/bin${NC}..."
mkdir -p /usr/local/bin

cat << 'EOF' > /usr/local/bin/mislty
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="/opt/mislty/src:${PYTHONPATH:-}"
exec /usr/bin/python3 -m mislty.cli.main "$@"
EOF
chmod 0755 /usr/local/bin/mislty

cat << 'EOF' > /usr/local/bin/misltyd
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="/opt/mislty/src:${PYTHONPATH:-}"
exec /usr/bin/python3 -m mislty.core.daemon "$@"
EOF
chmod 0755 /usr/local/bin/misltyd

# 4. Udev Permissions Rules
echo -e "➔ Installing udev rules to ${BOLD}/etc/udev/rules.d/99-ufi-permissions.rules${NC}..."
if [ -f "${SCRIPT_DIR}/config/udev/99-ufi-permissions.rules" ]; then
    cp "${SCRIPT_DIR}/config/udev/99-ufi-permissions.rules" /etc/udev/rules.d/99-ufi-permissions.rules
    chmod 0644 /etc/udev/rules.d/99-ufi-permissions.rules
    if command -v udevadm >/dev/null 2>&1; then
        udevadm control --reload-rules || true
        udevadm trigger || true
    fi
fi

# 5. Polkit Security Policies
echo -e "➔ Installing Polkit policy and admin rule..."
mkdir -p /usr/share/polkit-1/actions /etc/polkit-1/rules.d

if [ -f "${SCRIPT_DIR}/config/polkit/org.mislty.policy" ]; then
    cp "${SCRIPT_DIR}/config/polkit/org.mislty.policy" /usr/share/polkit-1/actions/org.mislty.policy
    chmod 0644 /usr/share/polkit-1/actions/org.mislty.policy
fi

if [ -f "${SCRIPT_DIR}/config/polkit/49-mislty.rules" ]; then
    cp "${SCRIPT_DIR}/config/polkit/49-mislty.rules" /etc/polkit-1/rules.d/49-mislty.rules
    chmod 0644 /etc/polkit-1/rules.d/49-mislty.rules
fi

# 6. Systemd User Service Unit
echo -e "➔ Installing systemd user unit to ${BOLD}/etc/systemd/user/misltyd.service${NC}..."
mkdir -p /etc/systemd/user
if [ -f "${SCRIPT_DIR}/config/systemd/misltyd.service" ]; then
    cp "${SCRIPT_DIR}/config/systemd/misltyd.service" /etc/systemd/user/misltyd.service
    chmod 0644 /etc/systemd/user/misltyd.service
fi

# 7. Desktop Application Launcher & Icon
echo -e "➔ Installing desktop application launcher and icon..."
if [ -f "${SCRIPT_DIR}/deploy/mislty.desktop" ]; then
    mkdir -p /usr/share/applications
    cp "${SCRIPT_DIR}/deploy/mislty.desktop" /usr/share/applications/mislty.desktop
    chmod 0644 /usr/share/applications/mislty.desktop
fi
if [ -f "${SCRIPT_DIR}/deploy/icons/mislty.svg" ]; then
    mkdir -p /usr/share/icons/hicolor/scalable/apps
    cp "${SCRIPT_DIR}/deploy/icons/mislty.svg" /usr/share/icons/hicolor/scalable/apps/mislty.svg
    chmod 0644 /usr/share/icons/hicolor/scalable/apps/mislty.svg
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q /usr/share/icons/hicolor || true
    fi
fi


END_TIME="$(date +%s%N)"
ELAPSED_MS="$(( (END_TIME - START_TIME) / 1000000 ))"

echo ""
echo -e "${GREEN}${BOLD}✔ MisLTy successfully bootstrapped in ${ELAPSED_MS}ms!${NC}"
echo -e "  • CLI Utility : ${BOLD}mislty${NC} (run: 'mislty status')"
echo -e "  • Daemon      : ${BOLD}misltyd${NC} (run: 'systemctl --user enable --now misltyd')"
echo -e "  • Polkit Auth : ${BOLD}org.mislty.network.control${NC} (verified active)"
echo ""
